"""High-level anonymization helpers built on the resumable JSONL loop."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from collections import defaultdict
import atexit
from concurrent.futures import ProcessPoolExecutor
import os
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple

from common.anonymize_jsonl import iter_jsonl_records, run_anonymize_jsonl
from common.deidentify import DEFAULT_PIPE_BATCH_SIZE, deidentify_text, deidentify_texts, load_spacy_model

logger = logging.getLogger(__name__)

FieldPair = Tuple[str, str]

API_RAW_TEXT_KEYS = frozenset({
    "title",
    "description",
    "snippet",
    "content",
    "summary",
    "body",
    "text",
    "paragraph_text",
    "full_text",
    "overview",
    "transcript",
    "htmlSnippet",
    "htmlTitle",
    "displayLink",
})


def language_for_record(lang: Any, *, fallback: str = "english") -> str:
    if not lang:
        return fallback
    normalized = str(lang).lower().strip()
    if normalized in ("spanish", "es"):
        return "spanish"
    if normalized in ("portuguese", "pt"):
        return "portuguese"
    if normalized in ("unknown", "und", "other"):
        return fallback
    return "english"


class LazyNlpMap:
    """Load spaCy models on first use so English-only batches skip Spanish."""

    def __init__(self, languages: Sequence[str], *, use_gpu: bool = False):
        self.languages = tuple(languages)
        self.use_gpu = use_gpu
        self._loaded: Dict[str, Any] = {}

    def __contains__(self, key: object) -> bool:
        return key in self.languages or key in self._loaded

    def __iter__(self):
        return iter(self.languages)

    def __getitem__(self, key: str):
        if key not in self._loaded:
            if key not in self.languages:
                raise KeyError(key)
            self._loaded[key] = load_spacy_model(use_gpu=self.use_gpu, language=key)
        return self._loaded[key]


def load_bilingual_models(*, use_gpu: bool = False):
    print("Loading spaCy models (english + spanish + portuguese, NER only)...")
    nlp = {
        "english": load_spacy_model(use_gpu=use_gpu, language="english"),
        "spanish": load_spacy_model(use_gpu=use_gpu, language="spanish"),
        "portuguese": load_spacy_model(use_gpu=use_gpu, language="portuguese"),
    }
    return nlp, {"english": None, "spanish": None, "portuguese": None}


def load_english_models(*, use_gpu: bool = False):
    print("Loading spaCy model (english, NER only)...")
    nlp = load_spacy_model(use_gpu=use_gpu, language="english")
    return nlp, None


def redact_api_raw(api_raw: Any, *, text_keys: Optional[frozenset] = None) -> Any:
    """Remove or redact free-text fields inside api_raw payloads."""
    keys = text_keys or API_RAW_TEXT_KEYS
    if isinstance(api_raw, dict):
        out: Dict[str, Any] = {}
        for key, value in api_raw.items():
            if key in keys and isinstance(value, str) and value.strip():
                out[key] = "[REDACTED]"
            elif isinstance(value, (dict, list)):
                out[key] = redact_api_raw(value, text_keys=keys)
            else:
                out[key] = value
        return out
    if isinstance(api_raw, list):
        return [redact_api_raw(item, text_keys=keys) for item in api_raw]
    return api_raw


def deidentify_fields(
    record: Dict[str, Any],
    field_pairs: Sequence[FieldPair],
    *,
    language: str,
    nlp,
    deidentifier=None,
    strip_originals: bool = True,
    strip_api_raw: bool = True,
    redact_api_raw_text: bool = True,
) -> Dict[str, Any]:
    out = dict(record)
    for src, dst in field_pairs:
        text = out.get(src)
        if isinstance(text, str) and text.strip():
            out[dst] = deidentify_text(text, nlp=nlp, language=language)
        if strip_originals:
            out.pop(src, None)
            if dst in out:
                out[src] = out.pop(dst)

    if strip_api_raw:
        out.pop("api_raw", None)
    elif redact_api_raw_text and "api_raw" in out:
        out["api_raw"] = redact_api_raw(out["api_raw"])

    return out


def anonymize_records_batch(
    records: List[Dict[str, Any]],
    field_pairs: Sequence[FieldPair],
    *,
    nlp_by_language: Dict[str, Any],
    language_field: Optional[str] = None,
    fixed_language: str = "english",
    fallback_language: str = "english",
    strip_originals: bool = True,
    strip_api_raw: bool = True,
    redact_api_raw_text: bool = True,
    pipe_batch_size: int = DEFAULT_PIPE_BATCH_SIZE,
) -> List[Dict[str, Any]]:
    """Deidentify a list of records with nlp.pipe (grouped by language)."""
    if not records:
        return []
    buckets: Dict[str, List[Tuple[int, str, str]]] = defaultdict(list)
    langs: List[str] = []
    for i, rec in enumerate(records):
        if language_field:
            lang = language_for_record(rec.get(language_field), fallback=fallback_language)
        else:
            lang = fixed_language
        if lang not in nlp_by_language:
            lang = fallback_language if fallback_language in nlp_by_language else next(iter(nlp_by_language))
        langs.append(lang)
        for src, _dst in field_pairs:
            text = rec.get(src)
            if isinstance(text, str) and text.strip():
                buckets[lang].append((i, src, text))

    filled: Dict[Tuple[int, str], str] = {}
    for lang, items in buckets.items():
        nlp = nlp_by_language[lang]
        deids = deidentify_texts([t for _i, _s, t in items], nlp, batch_size=pipe_batch_size)
        for (i, src, _t), deid in zip(items, deids):
            filled[(i, src)] = deid

    outs: List[Dict[str, Any]] = []
    for i, rec in enumerate(records):
        out = dict(rec)
        for src, dst in field_pairs:
            if (i, src) in filled:
                out[dst] = filled[(i, src)]
            if strip_originals:
                out.pop(src, None)
                if dst in out:
                    out[src] = out.pop(dst)
        if strip_api_raw:
            out.pop("api_raw", None)
        elif redact_api_raw_text and "api_raw" in out:
            out["api_raw"] = redact_api_raw(out["api_raw"])
        outs.append(out)
    return outs


def make_field_anonymizer(
    field_pairs: Sequence[FieldPair],
    *,
    nlp_by_language: Dict[str, Any],
    deidentifier_by_language: Dict[str, Any],
    language_field: Optional[str] = None,
    fixed_language: str = "english",
    fallback_language: str = "english",
    strip_originals: bool = True,
    strip_api_raw: bool = True,
    redact_api_raw_text: bool = True,
):
    def anonymize_record(record: Dict[str, Any]) -> Dict[str, Any]:
        if language_field:
            language = language_for_record(record.get(language_field), fallback=fallback_language)
        else:
            language = fixed_language
        return deidentify_fields(
            record,
            field_pairs,
            language=language,
            nlp=nlp_by_language[language],
            deidentifier=deidentifier_by_language[language],
            strip_originals=strip_originals,
            strip_api_raw=strip_api_raw,
            redact_api_raw_text=redact_api_raw_text,
        )

    return anonymize_record


_MP_STATE: Dict[str, Any] = {}


def _mp_init(payload: Dict[str, Any]) -> None:
    langs = ("english", "spanish", "portuguese") if payload.get("bilingual", True) else ("english",)
    _MP_STATE.clear()
    _MP_STATE["nlp"] = LazyNlpMap(langs, use_gpu=False)
    _MP_STATE.update(payload)


def _mp_anonymize_chunk(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return anonymize_records_batch(
        records,
        _MP_STATE["field_pairs"],
        nlp_by_language=_MP_STATE["nlp"],
        language_field=_MP_STATE.get("language_field"),
        fixed_language=_MP_STATE.get("fixed_language") or "english",
        fallback_language=_MP_STATE.get("fallback_language") or "english",
        strip_originals=_MP_STATE.get("strip_originals", True),
        strip_api_raw=_MP_STATE.get("strip_api_raw", True),
        redact_api_raw_text=_MP_STATE.get("redact_api_raw_text", True),
        pipe_batch_size=int(_MP_STATE.get("pipe_batch_size") or DEFAULT_PIPE_BATCH_SIZE),
    )


def default_anonymize_workers() -> int:
    cpus = os.cpu_count() or 2
    return max(1, min(8, cpus - 1))


def make_batch_anonymizer(
    field_pairs: Sequence[FieldPair],
    *,
    nlp_by_language: Optional[Dict[str, Any]] = None,
    language_field: Optional[str] = None,
    fixed_language: str = "english",
    fallback_language: str = "english",
    strip_originals: bool = True,
    strip_api_raw: bool = True,
    redact_api_raw_text: bool = True,
    pipe_batch_size: int = DEFAULT_PIPE_BATCH_SIZE,
    workers: int = 1,
    bilingual: bool = True,
):
    pairs = list(field_pairs)
    strip_kw = {
        "strip_originals": strip_originals,
        "strip_api_raw": strip_api_raw,
        "redact_api_raw_text": redact_api_raw_text,
    }
    if workers and workers > 1:
        payload = {
            "field_pairs": pairs,
            "language_field": language_field,
            "fixed_language": fixed_language,
            "fallback_language": fallback_language,
            "pipe_batch_size": pipe_batch_size,
            "bilingual": bilingual,
            **strip_kw,
        }
        pool = ProcessPoolExecutor(
            max_workers=int(workers),
            initializer=_mp_init,
            initargs=(payload,),
        )
        atexit.register(pool.shutdown, wait=False)

        def anonymize_batch(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            if not records:
                return []
            n = int(workers)
            chunk = max(1, (len(records) + n - 1) // n)
            chunks = [records[i : i + chunk] for i in range(0, len(records), chunk)]
            futs = [pool.submit(_mp_anonymize_chunk, c) for c in chunks]
            out: List[Dict[str, Any]] = []
            for fut in futs:
                out.extend(fut.result())
            return out

        return anonymize_batch

    if nlp_by_language is None:
        raise ValueError("nlp_by_language required when workers<=1")

    def anonymize_batch(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return anonymize_records_batch(
            records,
            pairs,
            nlp_by_language=nlp_by_language,
            language_field=language_field,
            fixed_language=fixed_language,
            fallback_language=fallback_language,
            pipe_batch_size=pipe_batch_size,
            **strip_kw,
        )

    return anonymize_batch


def add_standard_cli(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--save-interval", type=int, default=500)
    parser.add_argument(
        "--max-part-gb",
        type=float,
        default=0.04,
        help="Max anonymized shard size in GiB (default 0.04 ≈ 42 MiB, under GitHub's 50 MiB warning).",
    )
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument(
        "--workers",
        type=int,
        default=default_anonymize_workers(),
        help="Process workers for spaCy NER (default: min(8, CPUs-1)). Use 1 to disable.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=512,
        help="Records per anonymize batch (nlp.pipe inside each batch).",
    )
    parser.add_argument(
        "--keep-originals",
        action="store_true",
        help="Keep original text fields alongside deidentified output (not safe to publish).",
    )
    parser.add_argument(
        "--keep-api-raw",
        action="store_true",
        help="Keep api_raw in output (text fields redacted unless --keep-originals).",
    )


def strip_kwargs_from_args(args: argparse.Namespace) -> Dict[str, bool]:
    keep_originals = bool(args.keep_originals)
    keep_api_raw = bool(args.keep_api_raw)
    return {
        "strip_originals": not keep_originals,
        "strip_api_raw": not keep_api_raw,
        "redact_api_raw_text": not keep_originals,
    }


def standard_run_kwargs(args: argparse.Namespace) -> Dict[str, Any]:
    """Kwargs for run_anonymize_jsonl (GPU is applied when loading models, not here)."""
    return {
        "resume": args.resume and not args.no_resume,
        "save_interval": max(int(args.save_interval or 500), 1),
        "max_part_bytes": int(args.max_part_gb * (1024 ** 3)),
        "record_batch_size": max(int(getattr(args, "batch_size", 512) or 512), 1),
    }


def run_field_anonymize(
    args: argparse.Namespace,
    *,
    field_pairs: Sequence[FieldPair],
    require_any: Sequence[str],
    source: str,
    progress_desc: str,
    progress_unit: str = "item",
    language_field: Optional[str] = None,
    fixed_language: str = "english",
    fallback_language: str = "english",
    bilingual: bool = True,
    record_iter: Optional[Callable[[Path], Iterator[Dict[str, Any]]]] = None,
    checkpoint_extra: Optional[Dict[str, Any]] = None,
    shared_models: Optional[Tuple[Dict[str, Any], Dict[str, Any]]] = None,
) -> None:
    strip_kw = strip_kwargs_from_args(args)
    workers = max(int(getattr(args, "workers", 1) or 1), 1)
    pipe_batch = DEFAULT_PIPE_BATCH_SIZE
    if workers > 1:
        print(f"Anonymize workers={workers} (batched nlp.pipe, no pydeidentify)")
        anonymize_batch = make_batch_anonymizer(
            field_pairs,
            language_field=language_field,
            fixed_language=fixed_language,
            fallback_language=fallback_language,
            workers=workers,
            bilingual=bilingual,
            pipe_batch_size=pipe_batch,
            **strip_kw,
        )
        anonymize_fn = None
    else:
        if shared_models is not None:
            nlp_by_language, deidentifier_by_language = shared_models
        elif bilingual:
            nlp_by_language, deidentifier_by_language = load_bilingual_models(use_gpu=bool(args.gpu))
        else:
            nlp, deid = load_english_models(use_gpu=bool(args.gpu))
            nlp_by_language = {"english": nlp}
            deidentifier_by_language = {"english": deid}
            fixed_language = "english"

        anonymize_fn = make_field_anonymizer(
            field_pairs,
            nlp_by_language=nlp_by_language,
            deidentifier_by_language=deidentifier_by_language,
            language_field=language_field,
            fixed_language=fixed_language,
            fallback_language=fallback_language,
            **strip_kw,
        )
        anonymize_batch = make_batch_anonymizer(
            field_pairs,
            nlp_by_language=nlp_by_language,
            language_field=language_field,
            fixed_language=fixed_language,
            fallback_language=fallback_language,
            workers=1,
            pipe_batch_size=pipe_batch,
            **strip_kw,
        )
    extra = {"source": source, **(checkpoint_extra or {})}

    run_anonymize_jsonl(
        args.input,
        args.output_dir,
        record_iter=record_iter or (lambda p: iter_jsonl_records(p, require_any=tuple(require_any))),
        anonymize_record=anonymize_fn,
        anonymize_batch=anonymize_batch,
        progress_desc=progress_desc,
        progress_unit=progress_unit,
        **standard_run_kwargs(args),
        checkpoint_extra=extra,
        done_message="Anonymized",
    )


def run_field_anonymize_passes(
    args: argparse.Namespace,
    *,
    passes: Sequence[Dict[str, Any]],
    field_pairs: Sequence[FieldPair],
    require_any: Sequence[str],
    progress_unit: str = "item",
    bilingual: bool = True,
) -> None:
    """Run multiple anonymize passes with one shared model load (e.g. English + Spanish radio)."""
    strip_kw = strip_kwargs_from_args(args)
    workers = max(int(getattr(args, "workers", 1) or 1), 1)
    shared_models: Optional[Tuple[Dict[str, Any], Dict[str, Any]]] = None
    if workers <= 1:
        if bilingual:
            shared_models = load_bilingual_models(use_gpu=bool(args.gpu))
        else:
            nlp, deid = load_english_models(use_gpu=bool(args.gpu))
            shared_models = ({"english": nlp}, {"english": deid})
    else:
        print(f"Anonymize workers={workers} (batched nlp.pipe, no pydeidentify)")

    run_kw = standard_run_kwargs(args)
    for spec in passes:
        extra = {"source": spec["source"], **(spec.get("checkpoint_extra") or {})}
        anonymize_batch = make_batch_anonymizer(
            field_pairs,
            nlp_by_language=None if workers > 1 else shared_models[0],
            language_field=spec.get("language_field"),
            fixed_language=spec.get("fixed_language", "english"),
            fallback_language=spec.get("fallback_language", "english"),
            workers=workers,
            bilingual=bilingual,
            **strip_kw,
        )
        anonymize_fn = None
        if workers <= 1:
            anonymize_fn = make_field_anonymizer(
                field_pairs,
                nlp_by_language=shared_models[0],
                deidentifier_by_language=shared_models[1],
                language_field=spec.get("language_field"),
                fixed_language=spec.get("fixed_language", "english"),
                fallback_language=spec.get("fallback_language", "english"),
                **strip_kw,
            )
        run_anonymize_jsonl(
            spec["input"],
            spec["output_dir"],
            record_iter=spec.get("record_iter")
            or (lambda p, req=require_any: iter_jsonl_records(p, require_any=tuple(req))),
            anonymize_record=anonymize_fn,
            anonymize_batch=anonymize_batch,
            progress_desc=spec["progress_desc"],
            progress_unit=progress_unit,
            checkpoint_extra=extra,
            done_message="Anonymized",
            **run_kw,
        )


def iter_classified_news(input_path: Path) -> Iterator[Dict[str, Any]]:
    if input_path.is_dir():
        paths = sorted(input_path.glob("classified_part_*.jsonl"))
        if not paths:
            raise FileNotFoundError(f"No classified_part_*.jsonl files in {input_path}")
    else:
        paths = [input_path]

    for path in paths:
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    logger.warning("Skipping malformed JSON in %s:%d (%s)", path, line_no, exc)
                    continue
                if rec.get("paragraph_text"):
                    yield rec
