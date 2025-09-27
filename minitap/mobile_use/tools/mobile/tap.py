from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from openai import BaseModel

from minitap.mobile_use.constants import EXECUTOR_MESSAGES_KEY
from minitap.mobile_use.context import MobileUseContext
from minitap.mobile_use.controllers.mobile_command_controller import (
    CoordinatesSelectorRequest,
    IdSelectorRequest,
    SelectorRequestWithCoordinates,
    TextSelectorRequest,
    get_screen_data,
)
from minitap.mobile_use.controllers.mobile_command_controller import tap as tap_controller
from minitap.mobile_use.graph.state import State
from minitap.mobile_use.tools.tool_wrapper import ToolWrapper
from minitap.mobile_use.tools.types import Target
from minitap.mobile_use.tools.utils import find_element_by_text
from minitap.mobile_use.utils.logger import get_logger
from minitap.mobile_use.utils.ui_hierarchy import (
    ElementBounds,
    find_element_by_resource_id,
    get_bounds_for_element,
)

logger = get_logger(__name__)


class TapOutput(BaseModel):
    error: dict | None = None
    selector_info: str | None = None


def _tap_by_coordinates(ctx: MobileUseContext, bounds: ElementBounds) -> TapOutput:
    assert ctx.adb_client is not None

    error: dict | None = None
    selector_info = f"coordinates='{bounds}'"

    try:
        center = bounds.get_center()
        logger.info(f"Attempting to tap using coordinates: {center.x},{center.y}")
        ctx.adb_client.shell(
            serial=ctx.device.device_id,
            command=f"input tap {center.x} {center.y}",
        )

    except Exception as e:
        logger.warning(f"Exception during tap with coordinates '{bounds}': {e}")
        error = {"error": str(e)}

    return TapOutput(error=error, selector_info=selector_info)


def _tap_by_resource_id_or_text(
    ctx: MobileUseContext,
    state: State,
    resource_id: str | None = None,
    text: str | None = None,
    index: int | None = None,
) -> TapOutput:
    assert ctx.adb_client is not None

    error: dict | None = None
    selector_info: str | None = None

    hierarchy = (
        state.latest_ui_hierarchy
        or get_screen_data(screen_api_client=ctx.screen_api_client).elements
    )

    if resource_id:
        logger.info(f"Attempting to tap using resource_id: '{resource_id}' at index {index}")
        selector_info = f"resource_id='{resource_id}' (index={index})"
        ui_element = find_element_by_resource_id(
            ui_hierarchy=hierarchy,
            resource_id=resource_id,
            index=index,
        )
        if not ui_element:
            error = {
                "error": f"Element with resource_id '{resource_id}' not found",
            }
    elif text:
        logger.info(f"Attempting to tap using text: '{text}' at index {index}")
        selector_info = f"text='{text}' (index={index})"
        ui_element = find_element_by_text(
            ui_hierarchy=hierarchy,
            text=text,
            index=index,
        )
        if not ui_element:
            error = {
                "error": f"Element with text '{text}' not found",
            }
    else:
        msg = "Tap with coordinates failed and no fallback (text/resource_id) provided."
        logger.warning(msg)
        error = {"error": msg}
        ui_element = None

    if not ui_element:
        return TapOutput(error=error, selector_info=selector_info)

    try:
        bounds = get_bounds_for_element(ui_element)
        if bounds:
            center = bounds.get_center()
            ctx.adb_client.shell(
                serial=ctx.device.device_id,
                command=f"input tap {center.x} {center.y}",
            )
            selector_info = f"resource_id='{resource_id}' (index={index}) coordinates='{bounds}'"
        else:
            error = {
                "error": (
                    f"Element bounds not found for resource_id '{resource_id}' or text '{text}'",
                )
            }
    except Exception as e:
        logger.warning(
            f"Exception during tap with resource_id '{resource_id}' or text '{text}': {e}",
        )
        error = {"error": str(e)}

    return TapOutput(error=error, selector_info=selector_info)


def tap_android(
    ctx: MobileUseContext,
    tool_call_id: str,
    state: State,
    agent_thought: str,
    target: Target,
):
    """
    Taps on a UI element identified by the 'target' object.

    The 'target' object allows specifying an element by its resource_id
    (with an optional index), its coordinates, or its text content (with an optional index).
    The tool uses a fallback strategy, trying the locators in that order.
    """
    if not ctx.adb_client:
        raise ValueError("ADB client is not initialized")

    if target.coordinates:
        output = _tap_by_coordinates(
            ctx=ctx,
            bounds=target.coordinates,
        )
    else:
        output = _tap_by_resource_id_or_text(
            ctx=ctx,
            state=state,
            resource_id=target.resource_id,
            text=target.text,
            index=target.resource_id_index,
        )

    has_failed = output.error is not None
    agent_outcome = (
        tap_wrapper.on_failure_fn(output.selector_info or "N/A")
        if has_failed
        else tap_wrapper.on_success_fn(output.selector_info or "N/A")
    )

    tool_message = ToolMessage(
        tool_call_id=tool_call_id,
        content=agent_outcome,
        additional_kwargs={"error": output} if has_failed else {},
        status="error" if has_failed else "success",
    )
    return Command(
        update=state.sanitize_update(
            ctx=ctx,
            update={
                "agents_thoughts": [agent_thought, agent_outcome],
                EXECUTOR_MESSAGES_KEY: [tool_message],
            },
            agent="executor",
        ),
    )


def get_tap_tool(ctx: MobileUseContext):
    @tool
    def tap(
        tool_call_id: Annotated[str, InjectedToolCallId],
        state: Annotated[State, InjectedState],
        agent_thought: str,
        target: Target,
    ):
        """
        Taps on a UI element identified by the 'target' object.

        The 'target' object allows specifying an element by its resource_id
        (with an optional index), its coordinates, or its text content (with an optional index).
        The tool uses a fallback strategy, trying the locators in that order.
        """
        if ctx.adb_client:
            return tap_android(
                ctx=ctx,
                tool_call_id=tool_call_id,
                state=state,
                agent_thought=agent_thought,
                target=target,
            )

        output = {
            "error": "No valid selector provided or all selectors failed."
        }  # Default to failure
        final_selector_info = "N/A"

        # 1. Try with resource_id
        if target.resource_id:
            try:
                selector = IdSelectorRequest(id=target.resource_id)
                logger.info(
                    f"Attempting to tap using resource_id: '{target.resource_id}' "
                    f"at index {target.resource_id_index}"
                )
                result = tap_controller(
                    ctx=ctx, selector_request=selector, index=target.resource_id_index
                )
                if result is None:  # Success
                    output = None
                    final_selector_info = (
                        f"resource_id='{target.resource_id}' (index={target.resource_id_index})"
                    )
                else:
                    logger.warning(
                        f"Tap with resource_id '{target.resource_id}' failed. Error: {result}"
                    )
                    output = result
            except Exception as e:
                logger.warning(f"Exception during tap with resource_id '{target.resource_id}': {e}")
                output = {"error": str(e)}

        # 2. If resource_id failed or wasn't provided, try with coordinates
        if output is not None and target.coordinates:
            try:
                center_point = target.coordinates.get_center()
                selector = SelectorRequestWithCoordinates(
                    coordinates=CoordinatesSelectorRequest(x=center_point.x, y=center_point.y)
                )
                logger.info(
                    f"Attempting to tap using coordinates: {center_point.x},{center_point.y}"
                )
                result = tap_controller(ctx=ctx, selector_request=selector)
                if result is None:  # Success
                    output = None
                    final_selector_info = f"coordinates='{target.coordinates}'"
                else:
                    logger.warning(
                        f"Tap with coordinates '{target.coordinates}' failed. Error: {result}"
                    )
                    output = result
            except Exception as e:
                logger.warning(f"Exception during tap with coordinates '{target.coordinates}': {e}")
                output = {"error": str(e)}

        # 3. If coordinates failed or weren't provided, try with text
        if output is not None and target.text:
            try:
                selector = TextSelectorRequest(text=target.text)
                logger.info(
                    f"Attempting to tap using text: '{target.text}' at index {target.text_index}"
                )
                result = tap_controller(ctx=ctx, selector_request=selector, index=target.text_index)
                if result is None:  # Success
                    output = None
                    final_selector_info = f"text='{target.text}' (index={target.text_index})"
                else:
                    logger.warning(f"Tap with text '{target.text}' failed. Error: {result}")
                    output = result
            except Exception as e:
                logger.warning(f"Exception during tap with text '{target.text}': {e}")
                output = {"error": str(e)}

        has_failed = output is not None
        agent_outcome = (
            tap_wrapper.on_failure_fn(final_selector_info)
            if has_failed
            else tap_wrapper.on_success_fn(final_selector_info)
        )

        tool_message = ToolMessage(
            tool_call_id=tool_call_id,
            content=agent_outcome,
            additional_kwargs={"error": output} if has_failed else {},
            status="error" if has_failed else "success",
        )
        return Command(
            update=state.sanitize_update(
                ctx=ctx,
                update={
                    "agents_thoughts": [agent_thought, agent_outcome],
                    EXECUTOR_MESSAGES_KEY: [tool_message],
                },
                agent="executor",
            ),
        )

    return tap


tap_wrapper = ToolWrapper(
    tool_fn_getter=get_tap_tool,
    on_success_fn=lambda selector_info: f"Tap on element with {selector_info} was successful.",
    on_failure_fn=lambda selector_info: "Failed to tap on element. "
    + f"Last attempt was with {selector_info}.",
)
