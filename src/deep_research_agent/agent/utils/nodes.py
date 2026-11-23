import json
import os

from dotenv import load_dotenv
from langchain.messages import HumanMessage, SystemMessage
from langchain_core.decisions import Choice
from langchain_google_genai import GoogleGenAIClassifier
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilyExtract, TavilySearch
from langsmith import get_current_run_tree, traceable

from deep_research_agent.agent.utils.templates import (
    REWRITE_SYSTEM_PROMPT,
    REWRITE_USER_PROMPT,
)

from .models import ResearchReport
from .state import SearchResult, State, SynthesizedReport
from .templates import (
    QUALITY_CHECK_CRITERIA,
    QUALITY_CHECK_INSTRUCTIONS,
    SYNTHESIS_SYSTEM_PROMPT,
    SYNTHESIS_USER_PROMPT,
)
from .tools import call_mcp_tool

load_dotenv()


def research(state: State) -> dict[str, list[SearchResult]]:
    """
    Research a given task by calling the tavily tool
    """

    print("[research] start")
    tool = TavilySearch(
        max_results=(int(os.environ["MAX_SEARCH_RESULTS"])),
    )

    search_results = tool.invoke({"query": state["research_prompt"]})

    results: list[SearchResult] = []
    for index, result in enumerate(search_results["results"]):
        results.append(
            {
                "id": index + 1,
                "url": result["url"],
                "title": result["title"],
                "content": "",
                "score": result["score"],
            }
        )

    print(f"[research] end: {len(results)} results")
    return {"search_results": results}


def extract(state: State) -> dict[str, list[SearchResult]]:
    """
    Extract full page contents from the best Tavily search results.
    """
    print("[extract] start")
    updated_results: list[SearchResult] = []
    urls: list[str] = []
    for result in state["search_results"]:
        updated_results.append(result.copy())
        urls.append(result["url"])

    if not urls:
        print("[extract] end: 0 pages")
        return {"search_results": updated_results}

    tool = TavilyExtract(
        include_images=False,
        include_favicon=False,
        format="markdown",
        chunks_per_source=3,
    )

    extraction = tool.invoke({"urls": urls})

    for page in extraction["results"]:
        for result in updated_results:
            if result["url"] == page["url"]:
                result["content"] = page["raw_content"] or ""
                break

    extracted_count = sum(bool(result["content"]) for result in updated_results)
    print(f"[extract] end: {extracted_count} pages")
    return {"search_results": updated_results}


def synthesis(state: State) -> dict[str, SynthesizedReport]:
    """
    Generate a clear research report from the search results
    """

    print("[synthesis] start")
    llm: ChatOpenAI = ChatOpenAI(model="gpt-6-luna")

    system_message = SystemMessage(SYNTHESIS_SYSTEM_PROMPT)

    source_documents = json.dumps(
        state["search_results"],
        ensure_ascii=False,
        indent=2,
    )

    user_prompt = HumanMessage(
        SYNTHESIS_USER_PROMPT.format(
            question=state["original_question"],
            source_documents=source_documents,
        )
    )

    structured_llm = llm.with_structured_output(ResearchReport)
    report = structured_llm.invoke([system_message, user_prompt])
    print("[synthesis] end")
    return {"synthesized_report": {"title": report.title, "content": report.content}}


def quality_control(state: State) -> dict:
    """
    Checks if the generated report has quality content
    """
    print("[quality_control] start")
    classifier = GoogleGenAIClassifier(model="gemini-decision-1")

    response = classifier.invoke(
        {
            "state": {
                "question": state["original_question"],
                "content": state["synthesized_report"]["content"],
            },
            "questions": {
                "quality": Choice(
                    instructions=QUALITY_CHECK_INSTRUCTIONS,
                    criteria=QUALITY_CHECK_CRITERIA,
                )
            },
        }
    )

    quality_decision = response.choices["quality"].choice.upper()
    final_report = {"content": "", "title": ""}

    if quality_decision == "GOOD":
        final_report["content"] = state["synthesized_report"]["content"]
        final_report["title"] = state["synthesized_report"]["title"]

    print(f"[quality_control] end: {quality_decision}")
    return {"quality_decision": quality_decision, "final_report": final_report}


def rewrite_prompt(state: State):
    """
    Rewrite the research prompt if quality_control determins poor quality
    """

    print("[rewrite_prompt] start")
    llm: ChatOpenAI = ChatOpenAI(model="gpt-6-luna")

    system_message = SystemMessage(REWRITE_SYSTEM_PROMPT)

    user_message = HumanMessage(
        REWRITE_USER_PROMPT.format(
            question=state["original_question"],
            current_prompt=state["research_prompt"],
            report=state["synthesized_report"]["content"],
        )
    )

    response = llm.invoke(
        [
            system_message,
            user_message,
        ]
    )

    print("[rewrite_prompt] end")
    return {"research_prompt": response.text.strip()}


async def save_file(state: State) -> dict[str, object]:
    """
    Write the report to disk
    """

    print("[save_file] start")
    await call_mcp_tool("save_text", {"content": state["final_report"]["content"]})
    print("[save_file] end")
    return {}


@traceable(name="email_delivery", run_type="tool")
async def email_report(state: State) -> dict[str, str]:
    """
    Send the final report as an email
    """

    print("[email_report] start")
    try:
        await call_mcp_tool(
            "send_email",
            {
                "content": {
                    "subject": state["final_report"]["title"],
                    "message": state["final_report"]["content"],
                }
            },
        )
    except Exception as error:
        message = f"Failed to send email due to: {error}"
        run = get_current_run_tree()
        if run is not None:
            run.add_event({"name": "email_send_failed", "kwargs": {"message": message}})
        print(f"[email_report] end: {message}")
        return {"email_status": "failed", "email_error": message}

    print("[email_report] end: sent")
    return {"email_status": "sent", "email_error": ""}
