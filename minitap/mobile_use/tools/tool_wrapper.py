from collections.abc import Awaitable, Callable

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from minitap.mobile_use.context import MobileUseContext


ToolGetter = Callable[[MobileUseContext], BaseTool | Awaitable[BaseTool]]
CompositeToolsGetter = Callable[[MobileUseContext], list[BaseTool] | Awaitable[list[BaseTool]]]


class ToolWrapper(BaseModel):
    tool_fn_getter: ToolGetter
    on_success_fn: Callable[..., str]
    on_failure_fn: Callable[..., str]


class CompositeToolWrapper(ToolWrapper):
    composite_tools_fn_getter: CompositeToolsGetter
