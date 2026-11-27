from typing import TypedDict

MAX_RETRIES = 3


class SearchResult(TypedDict):
    id: int
    url: str
    title: str
    content: str
    score: float


class SynthesizedReport(TypedDict):
    title: str
    content: str


class InputState(TypedDict):
    original_question: str
    research_prompt: str


class State(InputState):
    """Hold the data shared by research graph nodes.

    Fields:
        original_question: The user's question. Set at the start; read by every node.
        research_prompt: The search query. Set at the start and improved after a retry;
            read by the Research node.
        cache_hit: Whether the question matched an approved cached report.
        cache_status: Hit, miss, or stored for the Redis cache.
        tried_questions: Search questions sent to Tavily, in the order tried.
        search_results: URLs and titles from Tavily Search. Research creates the list;
            Extract fills each result's content; Synthesis reads it.
        synthesized_report: Report written from search results by Synthesis;
            read by Quality Check.
        quality_decision: "good" or "not good". Written by Quality Check;
            read by the conditional edge.
        quality_feedback: Reason for a failed quality check, including length failures.
        retry_count: Number of completed retries. Updated during the quality loop;
            read by the conditional edge.
        final_report: Report to save and email. Set when quality is good;
            read by the Save and Email nodes.
        email_status: "sent" or "failed" after the email node runs.
        email_error: Error message when email delivery fails; empty on success.
        error_kind: Node exception or quality retry limit.
        error_source: Node that raised an error or reached the retry limit.
        error_message: Reason sent to the general error handler.
        is_complete: Whether the agent can finish. Written by Quality Check;
            read at the end of the graph.
    """

    search_results: list[SearchResult]
    cache_hit: bool
    cache_status: str
    tried_questions: list[str]
    synthesized_report: SynthesizedReport
    quality_decision: str
    quality_feedback: str
    retry_count: int
    final_report: SynthesizedReport
    email_status: str
    email_error: str
    error_kind: str
    error_source: str
    error_message: str
    is_complete: bool
