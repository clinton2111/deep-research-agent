"""Run the research and extract nodes, then display their state updates."""

import asyncio
from pprint import pprint

from deep_research_agent.agent.utils.nodes import extract, research
from deep_research_agent.agent.utils.state import State


async def main() -> None:
    state: State = {
        "original_question": "Who is Elon Musk?",
        "research_prompt": "Who is Elon Musk?",
        "search_results": [],
        "synthesized_report": "",
        "quality_decision": "",
        "retry_count": 0,
        "final_report": "",
        "is_complete": False,
    }

    research_update = research(state)
    state["search_results"] = research_update["search_results"]
    print("State after research:")
    pprint(state)

    extract_update = await extract(state)
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
    pprint(display_state)

    if not state["search_results"]:
        raise AssertionError("Extract returned no search results.")
    if not any(result["content"] for result in state["search_results"]):
        raise AssertionError("Extract returned no page content.")


if __name__ == "__main__":
    asyncio.run(main())
