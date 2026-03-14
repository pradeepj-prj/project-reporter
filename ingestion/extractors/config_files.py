"""Extract deployment and configuration metadata."""

from pathlib import Path
from typing import Any

from .base import RepoExtractor


class ConfigFileExtractor(RepoExtractor):
    name = "config_files"

    # Files to look for and how to label them
    CONFIG_FILES = {
        "manifest.yml": "cf_manifest",
        "Procfile": "procfile",
        "runtime.txt": "runtime",
        "ui5.yaml": "ui5_config",
        "xs-app.json": "approuter",
        "mta.yaml": "mta",
        "Dockerfile": "dockerfile",
        "docker-compose.yml": "docker_compose",
        "docker-compose.yaml": "docker_compose",
        ".cfignore": "cfignore",
    }

    def extract(self, repo_path: Path) -> dict[str, Any]:
        configs: dict[str, Any] = {}

        for filename, key in self.CONFIG_FILES.items():
            path = repo_path / filename
            content = self._read_file(path)
            if content:
                configs[key] = {
                    "file": filename,
                    "content": content,
                    "size": len(content),
                }

        # Also check for nested configs (e.g., in subdirectories)
        for filename, key in self.CONFIG_FILES.items():
            for found in repo_path.rglob(filename):
                if any(skip in found.parts for skip in (".venv", "node_modules", ".git")):
                    continue
                rel = str(found.relative_to(repo_path))
                if rel == filename:
                    continue  # Already captured above
                nested_key = f"{key}:{rel}"
                content = self._read_file(found)
                if content:
                    configs[nested_key] = {
                        "file": rel,
                        "content": content,
                        "size": len(content),
                    }

        return configs
