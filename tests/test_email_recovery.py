"""Check email delivery state without contacting Resend."""

import os
import unittest
from base64 import b64decode
from typing import cast
from unittest.mock import AsyncMock, Mock, patch

from fastmcp.exceptions import ToolError

from deep_research_agent.agent.utils.nodes import email_report
from deep_research_agent.agent.utils.state import State
from deep_research_agent.agent.utils.tools import call_mcp_tool


class EmailRecoveryTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.state = cast(
            State,
            {"final_report": {"title": "Example report", "content": "Report body"}},
        )

    async def test_success_records_sent_status(self) -> None:
        with (
            patch.dict(os.environ, {"LANGSMITH_TRACING": "false"}),
            patch(
                "deep_research_agent.agent.utils.nodes.call_mcp_tool",
                new_callable=AsyncMock,
            ) as call_tool,
        ):
            update = await email_report(self.state)

        self.assertEqual(update, {"email_status": "sent", "email_error": ""})
        call_tool.assert_awaited_once_with(
            "send_email",
            {"content": {"subject": "Example report", "message": "Report body"}},
        )

    async def test_failure_records_message_and_trace_event(self) -> None:
        run = Mock()
        message = "Failed to send email due to: Resend unavailable"
        with (
            patch.dict(os.environ, {"LANGSMITH_TRACING": "false"}),
            patch(
                "deep_research_agent.agent.utils.nodes.call_mcp_tool",
                new_callable=AsyncMock,
                side_effect=ToolError("Resend unavailable"),
            ),
            patch(
                "deep_research_agent.agent.utils.nodes.get_current_run_tree",
                return_value=run,
            ),
        ):
            update = await email_report(self.state)

        self.assertEqual(
            update,
            {"email_status": "failed", "email_error": message},
        )
        run.add_event.assert_called_once_with(
            {"name": "email_send_failed", "kwargs": {"message": message}}
        )

    async def test_resend_failure_reaches_mcp_client(self) -> None:
        with (
            patch.dict(
                os.environ,
                {"RESEND_API_KEY": "test-key", "RECEPIENT_EMAIL": "test@example.com"},
            ),
            patch(
                "deep_research_agent.mcp_server.resend.Emails.send",
                side_effect=RuntimeError("Resend unavailable"),
            ),
            self.assertRaises(ToolError) as raised,
        ):
            await call_mcp_tool(
                "send_email",
                {"content": {"subject": "Example report", "message": "Report body"}},
            )
        self.assertIn("Resend unavailable", str(raised.exception))

    async def test_email_renders_markdown_and_attaches_report(self) -> None:
        markdown = "## Introduction\n\nA **formatted** report.\n\n- First source"
        with (
            patch.dict(
                os.environ,
                {"RESEND_API_KEY": "test-key", "RECEPIENT_EMAIL": "test@example.com"},
            ),
            patch("deep_research_agent.mcp_server.resend.Emails.send") as send,
        ):
            await call_mcp_tool(
                "send_email",
                {"content": {"subject": "Example report", "message": markdown}},
            )

        params = send.call_args.args[0]
        self.assertIn("<h2>Introduction</h2>", params["html"])
        self.assertIn("<strong>formatted</strong>", params["html"])
        self.assertIn("<li>First source</li>", params["html"])
        self.assertEqual(params["text"], markdown)
        attachment = params["attachments"][0]
        self.assertEqual(attachment["filename"], "research_report.md")
        self.assertEqual(b64decode(attachment["content"]).decode("utf-8"), markdown)


if __name__ == "__main__":
    unittest.main()
