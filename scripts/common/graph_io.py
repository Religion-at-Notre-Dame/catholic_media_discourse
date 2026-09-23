"""Write pipeline graphs as JSONL + GraphML + a classroom PNG preview."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

try:
    import networkx as nx
except ImportError:  # pragma: no cover
    nx = None  # type: ignore

TYPE_COLOR = {
    "country": "#2E86AB",
    "theme": "#E94F37",
    "outlet": "#44AF69",
    "station": "#F6AE2D",
    "channel": "#8B5CF6",
    "actor": "#6B7280",
    "term": "#D97706",
    "concept": "#7C3AED",
}
DEFAULT_COLOR = "#9CA3AF"


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            n += 1
    return n


def _scalar(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if value != value:  # NaN
            return 0.0
        return value
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value[:12])
    return str(value)[:240]


def decorate_nodes(nodes: Sequence[Dict[str, Any]], edges: Sequence[Mapping[str, Any]]) -> None:
    """Set Gephi-friendly color/size from item_type and log degree / n."""
    degree: Dict[str, int] = {}
    for edge in edges:
        src = str(edge.get("source") or "")
        dst = str(edge.get("target") or "")
        if src:
            degree[src] = degree.get(src, 0) + 1
        if dst:
            degree[dst] = degree.get(dst, 0) + 1
    for node in nodes:
        ntype = str(node.get("item_type") or "")
        node["color"] = TYPE_COLOR.get(ntype, DEFAULT_COLOR)
        raw = node.get("n")
        if not isinstance(raw, (int, float)) or not raw:
            raw = degree.get(str(node.get("id") or ""), 1)
        node["size"] = round(8.0 + 6.0 * math.log1p(float(raw)), 2)
        node["degree"] = int(degree.get(str(node.get("id") or ""), 0))


def write_graphml(
    path: Path,
    nodes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    *,
    directed: bool = False,
) -> None:
    if nx is None:
        return
    graph = nx.DiGraph() if directed else nx.Graph()
    for node in nodes:
        nid = str(node.get("id") or "")
        if not nid:
            continue
        attrs = {k: _scalar(v) for k, v in node.items() if k != "id" and k != "attrs"}
        extra = node.get("attrs")
        if isinstance(extra, dict):
            for key, val in extra.items():
                attrs[str(key)] = _scalar(val)
        if "label" not in attrs:
            attrs["label"] = nid
        graph.add_node(nid, **attrs)
    for edge in edges:
        src = str(edge.get("source") or "")
        dst = str(edge.get("target") or "")
        if not src or not dst or src == dst:
            continue
        if src not in graph:
            graph.add_node(src, label=src)
        if dst not in graph:
            graph.add_node(dst, label=dst)
        attrs = {
            k: _scalar(v)
            for k, v in edge.items()
            if k not in {"source", "target", "attrs"}
        }
        extra = edge.get("attrs")
        if isinstance(extra, dict):
            for key, val in extra.items():
                attrs[str(key)] = _scalar(val)
        if directed or not graph.has_edge(src, dst):
            graph.add_edge(src, dst, **attrs)
        else:
            data = graph.edges[src, dst]
            w_new = float(attrs.get("weight") or 0)
            w_old = float(data.get("weight") or 0)
            if w_new > w_old:
                graph.edges[src, dst].update(attrs)
    path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(graph, path)


def _edge_sort_key(edge: Mapping[str, Any], key: str) -> float:
    try:
        return float(edge.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def focus_subgraph(
    nodes: Sequence[Dict[str, Any]],
    edges: Sequence[Dict[str, Any]],
    *,
    key: str = "weight",
    n_edges: int = 40,
    edge_types: Optional[Sequence[str]] = None,
    exclude_ids: Optional[Set[str]] = None,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    skip = exclude_ids or set()
    allowed = set(edge_types) if edge_types else None
    ranked = []
    for edge in edges:
        if allowed and str(edge.get("type") or "") not in allowed:
            continue
        src = str(edge.get("source") or "")
        dst = str(edge.get("target") or "")
        if src in skip or dst in skip:
            continue
        ranked.append(edge)
    ranked.sort(key=lambda e: -_edge_sort_key(e, key))
    kept = ranked[:n_edges]
    keep_ids = {str(e.get("source")) for e in kept} | {str(e.get("target")) for e in kept}
    focus_nodes = [n for n in nodes if str(n.get("id")) in keep_ids]
    return focus_nodes, kept


def write_preview_png(
    path: Path,
    nodes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    *,
    directed: bool = False,
    layout: str = "spring",
    title: str = "",
) -> None:
    if nx is None or not nodes:
        return
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    graph = nx.DiGraph() if directed else nx.Graph()
    colors = []
    sizes = []
    labels = {}
    for node in nodes:
        nid = str(node.get("id") or "")
        if not nid:
            continue
        graph.add_node(nid)
        colors.append(str(node.get("color") or DEFAULT_COLOR))
        sizes.append(float(node.get("size") or 12) * 18)
        labels[nid] = str(node.get("label") or nid)[:28]
    for edge in edges:
        src = str(edge.get("source") or "")
        dst = str(edge.get("target") or "")
        if src in graph and dst in graph and src != dst:
            graph.add_edge(src, dst)
    if graph.number_of_nodes() == 0:
        return
    if layout == "bipartite":
        left = [str(n["id"]) for n in nodes if n.get("item_type") == "country" and str(n.get("id")) in graph]
        try:
            pos = nx.bipartite_layout(graph, left) if left else nx.spring_layout(graph, seed=7)
        except Exception:
            pos = nx.spring_layout(graph, seed=7, k=1.8 / max(graph.number_of_nodes(), 1) ** 0.5)
    else:
        pos = nx.spring_layout(graph, seed=7, k=1.8 / max(graph.number_of_nodes(), 1) ** 0.5)
    fig, ax = plt.subplots(figsize=(11, 8.5))
    nx.draw_networkx_edges(graph, pos, ax=ax, alpha=0.35, arrows=directed, width=0.8)
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_color=colors, node_size=sizes, linewidths=0.4, edgecolors="#111827")
    nx.draw_networkx_labels(graph, pos, labels, ax=ax, font_size=7, font_color="#111827")
    ax.set_axis_off()
    if title:
        ax.set_title(title, fontsize=11, pad=8)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_graph(
    out_dir: Path,
    *,
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    summary: Dict[str, Any],
    directed: bool = False,
    focus_key: str = "weight",
    focus_n: int = 40,
    focus_edge_types: Optional[Sequence[str]] = None,
    focus_exclude_ids: Optional[Set[str]] = None,
    layout: str = "spring",
    preview: bool = True,
) -> Dict[str, Any]:
    decorate_nodes(nodes, edges)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "nodes.jsonl", nodes)
    write_jsonl(out_dir / "edges.jsonl", edges)
    write_graphml(out_dir / "graph.graphml", nodes, edges, directed=directed)
    focus_nodes, focus_edges = focus_subgraph(
        nodes,
        edges,
        key=focus_key,
        n_edges=focus_n,
        edge_types=focus_edge_types,
        exclude_ids=focus_exclude_ids,
    )
    decorate_nodes(focus_nodes, focus_edges)
    write_graphml(out_dir / "focus.graphml", focus_nodes, focus_edges, directed=directed)
    if preview:
        write_preview_png(
            out_dir / "preview.png",
            focus_nodes,
            focus_edges,
            directed=directed,
            layout=layout,
            title=out_dir.name.replace("_", " "),
        )
    payload = {
        **summary,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "directed": directed,
        "focus_node_count": len(focus_nodes),
        "focus_edge_count": len(focus_edges),
        "files": {
            "nodes": str(out_dir / "nodes.jsonl"),
            "edges": str(out_dir / "edges.jsonl"),
            "graphml": str(out_dir / "graph.graphml"),
            "focus": str(out_dir / "focus.graphml"),
            "preview": str(out_dir / "preview.png"),
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload
