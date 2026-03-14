"""Extract API routes from FastAPI and MCP tool decorators via AST parsing."""

import ast
import re
from pathlib import Path
from typing import Any

from .base import RepoExtractor

# FastAPI HTTP method decorators
FASTAPI_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}


class APIRouteExtractor(RepoExtractor):
    name = "api_routes"

    def extract(self, repo_path: Path) -> dict[str, Any]:
        routes: list[dict[str, str]] = []
        mcp_tools: list[dict[str, str]] = []

        for py_file in repo_path.rglob("*.py"):
            if any(skip in py_file.parts for skip in (".venv", "venv", "__pycache__", "node_modules")):
                continue
            source = self._read_file(py_file)
            if not source:
                continue

            rel = str(py_file.relative_to(repo_path))

            # AST-based FastAPI route extraction
            try:
                tree = ast.parse(source)
                routes.extend(self._extract_fastapi_routes(tree, rel))
            except SyntaxError:
                pass

            # Regex-based MCP tool extraction (FastMCP uses @mcp.tool())
            mcp_tools.extend(self._extract_mcp_tools(source, rel))

        return {"routes": routes, "mcp_tools": mcp_tools}

    def _extract_fastapi_routes(self, tree: ast.Module, file: str) -> list[dict[str, str]]:
        routes = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                method, path = self._parse_route_decorator(decorator)
                if method:
                    docstring = ast.get_docstring(node) or ""
                    routes.append({
                        "method": method.upper(),
                        "path": path,
                        "function": node.name,
                        "file": file,
                        "summary": docstring.split("\n")[0] if docstring else "",
                    })
        return routes

    def _parse_route_decorator(self, node: ast.expr) -> tuple[str | None, str]:
        """Parse @app.get("/path") or @router.get("/path") style decorators."""
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            method = node.func.attr
            if method in FASTAPI_METHODS:
                path = ""
                if node.args and isinstance(node.args[0], ast.Constant):
                    path = node.args[0].value
                return method, path
        return None, ""

    def _extract_mcp_tools(self, source: str, file: str) -> list[dict[str, str]]:
        tools = []
        # Match @mcp.tool() or @server.tool() decorators
        pattern = re.compile(
            r'@\w+\.tool\(\s*\)\s*\n'
            r'(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)',
            re.MULTILINE,
        )
        for match in pattern.finditer(source):
            func_name = match.group(1)
            # Try to find docstring
            after = source[match.end():]
            doc = ""
            doc_match = re.search(r'"""(.+?)"""', after, re.DOTALL)
            if doc_match:
                doc = doc_match.group(1).strip().split("\n")[0]
            tools.append({
                "name": func_name,
                "file": file,
                "summary": doc,
            })
        return tools
