"""Shared progress reporting (tqdm + rich) for pipeline scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, TypeVar

from tqdm import tqdm

try:
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.table import Table

    _RICH = True
except ImportError:
    _RICH = False

T = TypeVar("T")
console = Console() if _RICH else None


def write(msg: str, *, style: str = "") -> None:
    if _RICH and style:
        console.print(msg, style=style)
    else:
        print(msg, flush=True)


def section(title: str) -> None:
    if _RICH:
        console.rule(f"[bold cyan]{title}[/bold cyan]")
    else:
        print(f"\n=== {title} ===")


def print_table(rows: Sequence[Tuple[str, Any]], *, title: str = "") -> None:
    if title:
        section(title)
    if _RICH:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right", style="green")
        for label, value in rows:
            table.add_row(str(label), f"{value:,}" if isinstance(value, int) else str(value))
        console.print(table)
        return
    width = max(len(str(r[0])) for r in rows) if rows else 0
    for label, value in rows:
        if isinstance(value, int):
            print(f"{label:<{width}}  {value:>8,}")
        else:
            print(f"{label:<{width}}  {value}")


def count_nonempty_lines(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def count_jsonl_rows(
    path: Path,
    *,
    desc: Optional[str] = None,
    filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
) -> int:
    if not path.exists():
        return 0
    n = 0
    bar = tqdm(
        desc=desc or f"Count {path.name}",
        unit="row",
        dynamic_ncols=True,
        leave=False,
    )
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            bar.update(1)
            if filter_fn is None:
                n += 1
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if filter_fn(rec):
                n += 1
    bar.close()
    return n


def count_glob_rows(pattern: str, **kwargs) -> int:
    from glob import glob

    total = 0
    paths = sorted(glob(pattern))
    for path in tqdm(paths, desc="Count shards", unit="file", leave=False, dynamic_ncols=True):
        total += count_jsonl_rows(Path(path), desc=Path(path).name, **kwargs)
    return total


def iter_jsonl_records(
    path: Path,
    *,
    desc: Optional[str] = None,
    unit: str = "row",
    total: Optional[int] = None,
) -> Iterator[Dict[str, Any]]:
    if not path.exists():
        return
    bar = tqdm(
        desc=desc or path.name,
        unit=unit,
        total=total,
        dynamic_ncols=True,
    )
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            bar.update(1)
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
    bar.close()


def iter_jsonl_paths(
    paths: Iterable[str],
    *,
    desc: str = "Records",
    unit: str = "row",
) -> Iterator[Dict[str, Any]]:
    path_list = [Path(p) for p in paths]
    bar = tqdm(desc=desc, unit=unit, dynamic_ncols=True)
    for path in path_list:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                bar.update(1)
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    bar.close()


def map_with_progress(
    items: Iterable[T],
    fn: Callable[[T], Any],
    *,
    desc: str,
    unit: str = "item",
    total: Optional[int] = None,
) -> List[Any]:
    out: List[Any] = []
    for item in tqdm(items, desc=desc, unit=unit, total=total, dynamic_ncols=True):
        out.append(fn(item))
    return out


def run_steps(steps: Sequence[Tuple[str, List[str]]], *, cwd: Optional[Path] = None) -> None:
    """Run shell commands with a rich progress list (or plain prints)."""
    work = cwd or Path.cwd()
    if _RICH:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("Pipeline", total=len(steps))
            for label, cmd in steps:
                progress.update(task_id, description=label)
                result = subprocess.run(cmd, cwd=str(work))
                if result.returncode != 0:
                    raise SystemExit(result.returncode)
                progress.advance(task_id)
        return

    for i, (label, cmd) in enumerate(steps, 1):
        write(f"[{i}/{len(steps)}] {label}")
        result = subprocess.run(cmd, cwd=str(work))
        if result.returncode != 0:
            raise SystemExit(result.returncode)


def run_python(script: str, *args: str) -> List[str]:
    return [sys.executable, script, *args]
