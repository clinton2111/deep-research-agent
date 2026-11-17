from typing import TypedDict


class SearchResult(TypedDict):
    url: str
    title: str
    content: str
    score: float


class State(TypedDict):
    """Hold the data shared by research graph nodes.

    Fields:
        original_question: The user's question. Set at the start; read by every node.
        research_prompt: The search query. Set at the start and improved after a retry;
            read by the Research node.
        search_results: URLs and titles from Tavily Search. Research creates the list;
            Extract fills each result's content; Synthesis reads it.
        synthesized_report: Report written from search results by Synthesis;
            read by Quality Check.
        quality_decision: "good" or "not good". Written by Quality Check;
            read by the conditional edge.
        retry_count: Number of completed retries. Updated during the quality loop;
            read by the conditional edge.
        final_report: Report to save and email. Set when quality is good;
            read by the Save and Email nodes.
        is_complete: Whether the agent can finish. Written by Quality Check;
            read at the end of the graph.
    """

    original_question: str
    research_prompt: str
    search_results: list[SearchResult]
    synthesized_report: str
    quality_decision: str
    retry_count: int
    final_report: str
    is_complete: bool
