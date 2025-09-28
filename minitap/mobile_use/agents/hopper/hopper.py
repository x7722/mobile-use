from pathlib import Path

from jinja2 import Template
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from minitap.mobile_use.context import MobileUseContext
from minitap.mobile_use.services.llm import get_llm, invoke_llm_with_timeout_message


class HopperOutput(BaseModel):
    reason: str | None = Field(description=("Your reason for the action"))
    output: str | None = Field(description="The interesting data extracted from the input data.")


async def hopper(
    ctx: MobileUseContext,
    request: str,
    data: str,
) -> HopperOutput:
    print("Starting Hopper Agent", flush=True)
    system_message = Template(
        Path(__file__).parent.joinpath("hopper.md").read_text(encoding="utf-8")
    ).render()
    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=f"{request}\nHere is the data you must dig:\n{data}"),
    ]

    llm = get_llm(ctx=ctx, name="hopper", is_utils=True, temperature=0)
    structured_llm = llm.with_structured_output(HopperOutput)
    response: HopperOutput = await invoke_llm_with_timeout_message(structured_llm.ainvoke(messages))  # type: ignore
    return response
