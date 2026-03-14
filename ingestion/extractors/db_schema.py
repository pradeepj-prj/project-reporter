"""Extract database schema from SQL DDL files."""

import re
from pathlib import Path
from typing import Any

from .base import RepoExtractor


class DBSchemaExtractor(RepoExtractor):
    name = "db_schema"

    def extract(self, repo_path: Path) -> dict[str, Any]:
        tables: list[dict[str, Any]] = []

        for sql_file in repo_path.rglob("*.sql"):
            if any(skip in sql_file.parts for skip in (".venv", "node_modules")):
                continue
            content = self._read_file(sql_file)
            if not content:
                continue
            rel = str(sql_file.relative_to(repo_path))
            tables.extend(self._parse_create_tables(content, rel))

        return {"tables": tables}

    def _parse_create_tables(self, content: str, file: str) -> list[dict[str, Any]]:
        tables = []
        # Match CREATE TABLE statements
        pattern = re.compile(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?'
            r'(?:(\w+)\.)?(\w+)\s*\((.*?)\);',
            re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(content):
            schema = match.group(1) or "public"
            table_name = match.group(2)
            body = match.group(3)
            columns = self._parse_columns(body)
            fks = self._parse_foreign_keys(body)
            tables.append({
                "schema": schema,
                "name": table_name,
                "file": file,
                "columns": columns,
                "foreign_keys": fks,
            })
        return tables

    def _parse_columns(self, body: str) -> list[dict[str, str]]:
        columns = []
        for line in body.split(","):
            line = line.strip()
            if not line or line.upper().startswith(("PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT")):
                continue
            parts = line.split()
            if len(parts) >= 2:
                col_name = parts[0].strip('"')
                col_type = parts[1]
                nullable = "NOT NULL" not in line.upper()
                columns.append({
                    "name": col_name,
                    "type": col_type,
                    "nullable": nullable,
                })
        return columns

    def _parse_foreign_keys(self, body: str) -> list[dict[str, str]]:
        fks = []
        pattern = re.compile(
            r'FOREIGN\s+KEY\s*\((\w+)\)\s*REFERENCES\s+(?:(\w+)\.)?(\w+)\s*\((\w+)\)',
            re.IGNORECASE,
        )
        for match in pattern.finditer(body):
            fks.append({
                "column": match.group(1),
                "ref_schema": match.group(2) or "public",
                "ref_table": match.group(3),
                "ref_column": match.group(4),
            })
        return fks
