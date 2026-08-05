from pydantic import BaseModel, Field

class ActionItem(BaseModel):
    task: str = Field(description= "Specefic task or follow-up acttion explicitly assigned during the meeting.")
    owner: str | None = Field(default= None, description="Person responsible for completing the task or the person task is assigned to")
    deadline: str | None = Field(description= "Deadline or due date if explicitly mentioned.")

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
    tags: list[str]= Field(description="Concise business and technical topics discussed during the meeting.")


class NarrativeReport(BaseModel):
    # Dummy field added because some LLMs refuse to call a tool if the schema only has a single string field.
    # Having two fields forces the LLM to output a complex JSON object and prevents the 'Tool choice is required' crash.
    thought_process: str = Field(
        description="A brief 1-sentence thought on how you will structure this narrative."
    )
    discussion_narrative: str = Field(
        description=(
            "A professional business narrative explaining how the discussion "
            "progressed from beginning to end in exactly ONE short paragraph under 100 words."
        )
    )