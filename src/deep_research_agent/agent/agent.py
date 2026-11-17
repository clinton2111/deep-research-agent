from typing import Literal

from langgraph.graph import END, START, StateGraph

from deep_research_agent.agent.utils.nodes import (
    email_report,
    extract,
    quality_control,
    research,
    rewrite_prompt,
    save_file,
    synthesis,
)
from deep_research_agent.agent.utils.state import State

builder = StateGraph(State)

# Nodes
builder.add_node("research", research)
builder.add_node("extract", extract)
builder.add_node("synthesis", synthesis)
builder.add_node("quality_control", quality_control)
builder.add_node("rewrite_prompt", rewrite_prompt)
builder.add_node("save_file", save_file)
builder.add_node("email_report", email_report)


# Edges
def quality_check_route(state: State) -> Literal["rewrite_prompt", "save_file"]:
    if state["quality_decision"] == "GOOD":
        return "save_file"
    else:
        return "rewrite_prompt"


builder.add_edge(START, "research")
builder.add_edge("research", "extract")
builder.add_edge("extract", "synthesis")
builder.add_edge("synthesis", "quality_control")
builder.add_conditional_edges("quality_control", quality_check_route)
builder.add_edge("rewrite_prompt", "research")
builder.add_edge("save_file", "email_report")
builder.add_edge("email_report", END)

graph = builder.compile()

# graph.get_graph().draw_mermaid_png(output_file_path="graph.png")
