"""Extract dependency information from project configuration files."""

import re
from pathlib import Path
from typing import Any

from .base import RepoExtractor


class DependencyExtractor(RepoExtractor):
    name = "dependencies"

    def extract(self, repo_path: Path) -> dict[str, Any]:
        deps: dict[str, Any] = {}

        # requirements.txt
        req = self._read_file(repo_path / "requirements.txt")
        if req:
            deps["requirements.txt"] = self._parse_requirements(req)

        # pyproject.toml
        pyproject = self._read_file(repo_path / "pyproject.toml")
        if pyproject:
            deps["pyproject.toml"] = self._parse_pyproject(pyproject)

        # package.json
        pkg = self._read_file(repo_path / "package.json")
        if pkg:
            deps["package.json"] = self._parse_package_json(pkg)

        # mta.yaml
        mta = self._read_file(repo_path / "mta.yaml")
        if mta:
            deps["mta.yaml"] = self._parse_mta(mta)

        return deps

    def _parse_requirements(self, content: str) -> list[str]:
        deps = []
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                deps.append(line)
        return deps

    def _parse_pyproject(self, content: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        # Extract project name
        m = re.search(r'^name\s*=\s*"(.+?)"', content, re.MULTILINE)
        if m:
            result["name"] = m.group(1)
        # Extract dependencies block
        in_deps = False
        deps = []
        for line in content.splitlines():
            if line.strip() == "dependencies = [":
                in_deps = True
                continue
            if in_deps:
                if line.strip() == "]":
                    break
                dep = line.strip().strip('",')
                if dep:
                    deps.append(dep)
        if deps:
            result["dependencies"] = deps
        return result

    def _parse_package_json(self, content: str) -> dict[str, Any]:
        import json
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return {}
        result: dict[str, Any] = {}
        if "name" in data:
            result["name"] = data["name"]
        if "dependencies" in data:
            result["dependencies"] = data["dependencies"]
        if "devDependencies" in data:
            result["devDependencies"] = data["devDependencies"]
        return result

    def _parse_mta(self, content: str) -> dict[str, Any]:
        import yaml
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            return {}
        result: dict[str, Any] = {}
        if "ID" in data:
            result["id"] = data["ID"]
        if "modules" in data:
            result["modules"] = [
                {"name": m.get("name"), "type": m.get("type")}
                for m in data["modules"]
            ]
        if "resources" in data:
            result["resources"] = [
                {"name": r.get("name"), "type": r.get("type")}
                for r in data["resources"]
            ]
        return result
