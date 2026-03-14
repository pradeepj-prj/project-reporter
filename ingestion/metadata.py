"""Project metadata aggregation from all extractors."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .extractors import (
    APIRouteExtractor,
    CodeStructureExtractor,
    ConfigFileExtractor,
    DBSchemaExtractor,
    DependencyExtractor,
    FileTreeExtractor,
)


@dataclass
class RepoMetadata:
    """Metadata extracted from a single repository."""

    path: str
    role: str
    description: str
    file_tree: dict[str, Any] = field(default_factory=dict)
    dependencies: dict[str, Any] = field(default_factory=dict)
    api_routes: dict[str, Any] = field(default_factory=dict)
    db_schema: dict[str, Any] = field(default_factory=dict)
    config_files: dict[str, Any] = field(default_factory=dict)
    code_structure: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectMetadata:
    """Aggregated metadata for an entire project (all repos)."""

    name: str
    description: str
    repos: list[RepoMetadata] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    @property
    def all_routes(self) -> list[dict[str, str]]:
        routes = []
        for repo in self.repos:
            routes.extend(repo.api_routes.get("routes", []))
        return routes

    @property
    def all_mcp_tools(self) -> list[dict[str, str]]:
        tools = []
        for repo in self.repos:
            tools.extend(repo.api_routes.get("mcp_tools", []))
        return tools

    @property
    def all_tables(self) -> list[dict[str, Any]]:
        tables = []
        for repo in self.repos:
            tables.extend(repo.db_schema.get("tables", []))
        return tables

    @property
    def all_frameworks(self) -> list[str]:
        frameworks = set()
        for repo in self.repos:
            frameworks.update(repo.code_structure.get("frameworks", []))
        return sorted(frameworks)

    def to_context_string(self, max_tokens: int = 12000) -> str:
        """Serialize to a compact string suitable for LLM context."""
        lines = [
            f"# Project: {self.name}",
            f"Description: {self.description}",
            f"Tags: {', '.join(self.tags)}",
            f"Frameworks: {', '.join(self.all_frameworks)}",
            "",
        ]

        if self.all_routes:
            lines.append("## API Routes")
            for r in self.all_routes:
                lines.append(f"  {r['method']} {r['path']} → {r['function']} ({r['file']})")
            lines.append("")

        if self.all_mcp_tools:
            lines.append("## MCP Tools")
            for t in self.all_mcp_tools:
                lines.append(f"  {t['name']} ({t['file']}): {t['summary']}")
            lines.append("")

        if self.all_tables:
            lines.append("## Database Tables")
            for t in self.all_tables:
                cols = ", ".join(c["name"] for c in t["columns"][:8])
                lines.append(f"  {t['schema']}.{t['name']}: {cols}")
            lines.append("")

        for repo in self.repos:
            lines.append(f"## Repo: {Path(repo.path).name} ({repo.role})")
            lines.append(f"  {repo.description}")
            if repo.file_tree.get("key_files"):
                lines.append(f"  Key files: {', '.join(repo.file_tree['key_files'])}")
            if repo.code_structure.get("patterns"):
                lines.append(f"  Patterns: {', '.join(repo.code_structure['patterns'])}")
            lines.append("")

        return "\n".join(lines)


def extract_repo(repo_path: Path, role: str, description: str) -> RepoMetadata:
    """Run all extractors on a single repository."""
    extractors = [
        FileTreeExtractor(),
        DependencyExtractor(),
        APIRouteExtractor(),
        DBSchemaExtractor(),
        ConfigFileExtractor(),
        CodeStructureExtractor(),
    ]

    meta = RepoMetadata(path=str(repo_path), role=role, description=description)

    for ext in extractors:
        result = ext.extract(repo_path)
        setattr(meta, ext.name, result)

    return meta


def extract_project(project_config: dict) -> ProjectMetadata:
    """Run all extractors on all repos in a project."""
    project = ProjectMetadata(
        name=project_config["name"],
        description=project_config["description"],
        tags=project_config.get("tags", []),
    )

    for repo_cfg in project_config["repos"]:
        repo_path = Path(repo_cfg["path"]).expanduser()
        if not repo_path.exists():
            print(f"  ⚠ Skipping {repo_path} (not found)")
            continue
        print(f"  Extracting {repo_path.name} ({repo_cfg['role']})...")
        meta = extract_repo(repo_path, repo_cfg["role"], repo_cfg["description"])
        project.repos.append(meta)

    return project
