import uuid

import yaml
from adbutils import AdbClient
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field
from requests import JSONDecodeError

from minitap.mobile_use.clients.device_hardware_client import DeviceHardwareClient
from minitap.mobile_use.clients.screen_api_client import ScreenApiClient
from minitap.mobile_use.config import initialize_llm_config
from minitap.mobile_use.context import DeviceContext, DevicePlatform, MobileUseContext
from minitap.mobile_use.controllers.types import (
    CoordinatesSelectorRequest,
    IdSelectorRequest,
    IdWithTextSelectorRequest,
    Key,
    ScreenDataResponse,
    SelectorRequest,
    SelectorRequestWithCoordinates,
    SelectorRequestWithPercentages,
    SwipeRequest,
    TapOutput,
    TextSelectorRequest,
    WaitTimeout,
)
from minitap.mobile_use.utils.errors import ControllerErrors
from minitap.mobile_use.utils.logger import get_logger
from minitap.mobile_use.utils.ui_hierarchy import (
    find_element_by_resource_id,
    get_bounds_for_element,
    find_element_by_text,
)

logger = get_logger(__name__)


###### Screen elements retrieval ######


def get_screen_data(screen_api_client: ScreenApiClient):
    response = screen_api_client.get_with_retry("/screen-info")
    return ScreenDataResponse(**response.json())


def take_screenshot(ctx: MobileUseContext):
    return get_screen_data(ctx.screen_api_client).base64


class RunFlowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yaml: str
    dry_run: bool = Field(default=False, alias="dryRun")


def run_flow(ctx: MobileUseContext, flow_steps: list, dry_run: bool = False) -> dict | None:
    """
    Run a flow i.e, a sequence of commands.
    Returns None on success, or the response body of the failed command.
    """
    logger.info(f"Running flow: {flow_steps}")

    for step in flow_steps:
        step_yml = yaml.dump(step)
        payload = RunFlowRequest(yaml=step_yml, dryRun=dry_run).model_dump(by_alias=True)
        response = ctx.hw_bridge_client.post("run-command", json=payload)

        try:
            response_body = response.json()
        except JSONDecodeError:
            response_body = response.text

        if isinstance(response_body, dict):
            response_body = {k: v for k, v in response_body.items() if v is not None}

        if response.status_code >= 300:
            logger.error(f"Tool call failed with status code: {response.status_code}")
            return {"status_code": response.status_code, "body": response_body}

    logger.success("Tool call completed")
    return None


def _android_tap_by_coordinates(
    ctx: MobileUseContext,
    coords: CoordinatesSelectorRequest,
) -> TapOutput:
    assert ctx.adb_client is not None

    error: dict | None = None

    try:
        ctx.adb_client.shell(
            serial=ctx.device.device_id,
            command=f"input tap {coords.x} {coords.y}",
        )

    except Exception as e:
        logger.warning(f"Exception during tap with coordinates '{coords.to_str()}': {e}")
        error = {"error": str(e)}

    return TapOutput(error=error)


def _android_tap_by_resource_id_or_text(
    ctx: MobileUseContext,
    ui_hierarchy: list[dict],
    resource_id: str | None = None,
    text: str | None = None,
    index: int | None = None,
) -> TapOutput:
    assert ctx.adb_client is not None

    error: dict | None = None

    if resource_id:
        ui_element = find_element_by_resource_id(
            ui_hierarchy=ui_hierarchy,
            resource_id=resource_id,
            index=index,
        )
        if not ui_element:
            error = {
                "error": f"Element with resource_id '{resource_id}' not found",
            }
    elif text:
        ui_element = find_element_by_text(
            ui_hierarchy=ui_hierarchy,
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
        return TapOutput(error=error)

    try:
        bounds = get_bounds_for_element(ui_element)
        if bounds:
            center = bounds.get_center()
            ctx.adb_client.shell(
                serial=ctx.device.device_id,
                command=f"input tap {center.x} {center.y}",
            )
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

    return TapOutput(error=error)


def tap_android(
    ctx: MobileUseContext,
    selector: SelectorRequest,
    index: int | None = None,
    ui_hierarchy: list[dict] | None = None,
) -> TapOutput:
    """
    Taps on a UI element identified by the 'target' object.

    The 'target' object allows specifying an element by its resource_id
    (with an optional index), its coordinates, or its text content (with an optional index).
    The tool uses a fallback strategy, trying the locators in that order.
    """
    if not ctx.adb_client:
        raise ValueError("ADB client is not initialized")

    if isinstance(selector, SelectorRequestWithCoordinates):
        output = _android_tap_by_coordinates(
            ctx=ctx,
            coords=selector.coordinates,
        )
    elif isinstance(selector, SelectorRequestWithPercentages):
        x = int(round((ctx.device.device_width * selector.percentages.x_percent) / 100.0))
        y = int(round((ctx.device.device_height * selector.percentages.y_percent) / 100.0))
        output = _android_tap_by_coordinates(
            ctx=ctx,
            coords=CoordinatesSelectorRequest(x=x, y=y),
        )
    else:
        resource_id = None
        text = None

        if isinstance(selector, IdSelectorRequest):
            resource_id = selector.id
        elif isinstance(selector, TextSelectorRequest):
            text = selector.text
        elif isinstance(selector, IdWithTextSelectorRequest):
            resource_id = selector.id
            text = selector.text
        else:
            raise ValueError("Unsupported selector type")

        ui_hierarchy = (
            ui_hierarchy or get_screen_data(screen_api_client=ctx.screen_api_client).elements
        )
        output = _android_tap_by_resource_id_or_text(
            ctx=ctx,
            ui_hierarchy=ui_hierarchy,
            resource_id=resource_id,
            text=text,
            index=index,
        )

    return output


def tap(
    ctx: MobileUseContext,
    selector_request: SelectorRequest,
    dry_run: bool = False,
    index: int | None = None,
    ui_hierarchy: list[dict] | None = None,
):
    """
    Tap on a selector.
    Index is optional and is used when you have multiple views matching the same selector.
    """
    if ctx.adb_client:
        output = tap_android(
            ctx=ctx,
            selector=selector_request,
            index=index,
            ui_hierarchy=ui_hierarchy,
        )
        return output.error if output.error else None

    tap_body = selector_request.to_dict()
    if not tap_body:
        error = "Invalid tap selector request, could not format yaml"
        logger.error(error)
        raise ControllerErrors(error)
    if index:
        tap_body["index"] = index
    flow_input = [{"tapOn": tap_body}]
    return run_flow_with_wait_for_animation_to_end(ctx, flow_input, dry_run=dry_run)


def long_press_on(
    ctx: MobileUseContext,
    selector_request: SelectorRequest,
    dry_run: bool = False,
    index: int | None = None,
):
    long_press_on_body = selector_request.to_dict()
    if not long_press_on_body:
        error = "Invalid longPressOn selector request, could not format yaml"
        logger.error(error)
        raise ControllerErrors(error)
    if index:
        long_press_on_body["index"] = index
    flow_input = [{"longPressOn": long_press_on_body}]
    return run_flow_with_wait_for_animation_to_end(ctx, flow_input, dry_run=dry_run)


def swipe(ctx: MobileUseContext, swipe_request: SwipeRequest, dry_run: bool = False):
    swipe_body = swipe_request.to_dict()
    if not swipe_body:
        error = "Invalid swipe selector request, could not format yaml"
        logger.error(error)
        raise ControllerErrors(error)
    flow_input = [{"swipe": swipe_body}]
    return run_flow_with_wait_for_animation_to_end(ctx, flow_input, dry_run=dry_run)


##### Text related commands #####


def _escape_text_for_adb(text: str) -> str:
    processed = text.replace(" ", "%s")
    processed = processed.replace("'", "'\\''")
    return processed


def input_text(ctx: MobileUseContext, text: str, dry_run: bool = False):
    """
    Inputs text on the device, correctly handling special characters like newlines and tabs.
    Prioritizes direct ADB commands for performance and falls back to Maestro.
    """
    if dry_run:
        logger.info(f"[DRY RUN] Would have inputted complex text: '{text}'")
        return None

    if ctx.adb_client:
        try:
            logger.info(f"Inputting complex text via direct ADB: '{text}'")

            lines = text.split("\n")

            for i, line in enumerate(lines):
                segments = line.split("\t")

                for j, segment in enumerate(segments):
                    if segment:
                        processed_segment = _escape_text_for_adb(segment)
                        ctx.adb_client.shell(
                            command=f"input text '{processed_segment}'", serial=ctx.device.device_id
                        )

                    if j < len(segments) - 1:
                        ctx.adb_client.shell(
                            command="input keyevent 61", serial=ctx.device.device_id
                        )

                if i < len(lines) - 1:
                    ctx.adb_client.shell(command="input keyevent 66", serial=ctx.device.device_id)

            return None

        except Exception as e:
            logger.error(f"Direct ADB input text command failed: {e}")
            return {"status_code": 500, "body": f"ADB command failed: {e}"}

    logger.info("ADB client not configured, falling back to Maestro for input text.")
    return run_flow(ctx, [{"inputText": text}], dry_run=dry_run)


def erase_text(ctx: MobileUseContext, nb_chars: int | None = None, dry_run: bool = False):
    """
    Removes characters from the currently selected textfield (if any)
    Removes 50 characters if nb_chars is not specified.
    """
    adb_client = ctx.adb_client
    if adb_client:
        logger.info("Erasing text with adb")
        chars_to_delete = nb_chars if nb_chars is not None else 50
        for _ in range(chars_to_delete):
            adb_client.shell(command="input keyevent KEYCODE_DEL", serial=ctx.device.device_id)
        return

    if nb_chars is None:
        return run_flow(ctx, ["eraseText"], dry_run=dry_run)
    return run_flow(ctx, [{"eraseText": nb_chars}], dry_run=dry_run)


##### App related commands #####


def launch_app(ctx: MobileUseContext, package_name: str, dry_run: bool = False):
    adb_client = ctx.adb_client
    if adb_client:
        logger.info("Launching app with adb")
        adb_client.shell(
            command=f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1",
            serial=ctx.device.device_id,
        )
        return

    flow_input = [{"launchApp": package_name}]
    return run_flow_with_wait_for_animation_to_end(
        ctx, flow_input, dry_run=dry_run, wait_for_animation_to_end=True
    )


def stop_app(ctx: MobileUseContext, package_name: str | None = None, dry_run: bool = False):
    adb_client = ctx.adb_client
    if adb_client:
        if package_name is None:
            current_focus = str(
                adb_client.shell(
                    command="dumpsys window | grep -E 'mCurrentFocus'",
                    serial=ctx.device.device_id,
                )
            )
            current_app_package_name = current_focus.split(" ")[-1].split("/")[0]
            logger.info(f"Stopping current app `{current_app_package_name}` with adb")
            adb_client.shell(
                command=f"am force-stop {current_app_package_name}",
                serial=ctx.device.device_id,
            )
            return
        logger.info(f"Stopping app `{package_name}` with adb")
        adb_client.shell(command=f"am force-stop {package_name}", serial=ctx.device.device_id)
        return

    if package_name is None:
        flow_input = ["stopApp"]
    else:
        flow_input = [{"stopApp": package_name}]
    return run_flow_with_wait_for_animation_to_end(
        ctx,
        flow_input,
        dry_run=dry_run,
    )


def open_link(ctx: MobileUseContext, url: str, dry_run: bool = False):
    adb_client = ctx.adb_client
    if adb_client:
        logger.info("Opening link with adb")
        adb_client.shell(
            command=f"am start -a android.intent.action.VIEW -d {url}", serial=ctx.device.device_id
        )
        return

    flow_input = [{"openLink": url}]
    return run_flow_with_wait_for_animation_to_end(
        ctx, flow_input, dry_run=dry_run, wait_for_animation_to_end=True
    )


##### Key related commands #####


def back(ctx: MobileUseContext, dry_run: bool = False):
    adb_client = ctx.adb_client
    if adb_client:
        logger.info("Pressing back with adb")
        adb_client.shell(command="input keyevent KEYCODE_BACK", serial=ctx.device.device_id)
        return

    flow_input = ["back"]
    return run_flow_with_wait_for_animation_to_end(
        ctx, flow_input, dry_run=dry_run, wait_for_animation_to_end=True
    )


def press_key(ctx: MobileUseContext, key: Key, dry_run: bool = False):
    adb_client = ctx.adb_client
    if adb_client:
        logger.info(f"Pressing key {key.value} with adb")
        key_mapping = {"Home": "KEYCODE_HOME", "Back": "KEYCODE_BACK", "Enter": "KEYCODE_ENTER"}
        keycode = key_mapping.get(key.value)
        if keycode:
            adb_client.shell(command=f"input keyevent {keycode}", serial=ctx.device.device_id)
            return

    flow_input = [{"pressKey": key.value}]
    return run_flow_with_wait_for_animation_to_end(ctx, flow_input, dry_run=dry_run)


#### Other commands ####


def wait_for_animation_to_end(
    ctx: MobileUseContext, timeout: WaitTimeout | None = None, dry_run: bool = False
):
    if timeout is None:
        return run_flow(ctx, ["waitForAnimationToEnd"], dry_run=dry_run)
    return run_flow(ctx, [{"waitForAnimationToEnd": {"timeout": timeout.value}}], dry_run=dry_run)


def run_flow_with_wait_for_animation_to_end(
    ctx: MobileUseContext,
    base_flow: list,
    dry_run: bool = False,
    wait_for_animation_to_end: bool = False,
):
    if wait_for_animation_to_end:
        base_flow.append({"waitForAnimationToEnd": {"timeout": int(WaitTimeout.SHORT.value)}})
    return run_flow(ctx, base_flow, dry_run=dry_run)


if __name__ == "__main__":
    adb_client = AdbClient(host="192.168.1.6", port=5037)
    ctx = MobileUseContext(
        llm_config=initialize_llm_config(),
        device=DeviceContext(
            host_platform="WINDOWS",
            mobile_platform=DevicePlatform.ANDROID,
            device_id="986066a",
            device_width=1080,
            device_height=1920,
        ),
        hw_bridge_client=DeviceHardwareClient("http://localhost:9999"),
        screen_api_client=ScreenApiClient("http://localhost:9998"),
        adb_client=adb_client,
    )
    screen_data = get_screen_data(ctx.screen_api_client)
    from minitap.mobile_use.graph.state import State

    dummy_state = State(
        messages=[],
        initial_goal="",
        subgoal_plan=[],
        focused_app_info=None,
        device_date="",
        structured_decisions=None,
        latest_ui_hierarchy=None,
        complete_subgoals_by_ids=[],
        executor_messages=[],
        cortex_last_thought="",
        agents_thoughts=[],
    )

    # from minitap.mobile_use.tools.mobile.input_text import get_input_text_tool

    # input_resource_id = "com.google.android.apps.nexuslauncher:id/search_container_hotseat"
    # command_output: Command = get_input_text_tool(ctx=ctx).invoke(
    #     {
    #         "tool_call_id": uuid.uuid4().hex,
    #         "agent_thought": "",
    #         "text_input_resource_id": input_resource_id,
    #         "text": "Hello World",
    #         "state": dummy_state,
    #         "executor_metadata": None,
    #     }
    # )
    # from minitap.mobile_use.tools.mobile.clear_text import get_clear_text_tool

    # input_resource_id = "com.google.android.apps.nexuslauncher:id/input"
    # tool = get_clear_text_tool(ctx=ctx)
    # command_output: Command = tool.invoke(
    #     {
    #         "name": tool.name,
    #         "type": "tool_call",
    #         "id": uuid.uuid4().hex,
    #         "args": {
    #             "agent_thought": "",
    #             "target": {
    #                 "resource_id": None,
    #                 "resource_id_index": None,
    #                 "text": None,
    #                 "text_index": None,
    #                 "coordinates": None,
    #             },
    #             "state": dummy_state,
    #         },
    #     }
    # )
    # from minitap.mobile_use.tools.mobile.launch_app import get_launch_app_tool

    # tool = get_launch_app_tool(ctx=ctx)
    # command_output: Command = asyncio.run(
    #     tool.ainvoke(
    #         {
    #             "name": tool.name,
    #             "type": "tool_call",
    #             "id": uuid.uuid4().hex,
    #             "args": {
    #                 "agent_thought": "",
    #                 "app_name": "google keep",
    #                 "state": dummy_state,
    #             },
    #         }
    #     )
    # )

    # from minitap.mobile_use.tools.mobile.stop_app import get_stop_app_tool

    # tool = get_stop_app_tool(ctx=ctx)
    # command_output: Command = asyncio.run(
    #     tool.ainvoke(
    #         {
    #             "name": tool.name,
    #             "type": "tool_call",
    #             "id": uuid.uuid4().hex,
    #             "args": {
    #                 "agent_thought": "",
    #                 "app_name": "google keep",
    #                 "state": dummy_state,
    #             },
    #         }
    #     )
    # )

    # from minitap.mobile_use.tools.mobile.back import get_back_tool

    # tool = get_back_tool(ctx=ctx)
    # command_output: Command = tool.invoke(
    #     {
    #         "name": tool.name,
    #         "type": "tool_call",
    #         "id": uuid.uuid4().hex,
    #         "args": {
    #             "agent_thought": "",
    #             "state": dummy_state,
    #         },
    #     }
    # )

    # press key
    from minitap.mobile_use.tools.mobile.tap import get_tap_tool

    tool = get_tap_tool(ctx=ctx)
    command_output: Command = tool.invoke(
        {
            "name": tool.name,
            "type": "tool_call",
            "id": uuid.uuid4().hex,
            "args": {
                "agent_thought": "",
                "target": {
                    "text": "Search tab, 3 of 5",
                },
                "state": dummy_state,
            },
        }
    )
    print(command_output)
