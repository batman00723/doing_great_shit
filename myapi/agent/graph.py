from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from myapi.agent.state import MeetingState
from myapi.agent.nodes import (
    structured_report_node,
    narrative_report_node,
    historical_report_node,
    merge_report_node,
    markdown_report_node,
    make_html_report_node,
    save_to_db_node,
    send_report_to_mail,
    generate_embeddings_node,
)


def build_graph():
    builder = StateGraph(MeetingState)

    # Register Nodes
    builder.add_node("structured_report", structured_report_node)
    builder.add_node("narrative_report", narrative_report_node)
    builder.add_node("historical_report", historical_report_node)

    builder.add_node("merge_report", merge_report_node)

    builder.add_node("create_md", markdown_report_node)
    builder.add_node("html_report", make_html_report_node)

    builder.add_node("save_to_db", save_to_db_node)
    builder.add_node("send_email", send_report_to_mail)
    builder.add_node("generate_embeddings", generate_embeddings_node)

    # Start (Parallel)
    builder.add_edge(START, "structured_report")
    builder.add_edge(START, "narrative_report")

    # Fan In
    builder.add_edge("structured_report", "historical_report")
    builder.add_edge("narrative_report", "historical_report")

    # Merge
    builder.add_edge("historical_report", "merge_report")

    # Parallel deterministic generation
    builder.add_edge("merge_report", "create_md")
    builder.add_edge("merge_report", "html_report")

    # Fan In
    builder.add_edge("create_md", "save_to_db")
    builder.add_edge("html_report", "save_to_db")

    # Parallel after persistence
    builder.add_edge("save_to_db", "send_email")
    builder.add_edge("save_to_db", "generate_embeddings")

    builder.add_edge("send_email", END)
    builder.add_edge("generate_embeddings", END)

    memory = MemorySaver()

    return builder.compile(
        checkpointer=memory
    )