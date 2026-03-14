# Design Decisions

Living document tracking key architectural decisions for Project Reporter.

## Documentation Framework: MkDocs Material

**Decision:** Use MkDocs Material with separate sites per project + a hub landing page.

**Rationale:**
- Material theme provides navigation tabs, search, Mermaid diagram support, and custom admonitions out of the box
- Separate `mkdocs.yml` per project allows independent builds and deployment
- Hub landing page uses Material's grid cards feature for project discovery
- Python-native toolchain aligns with the ingestion pipeline (no Node.js dependency)

**Alternatives considered:**
- Docusaurus — heavier, React-based, overkill for static docs
- Sphinx — more complex configuration, less modern look
- VitePress — would require Node.js in the build chain

## Content Generation: Hybrid Approach

**Decision:** Python extractors build structured metadata, Claude API writes narrative sections.

**Rationale:**
- Extractors are deterministic and fast — AST parsing, regex, file tree walking
- Claude handles the creative, narrative work — turning metadata into readable articles
- Separation allows re-running generation without re-extracting
- Metadata can be inspected/debugged independently

**Models:**
- Ingestion (article generation): Claude Opus 4 — best quality for one-off generation
- Interactive Q&A: Claude Haiku 3.5 — fast and cheap for real-time responses (~$0.60/month at 10 msgs/day)

## Notifications: Discord Bot

**Decision:** Discord bot with per-project channels, scheduled cards, and interactive Q&A.

**Rationale:**
- Rich embeds support structured knowledge cards natively
- Threading model maps cleanly to Q&A conversations
- Bot API is well-documented with good Python SDK (discord.py)
- Free for small-scale use (no per-message costs)

**Format:**
- Knowledge cards posted every ~4 hours with quiet hours
- React with thumbs up = "got it", question mark = "explain more" (creates thread)
- Thread Q&A uses Claude Haiku with project documentation as context

## Content Indexing: Voyage AI Embeddings

**Decision:** Build a content index with Voyage AI embeddings for semantic search in Discord Q&A.

**Rationale:**
- Essentially free at this scale (<$0.02 per full index rebuild)
- Decouples the bot from the filesystem — works whether site is local or deployed
- Cosine similarity search is fast (numpy) and doesn't require external infrastructure
- Falls back to keyword search if embeddings aren't available

**Alternative considered:**
- ChromaDB — adds persistence but overkill for <100 pages
- OpenAI embeddings — more expensive, no quality advantage for this use case

## Custom Admonitions

**Decision:** Three custom admonition types: `btp-insight`, `key-pattern`, `extension-idea`.

**Rationale:**
- BTP insights surface SAP ecosystem integration opportunities (target audience: SAP solution engineers)
- Key patterns highlight architectural decisions and their rationale
- Extension ideas suggest concrete next steps for improving projects
- Custom CSS with distinct colors makes them visually scannable

## Deployment: Netlify

**Decision:** Deploy the built site to Netlify.

**Rationale:**
- Free tier is sufficient for documentation sites
- Git-connected auto-deploy on push
- Build command: `python scripts/build_all.py`, output dir: `build/`
- No server-side requirements — purely static output
