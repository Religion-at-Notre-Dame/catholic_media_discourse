"""Fast JSONL scan helpers for Mac — orjson, mtime cache, parallel file workers."""

from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Iterable, List, Optional

try:
    import orjson

    def loads_line(line: bytes | str) -> dict:
        if isinstance(line, str):
            line = line.encode("utf-8")
        return orjson.loads(line)

    def dumps_obj(obj: dict) -> bytes:
        return orjson.dumps(obj)

except ImportError:  # pragma: no cover

    def loads_line(line: bytes | str) -> dict:
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        return json.loads(line)

    def dumps_obj(obj: dict) -> bytes:
        return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def inventory_fingerprint(paths: Iterable[Path]) -> str:
    parts = []
    for p in sorted(paths):
        if p.exists():
            st = p.stat()
            parts.append(f"{p}:{st.st_mtime_ns}:{st.st_size}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def cache_path(cache_dir: Path, name: str, fingerprint: str) -> Path:
    return cache_dir / f"{name}_{fingerprint}.json"


def load_cache(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_cache(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def default_jobs() -> int:
    """Use performance cores on Apple Silicon, cap for memory."""
    n = os.cpu_count() or 4
    return max(1, min(n - 1, 6))


def scan_files_parallel(
    paths: List[Path],
    worker: Callable[[str], dict],
    *,
    jobs: int | None = None,
    max_rows: int | None = None,
) -> List[dict]:
    """Run worker(path_str) per file; merge returned dicts in caller."""
    jobs = jobs or default_jobs()
    if jobs <= 1 or len(paths) <= 1:
        return [worker(str(p)) for p in paths if p.exists()]

    results: List[dict] = []
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        futs = {pool.submit(worker, str(p)): p for p in paths if p.exists()}
        for fut in as_completed(futs):
            results.append(fut.result())
    return results
