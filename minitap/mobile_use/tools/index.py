import inspect

from langchain_core.tools import BaseTool

from minitap.mobile_use.context import MobileUseContext
from minitap.mobile_use.tools.mobile.back import back_wrapper
from minitap.mobile_use.tools.mobile.clear_text import focus_and_clear_text_wrapper
from minitap.mobile_use.tools.mobile.erase_one_char import erase_one_char_wrapper
from minitap.mobile_use.tools.mobile.focus_and_input_text import focus_and_input_text_wrapper
from minitap.mobile_use.tools.mobile.launch_app import launch_app_wrapper
from minitap.mobile_use.tools.mobile.long_press_on import long_press_on_wrapper
from minitap.mobile_use.tools.mobile.open_link import open_link_wrapper
from minitap.mobile_use.tools.mobile.press_key import press_key_wrapper
from minitap.mobile_use.tools.mobile.stop_app import stop_app_wrapper
from minitap.mobile_use.tools.mobile.swipe import swipe_wrapper
from minitap.mobile_use.tools.mobile.tap import tap_wrapper
from minitap.mobile_use.tools.mobile.wait_for_delay import wait_for_delay_wrapper
from minitap.mobile_use.tools.tool_wrapper import CompositeToolWrapper, ToolWrapper

EXECUTOR_WRAPPERS_TOOLS = [
    back_wrapper,
    open_link_wrapper,
    tap_wrapper,
    long_press_on_wrapper,
    swipe_wrapper,
    # analyze_screen_wrapper,
    focus_and_input_text_wrapper,
    erase_one_char_wrapper,
    launch_app_wrapper,
    stop_app_wrapper,
    focus_and_clear_text_wrapper,
    press_key_wrapper,
    wait_for_delay_wrapper,
    # wait_for_animation_to_end_wrapper,
]


async def get_tools_from_wrappers(
    ctx: "MobileUseContext",
    wrappers: list[ToolWrapper],
) -> list[BaseTool]:
    tools: list[BaseTool] = []
    for wrapper in wrappers:
        if ctx.llm_config.get_agent("executor").provider == "vertexai":
            # The main swipe tool argument structure is not supported by vertexai, we need to split
            # this tool into multiple tools
            if wrapper.tool_fn_getter == swipe_wrapper.tool_fn_getter and isinstance(
                wrapper, CompositeToolWrapper
            ):
                composite_tools = wrapper.composite_tools_fn_getter(ctx)
                if inspect.isawaitable(composite_tools):
                    composite_tools = await composite_tools
                tools.extend(composite_tools)
                continue

        tool = wrapper.tool_fn_getter(ctx)
        if inspect.isawaitable(tool):
            tool = await tool
        tools.append(tool)
    return tools


async def format_tools_list(ctx: MobileUseContext, wrappers: list[ToolWrapper]) -> str:
    tools = await get_tools_from_wrappers(ctx, wrappers)
    return ", ".join([tool.name for tool in tools])
