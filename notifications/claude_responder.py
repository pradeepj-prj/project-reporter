"""Interactive Q&A: respond to user questions using project context."""

import json
import os
from pathlib import Path
from typing import Any

import anthropic
import numpy as np

BUILD_DIR = Path(__file__).resolve().parent.parent / "build"


class ClaudeResponder:
    """Handles interactive Q&A in Discord threads using Claude + semantic search."""

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY required")
        self.client = anthropic.Anthropic(api_key=api_key)
        self._content_index: list[dict[str, Any]] | None = None
        self._embeddings: np.ndarray | None = None

    def _load_index(self) -> None:
        """Load content index and embeddings."""
        if self._content_index is not None:
            return
        index_path = BUILD_DIR / "content_index.json"
        self._content_index = json.loads(index_path.read_text(encoding="utf-8"))

        # Load pre-computed embeddings if available
        emb_path = BUILD_DIR / "embeddings.npy"
        if emb_path.exists():
            self._embeddings = np.load(str(emb_path))

    def find_relevant_pages(
        self, query: str, project: str | None = None, top_k: int = 3
    ) -> list[dict[str, Any]]:
        """Find pages most relevant to a query using embeddings or keyword matching."""
        self._load_index()
        assert self._content_index is not None

        pages = self._content_index
        if project:
            pages = [p for p in pages if p["project"] == project]

        if self._embeddings is not None:
            return self._semantic_search(query, pages, top_k)
        return self._keyword_search(query, pages, top_k)

    def _keyword_search(
        self, query: str, pages: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]]:
        """Fallback keyword-based search."""
        query_terms = set(query.lower().split())
        scored = []
        for page in pages:
            content_lower = page["content"].lower()
            score = sum(1 for term in query_terms if term in content_lower)
            title_lower = page["title"].lower()
            score += sum(2 for term in query_terms if term in title_lower)
            if score > 0:
                scored.append((score, page))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [page for _, page in scored[:top_k]]

    def _semantic_search(
        self, query: str, pages: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]]:
        """Semantic search using pre-computed Voyage AI embeddings."""
        try:
            import voyageai
        except ImportError:
            return self._keyword_search(query, pages, top_k)

        vo = voyageai.Client()
        query_emb = vo.embed([query], model="voyage-3").embeddings[0]
        query_vec = np.array(query_emb)

        assert self._embeddings is not None
        # Cosine similarity
        norms = np.linalg.norm(self._embeddings, axis=1) * np.linalg.norm(query_vec)
        similarities = np.dot(self._embeddings, query_vec) / np.where(norms == 0, 1, norms)

        # Map back to filtered pages
        index_map = {
            i: page
            for i, page in enumerate(self._content_index or [])
            if page in pages
        }
        scored = [(similarities[i], page) for i, page in index_map.items()]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [page for _, page in scored[:top_k]]

    def respond(
        self,
        question: str,
        project: str | None = None,
        thread_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate a response to a user question.

        Args:
            question: The user's question.
            project: Optional project filter for context.
            thread_history: Previous messages in the thread.

        Returns:
            Response text.
        """
        relevant_pages = self.find_relevant_pages(question, project)

        context_parts = []
        for page in relevant_pages:
            # Truncate content to keep within token budget
            content = page["content"][:4000]
            context_parts.append(f"## {page['title']}\n{content}")

        context = "\n\n---\n\n".join(context_parts)

        messages: list[dict[str, str]] = []

        # Add thread history (keep recent, summarize old)
        if thread_history:
            if len(thread_history) > 10:
                # Keep last 5, summarize the rest
                old = thread_history[:-5]
                recent = thread_history[-5:]
                summary = "Previous conversation covered: " + "; ".join(
                    m["content"][:50] for m in old
                )
                messages.append({"role": "user", "content": summary})
                messages.append({"role": "assistant", "content": "I understand the context. Please continue."})
                messages.extend(recent)
            else:
                messages.extend(thread_history)

        messages.append({"role": "user", "content": question})

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=(
                f"You are a helpful assistant answering questions about technical projects. "
                f"Use the following documentation context to answer. Be concise and specific. "
                f"If you don't know, say so.\n\n"
                f"Documentation context:\n{context}"
            ),
            messages=messages,
        )

        return response.content[0].text
