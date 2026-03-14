"""Base class for repository extractors."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class RepoExtractor(ABC):
    """Abstract base for extractors that analyze a repository and return structured data."""

    name: str = "base"

    @abstractmethod
    def extract(self, repo_path: Path) -> dict[str, Any]:
        """Extract metadata from a repository.

        Args:
            repo_path: Path to the repository root.

        Returns:
            Dictionary of extracted metadata keyed by category.
        """
        ...

    def _read_file(self, path: Path) -> str | None:
        """Safely read a file, returning None if it doesn't exist."""
        try:
            return path.read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError, UnicodeDecodeError):
            return None
