from pydantic import BaseModel, Field


class CortexOutput(BaseModel):
    decisions: str = Field(..., description="The decisions to be made. A stringified JSON object")
    decisions_reason: str = Field(..., description="The reason for the decisions")
    goals_completion_reason: str = Field(..., description="The reason for the goals completion")
    complete_subgoals_by_ids: list[str] | None = Field(
        [], description="List of subgoal IDs to complete"
    )
