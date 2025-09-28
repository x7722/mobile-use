from pathlib import Path

from jinja2 import Template
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from minitap.mobile_use.context import MobileUseContext
from minitap.mobile_use.controllers.mobile_command_controller import (
    take_screenshot as take_screenshot_controller,
)
from minitap.mobile_use.services.llm import get_llm, invoke_llm_with_timeout_message
from minitap.mobile_use.utils.conversations import get_screenshot_message_for_llm
from minitap.mobile_use.utils.logger import get_logger
from minitap.mobile_use.utils.media import compress_base64_jpeg

logger = get_logger(__name__)


async def screen_analyzer(ctx: MobileUseContext, prompt: str):
    logger.info("Starting Screen Analyzer Agent")

    system_message = Template(
        Path(__file__).parent.joinpath("screen_analyzer.md").read_text(encoding="utf-8")
    ).render()

    output = take_screenshot_controller(ctx=ctx)
    compressed_image_base64 = compress_base64_jpeg(output)

    messages: list[BaseMessage] = [
        SystemMessage(content=system_message),
        get_screenshot_message_for_llm(compressed_image_base64),
        HumanMessage(content=prompt),
    ]

    llm = get_llm(ctx=ctx, name="screen_analyzer", is_utils=True, temperature=1)
    response = await invoke_llm_with_timeout_message(llm.ainvoke(messages))
    return response.content
