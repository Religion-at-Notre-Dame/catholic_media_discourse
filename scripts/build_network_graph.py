"""
Build a cross-source network graph from all collected JSONL datasets.

Reads news, TV, radio, and Spotify records (raw or anonymized) and writes:
  - nodes.jsonl  (entities: content, stations, outlets, keywords, publishers)
  - edges.jsonl  (relationships: matched_keyword, aired_on, episode_of, etc.)

Each input record should include `api_raw` with the full API payload; convenience
fields at the top level are also used for node labels and edges.
"""


from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_ROOT = Path(__file__).resolve().parents[0]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import argparse
import json
import os
from glob import glob
from typing import Any, Dict, List, Set, Tuple

from common.api_record import record_to_network
from common.gdelt_paths import americas_corpus_path, project_root, us_corpus_path  # noqa: E402
from common.progress import iter_jsonl_paths, section, write  # noqa: E402

ROOT = project_root()


def _us_news_raw() -> str:
    p = us_corpus_path(ROOT)
    return str(p) if p else "data/us/news/gdelt_us_paragraphs_20150101_20260630.jsonl"


def _am_news_raw() -> str:
    p = americas_corpus_path(ROOT)
    return str(p) if p else "data/americas/news/gdelt_americas_paragraphs_20150101_20260630.jsonl"


# Per source: prefer anonymized shards when present, else unified/raw collection file.
SOURCE_INPUT_LAYERS: List[Tuple[str, str]] = [
    (
        "data/us/news/anonymized/anonymized_part_*.jsonl",
        _us_news_raw(),
    ),
    (
        "data/americas/news/anonymized/anonymized_part_*.jsonl",
        _am_news_raw(),
    ),
    (
        "data/us/tv/anonymized/anonymized_part_*.jsonl",
        "data/us/tv/gdelt_tv_us_2015-01-01_to_2025-12-31.jsonl",
    ),
    (
        "data/us/english/radio/anonymized/anonymized_part_*.jsonl",
        "data/us/english/radio/aapb_us_2015-01-01_to_2025-12-31.jsonl",
    ),
    (
        "data/us/spanish/radio/anonymized/anonymized_part_*.jsonl",
        "data/us/spanish/radio/aapb_us_2015-01-01_to_2025-12-31.jsonl",
    ),
    (
        "data/us/spotify/anonymized/anonymized_part_*.jsonl",
        "data/us/spotify/spotify_us_2015-01-01_to_2025-12-31.jsonl",
    ),
    (
        "data/us/youtube/anonymized/anonymized_part_*.jsonl",
        "data/us/youtube/youtube_us_2015-01-01_to_2025-12-31.jsonl",
    ),
    (
        "data/us/google_search/anonymized/anonymized_part_*.jsonl",
        "data/us/google_search/google_search_us_2015-01-01_to_2025-12-31.jsonl",
    ),
]


def resolve_default_input_paths() -> List[str]:
    paths: List[str] = []
    for anonymized_glob, raw_glob in SOURCE_INPUT_LAYERS:
        matched = sorted(glob(anonymized_glob))
        if matched:
            paths.extend(matched)
        else:
            paths.extend(sorted(glob(raw_glob)))
    return paths


def normalize_legacy_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure older rows without api_raw still participate in the graph."""
    if rec.get("api_raw"):
        out = dict(rec)
    else:
        source = str(rec.get("source") or "")
        if source == "gdelt_events":
            source = "gdelt_news"
        if not source:
            if rec.get("paragraph_text") or rec.get("url"):
                source = "gdelt_news"
            elif rec.get("snippet"):
                source = "gdelt_tv"
            elif rec.get("item_id"):
                source = "aapb"

        api_raw = dict(rec)
        for key in ("source", "record_id", "item_type", "keyword_query"):
            api_raw.pop(key, None)

        record_id = (
            rec.get("record_id")
            or rec.get("clip_id")
            or rec.get("item_id")
            or rec.get("article_id")
            or rec.get("id")
            or ""
        )
        item_type = rec.get("item_type") or (
            "paragraph" if rec.get("paragraph_text") else source
        )
        out = dict(rec)
        out["source"] = source
        out["record_id"] = str(record_id)
        out["item_type"] = item_type
        out["api_raw"] = api_raw

    if out.get("source") == "gdelt_events":
        out["source"] = "gdelt_news"
    return out


def record_dedup_key(rec: Dict[str, Any]) -> Tuple[str, str]:
    source = str(rec.get("source") or "")
    record_id = str(
        rec.get("record_id")
        or rec.get("clip_id")
        or rec.get("item_id")
        or rec.get("event_id")
        or rec.get("article_id")
        or rec.get("id")
        or ""
    )
    if not record_id:
        url = str(rec.get("url") or rec.get("catalog_url") or "").strip()
        if url:
            record_id = url
    return source, record_id


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def build_graph(input_paths: List[str]) -> Dict[str, Any]:
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []
    records_seen = 0
    records_skipped = 0
    seen_keys: Set[Tuple[str, str]] = set()

    for rec in iter_jsonl_paths(input_paths, desc="Network records", unit="rec"):
        normalized = normalize_legacy_record(rec)
        key = record_dedup_key(normalized)
        if not key[0] or not key[1]:
            records_skipped += 1
            continue
        if key in seen_keys:
            records_skipped += 1
            continue
        seen_keys.add(key)
        records_seen += 1
        record_to_network(normalized, nodes, edges)

    return {
        "records_seen": records_seen,
        "records_skipped": records_skipped,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": list(nodes.values()),
        "edges": edges,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build cross-source network graph from JSONL data.")
    p.add_argument(
        "--input-glob",
        action="append",
        default=[],
        help="Glob for input JSONL (repeatable). Defaults to anonymized data when present.",
    )
    p.add_argument(
        "--output-dir",
        "-o",
        default=os.path.join("data", "us", "network"),
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_paths = []
    if args.input_glob:
        for pattern in args.input_glob:
            input_paths.extend(sorted(glob(pattern)))
    else:
        input_paths = resolve_default_input_paths()

    if not input_paths:
        raise SystemExit("No input JSONL files matched. Collect data first or pass --input-glob.")

    section(f"Building network from {len(input_paths)} file(s)")
    graph = build_graph(input_paths)
    out_dir = Path(args.output_dir)
    write_jsonl(out_dir / "nodes.jsonl", graph["nodes"])
    write_jsonl(out_dir / "edges.jsonl", graph["edges"])

    summary = {
        "records_seen": graph["records_seen"],
        "records_skipped": graph["records_skipped"],
        "node_count": graph["node_count"],
        "edge_count": graph["edge_count"],
        "input_files": input_paths,
    }
    with (out_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")

    write(
        f"Network graph: {graph['node_count']:,} nodes, {graph['edge_count']:,} edges "
        f"from {graph['records_seen']:,} records "
        f"({graph['records_skipped']:,} skipped duplicates) -> {out_dir}"
    )


if __name__ == "__main__":
    main()
