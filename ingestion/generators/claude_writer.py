"""Generate documentation articles using the Claude API."""

import os

import anthropic

from .prompts import SYSTEM_PROMPT, get_prompt


class ClaudeWriter:
    """Generates MkDocs-ready markdown articles via Claude API calls."""

    def __init__(self, model: str = "claude-opus-4-20250514"):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable is required")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate_section(
        self,
        section: str,
        metadata_context: str,
        extra_context: dict[str, str] | None = None,
    ) -> str:
        """Generate a single documentation section.

        Args:
            section: Section type key (overview, architecture, etc.)
            metadata_context: Serialized project metadata string.
            extra_context: Additional kwargs for the prompt template
                (tables, routes, configs, etc.)

        Returns:
            Generated markdown content.
        """
        kwargs = {"metadata": metadata_context}
        if extra_context:
            kwargs.update(extra_context)

        user_prompt = get_prompt(section, **kwargs)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return response.content[0].text

    def generate_all_sections(
        self,
        metadata_context: str,
        sections: list[str] | None = None,
        extra_contexts: dict[str, dict[str, str]] | None = None,
    ) -> dict[str, str]:
        """Generate multiple documentation sections.

        Args:
            metadata_context: Serialized project metadata.
            sections: List of section keys to generate. Defaults to all.
            extra_contexts: Per-section extra context dicts.

        Returns:
            Dict mapping section key to generated markdown.
        """
        if sections is None:
            sections = ["overview", "architecture", "data_model", "api", "deployment", "btp_insights"]
        if extra_contexts is None:
            extra_contexts = {}

        results = {}
        for section in sections:
            print(f"  Generating {section}...")
            extra = extra_contexts.get(section, {})
            results[section] = self.generate_section(section, metadata_context, extra)

        return results
