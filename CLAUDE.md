# Project Reporter

## Overview

A meta-project that ingests other projects (code, documentation, APIs), analyzes them, and produces:

1. **A multi-project documentation website** — code-documentation-style articles (not raw code) organized in tabs with intelligent cross-linking and external doc references. One entry per project, each with multiple navigable articles.
2. **Digestible "tweet-style" notifications** — bite-sized insights delivered over time via messaging channels (WhatsApp, Telegram, Discord, or email as fallback) so the user can absorb project knowledge passively on mobile.

## Target Audience & Depth

- **Perspective:** A competent solution engineer with a data science background.
- **Level:** Architectural and implementation details — not syntax or line-by-line code, but how components connect, what patterns are used, what trade-offs were made.
- **Exception:** Data science / ML work gets deeper treatment (model choices, data pipelines, evaluation strategies) — still not at the syntax level.
- **Context:** Projects are AI-assisted POCs built rapidly; the goal is fast comprehension without reading every source file.

## SAP BTP Context

Each project analysis should include ideas and insights for extending or improving the project within the **SAP BTP landscape** (e.g., integration with SAP AI Core, BTP services, CAP, HANA Cloud, Integration Suite, etc.).

## Key Design Principles

- Content is for humans, not machines — articles should read naturally, not like auto-generated API docs.
- Smart linking: articles within a project link to each other and to relevant external documentation.
- Incremental digestion: the notification system breaks knowledge into small, engaging pieces delivered over time.
- Multi-project: the website is a single hub for all projects, not a one-off.

## Tech Stack

Not yet decided. Considerations:
- Static site generator or lightweight web framework for the documentation site.
- Messaging API integrations (Telegram Bot API, Discord webhooks, WhatsApp Business API, or email via SMTP/SendGrid).
- AI-powered ingestion pipeline to analyze project source and produce structured content.
- Storage for project metadata, generated articles, and notification state.

## Project Structure

To be established. Expected top-level layout:
```
project_reporter/
├── CLAUDE.md          # This file
├── INITIAL.md         # Original vision document
├── ingestion/         # Project analysis & content generation pipeline
├── site/              # Documentation website
├── notifications/     # Tweet-style messaging system
└── config/            # Project registry & settings
```

## Development Notes

- Refer to `INITIAL.md` for the original vision and motivation.
- When ingesting a project, prioritize architectural understanding over code-level detail.
- For ML/DS projects, go one level deeper into methodology and pipeline design.
- Always consider SAP BTP extension points in generated content.
