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
