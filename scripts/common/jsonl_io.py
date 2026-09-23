"""Shared JSONL read/write helpers for collection scripts."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, Set


def append_jsonl(path: str, rows: Iterable[Dict[str, Any]]) -> int:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    n = 0
    with open(path, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            n += 1
    return n


def load_seen_urls(path: str) -> Set[str]:
    seen: Set[str] = set()
    if not os.path.exists(path):
        return seen
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            url = rec.get("url")
            if url:
                seen.add(str(url))
    return seen


def load_seen_ids(path: str, *, key_fn) -> Set[str]:
    seen: Set[str] = set()
    if not os.path.exists(path):
        return seen
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            val = key_fn(rec)
            if val:
                seen.add(str(val))
    return seen


def load_seen_item_ids(
    path: str,
    *,
    id_field: str = "record_id",
    type_field: str = "item_type",
) -> Set[str]:
    def key_fn(rec: Dict[str, Any]) -> str:
        item_type = rec.get(type_field)
        rid = rec.get(id_field) or rec.get("id")
        if item_type and rid:
            return f"{item_type}:{rid}"
        return ""

    return load_seen_ids(path, key_fn=key_fn)


def load_seen_field_ids(path: str, field: str) -> Set[str]:
    return load_seen_ids(path, key_fn=lambda rec: str(rec.get(field) or ""))
