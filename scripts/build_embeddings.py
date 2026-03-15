#!/usr/bin/env python3
"""Pre-compute Voyage AI embeddings for all content pages."""

import json
import os
from pathlib import Path

import numpy as np
import voyageai
from dotenv import load_dotenv

load_dotenv()

BUILD_DIR = Path(__file__).resolve().parent.parent / "build"


def main() -> None:
    index_path = BUILD_DIR / "content_index.json"
    if not index_path.exists():
        print(f"Content index not found at {index_path}. Run 'python scripts/build_all.py' first.")
        return

    pages = json.loads(index_path.read_text(encoding="utf-8"))
    print(f"Embedding {len(pages)} pages...")

    # Prepare texts: title + first 4000 chars of content (Voyage has token limits)
    texts = [f"{page['title']}\n\n{page['content'][:4000]}" for page in pages]

    vo = voyageai.Client(api_key=os.environ.get("VOYAGE_API_KEY"))

    # Voyage API has batch limits, embed in chunks of 20
    all_embeddings = []
    batch_size = 20
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        result = vo.embed(batch, model="voyage-3")
        all_embeddings.extend(result.embeddings)
        print(f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)}")

    embeddings_array = np.array(all_embeddings)
    out_path = BUILD_DIR / "embeddings.npy"
    np.save(str(out_path), embeddings_array)
    print(f"Saved {embeddings_array.shape} embeddings to {out_path}")


if __name__ == "__main__":
    main()
