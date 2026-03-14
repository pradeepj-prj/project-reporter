"""Section-specific prompt templates for Claude-based article generation."""

SYSTEM_PROMPT = """\
You are a technical writer creating documentation for a solution engineer audience \
with a data science background. Write at the architectural and implementation level — \
not syntax or line-by-line code, but how components connect, what patterns are used, \
and what trade-offs were made. For ML/DS work, go deeper into methodology and pipeline design.

Use MkDocs Material markdown:
- Mermaid diagrams for architecture/flow
- Admonitions: !!! btp-insight, !!! key-pattern, !!! extension-idea, !!! note, !!! warning
- Tabbed content for multi-option comparisons
- Code blocks with language tags

Include SAP BTP extension ideas where relevant.\
"""

SECTION_PROMPTS = {
    "overview": """\
Write a project overview page. Include:
- Executive summary (2-3 paragraphs)
- Problem statement and what the project solves
- Ecosystem overview (Mermaid diagram of components)
- Technology summary table
- Links to other sections (use relative MkDocs paths)

Project metadata:
{metadata}
""",

    "architecture": """\
Write an architecture documentation page. Include:
- High-level system architecture (Mermaid diagram)
- Component descriptions and responsibilities
- Three-layer architecture explanation (if applicable)
- End-to-end data flow (Mermaid sequence diagram)
- Key architectural decisions with rationale
- Technology stack breakdown

Project metadata:
{metadata}
""",

    "data_model": """\
Write a data model documentation page. Include:
- Schema overview with ER diagram (Mermaid)
- Table descriptions with column details
- Relationship explanations
- Design patterns used (SCD Type 2, Data Vault, etc.)
- Cross-schema synchronization if applicable

Database tables found:
{tables}

Project metadata:
{metadata}
""",

    "api": """\
Write an API documentation page. Include:
- Endpoint inventory table (method, path, description)
- Request/response examples for key endpoints
- Authentication and authorization patterns
- Error handling approach
- API design decisions

Routes found:
{routes}

MCP tools found:
{mcp_tools}

Project metadata:
{metadata}
""",

    "deployment": """\
Write a deployment documentation page. Include:
- Deployment topology (Mermaid diagram)
- Configuration artifacts and their purpose
- Secret management approach
- Build and deploy process
- Environment-specific considerations
- BTP deployment specifics if applicable

Configuration files found:
{configs}

Project metadata:
{metadata}
""",

    "btp_insights": """\
Write a page focused on SAP BTP integration opportunities. Include:
- Current BTP services used
- Extension ideas with SAP AI Core, Integration Suite, HANA Cloud
- Migration paths from current stack to BTP-native services
- CAP framework integration opportunities
- Security enhancements via XSUAA/IAS

Project metadata:
{metadata}
""",
}


def get_prompt(section: str, **kwargs) -> str:
    """Get a formatted prompt for a specific section."""
    template = SECTION_PROMPTS.get(section, SECTION_PROMPTS["overview"])
    return template.format(**kwargs)
