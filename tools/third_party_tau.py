#!/usr/bin/env python3
"""Speculative-decoding acceptance (tau) for the compositions.

OWNER DECISION (2026-10-05): the DeepSeek-V4.1 default is tau = 4.159, the owner 6-class workload blend (harmonic,
greedy, gamma 5) in results/speculative/v41_mtp_acceptance_qualified_20261003/blend_owner6.json
(blends["owner 6-class equal"].greedy.tau_blend_harmonic).  Reason: the published V4.1 primary (3.8879, vLLM PR #57432)
is a single GSM8K dataset, and several published sources are V4-Flash, not V4.1.  The published V4.1 value 3.8879 and
the published V4.1 gamma-5 range 3.43-4.32 stay as a SENSITIVITY (OT_TAU_SOURCE=third_party, or sensitivity_ds_v41()).
Qwen3-8B keeps the third-party derived value 3.1445 (results/speculative/third_party_acceptance_20261004/acceptance.json,
built by tools/external_registry.py from results/external/registry.json).

tau convention: mean tokens committed per verify step INCLUDING the target's bonus token.

Selection (default adopted):
  env OT_TAU_SOURCE=adopted | third_party | self_measured
    adopted        DS 4.159 owner 6-class blend; Qwen 3.1445 third-party derived            (composition default)
    third_party    DS 3.8879 published V4.1 (sensitivity); Qwen 3.1445                      (the 2026-10-04 records)
    self_measured  DS 4.159; Qwen 3.0375 self-measured                                      (SUPERSEDED, reproduction only)
  or pass source= to tau_ds_v41() / tau_qwen3_8b().
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/speculative/third_party_acceptance_20261004/acceptance.json"
REC_REL = "results/speculative/third_party_acceptance_20261004/acceptance.json"
BLEND_REL = "results/speculative/v41_mtp_acceptance_qualified_20261003/blend_owner6.json"
BLEND = ROOT / BLEND_REL
BLEND_KEY = "owner 6-class equal"
DS_ADOPTED_LABEL = "owner 6-class workload blend (adopted 2026-10-05)"
SOURCES = ("adopted", "third_party", "self_measured")

SUPERSEDED = {
    "deepseek_v41": dict(tau=4.159, draft_tokens=5,
                         source=f"{BLEND_REL} (self-measured, owner 6-class equal blend; superseded 2026-10-04, "
                                "RE-ADOPTED as the default 2026-10-05 by owner decision)"),
    "qwen3_8b": dict(tau=3.0375, draft_tokens=3,
                     source="results/rtl/qwen_rom_dspark_20261003/drafter/tau_summary.json tau_w8_S3_B4 "
                            "(self-measured, owner 6 classes; SUPERSEDED 2026-10-04 by owner rule)"),
}


def _source(source: str | None) -> str:
    s = source or os.environ.get("OT_TAU_SOURCE", "adopted")
    if s not in SOURCES:
        raise ValueError(f"tau source must be one of {SOURCES}, not {s!r}")
    return s


def record() -> dict:
    return json.loads(REC.read_text())


def ds_owner_blend() -> tuple[float, str]:
    """The adopted DS tau, read from the owner 6-class blend record."""
    b = json.loads(BLEND.read_text())["blends"][BLEND_KEY]["greedy"]
    return b["tau_blend_harmonic"], (f"{BLEND_REL} blends['{BLEND_KEY}'].greedy.tau_blend_harmonic "
                                     f"({DS_ADOPTED_LABEL}; harmonic, greedy, gamma 5)")


def _third_party(model: str, draft_tokens: int | None) -> tuple[float, str]:
    m = record()["models"][model]
    k = str(draft_tokens if draft_tokens is not None else m["primary"]["draft_tokens"])
    row = m["by_draft_tokens"].get(k)
    if row is None:
        raise KeyError(f"no third-party {model} tau at {k} draft tokens (have {sorted(m['by_draft_tokens'])})")
    return row["tau"], f"{REC_REL} models.{model}.by_draft_tokens.{k} ({row['basis']})"


def _model(model: str, draft_tokens: int | None, source: str | None) -> tuple[float, str]:
    s = _source(source)
    if s == "self_measured":
        r = SUPERSEDED[model]
        if draft_tokens is not None and draft_tokens != r["draft_tokens"]:
            raise ValueError(f"superseded {model} tau exists only at {r['draft_tokens']} draft tokens")
        return r["tau"], r["source"]
    if s == "adopted" and model == "deepseek_v41":
        if draft_tokens not in (None, 5):
            raise ValueError("the adopted DS owner blend exists only at gamma 5 (5 draft tokens)")
        return ds_owner_blend()
    return _third_party(model, draft_tokens)


def tau_ds_v41(draft_tokens: int | None = 5, source: str | None = None) -> float:
    return _model("deepseek_v41", draft_tokens, source)[0]


def tau_qwen3_8b(draft_tokens: int | None = 3, source: str | None = None) -> float:
    return _model("qwen3_8b", draft_tokens, source)[0]


def tau_src(model: str, draft_tokens: int | None = None, source: str | None = None) -> str:
    return _model(model, draft_tokens, source)[1]


def sensitivity_ds_v41() -> dict:
    """SENSITIVITY rows for DS gamma 5: the published V4.1 primary and the published V4.1 gamma-5 range."""
    d = record()["models"]["deepseek_v41"]
    return dict(published=dict(tau=d["primary"]["tau"], source=f"{REC_REL} models.deepseek_v41.primary "
                               f"({', '.join(d['primary']['source_ids'])}; {d['primary']['mismatch'][0]})"),
                published_low=dict(tau=d["range"]["low"], source=f"{REC_REL} models.deepseek_v41.range.low"),
                published_high=dict(tau=d["range"]["high"], source=f"{REC_REL} models.deepseek_v41.range.high"))


def mtp_sensitivity(step_us: float) -> dict:
    """MTP tok/s at the sensitivity taus for a tau-independent step (MTP = tau x 1e6 / step)."""
    return {k: dict(tau=v["tau"], MTP_tok_s=round(v["tau"] * 1e6 / step_us, 1), source=v["source"])
            for k, v in sensitivity_ds_v41().items()}


if __name__ == "__main__":
    for mdl, k in (("deepseek_v41", 5), ("qwen3_8b", 3)):
        for s in SOURCES:
            t, src = _model(mdl, k, s)
            print(f"{mdl:13s} k={k} {s:13s} tau={t:<7g} {src}")
    print("DS sensitivity:", {k: v["tau"] for k, v in sensitivity_ds_v41().items()})
