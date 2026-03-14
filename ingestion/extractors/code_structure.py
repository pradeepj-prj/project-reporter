"""Identify architectural patterns in a repository."""

import re
from pathlib import Path
from typing import Any

from .base import RepoExtractor

# Directory-based pattern indicators
PATTERN_DIRS = {
    "routers": "router-layer",
    "routes": "router-layer",
    "api": "router-layer",
    "services": "service-layer",
    "queries": "query-layer",
    "models": "model-layer",
    "schemas": "schema-layer",
    "controllers": "controller-layer",
    "views": "view-layer",
    "templates": "template-layer",
    "middleware": "middleware",
    "utils": "utility-layer",
    "helpers": "utility-layer",
    "tests": "test-suite",
    "migrations": "db-migrations",
    "components": "component-based",
    "pages": "page-based",
}


class CodeStructureExtractor(RepoExtractor):
    name = "code_structure"

    def extract(self, repo_path: Path) -> dict[str, Any]:
        patterns: list[str] = []
        frameworks: list[str] = []
        entry_points: list[str] = []

        # Detect directory-based patterns
        for d in repo_path.iterdir():
            if d.is_dir() and d.name in PATTERN_DIRS:
                patterns.append(PATTERN_DIRS[d.name])

        # Detect frameworks from imports
        for py_file in repo_path.rglob("*.py"):
            if any(skip in py_file.parts for skip in (".venv", "venv", "__pycache__")):
                continue
            content = self._read_file(py_file)
            if not content:
                continue
            rel = str(py_file.relative_to(repo_path))

            # Detect frameworks
            if re.search(r"from\s+fastapi\s+import|import\s+fastapi", content):
                if "fastapi" not in frameworks:
                    frameworks.append("fastapi")
            if re.search(r"from\s+fastmcp\s+import|import\s+fastmcp", content):
                if "fastmcp" not in frameworks:
                    frameworks.append("fastmcp")
            if re.search(r"import\s+streamlit|from\s+streamlit", content):
                if "streamlit" not in frameworks:
                    frameworks.append("streamlit")
            if re.search(r"from\s+flask\s+import|import\s+flask", content):
                if "flask" not in frameworks:
                    frameworks.append("flask")

            # Detect entry points
            if re.search(r'if\s+__name__\s*==\s*["\']__main__["\']', content):
                entry_points.append(rel)

        # Detect JS/TS frameworks
        for js_file in repo_path.rglob("*.js"):
            if any(skip in js_file.parts for skip in ("node_modules", ".next")):
                continue
            content = self._read_file(js_file)
            if not content:
                continue
            if re.search(r"from\s+['\"]react['\"]|require\(['\"]react['\"]\)", content):
                if "react" not in frameworks:
                    frameworks.append("react")

        # Detect SAPUI5
        for xml_file in repo_path.rglob("*.xml"):
            content = self._read_file(xml_file)
            if content and "sap.m" in content:
                if "sapui5" not in frameworks:
                    frameworks.append("sapui5")
                break

        return {
            "patterns": list(set(patterns)),
            "frameworks": frameworks,
            "entry_points": entry_points,
        }
