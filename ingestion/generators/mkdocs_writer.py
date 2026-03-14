"""Write generated content to MkDocs site structure."""

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Default section-to-path mapping
SECTION_PATHS = {
    "overview": "index.md",
    "architecture": "architecture/index.md",
    "component_inventory": "architecture/component-inventory.md",
    "data_model": "data-model/index.md",
    "tm_schema": "data-model/tm-schema.md",
    "data_generation": "data-generation/index.md",
    "attrition_model": "data-generation/attrition-model.md",
    "api": "business-queries/index.md",
    "mcp_integration": "mcp-integration/index.md",
    "audit_dashboard": "mcp-integration/audit-dashboard.md",
    "dashboards_hr": "dashboards/hr-analytics.md",
    "dashboards_mcp": "dashboards/mcp-audit.md",
    "dashboards_ui5": "dashboards/sapui5-enterprise.md",
    "deployment": "deployment/index.md",
    "security": "security/index.md",
    "learnings": "learnings/index.md",
    "btp_insights": "btp-insights/index.md",
}


class MkDocsWriter:
    """Writes generated markdown to a MkDocs project structure."""

    def __init__(self, site_dir: Path):
        self.site_dir = site_dir
        self.docs_dir = site_dir / "docs"
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    def write_section(self, section: str, content: str) -> Path:
        """Write a section's content to its corresponding file path."""
        rel_path = SECTION_PATHS.get(section, f"{section}/index.md")
        out_path = self.docs_dir / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        return out_path

    def write_all_sections(self, sections: dict[str, str]) -> list[Path]:
        """Write multiple sections and return paths of written files."""
        paths = []
        for section, content in sections.items():
            path = self.write_section(section, content)
            print(f"  Wrote {path.relative_to(self.site_dir)}")
            paths.append(path)
        return paths

    def generate_mkdocs_yml(
        self,
        site_name: str,
        sections: list[str],
        extra_css: list[str] | None = None,
    ) -> Path:
        """Generate an mkdocs.yml from available sections."""
        nav = self._build_nav(sections)
        config: dict[str, Any] = {
            "site_name": site_name,
            "theme": {
                "name": "material",
                "palette": {"scheme": "default", "primary": "indigo", "accent": "teal"},
                "features": [
                    "navigation.tabs",
                    "navigation.sections",
                    "navigation.expand",
                    "navigation.top",
                    "content.code.copy",
                    "content.tabs.link",
                    "toc.integrate",
                ],
            },
            "markdown_extensions": [
                "admonition",
                "pymdownx.details",
                {
                    "pymdownx.superfences": {
                        "custom_fences": [
                            {
                                "name": "mermaid",
                                "class": "mermaid",
                                "format": "!!python/name:pymdownx.superfences.fence_code_format",
                            }
                        ]
                    }
                },
                {"pymdownx.tabbed": {"alternate_style": True}},
                {"pymdownx.highlight": {"anchor_linenums": True}},
                "pymdownx.inlinehilite",
                "attr_list",
                "md_in_html",
                "tables",
                {"toc": {"permalink": True}},
            ],
            "plugins": ["search"],
            "nav": nav,
        }

        if extra_css:
            config["extra_css"] = extra_css

        yml_path = self.site_dir / "mkdocs.yml"
        yml_path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False), encoding="utf-8")
        return yml_path

    def _build_nav(self, sections: list[str]) -> list[Any]:
        """Build nav structure from available section keys."""
        nav: list[Any] = []
        for section in sections:
            path = SECTION_PATHS.get(section, f"{section}/index.md")
            label = section.replace("_", " ").title()
            nav.append({label: path})
        return nav
