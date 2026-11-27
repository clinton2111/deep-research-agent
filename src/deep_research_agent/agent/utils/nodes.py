import json
import os

from dotenv import load_dotenv
from fastmcp.exceptions import McpError, ToolError
from langchain.messages import HumanMessage, SystemMessage
from langchain_core.decisions import Choice
from langchain_google_genai import GoogleGenAIClassifier
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilyExtract, TavilySearch

from deep_research_agent.agent.utils.templates import (
    REWRITE_SYSTEM_PROMPT,
    REWRITE_USER_PROMPT,
)

from .cache import lookup_report, store_report
from .models import ResearchReport
from .state import MAX_RETRIES, SearchResult, State, SynthesizedReport
from .templates import (
    MAX_REPORT_CHARACTERS,
    QUALITY_CHECK_CRITERIA,
    QUALITY_CHECK_INSTRUCTIONS,
    SYNTHESIS_SYSTEM_PROMPT,
    SYNTHESIS_USER_PROMPT,
)
from .tools import call_mcp_tool

load_dotenv()


async def cache_lookup(state: State) -> dict[str, object]:
    """Check for an approved report before starting research."""

    print("[cache_lookup] start")
    report = await lookup_report(state["original_question"])

    if report is None:
        print("[cache_lookup] end: miss")
        return {"cache_hit": False, "cache_status": "miss"}

    print("[cache_lookup] end: hit")
    return {
        "cache_hit": True,
        "cache_status": "hit",
        "final_report": report,
        "quality_decision": "GOOD",
        "retry_count": 0,
    }


async def cache_store(state: State) -> dict[str, str]:
    """Cache a report after it passes quality control."""

    print("[cache_store] start")
    await store_report(state["original_question"], state["final_report"])

    print("[cache_store] end: stored")
    return {"cache_status": "stored"}


def research(state: State) -> dict[str, object]:
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

    tried_questions = state.get("tried_questions", []) + [state["research_prompt"]]
    print(f"[research] end: {len(results)} results")
    return {"search_results": results, "tried_questions": tried_questions}


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


def quality_control(state: State) -> dict[str, object]:
    """
    Checks if the generated report has quality content
    """
    print("[quality_control] start")
    report_content = state["synthesized_report"]["content"]
    character_count = len(report_content)
    if character_count > MAX_REPORT_CHARACTERS:
        quality_decision = "BAD"
        quality_feedback = (
            f"Report body has {character_count} characters; the limit is "
            f"{MAX_REPORT_CHARACTERS}. Focus on essential facts for a shorter report."
        )
    else:
        classifier = GoogleGenAIClassifier(model="gemini-decision-1")
        response = classifier.invoke(
            {
                "state": {
                    "question": state["original_question"],
                    "content": report_content,
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
        quality_feedback = (
            "The decision model marked the report BAD."
            if quality_decision == "BAD"
            else ""
        )

    final_report = {"content": "", "title": ""}
    retry_count = state.get("retry_count", 0)
    retry_limit_reached = quality_decision != "GOOD" and retry_count >= MAX_RETRIES

    if quality_decision == "GOOD":
        final_report["content"] = state["synthesized_report"]["content"]
        final_report["title"] = state["synthesized_report"]["title"]

    print(f"[quality_control] end: {quality_decision} ({character_count} characters)")
    return {
        "quality_decision": quality_decision,
        "quality_feedback": quality_feedback,
        "final_report": final_report,
        "retry_count": retry_count,
        "error_kind": "quality_limit" if retry_limit_reached else "",
        "error_source": "quality_control" if retry_limit_reached else "",
        "error_message": (
            f"The report did not pass the quality check after {MAX_RETRIES} retries. "
            f"{quality_feedback}"
            if retry_limit_reached
            else ""
        ),
    }


def rewrite_prompt(state: State) -> dict[str, str | int]:
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
            feedback=state["quality_feedback"],
            report=state["synthesized_report"]["content"],
        )
    )

    response = llm.invoke(
        [
            system_message,
            user_message,
        ]
    )

    retry_count = state.get("retry_count", 0) + 1
    print(f"[rewrite_prompt] end: retry {retry_count}/{MAX_RETRIES}")
    return {"research_prompt": response.text.strip(), "retry_count": retry_count}


async def save_file(state: State) -> dict[str, object]:
    """
    Write the report to disk
    """

    print("[save_file] start")
    await call_mcp_tool("save_text", {"content": state["final_report"]["content"]})
    print("[save_file] end")
    return {}


async def email_report(state: State) -> dict[str, str]:
    """
    Send the approved report by email.
    """

    print("[email_report] start")
    await call_mcp_tool(
        "send_email",
        {
            "content": {
                "subject": state["final_report"]["title"],
                "message": state["final_report"]["content"],
            }
        },
    )

    print("[email_report] end: sent")
    return {"email_status": "sent", "email_error": ""}


async def handle_error(state: State) -> dict[str, str]:
    """Notify the user about a failed run and record delivery errors."""

    print("[handle_error] start")
    kind = state["error_kind"]
    source = state["error_source"]
    reason = state["error_message"]

    if source == "email_report":
        message = f"Failed to send email due to: {reason}"
        print(f"[handle_error] end: {message}")
        return {"email_status": "failed", "email_error": message}

    questions = "\n".join(
        f"{index}. {question}"
        for index, question in enumerate(state.get("tried_questions", []), start=1)
    )
    subject = (
        f"Research stopped after {MAX_RETRIES} retries"
        if kind == "quality_limit"
        else f"Research failed in {source}"
    )
    message = f"Research question: {state['original_question']}\n\n{reason}"
    if questions:
        message += f"\n\nQuestions tried:\n\n{questions}"
    if kind == "quality_limit":
        message += "\n\nNo report was saved for this run."
    else:
        message += "\n\nThe run did not complete."

    try:
        await call_mcp_tool(
            "send_email",
            {
                "content": {"subject": subject, "message": message},
                "attach_report": False,
            },
        )
    except (ToolError, McpError) as error:
        delivery_error = f"Failed to send email due to: {error}"
        print(f"[handle_error] end: {delivery_error}")
        return {"email_status": "failed", "email_error": delivery_error}

    print("[handle_error] end: notification sent")
    return {"email_status": "sent", "email_error": ""}
