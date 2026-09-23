"""Write data/us/anonymized_manifest.json — inventory of anonymized outputs for git."""

import sys
from pathlib import Path

_SCRIPTS_ROOT = Path(__file__).resolve().parents[0]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from tqdm import tqdm

from common.progress import section, write


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def count_jsonl_rows(path: Path) -> int:
    n = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def load_checkpoint(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def describe_dataset(
    *,
    name: str,
    output_dir: Path,
    part_glob: str,
    regenerate_script: str,
    include_hashes: bool,
) -> Dict[str, Any]:
    parts = sorted(output_dir.glob(part_glob)) if output_dir.is_dir() else []
    ckpt = load_checkpoint(output_dir / "_checkpoint.json")
    part_entries: List[Dict[str, Any]] = []
    total_bytes = 0
    total_rows = 0

    for part in tqdm(parts, desc=f"{name} parts", unit="file", leave=False, dynamic_ncols=True):
        rows = count_jsonl_rows(part)
        size = part.stat().st_size
        total_bytes += size
        total_rows += rows
        entry: Dict[str, Any] = {
            "path": str(part.as_posix()),
            "rows": rows,
            "bytes": size,
        }
        if include_hashes:
            entry["sha256"] = sha256_file(part)
        part_entries.append(entry)

    return {
        "name": name,
        "output_dir": str(output_dir.as_posix()),
        "regenerate_script": regenerate_script,
        "checkpoint": ckpt,
        "complete": bool((ckpt or {}).get("complete")) if ckpt else False,
        "processed_count": int((ckpt or {}).get("processed_count", total_rows)),
        "parts": part_entries,
        "total_rows": total_rows,
        "total_bytes": total_bytes,
    }


def build_manifest(data_root: Path, *, include_hashes: bool) -> Dict[str, Any]:
    common = {"include_hashes": include_hashes}
    specs = [
        describe_dataset(
            name="gdelt_web_news",
            output_dir=data_root / "news" / "anonymized",
            part_glob="anonymized_part_*.jsonl",
            regenerate_script=(
                "scripts/refresh_derived.py  # classify unified corpus → anonymize"
            ),
            **common,
        ),
        describe_dataset(
            name="gdelt_tv",
            output_dir=data_root / "tv" / "anonymized",
            part_glob="anonymized_part_*.jsonl",
            regenerate_script="scripts/anonymize/gdelt_tv.py",
            **common,
        ),
        describe_dataset(
            name="aapb_radio_english",
            output_dir=data_root / "english" / "radio" / "anonymized",
            part_glob="anonymized_part_*.jsonl",
            regenerate_script="scripts/anonymize/aapb_radio.py --language english",
            **common,
        ),
        describe_dataset(
            name="aapb_radio_spanish",
            output_dir=data_root / "spanish" / "radio" / "anonymized",
            part_glob="anonymized_part_*.jsonl",
            regenerate_script="scripts/anonymize/aapb_radio.py --language spanish",
            **common,
        ),
        describe_dataset(
            name="spotify_podcasts",
            output_dir=data_root / "spotify" / "anonymized",
            part_glob="anonymized_part_*.jsonl",
            regenerate_script="scripts/anonymize/spotify.py",
            **common,
        ),
        describe_dataset(
            name="youtube",
            output_dir=data_root / "youtube" / "anonymized",
            part_glob="anonymized_part_*.jsonl",
            regenerate_script="scripts/anonymize/youtube.py",
            **common,
        ),
        describe_dataset(
            name="google_search",
            output_dir=data_root / "google_search" / "anonymized",
            part_glob="anonymized_part_*.jsonl",
            regenerate_script="scripts/anonymize/google_search.py",
            **common,
        ),
    ]
    datasets = []
    for spec in tqdm(specs, desc="Datasets", unit="dataset", dynamic_ncols=True):
        datasets.append(spec)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Anonymized JSONL shards are plain git blobs, kept under ~40 MiB each "
            "(see --max-part-gb on anonymize scripts). Checkpoints and this manifest "
            "are plain git. Raw/classified GDELT web files are gitignored; regenerate "
            "with the scripts listed per dataset."
        ),
        "git_lfs": False,
        "datasets": datasets,
    }


def parse_args() -> argparse.Namespace:
    default_root = os.path.join("data", "us")
    default_out = os.path.join(default_root, "anonymized_manifest.json")
    p = argparse.ArgumentParser(description="Build anonymized data manifest for git.")
    p.add_argument("--data-root", default=default_root)
    p.add_argument("--output", "-o", default=default_out)
    p.add_argument("--no-hashes", action="store_true", help="Skip sha256 (faster).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    data_root = Path(args.data_root)
    out_path = Path(args.output)
    include_hashes = not args.no_hashes

    section("Anonymized manifest")
    if include_hashes:
        write("Computing sha256 hashes (use --no-hashes to skip).")
    manifest = build_manifest(data_root, include_hashes=include_hashes)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(out_path)
    total_rows = sum(d["total_rows"] for d in manifest["datasets"])
    write(
        f"Wrote {out_path} ({len(manifest['datasets'])} datasets, {total_rows:,} rows)",
        style="bold green",
    )


if __name__ == "__main__":
    main()

