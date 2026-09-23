"""Shared resumable JSONL anonymization loop (checkpoint + sharded output)."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from tqdm import tqdm

logger = logging.getLogger(__name__)


def checkpoint_path(output_dir: Path) -> Path:
    return output_dir / "_checkpoint.json"


def part_path(output_dir: Path, part_index: int) -> Path:
    return output_dir / f"anonymized_part_{part_index:05d}.jsonl"


def save_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    tmp_path = Path(f"{path}.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def load_checkpoint(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def discover_resume_state(output_dir: Path) -> Tuple[int, int, int, int]:
    part_files = sorted(output_dir.glob("anonymized_part_*.jsonl"))
    if not part_files:
        return 0, 1, 0, 0

    processed_count = 0
    for part in part_files:
        with part.open("r", encoding="utf-8") as f:
            for _ in f:
                processed_count += 1

    last_part = part_files[-1]
    try:
        current_part_index = int(last_part.stem.split("_")[-1])
    except ValueError:
        current_part_index = len(part_files)
    current_part_bytes = last_part.stat().st_size
    current_part_records = 0
    with last_part.open("r", encoding="utf-8") as f:
        for _ in f:
            current_part_records += 1

    return processed_count, current_part_index, current_part_bytes, current_part_records


def reset_output_dir(output_dir: Path) -> None:
    for part in sorted(output_dir.glob("anonymized_part_*.jsonl")):
        part.unlink()
    ckpt = checkpoint_path(output_dir)
    if ckpt.exists():
        ckpt.unlink()


def write_checkpoint(
    ckpt_path: Path,
    *,
    input_file: Path,
    processed_count: int,
    current_part_index: int,
    current_part_bytes: int,
    current_part_records: int,
    max_part_bytes: int,
    save_interval: int,
    extra: Dict[str, Any],
    complete: bool = False,
) -> None:
    payload = {
        "input_path": str(input_file),
        "processed_count": processed_count,
        "current_part_index": current_part_index,
        "current_part_bytes": current_part_bytes,
        "current_part_records": current_part_records,
        "max_part_bytes": max_part_bytes,
        "save_interval": save_interval,
        **extra,
    }
    if complete:
        payload["complete"] = True
    save_json_atomic(ckpt_path, payload)


def iter_jsonl_records(input_path: Path, *, require_any: Tuple[str, ...] = ()) -> Iterator[Dict[str, Any]]:
    paths: list[Path]
    if input_path.is_dir():
        paths = sorted(input_path.glob("*.jsonl"))
        paths = [p for p in paths if not p.name.startswith("anonymized_part_")]
        if not paths:
            raise FileNotFoundError(f"No JSONL files in {input_path}")
    else:
        paths = [input_path]

    for path in paths:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    logger.warning("Skipping malformed JSON in %s (%s)", path, exc)
                    continue
                if require_any and not any(rec.get(k) for k in require_any):
                    continue
                yield rec


def run_anonymize_jsonl(
    input_path: str,
    output_dir: str,
    *,
    record_iter: Callable[[Path], Iterator[Dict[str, Any]]],
    anonymize_record: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    anonymize_batch: Optional[Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]]] = None,
    progress_desc: str,
    progress_unit: str,
    resume: bool,
    save_interval: int,
    max_part_bytes: int,
    checkpoint_extra: Dict[str, Any],
    done_message: str,
    record_batch_size: int = 128,
) -> int:
    input_file = Path(input_path)
    output_dir_path = Path(output_dir)

    if not input_file.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    output_dir_path.mkdir(parents=True, exist_ok=True)
    ckpt_path = checkpoint_path(output_dir_path)

    if not resume:
        reset_output_dir(output_dir_path)

    start_idx = 0
    current_part_index = 1
    current_part_bytes = 0
    current_part_records = 0

    if resume and ckpt_path.exists():
        try:
            ckpt = load_checkpoint(ckpt_path)
            start_idx = int(ckpt.get("processed_count", 0))
            current_part_index = int(ckpt.get("current_part_index", 1))
            current_part_bytes = int(ckpt.get("current_part_bytes", 0))
            current_part_records = int(ckpt.get("current_part_records", 0))
            print(
                f"Resuming from checkpoint at record {start_idx:,}, part {current_part_index}."
            )
        except (json.JSONDecodeError, OSError, ValueError, TypeError) as exc:
            logger.warning("Could not load checkpoint (%s). Starting from scratch.", exc)

    disk_processed, disk_part_index, disk_part_bytes, disk_part_records = discover_resume_state(
        output_dir_path
    )
    if disk_processed != start_idx:
        print(
            f"Reconciling checkpoint with on-disk output: checkpoint={start_idx:,}, on_disk={disk_processed:,}."
        )
    start_idx = disk_processed
    current_part_index = disk_part_index
    current_part_bytes = disk_part_bytes
    current_part_records = disk_part_records

    current_part_path = part_path(output_dir_path, current_part_index)
    if current_part_path.exists() and current_part_bytes == 0:
        current_part_bytes = current_part_path.stat().st_size
    part_file = current_part_path.open("a", encoding="utf-8")

    if anonymize_record is None and anonymize_batch is None:
        raise ValueError("Provide anonymize_record and/or anonymize_batch")

    processed_count = start_idx
    record_idx = 0
    progress = tqdm(
        desc=progress_desc,
        unit=progress_unit,
        dynamic_ncols=True,
        initial=start_idx,
    )
    interrupted = False
    rec_batch_size = max(int(record_batch_size or 1), 1)

    def write_anon(anon: Dict[str, Any]) -> None:
        nonlocal current_part_index, current_part_bytes, current_part_records, part_file
        nonlocal processed_count
        out_line = json.dumps(anon, ensure_ascii=False, separators=(",", ":")) + "\n"
        line_bytes = len(out_line.encode("utf-8"))

        if current_part_records > 0 and current_part_bytes + line_bytes > max_part_bytes:
            part_file.close()
            current_part_index += 1
            current_part_records = 0
            current_part_bytes = 0
            next_part = part_path(output_dir_path, current_part_index)
            part_file = next_part.open("a", encoding="utf-8")

        part_file.write(out_line)
        current_part_bytes += line_bytes
        current_part_records += 1
        processed_count += 1
        progress.update(1)

        if processed_count % save_interval == 0:
            write_checkpoint(
                ckpt_path,
                input_file=input_file,
                processed_count=processed_count,
                current_part_index=current_part_index,
                current_part_bytes=current_part_bytes,
                current_part_records=current_part_records,
                max_part_bytes=max_part_bytes,
                save_interval=save_interval,
                extra=checkpoint_extra,
            )
            part_file.flush()
            os.fsync(part_file.fileno())
            progress.set_postfix(
                part=current_part_index,
                part_mb=round(current_part_bytes / (1024 * 1024), 1),
            )

    def flush_pending(pending: List[Dict[str, Any]]) -> None:
        if not pending:
            return
        if anonymize_batch is not None:
            anons = anonymize_batch(pending)
        else:
            assert anonymize_record is not None
            anons = [anonymize_record(rec) for rec in pending]
        for anon in anons:
            write_anon(anon)

    pending: List[Dict[str, Any]] = []
    try:
        for rec in record_iter(input_file):
            if record_idx < start_idx:
                record_idx += 1
                continue
            record_idx += 1
            pending.append(rec)
            if len(pending) >= rec_batch_size:
                flush_pending(pending)
                pending = []
        flush_pending(pending)
        pending = []
    except KeyboardInterrupt:
        interrupted = True
        print("\nInterrupted; saving checkpoint...")
    finally:
        part_file.close()
        progress.close()
        write_checkpoint(
            ckpt_path,
            input_file=input_file,
            processed_count=processed_count,
            current_part_index=current_part_index,
            current_part_bytes=current_part_bytes,
            current_part_records=current_part_records,
            max_part_bytes=max_part_bytes,
            save_interval=save_interval,
            extra=checkpoint_extra,
            complete=not interrupted,
        )

    if interrupted:
        print(f"{done_message} {processed_count:,} records (interrupted) -> {output_dir_path}")
        raise SystemExit(130)

    print(f"{done_message} {processed_count:,} records -> {output_dir_path}")
    return processed_count
