#!/usr/bin/env python3
"""Build all MkDocs sites into a unified build/ directory.

Usage:
    python scripts/build_all.py          # build all sites
    python scripts/build_all.py --serve  # build and serve locally
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
HUB_DIR = ROOT / "hub"
PROJECTS_DIR = ROOT / "projects"


def build_site(site_dir: Path, output_dir: Path) -> None:
    """Build a single MkDocs site."""
    print(f"  Building {site_dir.name} → {output_dir.relative_to(BUILD_DIR)}")
    subprocess.run(
        ["mkdocs", "build", "--site-dir", str(output_dir)],
        cwd=str(site_dir),
        check=True,
    )


def build_content_index() -> None:
    """Generate build/content_index.json from all built .md source files."""
    index = []
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        docs_dir = project_dir / "docs"
        if not docs_dir.exists():
            continue
        project_name = project_dir.name
        for md_file in docs_dir.rglob("*.md"):
            if md_file.name == "extra.css":
                continue
            rel_path = md_file.relative_to(docs_dir)
            content = md_file.read_text(encoding="utf-8")
            # Extract title from first heading
            title = project_name
            for line in content.splitlines():
                if line.startswith("# "):
                    title = line.lstrip("# ").strip()
                    break
            index.append({
                "project": project_name,
                "title": title,
                "path": str(rel_path),
                "url": f"/{project_name}/{str(rel_path).replace('.md', '/').replace('index/', '')}",
                "content": content,
            })

    index_path = BUILD_DIR / "content_index.json"
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Content index: {len(index)} pages → {index_path.relative_to(ROOT)}")


def main() -> None:
    print(f"Building all sites into {BUILD_DIR.relative_to(ROOT)}/\n")

    # Clean build directory
    if BUILD_DIR.exists():
        import shutil
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)

    # Build hub at root
    build_site(HUB_DIR, BUILD_DIR)

    # Build each project site into a subdirectory
    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        mkdocs_yml = project_dir / "mkdocs.yml"
        if mkdocs_yml.exists():
            build_site(project_dir, BUILD_DIR / project_dir.name)

    # Build content index for Discord bot
    build_content_index()

    print(f"\nDone. Output in {BUILD_DIR.relative_to(ROOT)}/")

    if "--serve" in sys.argv:
        print("\nServing on http://localhost:8000 ...")
        subprocess.run(
            ["python", "-m", "http.server", "8000", "--directory", str(BUILD_DIR)],
            check=True,
        )


if __name__ == "__main__":
    main()
