from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import NodeError
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from deep_research_agent.agent.utils.nodes import (
    cache_lookup,
    cache_store,
    email_report,
    extract,
    handle_error,
    quality_control,
    research,
    rewrite_prompt,
    save_file,
    synthesis,
)
from deep_research_agent.agent.utils.state import MAX_RETRIES, InputState, State

builder = StateGraph(State, input_schema=InputState)


def route_node_error(state: State, error: NodeError) -> Command[Literal["handle_error"]]:
    return Command(
        update={
            "error_kind": "node_exception",
            "error_source": error.node,
            "error_message": f"{type(error.error).__name__}: {error.error}",
        },
        goto="handle_error",
    )


# Nodes
builder.add_node("cache_lookup", cache_lookup, error_handler=route_node_error)
builder.add_node("cache_store", cache_store, error_handler=route_node_error)
builder.add_node("research", research, error_handler=route_node_error)
builder.add_node("extract", extract, error_handler=route_node_error)
builder.add_node("synthesis", synthesis, error_handler=route_node_error)
builder.add_node("quality_control", quality_control, error_handler=route_node_error)
builder.add_node("rewrite_prompt", rewrite_prompt, error_handler=route_node_error)
builder.add_node("save_file", save_file, error_handler=route_node_error)
builder.add_node("email_report", email_report, error_handler=route_node_error)
builder.add_node("handle_error", handle_error)


# Edges
def cache_route(state: State) -> Literal["save_file", "research"]:
    return "save_file" if state["cache_hit"] else "research"


def quality_check_route(state: State) -> Literal["rewrite_prompt", "cache_store", "handle_error"]:
    if state["quality_decision"] == "GOOD":
        return "cache_store"
    if state.get("retry_count", 0) >= MAX_RETRIES:
        return "handle_error"
    return "rewrite_prompt"


builder.add_edge(START, "cache_lookup")
builder.add_conditional_edges("cache_lookup", cache_route)
builder.add_edge("research", "extract")
builder.add_edge("extract", "synthesis")
builder.add_edge("synthesis", "quality_control")
builder.add_conditional_edges("quality_control", quality_check_route)
builder.add_edge("rewrite_prompt", "research")
builder.add_edge("cache_store", "save_file")
builder.add_edge("save_file", "email_report")
builder.add_edge("email_report", END)
builder.add_edge("handle_error", END)

graph = builder.compile(checkpointer=InMemorySaver())

# graph.get_graph().draw_mermaid_png(output_file_path="graph.png")
