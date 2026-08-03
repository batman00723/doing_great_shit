from pydantic import BaseModel, Field

class ActionItem(BaseModel):
    task: str
    owner: str | None = Field(default= None, description="Person responsible for completing the task or the person task is assigned to")
    deadline: str | None = None

class StructuredMeetingAnalysis(BaseModel):
    meeting_title: str= Field(description="Title for the meeting")
    summary: str= Field(description= "A concise executive summary of the meeting covering objectives, discussion, key outcomes and important context.")
    action_items: list[ActionItem]= Field(description="List of all the action items in the meeting")
    decisions: list[str]= Field(description="List of the Explicit decisions that were finalized during the meeting.")
    risks: list[str]= Field(description="List of all the risks items from the meeting")
    opportunities: list[str]= Field(description="List of all the opportunities in the meeting")
    open_questions: list[str]= Field(description="List of the open questions from the meeting")
    resources_mentioned: list[str]= Field(description="List all the resources mentioned in meeting")
    kpis: list[str]= Field(description= "Metrics, performance indicators, targets or numerical values explicitly mentioned.")
    participants: list[str]= Field(description="Participants who joined meeting")
    tags: list[str]= Field(description="Metrics, performance indicators, targets or numerical values explicitly mentioned.")




class NarrativeReport(BaseModel):
    executive_summary: list[str] = Field(
        description=(
            "A concise executive-level summary of the meeting in bullet points, "
            "highlighting the primary purpose, major discussions, key outcomes, "
            "and overall direction of the meeting."
        )
    )

    discussion_flow: list[str] = Field(
        description=(
            "A chronological sequence of the meeting's discussion in bullet points, "
            "where each bullet represents one major topic or conversation segment "
            "from beginning to end without adding opinions, recommendations, or "
            "information not present in the transcript."
        )
    )