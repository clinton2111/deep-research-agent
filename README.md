# Research Agent – Local Version

## What This Agent Does

This is a local research agent built with LangGraph.

You give it a question.
It searches the web.
It checks if the answer is good.
If the answer is not good, it tries again with a better prompt.
If the answer is good, it saves the answer to a file and sends it to your email.

## Current Status

This document is for the local version only.
AWS and Terraform come later.

## How to Use the Playbook

Open `PLAYBOOK.md`.
Follow the steps in order.
Do not skip steps.
Check the expected output of each step before you continue.

After the basic agent works, follow the Evals and Guardrails section.
Then follow the Frontend (React) section.

## Key Decisions

- Search tool: Tavily
- Email tool: Resend
- Graph framework: LangGraph
- Tracing: LangSmith
- MCP: Local FastMCP server
- LLM: Free tier (Gemini or Groq)

## Folder Structure (After You Finish)

```
deep-research-agent/
├── .env
├── AGENTS.md
├── PLAYBOOK.md
├── README.md
└── (your Python files)
```

## Support

If you need help with a step, give an AI agent the `AGENTS.md` file.
Tell the agent which step number you are on.
Ask the agent to help only with that step.
