"""Ingestion pipeline: extractors → metadata → Claude → MkDocs output."""

from pathlib import Path

import yaml

from .metadata import ProjectMetadata, extract_project

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "projects.yaml"
PROJECTS_DIR = Path(__file__).resolve().parent.parent / "projects"


class IngestionPipeline:
    """Orchestrates the full ingestion flow for a project."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or CONFIG_PATH
        self.config = yaml.safe_load(self.config_path.read_text())

    def extract(self, project_name: str) -> ProjectMetadata:
        """Run extractors on all repos for a project."""
        project_cfg = self.config["projects"][project_name]
        print(f"Extracting metadata for: {project_cfg['name']}")
        return extract_project(project_cfg)

    def ingest_project(
        self,
        project_name: str,
        sections: list[str] | None = None,
        model: str = "claude-opus-4-20250514",
    ) -> None:
        """Full pipeline: extract → generate → write.

        Args:
            project_name: Key in projects.yaml.
            sections: Sections to generate. None = all.
            model: Claude model to use for generation.
        """
        # Step 1: Extract metadata
        metadata = self.extract(project_name)
        context = metadata.to_context_string()

        print(f"\nExtracted {len(metadata.repos)} repos")
        print(f"  Routes: {len(metadata.all_routes)}")
        print(f"  MCP tools: {len(metadata.all_mcp_tools)}")
        print(f"  DB tables: {len(metadata.all_tables)}")
        print(f"  Frameworks: {', '.join(metadata.all_frameworks)}")

        # Step 2: Generate content via Claude
        print(f"\nGenerating articles with {model}...")
        from .generators.claude_writer import ClaudeWriter
        from .generators.mkdocs_writer import MkDocsWriter

        writer = ClaudeWriter(model=model)

        extra_contexts = {
            "data_model": {
                "tables": "\n".join(
                    f"  {t['schema']}.{t['name']}: "
                    + ", ".join(c["name"] for c in t["columns"])
                    for t in metadata.all_tables
                ),
            },
            "api": {
                "routes": "\n".join(
                    f"  {r['method']} {r['path']} → {r['function']}"
                    for r in metadata.all_routes
                ),
                "mcp_tools": "\n".join(
                    f"  {t['name']}: {t['summary']}"
                    for t in metadata.all_mcp_tools
                ),
            },
            "deployment": {
                "configs": "\n".join(
                    f"  {k}: {v.get('file', k)}"
                    for repo in metadata.repos
                    for k, v in repo.config_files.items()
                ),
            },
        }

        generated = writer.generate_all_sections(
            context,
            sections=sections,
            extra_contexts=extra_contexts,
        )

        # Step 3: Write to MkDocs
        site_dir = PROJECTS_DIR / project_name
        mkdocs_writer = MkDocsWriter(site_dir)
        mkdocs_writer.write_all_sections(generated)

        print(f"\nDone. Site at: {site_dir}")
        print(f"Run: cd {site_dir} && mkdocs serve")
