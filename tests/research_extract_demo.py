"""Run research, extract, synthesis, and quality check; display their updates."""

from pprint import pprint

from deep_research_agent.agent.utils.nodes import (
    extract,
    quality_control,
    research,
    synthesis,
)
from deep_research_agent.agent.utils.state import State

# uv run python tests/research_extract_demo.py


def main() -> None:
    state: State = {
        "original_question": "Who is Elon Musk?",
        "research_prompt": "Who is Elon Musk?",
        "search_results": [],
        "synthesized_report": {"title": "", "content": ""},
        "quality_decision": "",
        "retry_count": 0,
        "final_report": {"title": "", "content": ""},
        "email_status": "",
        "email_error": "",
        "is_complete": False,
    }

    research_update = research(state)
    state["search_results"] = research_update["search_results"]
    print("State after research:")
    pprint(state)

    extract_update = extract(state)
    state["search_results"] = extract_update["search_results"]
    print("\nState after extract:")
    display_state = state.copy()
    display_results = []
    for result in state["search_results"]:
        display_result = result.copy()
        content = result["content"]
        display_result["content"] = content[:100]
        if len(content) > 100:
            display_result["content"] += "..."
        display_results.append(display_result)
    display_state["search_results"] = display_results
    # pprint(display_state)

    if not state["search_results"]:
        raise AssertionError("Extract returned no search results.")
    if not any(result["content"] for result in state["search_results"]):
        raise AssertionError("Extract returned no page content.")

    synthesis_update = synthesis(state)
    state["synthesized_report"] = synthesis_update["synthesized_report"]
    print("\nState after synthesis:")
    pprint(state["synthesized_report"])

    if not state["synthesized_report"]["title"]:
        raise AssertionError("Synthesis returned no report title.")
    if not state["synthesized_report"]["content"]:
        raise AssertionError("Synthesis returned no report content.")

    quality_update = quality_control(state)
    state["quality_decision"] = quality_update["quality_decision"]
    print("\nState after quality check:")
    pprint({"quality_decision": state["quality_decision"]})

    if state["quality_decision"] not in {"GOOD", "BAD"}:
        raise AssertionError("Quality check returned an invalid decision.")


if __name__ == "__main__":
    main()
