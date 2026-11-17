import os
from pathlib import Path

import resend
from dotenv import load_dotenv
from fastmcp import FastMCP
from resend.exceptions import ResendError

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
def send_email(content: dict[str, str]):
    """
    Sends the research content via email

    args - content - content to be emailed
    """

    resend.api_key = os.environ["RESEND_API_KEY"]

    params: resend.Emails.SendParams = {
        "from": "Deep Research Bot <deep-research-bot@cd21.dev>",
        "to": [os.environ["RECEPIENT_EMAIL"]],
        "subject": content["subject"],
        "html": content["message"],
    }

    try:
        email = resend.Emails.send(params)
        print(email)
    except ResendError as error:
        print(error)


if __name__ == "__main__":
    mcp.run()
