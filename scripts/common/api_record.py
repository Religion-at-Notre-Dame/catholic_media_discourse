"""Shared helpers for preserving full API payloads and building network graphs."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, Iterator, List, Optional
from urllib.parse import urlparse


def serialize_value(value: Any) -> Any:
    try:
        import pandas as pd

        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
    except Exception:
        if value is None:
            return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def build_gdelt_row_raw(chunk, pandas_idx, idx: Dict[str, int]) -> Dict[str, Any]:
    """Capture every GDELT EVENTS column for a matched row."""
    row = chunk.loc[pandas_idx]
    raw: Dict[str, Any] = {}
    for i in range(chunk.shape[1]):
        raw[f"col_{i}"] = serialize_value(row.iloc[i])
    for name, col_i in idx.items():
        if col_i >= 0 and col_i < chunk.shape[1]:
            raw[name] = serialize_value(row.iloc[col_i])
    return raw


def wrap_api_record(
    *,
    source: str,
    record_id: str,
    item_type: str,
    keyword_query: str = "",
    api_raw: Any,
    **fields: Any,
) -> Dict[str, Any]:
    """Standard record envelope: metadata + full API payload + convenience fields."""
    record: Dict[str, Any] = {
        "source": source,
        "record_id": record_id,
        "item_type": item_type,
        "keyword_query": keyword_query,
        "api_raw": api_raw,
    }
    record.update(fields)
    return record


def node_id(source: str, record_id: str) -> str:
    return f"{source}:{record_id}"


def domain_from_url(url: str) -> str:
    try:
        host = urlparse(str(url or "")).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def iter_jsonl_paths(paths: Iterable[str]) -> Iterator[Dict[str, Any]]:
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            continue


def add_node(
    nodes: Dict[str, Dict[str, Any]],
    *,
    source: str,
    record_id: str,
    item_type: str,
    label: str = "",
    attrs: Optional[Dict[str, Any]] = None,
) -> str:
    nid = node_id(source, record_id)
    if nid not in nodes:
        nodes[nid] = {
            "id": nid,
            "source": source,
            "record_id": record_id,
            "item_type": item_type,
            "label": label or record_id,
            "attrs": {},
        }
    if label:
        nodes[nid]["label"] = label
    if attrs:
        nodes[nid]["attrs"].update(attrs)
    return nid


def add_edge(
    edges: List[Dict[str, Any]],
    *,
    source_id: str,
    target_id: str,
    edge_type: str,
    attrs: Optional[Dict[str, Any]] = None,
) -> None:
    if not source_id or not target_id or source_id == target_id:
        return
    edge = {
        "source": source_id,
        "target": target_id,
        "type": edge_type,
    }
    if attrs:
        edge["attrs"] = attrs
    edges.append(edge)


def flatten_api_raw(api_raw: Any, *, prefix: str = "") -> Dict[str, Any]:
    """Shallow flatten for node attributes (one level of nesting)."""
    if not isinstance(api_raw, dict):
        return {}
    out: Dict[str, Any] = {}
    for key, value in api_raw.items():
        attr_key = f"{prefix}{key}" if not prefix else f"{prefix}_{key}"
        if isinstance(value, dict):
            for sub_key, sub_val in value.items():
                if isinstance(sub_val, (str, int, float, bool)) or sub_val is None:
                    out[f"{attr_key}_{sub_key}"] = sub_val
        elif isinstance(value, list):
            if value and all(isinstance(v, str) for v in value[:5]):
                out[attr_key] = ", ".join(value[:20])
        elif isinstance(value, (str, int, float, bool)) or value is None:
            out[attr_key] = value
    return out


def record_to_network(
    rec: Dict[str, Any],
    nodes: Dict[str, Dict[str, Any]],
    edges: List[Dict[str, Any]],
) -> None:
    """Extract nodes and edges from one collection record."""
    source = str(rec.get("source") or "")
    record_id = str(rec.get("record_id") or rec.get("clip_id") or rec.get("item_id") or "")
    if not record_id:
        if rec.get("url"):
            record_id = str(rec.get("article_id") or rec.get("event_id") or rec.get("url"))
        elif rec.get("id"):
            record_id = str(rec.get("id"))
    if not source or not record_id:
        return

    item_type = str(rec.get("item_type") or source)
    api_raw = rec.get("api_raw") if isinstance(rec.get("api_raw"), dict) else rec
    label = (
        str(rec.get("title") or rec.get("name") or rec.get("show") or rec.get("url") or record_id)[:200]
    )
    attrs = flatten_api_raw(api_raw if isinstance(api_raw, dict) else {})
    attrs.update(
        {
            k: rec[k]
            for k in (
                "date",
                "year",
                "station",
                "market",
                "language",
                "content_language",
                "publisher",
                "release_date",
                "url",
                "catalog_url",
                "preview_url",
            )
            if rec.get(k) not in (None, "")
        }
    )
    content_nid = add_node(
        nodes,
        source=source,
        record_id=record_id,
        item_type=item_type,
        label=label,
        attrs=attrs,
    )

    keyword = str(rec.get("keyword_query") or rec.get("keyword") or "").strip()
    if keyword:
        kw_id = f"keyword:{keyword.lower()}"
        add_node(nodes, source="keyword", record_id=keyword.lower(), item_type="keyword", label=keyword)
        add_edge(edges, source_id=content_nid, target_id=kw_id, edge_type="matched_keyword")

    if source == "spotify":
        show = api_raw.get("show") if isinstance(api_raw, dict) else None
        if isinstance(show, dict) and show.get("id"):
            show_nid = add_node(
                nodes,
                source="spotify_show",
                record_id=str(show["id"]),
                item_type="show",
                label=str(show.get("name") or show["id"]),
                attrs=flatten_api_raw(show),
            )
            add_edge(edges, source_id=content_nid, target_id=show_nid, edge_type="episode_of")
            publisher = str(show.get("publisher") or "").strip()
            if publisher:
                pub_nid = add_node(
                    nodes,
                    source="publisher",
                    record_id=re.sub(r"\s+", "_", publisher.lower())[:120],
                    item_type="publisher",
                    label=publisher,
                )
                add_edge(edges, source_id=show_nid, target_id=pub_nid, edge_type="published_by")

    if source in ("gdelt_tv",):
        station = str(rec.get("station") or rec.get("station_id") or "").strip()
        if station:
            st_nid = add_node(
                nodes,
                source="tv_station",
                record_id=station,
                item_type="station",
                label=station,
                attrs={"market": rec.get("market")},
            )
            add_edge(edges, source_id=content_nid, target_id=st_nid, edge_type="aired_on")

    if source in ("aapb",):
        station = str(rec.get("station") or "").strip()
        if station:
            st_nid = add_node(
                nodes,
                source="radio_station",
                record_id=station,
                item_type="station",
                label=station,
            )
            add_edge(edges, source_id=content_nid, target_id=st_nid, edge_type="broadcast_by")
        series = str(rec.get("series_title") or "").strip()
        if series:
            series_nid = add_node(
                nodes,
                source="radio_series",
                record_id=series,
                item_type="series",
                label=series,
            )
            add_edge(edges, source_id=content_nid, target_id=series_nid, edge_type="part_of_series")

    if source in ("gdelt_news", "google_search"):
        url = str(rec.get("url") or "").strip()
        domain = domain_from_url(url)
        if domain:
            dom_nid = add_node(
                nodes,
                source="news_outlet",
                record_id=domain,
                item_type="outlet",
                label=domain,
            )
            add_edge(edges, source_id=content_nid, target_id=dom_nid, edge_type="hosted_at")

    if source == "youtube":
        channel_id = str(rec.get("channel_id") or "").strip()
        channel_title = str(rec.get("channel_title") or channel_id).strip()
        if channel_id:
            ch_nid = add_node(
                nodes,
                source="youtube_channel",
                record_id=channel_id,
                item_type="channel",
                label=channel_title or channel_id,
            )
            if str(rec.get("item_type") or "") in ("video", "playlist"):
                add_edge(edges, source_id=content_nid, target_id=ch_nid, edge_type="uploaded_by")
