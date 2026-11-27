"""Cache approved research reports with RedisSemanticCache."""

import os

from langchain_core.outputs import Generation
from langchain_openai import OpenAIEmbeddings
from langchain_redis import RedisSemanticCache

from .models import ResearchReport
from .state import SynthesizedReport

CACHE_ID = "deep-research-report"
CACHE_TTL_SECONDS = 30 * 60


def _cache() -> RedisSemanticCache:
    return RedisSemanticCache(
        redis_url=os.environ["REDIS_URL"],
        embeddings=OpenAIEmbeddings(model="text-embedding-3-small"),
        distance_threshold=0.1,
        ttl=CACHE_TTL_SECONDS,
        name="deep-research-reports",
    )


async def lookup_report(question: str) -> SynthesizedReport | None:
    """Return a cached report for a semantically similar question."""

    generations = await _cache().alookup(question, CACHE_ID)
    if not generations:
        return None
    return ResearchReport.model_validate_json(generations[0].text).model_dump()


async def store_report(question: str, report: SynthesizedReport) -> None:
    """Cache a report after it passes quality control."""

    content = ResearchReport.model_validate(report).model_dump_json()
    await _cache().aupdate(question, CACHE_ID, [Generation(text=content)])
