from myapi.agent.state import MeetingState
from myapi.agent.llm import LLMService
from myapi.agent.schema import StructuredMeetingAnalysis, NarrativeReport
from myapi.models import MeetingReport, MeetingAnalysis, TranscriptReport, Embedding, Customer, User
from myapi.agent.prompts.loader import load_prompt
from langchain_core.messages import SystemMessage, HumanMessage
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import json
from myapi.email_service.email_service import send_email


llm= LLMService()

AGENT_1_PROMPT = load_prompt("agent_1.md")
AGENT_2_PROMPT = load_prompt("agent_2.md")
AGENT_3_PROMPT = load_prompt("agent_3.md")

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR)
)

template = env.get_template("report_template.html")



def structured_report_node(state: MeetingState):
    print("Agent 1: Generating Structured Report")

    transcript= state['transcript']

    try: 

        messages= [
            SystemMessage(content= AGENT_1_PROMPT),
            HumanMessage(content= transcript),
        ]
        
        structured_report= llm.get_structured(StructuredMeetingAnalysis, messages)
        print(f"Structured Report: {structured_report}")

        return {
            "meeting_analysis": structured_report
        }

    except Exception as e:
        print(f"Agent 1 failed: {e}")

        return {
            "errors": [str(e)]
        }
    
def narrative_report_node(state: MeetingState):
    print("Agent 2: Gererating Narrative Report")

    transcript= state['transcript']

    try:
        messages= [
            SystemMessage(content= AGENT_2_PROMPT),
            HumanMessage(content= transcript),
       ]

        narrative_report= llm.get_structured(schema= NarrativeReport,
                                             messages= messages)
        print(f"Narrative Report: {narrative_report}")

        return {
            "narrative_report": narrative_report
        }

    except Exception as e:
        print(f"Agent 2 failed: {e}")

        return {
            "errors": [str(e)]
        }

def historical_report_node(state: MeetingState):
    print("Agent 3: Gererating Historical Report")

    current_report= state['meeting_analysis']
    

    try:
        previous_meetings = (
            MeetingAnalysis.objects
            .filter(
                customer_id=state["customer_id"],
                organisation_id=state["organisation_id"],
            )
            .exclude(meeting_id=state["meeting_id"])
            .order_by("-created_at")[:4]
        )

        history = [
            meeting.agent_1_report_persistent
            for meeting in previous_meetings
        ]

        
        prompt= json.dumps({
            "current_report": current_report.model_dump(),
            "historical_context": history
        },
        indent= 2,
        )

        messages= [SystemMessage(content= AGENT_3_PROMPT),
                    HumanMessage(content= prompt)]

        historical_report= llm.invoke(messages)

        return {
            "historical_analysis": historical_report.content
        }

    except Exception as e:
        print(f"Agent 3 failed: {e}")

        return {
            "errors": [str(e)]
        }


def merge_report_node(state: MeetingState):

    return {
        "merged_report": {
            "meeting_analysis": state["meeting_analysis"],
            "narrative_report": state["narrative_report"],
            "historical_report": state["historical_analysis"],
        }
    }


def markdown_report_node(state: MeetingState):
    print("Generating Markdown Report")

    analysis = state['meeting_analysis']
    # Converting json to md file as out db column is for text field and gin index works on text not on json

    merged_report = f""" # {analysis.meeting_title}

        ## Executive Summary

            {analysis.summary}

        ## Narrative Report

            {state['narrative_report']}

        ## Action Items

        """

    for item in analysis.action_items:
        merged_report += f"- **Task:** {item.task}\n"
        merged_report += f"  - Owner: {item.owner or 'Not Assigned'}\n"
        merged_report += f"  - Deadline: {item.deadline or 'Not Specified'}\n\n"

    merged_report += "## Key Decisions\n\n"

    for decision in analysis.decisions:
        merged_report += f"- {decision}\n"

    merged_report += "\n## Risks\n\n"

    for risk in analysis.risks:
        merged_report += f"- {risk}\n"

    merged_report += "\n## Opportunities\n\n"

    for opportunity in analysis.opportunities:
        merged_report += f"- {opportunity}\n"

    merged_report += "\n## Open Questions\n\n"

    for question in analysis.open_questions:
        merged_report += f"- {question}\n"

    merged_report += "\n## Resources Mentioned\n\n"

    for resource in analysis.resources_mentioned:
        merged_report += f"- {resource}\n"

    merged_report += "\n## KPIs\n\n"

    for kpi in analysis.kpis:
        merged_report += f"- {kpi}\n"

    merged_report += "\n## Participants\n\n"

    for participant in analysis.participants:
        merged_report += f"- {participant}\n"

    merged_report += "\n## Tags\n\n"

    for tag in analysis.tags:
        merged_report += f"`{tag}` "

    merged_report += f"""

    ## Historical Trends

    {state['historical_analysis']}
        """


    return {
        "markdown_report": merged_report
    }


def make_html_report_node(state: MeetingState):
    "use jinja 2 to bake into html here"

    # Using the merged report here instead of the maekdown report so that i can generate tables and beautiful in html and save the markdown report

    report= state['merged_report']

    try:

        html = template.render(
            report= report
        )

        print(f"Generated HTML ({len(html)} chars)")

        return {
            "html_report": html
        }

    except Exception as e:
        print(f"HTML Rendering Failed: {e}")

        return {
            "errors": [f"HTML Generation: {str(e)}"]
        }
    

def save_to_db_node(state: MeetingState):

    print("Saving Reports")

    try:
        MeetingAnalysis.objects.create(
            meeting_id=state['meeting_id'],
            organisation_id=state['organisation_id'],
            customer_id=state['customer_id'],
            agent_1_report_persistent=state['meeting_analysis'].model_dump()
        )


        TranscriptReport.objects.create(
            meeting_id=state['meeting_id'],
            organisation_id=state['organisation_id'],
            transcript=state['transcript'],
            summary=state['meeting_analysis'].summary,
            merged_final_report=state['markdown_report']
        )


        MeetingReport.objects.create(
            meeting_id=state['meeting_id'],
            organisation_id=state['organisation_id'],
            customer_id=state['customer_id'],
            salesperson_id=state['salesperson_id'],
            html_report=state['html_report']
        )

        return {
            "status": "Saved to DB Successfully"
        }

    except Exception as e:

        return {
            "errors": [str(e)]
        }

def send_report_to_mail(state: MeetingState):

    customer = Customer.objects.get(id=state["customer_id"])

    salesperson = User.objects.get(id=state["salesperson_id"])

    # Email to salesperson
    send_email(
        recipient_email=salesperson.email,
        recipient_name=salesperson.salesperson_name,
        subject="Meeting Report",
        html_content=state["html_report"],
    )

    # Email to customer
    # send_email(
    #     recipient_email=customer.email,
    #     recipient_name=customer.customer_name,
    #     subject="Meeting Summary",
    #     html_content=state["html_report"],
    # )

    return {
        "status": "Emails Sent Successfully"
    }
