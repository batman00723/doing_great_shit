from django.test import TestCase
from unittest.mock import patch, MagicMock
from myapi.models import Organisation, Customer, User, Meeting, MeetingAnalysis, TranscriptReport, MeetingReport
from myapi.agent.state import MeetingState
from myapi.agent.nodes import (
    structured_report_node,
    narrative_report_node,
    historical_report_node,
    merge_report_node,
    markdown_report_node,
    make_html_report_node,
    save_to_db_node,
    send_report_to_mail
)
from myapi.agent.schema import StructuredMeetingAnalysis, NarrativeReport, ActionItem
from myapi.services.transcript_processor import process_transcript

class AgentNodesTestCase(TestCase):
    def setUp(self):
        # 1. Set up database mock models required for state
        self.org = Organisation.objects.create(name="Test Org")
        self.customer = Customer.objects.create(customer_name="Test Customer", email="customer@test.com", organisation=self.org)
        self.salesperson = User.objects.create(salesperson_name="Test Sales", email="sales@test.com", organisation=self.org)
        self.meeting = Meeting.objects.create(
            organisation=self.org,
            customer=self.customer,
            salesperson=self.salesperson,
            title="Test Meeting"
        )
        
        # 2. Initial LangGraph State
        self.state: MeetingState = {
            "meeting_id": self.meeting.id,
            "organisation_id": self.org.id,
            "customer_id": self.customer.id,
            "salesperson_id": self.salesperson.id,
            "transcript": "Test transcript",
            "meeting_analysis": None,
            "narrative_report": None,
            "historical_analysis": None,
            "merged_report": None,
            "markdown_report": None,
            "html_report": None,
            "status": "pending",
            "errors": []
        }

        # 3. Mock structured data to prevent burning actual LLM tokens
        self.mock_structured_analysis = StructuredMeetingAnalysis(
            meeting_title="Test Meeting Title",
            summary="Test Summary",
            action_items=[ActionItem(task="Task 1", owner="Owner 1", deadline="Tomorrow")],
            decisions=["Decision 1"],
            risks=["Risk 1"],
            opportunities=["Opportunity 1"],
            open_questions=["Question 1"],
            resources_mentioned=["Resource 1"],
            kpis=["KPI 1"],
            participants=["Participant 1"],
            tags=["Tag 1"]
        )

        self.mock_narrative_report = NarrativeReport(
            narrative="This is a test narrative report",
            thought_process="Thinking..."
        )

    @patch('myapi.agent.nodes.llm')
    def test_structured_report_node(self, mock_llm):
        """Test Agent 1 successfully extracts structured data"""
        mock_llm.get_structured.return_value = self.mock_structured_analysis
        result = structured_report_node(self.state)
        
        self.assertIn("meeting_analysis", result)
        self.assertEqual(result["meeting_analysis"].meeting_title, "Test Meeting Title")

    @patch('myapi.agent.nodes.llm')
    def test_structured_report_node_fallback(self, mock_llm):
        """Test Agent 1 correctly falls back to Cerebras if Groq fails"""
        mock_llm.get_structured.side_effect = Exception("Groq failed")
        
        with patch('myapi.agent.nodes.altllm') as mock_altllm:
            mock_altllm.get_structured.return_value = self.mock_structured_analysis
            result = structured_report_node(self.state)
            
            self.assertIn("meeting_analysis", result)
            self.assertEqual(result["meeting_analysis"].meeting_title, "Test Meeting Title")
            mock_altllm.get_structured.assert_called_once()

    @patch('myapi.agent.nodes.llm')
    def test_narrative_report_node(self, mock_llm):
        """Test Agent 2 successfully extracts narrative data"""
        mock_llm.get_structured.return_value = self.mock_narrative_report
        result = narrative_report_node(self.state)
        
        self.assertIn("narrative_report", result)
        self.assertEqual(result["narrative_report"].narrative, "This is a test narrative report")

    @patch('myapi.agent.nodes.llm')
    def test_historical_report_node_no_history(self, mock_llm):
        """Test Agent 3 correctly bypasses LLM call when no history exists"""
        self.state["meeting_analysis"] = self.mock_structured_analysis
        result = historical_report_node(self.state)
        
        self.assertIn("historical_analysis", result)
        self.assertEqual(result["historical_analysis"], "No historical meetings are available for comparison.")
        mock_llm.invoke.assert_not_called()  # Verifies we saved API costs

    def test_merge_report_node(self):
        """Test data merges correctly for rendering"""
        self.state["meeting_analysis"] = self.mock_structured_analysis
        self.state["narrative_report"] = "Narrative String"
        self.state["historical_analysis"] = "Historical String"
        
        result = merge_report_node(self.state)
        self.assertIn("merged_report", result)
        self.assertEqual(result["merged_report"]["meeting_analysis"], self.mock_structured_analysis)

    def test_markdown_report_node(self):
        """Test Markdown generation formats properly"""
        self.state["meeting_analysis"] = self.mock_structured_analysis
        self.state["narrative_report"] = "Narrative Flow"
        self.state["historical_analysis"] = "Historical Trends"
        
        result = markdown_report_node(self.state)
        self.assertIn("markdown_report", result)
        self.assertIn("Test Meeting Title", result["markdown_report"])
        self.assertIn("Narrative Flow", result["markdown_report"])

    def test_make_html_report_node(self):
        """Test HTML report generates and correctly embeds the SVG"""
        self.state["merged_report"] = {
            "meeting_analysis": self.mock_structured_analysis,
            "narrative_report": "Narrative Flow",
            "historical_report": "Historical Trends"
        }
        
        result = make_html_report_node(self.state)
        self.assertIn("html_report", result)
        self.assertIn("Test Meeting Title", result["html_report"])
        self.assertIn("<svg", result["html_report"]) # Verify inline SVG is there

    def test_save_to_db_node(self):
        """Test database transactional save functionality"""
        self.state["meeting_analysis"] = self.mock_structured_analysis
        self.state["transcript"] = "Test transcript"
        self.state["markdown_report"] = "Markdown content"
        self.state["html_report"] = "<html></html>"
        
        result = save_to_db_node(self.state)
        self.assertEqual(result["status"], "Saved to DB Successfully")
        
        # Verify db records were actually created
        self.assertEqual(MeetingAnalysis.objects.count(), 1)
        self.assertEqual(TranscriptReport.objects.count(), 1)
        self.assertEqual(MeetingReport.objects.count(), 1)

    @patch('myapi.agent.nodes.send_email')
    def test_send_report_to_mail(self, mock_send_email):
        """Test email dispatching"""
        self.state["html_report"] = "<html></html>"
        result = send_report_to_mail(self.state)
        
        self.assertEqual(result["status"], "Emails Sent Successfully")
        mock_send_email.assert_called_once()
        args, kwargs = mock_send_email.call_args
        self.assertEqual(kwargs['recipient_email'], "sales@test.com")


class ProcessorTestCase(TestCase):
    @patch('myapi.services.transcript_processor.meeting_agent')
    def test_process_transcript_success(self, mock_agent):
        """Test entire processing orchestrator on success"""
        org = Organisation.objects.create(name="Test Org")
        Customer.objects.create(customer_name="Test Customer", email="c@test.com", organisation=org)
        User.objects.create(salesperson_name="Test Sales", email="s@test.com", organisation=org)
        
        mock_agent.invoke.return_value = {"status": "success"}
        
        status = process_transcript("Dummy Transcript")
        self.assertEqual(status, "success")
        
        meeting = Meeting.objects.first()
        self.assertEqual(meeting.status, Meeting.Status.COMPLETED)

    @patch('myapi.services.transcript_processor.meeting_agent')
    def test_process_transcript_failure(self, mock_agent):
        """Test entire processing orchestrator gracefully marks DB as FAILED if graph crashes"""
        org = Organisation.objects.create(name="Test Org")
        Customer.objects.create(customer_name="Test Customer", email="c@test.com", organisation=org)
        User.objects.create(salesperson_name="Test Sales", email="s@test.com", organisation=org)
        
        mock_agent.invoke.side_effect = Exception("Fatal Pipeline Error")
        
        with self.assertRaises(Exception):
            process_transcript("Dummy Transcript")
            
        meeting = Meeting.objects.first()
        self.assertEqual(meeting.status, Meeting.Status.FAILED)
