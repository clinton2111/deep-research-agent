import os

from dotenv import load_dotenv
from langchain_tavily import TavilyExtract, TavilySearch

from .state import SearchResult, State
from .tools import call_mcp_tool

load_dotenv()


def research(state: State) -> dict[str, list[SearchResult]]:
    """
    Research a given task by calling the tavily tool
    """

    tool = TavilySearch(
        max_results=(int(os.environ["MAX_SEARCH_RESULTS"])),
    )

    search_results = tool.invoke({"query": state["research_prompt"]})

    results: list[SearchResult] = []
    for result in search_results["results"]:
        results.append(
            {
                "url": result["url"],
                "title": result["title"],
                "content": "",
                "score": result["score"],
            }
        )

    return {"search_results": results}


async def extract(state: State) -> dict[str, list[SearchResult]]:
    """
    Extract full page contents from the best Tavily search results.
    """
    updated_results: list[SearchResult] = []
    urls: list[str] = []
    for result in state["search_results"]:
        updated_results.append(result.copy())
        urls.append(result["url"])

    if not urls:
        return {"search_results": updated_results}

    tool = TavilyExtract(
        include_images=False,
        include_favicon=False,
        format="markdown",
        chunks_per_source=3,
    )

    extraction = await tool.ainvoke({"urls": urls})

    for page in extraction["results"]:
        for result in updated_results:
            if result["url"] == page["url"]:
                result["content"] = page["raw_content"] or ""
                break

    return {"search_results": updated_results}


def synthesis(state: State):
    """
    Generate a clear research report from the search results
    """


def quality_control(state: State):
    """
    Checks if the generated report has quality content
    """


def rewrite_prompt(state: State):
    """
    Rewrite the research prompt if quality_control determins poor quality
    """


async def save_file(state: State) -> dict[str, object]:
    """
    Write the report to disk
    """

    await call_mcp_tool("save_text", {"content": state["final_report"]})
    return {}


async def email_report(state: State) -> dict[str, object]:
    """
    Send the final report as an email
    """

    await call_mcp_tool(
        "send_email",
        {"content": {"subject": "Research report", "message": state["final_report"]}},
    )
    return {}
