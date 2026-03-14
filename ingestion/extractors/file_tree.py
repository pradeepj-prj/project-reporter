"""Extract directory structure respecting .gitignore patterns."""

from pathlib import Path
from typing import Any

from .base import RepoExtractor

# Always skip these directories
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "dist", "build", ".next", ".nuxt", "coverage",
    ".DS_Store", "egg-info",
}

# Key files to flag
KEY_FILES = {
    "README.md", "README.rst", "CLAUDE.md",
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "package.json", "tsconfig.json",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "Makefile", "Procfile", "runtime.txt",
    "mta.yaml", "manifest.yml", "xs-app.json",
    ".env.example", "ui5.yaml",
}


class FileTreeExtractor(RepoExtractor):
    name = "file_tree"

    def extract(self, repo_path: Path) -> dict[str, Any]:
        tree: list[str] = []
        key_files: list[str] = []
        file_counts: dict[str, int] = {}

        self._walk(repo_path, repo_path, tree, key_files, file_counts, depth=0)

        return {
            "tree": tree,
            "key_files": key_files,
            "file_counts": file_counts,
            "total_files": sum(file_counts.values()),
        }

    def _walk(
        self,
        root: Path,
        current: Path,
        tree: list[str],
        key_files: list[str],
        counts: dict[str, int],
        depth: int,
    ) -> None:
        if depth > 6:
            return

        entries = sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        for entry in entries:
            rel = entry.relative_to(root)

            if entry.is_dir():
                if entry.name in SKIP_DIRS or entry.name.startswith("."):
                    continue
                indent = "  " * depth
                tree.append(f"{indent}{entry.name}/")
                self._walk(root, entry, tree, key_files, counts, depth + 1)
            else:
                indent = "  " * depth
                tree.append(f"{indent}{entry.name}")
                ext = entry.suffix.lower()
                counts[ext] = counts.get(ext, 0) + 1
                if entry.name in KEY_FILES:
                    key_files.append(str(rel))
