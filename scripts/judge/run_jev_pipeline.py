#!/usr/bin/env python3
"""Education-track Jev pipeline: dual taxonomies + stratified sample + $ budget.

Parallel OpenRouter calls, tqdm progress, incremental JSONL, and a cost ledger so
resume continues the *same* budget (spent is carried forward — not a fresh $7).

Examples:

  python3 scripts/judge/run_jev_pipeline.py --dry-run --total 2000 --budget-usd 7
  python3 scripts/judge/run_jev_pipeline.py --self-test
  python3 scripts/judge/run_jev_pipeline.py --total 500 --budget-usd 1 --workers 8
  python3 scripts/judge/run_jev_pipeline.py --resume out.jsonl --budget-usd 7 --workers 8
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import threading
import time
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from tqdm import tqdm  # noqa: E402

from common.config import OPENROUTER_JEV_MODEL  # noqa: E402
from common.content_acts import discourse_modes  # noqa: E402
from common.openrouter_jev import (  # noqa: E402
    JEV_INPUT_USD_PER_MTOK,
    OpenRouterJevError,
    approx_tokens,
    build_judge_questions,
    estimate_usd,
    jev_decide,
    parse_judge_answers,
)
from common.stratified_sample import (  # noqa: E402
    DEFAULT_QUOTAS,
    load_sample_cache,
    save_sample_cache,
    stratified_sample,
)
from common.taxonomies import (  # noqa: E402
    human_review_confidence_below,
    include_threshold,
    label_ids,
    taxonomy_bundle,
)

OUT_DIR = ROOT / "papers" / "rise_education_2026" / "analysis" / "jev_judgments"
CACHE_DIR = OUT_DIR / "samples"

_SOURCE_PRIORITY = (
    "gdelt_news_us",
    "gdelt_news_americas",
    "aapb_es",
    "aapb_en",
    "americas_radio",
    "gdelt_tv",
    "youtube",
    "americas_youtube",
)


def scale_quotas(total: int, base: dict[str, int] | None = None) -> dict[str, int]:
    if total < 1:
        raise ValueError("--total must be >= 1")
    base = dict(base or DEFAULT_QUOTAS)
    keys = [k for k in _SOURCE_PRIORITY if k in base] + [
        k for k in sorted(base) if k not in _SOURCE_PRIORITY
    ]
    while len(keys) > total:
        keys.pop()
    base = {k: base[k] for k in keys}
    s = sum(base.values()) or 1
    raw = {k: max(1, int(round(total * v / s))) for k, v in base.items()}
    drift = total - sum(raw.values())
    order = sorted(raw.keys(), key=lambda k: -raw[k])
    i = guard = 0
    while drift != 0 and order and guard < len(order) * 50:
        k = order[i % len(order)]
        if drift > 0:
            raw[k] += 1
            drift -= 1
        elif raw[k] > 1:
            raw[k] -= 1
            drift += 1
        i += 1
        guard += 1
    return raw


def balance_languages(
    rows: list[dict],
    *,
    target_es_frac: float = 0.25,
    target_pt_frac: float = 0.10,
    seed: int = 42,
) -> list[dict]:
    if not rows:
        return rows
    rng = random.Random(seed)
    buckets: dict[str, list[dict]] = {
        "english": [],
        "spanish": [],
        "portuguese": [],
        "other": [],
    }
    for r in rows:
        lang = (r.get("language") or "other").lower()
        buckets[lang if lang in buckets else "other"].append(r)
    for b in buckets.values():
        rng.shuffle(b)
    n = len(rows)
    want_es = min(len(buckets["spanish"]), max(0, int(round(n * target_es_frac))))
    want_pt = min(len(buckets["portuguese"]), max(0, int(round(n * target_pt_frac))))
    out: list[dict] = []
    out.extend(buckets["spanish"][:want_es])
    out.extend(buckets["portuguese"][:want_pt])
    remain = n - len(out)
    rest = (
        buckets["english"]
        + buckets["other"]
        + buckets["spanish"][want_es:]
        + buckets["portuguese"][want_pt:]
    )
    rng.shuffle(rest)
    out.extend(rest[:remain])
    rng.shuffle(out)
    return out


def row_uid(row: dict, text: str) -> str:
    parts = [
        str(row.get("source") or ""),
        str(row.get("record_id") or row.get("event_id") or row.get("article_id") or ""),
        hashlib.sha1(text.encode("utf-8")).hexdigest()[:16],
    ]
    return "|".join(parts)


def cost_ledger_path(out: Path) -> Path:
    return out.with_suffix(".cost.json")


def load_prior_spend(out: Path, usd_est: float) -> tuple[set[str], float, int]:
    """Return (done_ids, spent_usd, n_ok) from JSONL + cost ledger / summary."""
    done: set[str] = set()
    spent = 0.0
    n_ok = 0
    if out.exists():
        with out.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                uid = rec.get("id")
                if not uid:
                    continue
                if rec.get("error"):
                    continue
                done.add(uid)
                n_ok += 1
                usage = rec.get("usage") or {}
                c = 0.0
                try:
                    c = float(usage.get("cost") or 0)
                except (TypeError, ValueError):
                    c = 0.0
                if c <= 0 and usage.get("input_tokens"):
                    try:
                        c = estimate_usd(int(usage["input_tokens"]))
                    except (TypeError, ValueError):
                        c = 0.0
                if c <= 0:
                    c = float(rec.get("cost_usd") or 0) or usd_est
                spent += c

    ledger = cost_ledger_path(out)
    if ledger.exists():
        try:
            data = json.loads(ledger.read_text(encoding="utf-8"))
            ledger_spent = float(data.get("spent_usd") or 0)
            # Prefer the larger of summed JSONL vs ledger (ledger may be ahead if crash mid-write)
            spent = max(spent, ledger_spent)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    summary = out.with_suffix(".summary.json")
    if summary.exists():
        try:
            data = json.loads(summary.read_text(encoding="utf-8"))
            spent = max(spent, float(data.get("total_cost_usd") or 0))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    return done, spent, n_ok


def write_cost_ledger(
    out: Path,
    *,
    budget_usd: float,
    spent_usd: float,
    usd_est: float,
    wrote_session: int,
    n_ok_total: int,
    status: str = "running",
) -> None:
    payload = {
        "budget_usd": budget_usd,
        "spent_usd": round(spent_usd, 8),
        "remaining_usd": round(max(0.0, budget_usd - spent_usd), 8),
        "usd_per_example_estimate": usd_est,
        "n_ok_total": n_ok_total,
        "wrote_this_session": wrote_session,
        "status": status,
        "updated": datetime.now(timezone.utc).isoformat(),
        "model": OPENROUTER_JEV_MODEL,
        "out": str(out),
    }
    path = cost_ledger_path(out)
    tmp = path.with_suffix(".cost.json.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_input_jsonl(path: Path, *, total: int, min_text: int, max_chars: int) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            text = rec.get("text") or rec.get("paragraph_text") or ""
            if len(text) < min_text:
                continue
            rows.append(
                {
                    "source": rec.get("source") or "input",
                    "family": rec.get("family") or "other",
                    "language": rec.get("language") or "",
                    "record_id": rec.get("record_id") or rec.get("event_id") or "",
                    "text": text[:max_chars],
                }
            )
            if len(rows) >= total:
                break
    return rows


def build_sample(args: argparse.Namespace) -> list[dict]:
    if args.sample_cache and Path(args.sample_cache).exists() and not args.refresh_sample:
        rows = load_sample_cache(Path(args.sample_cache))
        print(f"loaded sample cache n={len(rows)} ← {args.sample_cache}")
        return rows[: args.total] if args.total else rows

    fetch_n = max(args.total, int(args.total * 1.35))
    quotas = scale_quotas(fetch_n)
    print(f"stratified sample fetch={fetch_n} (keep={args.total}) quotas={quotas}")
    rows = stratified_sample(
        ROOT,
        total=fetch_n,
        quotas=quotas,
        seed=args.seed,
        min_text=args.min_text,
        text_cap=args.max_chars,
    )
    rows = balance_languages(rows, seed=args.seed)
    if len(rows) > args.total:
        rows = rows[: args.total]

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = Path(args.sample_cache) if args.sample_cache else (
        CACHE_DIR / f"stratified_{args.total}_s{args.seed}.jsonl"
    )
    save_sample_cache(cache_path, rows)
    print(f"wrote sample cache n={len(rows)} → {cache_path.relative_to(ROOT)}")
    lang_c = Counter((r.get("language") or "?") for r in rows)
    src_c = Counter((r.get("source") or "?") for r in rows)
    print(f"  languages: {dict(lang_c)}")
    print(f"  sources: {dict(src_c)}")
    return rows


def judge_one(
    row: dict,
    *,
    questions: dict[str, Any],
    content_tax: dict | None,
    discourse_tax: dict | None,
    max_chars: int,
    min_text: int,
    c_thr: float,
    d_thr: float,
    review_conf: float,
    usd_est: float,
) -> tuple[str, dict[str, Any] | None, float, str | None]:
    """Return (uid, record_or_None, cost_usd, error_or_None)."""
    text = (row.get("text") or "")[:max_chars]
    uid = row_uid(row, text)
    if len(text) < min_text:
        return uid, None, 0.0, "text_too_short"
    cues = discourse_modes(text)
    state = {
        "language": row.get("language") or "",
        "source": row.get("source") or "",
        "family": row.get("family") or "",
        "text": text,
        "task": "dual_taxonomy_informal_learning",
        "content_taxonomy": (content_tax or {}).get("version"),
        "discourse_taxonomy": (discourse_tax or {}).get("version"),
        "surface_cues": {k: bool(v) for k, v in cues.items()},
    }
    try:
        resp = jev_decide(state, questions)
    except OpenRouterJevError as e:
        return uid, None, 0.0, str(e)

    parsed = parse_judge_answers(
        resp.get("answers") or {},
        content_include_at=c_thr,
        discourse_include_at=d_thr,
        human_review_conf_below=review_conf,
    )
    usage = resp.get("usage") or {}
    cost = 0.0
    try:
        cost = float(usage.get("cost") or 0.0)
    except (TypeError, ValueError):
        cost = 0.0
    if cost <= 0 and usage.get("input_tokens"):
        try:
            cost = estimate_usd(int(usage["input_tokens"]))
        except (TypeError, ValueError):
            cost = 0.0
    if cost <= 0:
        cost = usd_est
    rec = {
        "id": uid,
        "language": state["language"],
        "source": state["source"],
        "family": state["family"],
        "text_preview": text[:240],
        "surface_cues": state["surface_cues"],
        "model": resp.get("model"),
        "usage": usage,
        "cost_usd": cost,
        **parsed,
    }
    return uid, rec, cost, None


def self_test() -> int:
    bundle = taxonomy_bundle(content=True, discourse=True)
    q = build_judge_questions(
        content_tax=bundle["content"],
        discourse_tax=bundle["discourse"],
        with_accuracy=True,
    )
    assert len(q) == len(label_ids(bundle["content"])) + len(label_ids(bundle["discourse"])) + 1
    fake = {
        "content_cst_papal": {"type": "noul", "noul": 0.91},
        "discourse_news_report": {"type": "noul", "noul": 0.8},
        "factual_theological_accuracy": {
            "type": "score",
            "score": 3.1,
            "confidence": 0.7,
        },
    }
    parsed = parse_judge_answers(fake)
    assert "cst_papal" in parsed["content_labels"]
    assert sum(scale_quotas(5).values()) == 5
    # cost ledger round-trip
    tmp = OUT_DIR / "_selftest_cost.jsonl"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_cost_ledger(tmp, budget_usd=7.0, spent_usd=1.5, usd_est=0.0001, wrote_session=0, n_ok_total=10)
    assert cost_ledger_path(tmp).exists()
    cost_ledger_path(tmp).unlink(missing_ok=True)
    from common.taxonomies import validate_taxonomy_schema

    for tax in (bundle["content"], bundle["discourse"]):
        verrs = validate_taxonomy_schema(tax, require_examples=True)
        assert not verrs, verrs
    fixture = (
        ROOT
        / "papers/rise_education_2026/analysis/jev_judgments/fixtures/demo_dual_en_es_pt.jsonl"
    )
    assert fixture.exists(), "missing offline fixture pack"
    print("self-test OK")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--total", type=int, default=500, help="Stratified sample size to keep")
    p.add_argument(
        "--budget-usd",
        type=float,
        default=1.0,
        help="Lifetime budget cap (resume subtracts prior spend from this same cap)",
    )
    p.add_argument("--workers", type=int, default=8, help="Parallel OpenRouter calls (1=serial)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--min-text", type=int, default=80)
    p.add_argument("--max-chars", type=int, default=1600)
    p.add_argument("--sleep", type=float, default=0.0, help="Optional pause after each completed call")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--content", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--discourse", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--accuracy", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--sample-cache", type=Path, default=None)
    p.add_argument("--refresh-sample", action="store_true")
    p.add_argument("--resume", type=Path, default=None, help="Append to this JSONL; carry spend forward")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--input", type=Path, default=None)
    args = p.parse_args()

    if args.self_test:
        return self_test()
    if args.workers < 1:
        raise SystemExit("--workers must be >= 1")

    bundle = taxonomy_bundle(content=args.content, discourse=args.discourse)
    content_tax = bundle["content"]
    discourse_tax = bundle["discourse"]
    questions = build_judge_questions(
        content_tax=content_tax,
        discourse_tax=discourse_tax,
        with_accuracy=bool(args.accuracy and content_tax),
    )
    c_thr = include_threshold(content_tax) if content_tax else 0.55
    d_thr = include_threshold(discourse_tax) if discourse_tax else 0.55
    review_conf = human_review_confidence_below(content_tax) if content_tax else 0.45

    demo_state = {
        "language": "english",
        "source": "estimate",
        "family": "news",
        "text": "x" * 320,
        "task": "dual_taxonomy_informal_learning",
        "content_taxonomy": (content_tax or {}).get("version"),
        "discourse_taxonomy": (discourse_tax or {}).get("version"),
    }
    tok_est = approx_tokens(
        {"model": OPENROUTER_JEV_MODEL, "state": demo_state, "questions": questions}
    )
    usd_est = estimate_usd(tok_est)
    n_budget = int(args.budget_usd / usd_est) if usd_est else 0
    print(
        f"estimate ~{tok_est} input tok/ex × ${JEV_INPUT_USD_PER_MTOK}/M "
        f"≈ ${usd_est:.6f}/ex → @${args.budget_usd:.2f} ≈ {n_budget:,} examples "
        f"(workers={args.workers}, content={args.content}, discourse={args.discourse})"
    )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "model": OPENROUTER_JEV_MODEL,
                    "n_questions": len(questions),
                    "workers": args.workers,
                    "budget_usd": args.budget_usd,
                },
                indent=2,
            )
        )
        return 0

    if args.input:
        rows = load_input_jsonl(
            args.input, total=args.total, min_text=args.min_text, max_chars=args.max_chars
        )
        print(f"loaded input file n={len(rows)}")
    else:
        rows = build_sample(args)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(args.resume) if args.resume else (
        args.out or (OUT_DIR / f"jev_dual_{stamp}.jsonl")
    )

    done, prior_spent, n_prior = load_prior_spend(out, usd_est)
    spent = prior_spent
    remaining = args.budget_usd - spent
    if done:
        print(
            f"resume: {len(done)} done, prior_spend=${prior_spent:.4f}, "
            f"budget=${args.budget_usd:.2f}, remaining≈${remaining:.4f}"
        )
    if remaining <= usd_est:
        print(f"budget already exhausted (remaining ${remaining:.4f}) — nothing to do")
        write_cost_ledger(
            out,
            budget_usd=args.budget_usd,
            spent_usd=spent,
            usd_est=usd_est,
            wrote_session=0,
            n_ok_total=n_prior,
            status="exhausted",
        )
        return 0

    meta = {
        "started": stamp,
        "model": OPENROUTER_JEV_MODEL,
        "budget_usd": args.budget_usd,
        "prior_spent_usd": prior_spent,
        "workers": args.workers,
        "total_requested": args.total,
        "content_path": bundle["content_path"],
        "discourse_path": bundle["discourse_path"],
        "usd_per_example_estimate": usd_est,
    }
    out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    write_cost_ledger(
        out,
        budget_usd=args.budget_usd,
        spent_usd=spent,
        usd_est=usd_est,
        wrote_session=0,
        n_ok_total=n_prior,
        status="running",
    )

    # Build pending worklist (skip done)
    pending: list[dict] = []
    skipped = 0
    for row in rows:
        text = (row.get("text") or "")[: args.max_chars]
        if len(text) < args.min_text:
            continue
        uid = row_uid(row, text)
        if uid in done:
            skipped += 1
            continue
        pending.append(row)

    # Cap pending by remaining budget (estimate)
    max_by_budget = max(0, int(remaining / usd_est)) if usd_est else len(pending)
    if len(pending) > max_by_budget:
        print(f"capping pending {len(pending)} → {max_by_budget} by remaining budget")
        pending = pending[:max_by_budget]

    written = 0
    errors = 0
    lock = threading.Lock()
    stop = threading.Event()
    mode = "a" if out.exists() else "w"

    def _write(sink, rec: dict) -> None:
        sink.write(json.dumps(rec, ensure_ascii=False) + "\n")
        sink.flush()

    try:
        with out.open(mode, encoding="utf-8") as sink:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures: dict[Future, float] = {}
                pending_iter = iter(pending)
                reserved_inflight = 0.0

                def submit_one() -> bool:
                    nonlocal reserved_inflight
                    if stop.is_set():
                        return False
                    with lock:
                        if spent + reserved_inflight + usd_est > args.budget_usd + 1e-12:
                            return False
                    try:
                        row = next(pending_iter)
                    except StopIteration:
                        return False
                    fut = pool.submit(
                        judge_one,
                        row,
                        questions=questions,
                        content_tax=content_tax,
                        discourse_tax=discourse_tax,
                        max_chars=args.max_chars,
                        min_text=args.min_text,
                        c_thr=c_thr,
                        d_thr=d_thr,
                        review_conf=review_conf,
                        usd_est=usd_est,
                    )
                    futures[fut] = usd_est
                    reserved_inflight += usd_est
                    return True

                for _ in range(args.workers):
                    if not submit_one():
                        break

                pbar = tqdm(total=len(pending), desc="jev", unit="ex")
                try:
                    while futures:
                        done_fut = next(as_completed(futures))
                        reserved = futures.pop(done_fut, usd_est)
                        reserved_inflight = max(0.0, reserved_inflight - reserved)
                        try:
                            uid, rec, cost, err = done_fut.result()
                        except Exception as e:  # noqa: BLE001
                            errors += 1
                            with lock:
                                _write(sink, {"id": "unknown", "error": str(e)})
                            pbar.update(1)
                            if not stop.is_set():
                                submit_one()
                            continue

                        with lock:
                            if err and rec is None:
                                errors += 1
                                _write(sink, {"id": uid, "error": err, "text_preview": ""})
                            elif rec is not None:
                                spent += cost
                                written += 1
                                done.add(uid)
                                _write(sink, rec)
                                write_cost_ledger(
                                    out,
                                    budget_usd=args.budget_usd,
                                    spent_usd=spent,
                                    usd_est=usd_est,
                                    wrote_session=written,
                                    n_ok_total=n_prior + written,
                                    status="running",
                                )
                                if spent + usd_est > args.budget_usd:
                                    stop.set()
                            pbar.set_postfix(
                                spent=f"${spent:.4f}",
                                left=f"${max(0.0, args.budget_usd - spent):.4f}",
                                refresh=False,
                            )
                            pbar.update(1)

                        if args.sleep:
                            time.sleep(args.sleep)
                        if not stop.is_set():
                            submit_one()
                finally:
                    pbar.close()

                if stop.is_set():
                    for fut in list(futures):
                        fut.cancel()
                        futures.pop(fut, None)
    except KeyboardInterrupt:
        print("\ninterrupted — ledger + JSONL already flushed", file=sys.stderr)
        stop.set()

    write_cost_ledger(
        out,
        budget_usd=args.budget_usd,
        spent_usd=spent,
        usd_est=usd_est,
        wrote_session=written,
        n_ok_total=n_prior + written,
        status="stopped" if stop.is_set() else "done",
    )

    try:
        out_rel = str(out.relative_to(ROOT))
    except ValueError:
        out_rel = str(out)
    summary = {
        "wrote_this_session": written,
        "errors": errors,
        "skipped_resume": skipped,
        "prior_spent_usd": round(prior_spent, 6),
        "total_cost_usd": round(spent, 6),
        "budget_usd": args.budget_usd,
        "remaining_usd": round(max(0.0, args.budget_usd - spent), 6),
        "workers": args.workers,
        "out": out_rel,
        "cost_ledger": str(cost_ledger_path(out)),
    }
    try:
        summary["cost_ledger"] = str(cost_ledger_path(out).relative_to(ROOT))
    except ValueError:
        pass
    print(json.dumps(summary, indent=2))
    out.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return 0 if errors == 0 or written > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
