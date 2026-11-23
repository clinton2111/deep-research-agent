import asyncio
from uuid import uuid4

from .graph import graph
from .utils.state import InputState


async def main() -> None:
    question = "What is LangGraph?"
    initial_state: InputState = {
        "original_question": question,
        "research_prompt": question,
    }

    config = {"configurable": {"thread_id": str(uuid4())}}
    result = await graph.ainvoke(initial_state, config=config)
    print(f"Report: {result['final_report']['title']}")
    print(f"Quality: {result['quality_decision']}")
    print(f"Email: {result['email_status']}")
    if result["email_error"]:
        print(result["email_error"])


if __name__ == "__main__":
    asyncio.run(main())
