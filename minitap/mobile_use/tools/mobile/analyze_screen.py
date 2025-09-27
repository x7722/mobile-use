from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from minitap.mobile_use.agents.screen_analyzer.screen_analyzer import screen_analyzer
from minitap.mobile_use.constants import EXECUTOR_MESSAGES_KEY
from minitap.mobile_use.context import MobileUseContext
from minitap.mobile_use.graph.state import State
from minitap.mobile_use.tools.tool_wrapper import ToolWrapper


async def get_analyze_screen_tool(ctx: MobileUseContext):
    @tool
    async def analyze_screen(
        tool_call_id: Annotated[str, InjectedToolCallId],
        state: Annotated[State, InjectedState],
        agent_thought: str,
        prompt: str,
    ):
        """
        Analyzes the current screen using a description prompt.
        """

        agent_outcome = await screen_analyzer(ctx=ctx, prompt=prompt)

        tool_message = ToolMessage(
            tool_call_id=tool_call_id,
            content=agent_outcome,
            status="success",
        )
        updates = {
            "agents_thoughts": [agent_thought, agent_outcome],
            EXECUTOR_MESSAGES_KEY: [tool_message],
        }
        return Command(
            update=state.sanitize_update(
                ctx=ctx,
                update=updates,
                agent="executor",
            ),
        )

    return analyze_screen


analyze_screen_wrapper = ToolWrapper(
    tool_fn_getter=get_analyze_screen_tool,
    on_success_fn=lambda: "Visual context captured successfully."
    + "It is now available for immediate analysis.",
    on_failure_fn=lambda: "Failed to capture visual context.",
)
