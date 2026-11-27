import asyncio
from time import perf_counter
from uuid import uuid4

from .graph import graph
from .utils.state import InputState


async def main() -> None:
    question = "How do I install LangGraph?"
    initial_state: InputState = {
        "original_question": question,
        "research_prompt": question,
    }

    config = {"configurable": {"thread_id": str(uuid4())}}
    start_time = perf_counter()
    try:
        result = await graph.ainvoke(initial_state, config=config)
    finally:
        print(f"Graph duration: {perf_counter() - start_time:.2f} seconds")
    print(f"Question: {question}")
    print(f"Cache: {result.get('cache_status', 'unavailable')}")
    report = result.get("final_report")
    if report and report["title"]:
        print(f"Report: {report['title']}")
    if result.get("error_kind") == "quality_limit":
        print(f"Research stopped after {result['retry_count']} retries")
    if result.get("error_message"):
        print(f"Error in {result['error_source']}: {result['error_message']}")
    print(f"Quality: {result.get('quality_decision', 'not checked')}")
    print(f"Email: {result.get('email_status', 'not attempted')}")
    if result.get("email_error"):
        print(result["email_error"])


if __name__ == "__main__":
    asyncio.run(main())
