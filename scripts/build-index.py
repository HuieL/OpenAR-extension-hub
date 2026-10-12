#!/usr/bin/env python3
"""Generate extensions.json from entries/extensions/*/entry.json.

The index is a rebuildable projection of the entries; it is never hand-edited.
Run with --check to verify the committed index is current without writing.
"""

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENTRIES = ROOT / "entries" / "extensions"


def build() -> dict:
    rows = []
    if ENTRIES.is_dir():
        for entry_path in sorted(ENTRIES.glob("*/entry.json")):
            raw = entry_path.read_bytes()
            entry = json.loads(raw)
            rows.append(
                {
                    "id": entry["id"],
                    "name": entry["name"],
                    "summary": entry["summary"],
                    "delivery": entry["delivery"],
                    "integration": entry["integration"],
                    "version": entry["version"],
                    "revision": entry["source"]["revision"],
                    "entryPath": entry_path.relative_to(ROOT).as_posix(),
                    "entrySha256": hashlib.sha256(raw).hexdigest(),
                }
            )
    rows.sort(key=lambda row: row["id"])
    return {"schemaVersion": 1, "entries": rows}


def render(index: dict) -> str:
    return json.dumps(index, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    index = build()
    rendered = render(index)
    path = ROOT / "extensions.json"
    if "--check" in sys.argv:
        current = path.read_text() if path.exists() else ""
        if current != rendered:
            sys.exit("extensions.json is stale; run scripts/build-index.py and commit it")
        print(f"extensions.json is current ({len(index['entries'])} entries)")
        return
    path.write_text(rendered)
    print(f"wrote extensions.json ({len(index['entries'])} entries)")


if __name__ == "__main__":
    main()
