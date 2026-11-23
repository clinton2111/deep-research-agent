from pydantic import BaseModel, Field


class ResearchReport(BaseModel):
    """Structured report returned by the synthesis model."""

    title: str = Field(description="A descriptive title for the research report")
    content: str = Field(
        description="The Markdown report body, including citations and sources"
    )
