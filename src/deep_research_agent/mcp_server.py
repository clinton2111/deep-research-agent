import os
from base64 import b64encode
from pathlib import Path

import resend
from dotenv import load_dotenv
from fastmcp import FastMCP
from markdown_it import MarkdownIt

load_dotenv()

PROJECT_DIR = str(Path(__file__).resolve().parent.parent)

mcp = FastMCP(
    name="Deep Research MCP",
    instructions="Provides tools for writing report content to disk and for send the report via email",
)


@mcp.tool
def save_text(content: str) -> str:
    """
    Saves content to a md file in the output folder

    args: content - content to be written to the file
    """

    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "research_report.md"
    report_path.write_text(content, encoding="utf-8")
    return str(report_path)


@mcp.tool
def send_email(content: dict[str, str], attach_report: bool = True) -> None:
    """
    Sends the research content via email

    args - content - content to be emailed
    """

    resend.api_key = os.environ["RESEND_API_KEY"]
    markdown = content["message"]
    html = MarkdownIt("js-default").render(markdown)

    params: resend.Emails.SendParams = {
        "from": "Deep Research Bot <deep-research-bot@cd21.dev>",
        "to": [os.environ["RECEPIENT_EMAIL"]],
        "subject": content["subject"],
        "html": html,
        "text": markdown,
    }

    if attach_report:
        params["attachments"] = [
            {
                "filename": "research_report.md",
                "content": b64encode(markdown.encode("utf-8")).decode("ascii"),
                "content_type": "text/markdown",
            }
        ]

    resend.Emails.send(params)


if __name__ == "__main__":
    mcp.run()
