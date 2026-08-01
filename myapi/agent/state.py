from typing import TypedDict, Annotated, Any
from myapi.agent.schema import StructuredMeetingAnalysis
from operator import add

class MeetingState(TypedDict):
    meeting_id: int
    organization_id: int
    customer_id: int
    salesperson_id: int

    transcript: str

    meeting_analysis: StructuredMeetingAnalysis | None # agent 1 report

    narrative_report: str | None # agent 2 report 


    historical_analysis: str | None # Agent 3 report

    

    merged_report: dict[str, Any] | None # after agent 3 to save in db for chatbot

    markdown_report: str | None

    html_report: str | None # html 

    status: str | None

    errors: Annotated[list[str], add]