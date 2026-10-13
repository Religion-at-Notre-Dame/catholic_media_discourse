"""OpenRouter Decisions API client for TypeSafe Jev (typed decisions, not chat).

Docs: https://openrouter.ai/docs/guides/community/jev
Endpoint: POST https://openrouter.ai/api/alpha/decisions
Model default: typesafe/jev-1.13

Prices (~2026): $0.042 / 1M input tokens; output free.
"""

from __future__ import annotations

import json
import time
from typing import Any

import requests

from common.config import OPENROUTER_API_KEY, OPENROUTER_JEV_MODEL
from common.taxonomies import accuracy_legend, label_criteria

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
JEV_INPUT_USD_PER_MTOK = 0.042


class OpenRouterJevError(RuntimeError):
    pass


def approx_tokens(obj: Any) -> int:
    """Rough token estimate (~4 chars/token) for budget planning."""
    raw = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return max(1, len(raw) // 4)


def estimate_usd(tokens: int, usd_per_mtok: float = JEV_INPUT_USD_PER_MTOK) -> float:
    return tokens / 1_000_000 * usd_per_mtok


def jev_decide(
    state: dict[str, Any],
    questions: dict[str, Any],
    *,
    model: str | None = None,
    api_key: str | None = None,
    timeout: float = 90.0,
    max_retries: int = 4,
) -> dict[str, Any]:
    """Call Jev once; return full JSON (answers + usage)."""
    key = api_key or OPENROUTER_API_KEY
    if not key or key.startswith("sk-or-v1-your_"):
        raise OpenRouterJevError(
            "OPENROUTER_API_KEY is not set. Copy .env.example → .env and add your key."
        )
    payload = {
        "model": model or OPENROUTER_JEV_MODEL,
        "state": state,
        "questions": questions,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/jonathankarr/catholic_media_discourse",
        "X-Title": "Catholic Media of the Americas - dual-taxonomy Jev judge",
    }
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            r = requests.post(
                DECISIONS_URL, headers=headers, json=payload, timeout=timeout
            )
            if r.status_code in {429, 500, 502, 503, 504} and attempt + 1 < max_retries:
                time.sleep(min(8.0, 1.5 * (2**attempt)))
                continue
            if r.status_code >= 400:
                raise OpenRouterJevError(f"HTTP {r.status_code}: {r.text[:800]}")
            data = r.json()
            if "answers" not in data:
                raise OpenRouterJevError(f"Unexpected response keys: {list(data)}")
            return data
        except (requests.RequestException, ValueError) as e:
            last_err = e
            if attempt + 1 < max_retries:
                time.sleep(min(8.0, 1.5 * (2**attempt)))
                continue
            raise OpenRouterJevError(str(e)) from e
    raise OpenRouterJevError(str(last_err) if last_err else "Jev request failed")


def _noul_question(instructions: str, true_c: str, false_c: str) -> dict[str, Any]:
    return {
        "type": "noul",
        "instructions": instructions,
        "criteria": {"true": true_c, "false": false_c},
    }


def build_judge_questions(
    *,
    content_tax: dict[str, Any] | None = None,
    discourse_tax: dict[str, Any] | None = None,
    with_accuracy: bool = True,
) -> dict[str, Any]:
    """Build one Jev request: content_* + discourse_* Nouls + optional accuracy Score."""
    questions: dict[str, Any] = {}

    if content_tax:
        for lid, crit in label_criteria(content_tax).items():
            questions[f"content_{lid}"] = _noul_question(
                (
                    "Does this media passage informally teach or strongly imply the "
                    f"following CONTENT category for a learner entering faith formation? {crit}"
                ),
                (
                    "The passage clearly conveys content in this category that a "
                    "learner could absorb as prior knowledge (even if incomplete)."
                ),
                (
                    "The passage does not meaningfully teach this category, or the "
                    "category is only incidental."
                ),
            )
        if with_accuracy:
            legend = accuracy_legend(content_tax)
            if legend:
                questions["factual_theological_accuracy"] = {
                    "type": "score",
                    "instructions": (
                        "Rate how accurate the informal Catholic teaching claim is "
                        "relative to mainstream Catholic doctrine / CST as taught in "
                        "formation settings. Use the lowest level if there is no clear "
                        "religious claim."
                    ),
                    "criteria": legend,
                }

    if discourse_tax:
        for lid, crit in label_criteria(discourse_tax).items():
            questions[f"discourse_{lid}"] = _noul_question(
                (
                    "Does this passage exhibit the following DISCOURSE / speech-act "
                    f"category (how it speaks, orthogonal to content/teaching type)? {crit}"
                ),
                "The passage clearly exhibits this discourse/speech-act category.",
                "The passage does not meaningfully exhibit this category.",
            )

    if not questions:
        raise ValueError("No questions built — enable content and/or discourse taxonomy")
    return questions


def _parse_prefix(
    answers: dict[str, Any],
    prefix: str,
    *,
    include_at: float,
) -> tuple[dict[str, float], list[str]]:
    probs: dict[str, float] = {}
    selected: list[str] = []
    for key, ans in answers.items():
        if not key.startswith(prefix):
            continue
        if not isinstance(ans, dict):
            continue
        lid = key[len(prefix) :]
        try:
            p = float(ans.get("noul") if ans.get("type") == "noul" else 0.0)
        except (TypeError, ValueError):
            p = 0.0
        probs[lid] = p
        if p >= include_at:
            selected.append(lid)
    return probs, sorted(selected)


def parse_judge_answers(
    answers: dict[str, Any],
    *,
    content_include_at: float = 0.55,
    discourse_include_at: float = 0.55,
    human_review_conf_below: float = 0.45,
) -> dict[str, Any]:
    """Flatten dual-taxonomy Jev answers for JSONL storage."""
    content_probs, content_labels = _parse_prefix(
        answers, "content_", include_at=content_include_at
    )
    discourse_probs, discourse_labels = _parse_prefix(
        answers, "discourse_", include_at=discourse_include_at
    )

    acc = answers.get("factual_theological_accuracy") or {}
    needs_review = False
    if acc:
        try:
            conf = acc.get("confidence")
            score = acc.get("score")
            if conf is not None and float(conf) < human_review_conf_below:
                needs_review = True
            # Mid-scale ambiguity: partial/misleading band on 0–4 scale
            if score is not None and 0.75 <= float(score) <= 2.25:
                needs_review = True
        except (TypeError, ValueError):
            needs_review = True

    return {
        "content_label_probs": content_probs,
        "content_labels": content_labels,
        "discourse_label_probs": discourse_probs,
        "discourse_labels": discourse_labels,
        "accuracy_score": acc.get("score"),
        "accuracy_confidence": acc.get("confidence"),
        "accuracy_probabilities": acc.get("probabilities"),
        "accuracy_legend": acc.get("legend"),
        "needs_human_review": needs_review,
    }
