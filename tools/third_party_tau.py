#!/usr/bin/env python3
"""Speculative-decoding acceptance (tau) for the compositions: THIRD-PARTY published values by default.

OWNER RULE (2026-10-04): speculative-decoding acceptance must come from PUBLISHED THIRD-PARTY sources, never from
our own measurement.  The values live in results/speculative/third_party_acceptance_20261004/acceptance.json
(built by tools/external_registry.py from results/external/registry.json); this module only reads them.

tau convention: mean tokens committed per verify step INCLUDING the target's bonus token.

Selection (default third_party):
  env OT_TAU_SOURCE=third_party | self_measured     (self_measured reproduces the SUPERSEDED records)
  or pass source= to tau_ds_v41() / tau_qwen3_8b().

SUPERSEDED self-measured values (kept for reproduction only):
  DeepSeek-V4.1 DSpark gamma 5, owner 6-class equal blend  4.159  (results/speculative/v41_mtp_acceptance_qualified_20261003/blend_owner6.json)
  Qwen3-8B DSpark W8 S=3 verify block 4, owner 6 classes   3.0375 (results/rtl/qwen_rom_dspark_20261003/drafter/tau_summary.json)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/speculative/third_party_acceptance_20261004/acceptance.json"
REC_REL = "results/speculative/third_party_acceptance_20261004/acceptance.json"

SUPERSEDED = {
    "deepseek_v41": dict(tau=4.159, draft_tokens=5,
                         source="results/speculative/v41_mtp_acceptance_qualified_20261003/blend_owner6.json "
                                "(self-measured, owner 6-class equal blend; SUPERSEDED 2026-10-04 by owner rule)"),
    "qwen3_8b": dict(tau=3.0375, draft_tokens=3,
                     source="results/rtl/qwen_rom_dspark_20261003/drafter/tau_summary.json tau_w8_S3_B4 "
                            "(self-measured, owner 6 classes; SUPERSEDED 2026-10-04 by owner rule)"),
}


def _source(source: str | None) -> str:
    s = source or os.environ.get("OT_TAU_SOURCE", "third_party")
    if s not in ("third_party", "self_measured"):
        raise ValueError(f"tau source must be third_party or self_measured, not {s!r}")
    return s


def record() -> dict:
    return json.loads(REC.read_text())


def _model(model: str, draft_tokens: int | None, source: str | None) -> tuple[float, str]:
    if _source(source) == "self_measured":
        s = SUPERSEDED[model]
        if draft_tokens is not None and draft_tokens != s["draft_tokens"]:
            raise ValueError(f"superseded {model} tau exists only at {s['draft_tokens']} draft tokens")
        return s["tau"], s["source"]
    m = record()["models"][model]
    k = str(draft_tokens if draft_tokens is not None else m["primary"]["draft_tokens"])
    row = m["by_draft_tokens"].get(k)
    if row is None:
        raise KeyError(f"no third-party {model} tau at {k} draft tokens (have {sorted(m['by_draft_tokens'])})")
    return row["tau"], f"{REC_REL} models.{model}.by_draft_tokens.{k} ({row['basis']})"


def tau_ds_v41(draft_tokens: int | None = 5, source: str | None = None) -> float:
    return _model("deepseek_v41", draft_tokens, source)[0]


def tau_qwen3_8b(draft_tokens: int | None = 3, source: str | None = None) -> float:
    return _model("qwen3_8b", draft_tokens, source)[0]


def tau_src(model: str, draft_tokens: int | None = None, source: str | None = None) -> str:
    return _model(model, draft_tokens, source)[1]


if __name__ == "__main__":
    for mdl, k in (("deepseek_v41", 5), ("qwen3_8b", 3)):
        for s in ("third_party", "self_measured"):
            t, src = _model(mdl, k, s)
            print(f"{mdl:13s} k={k} {s:13s} tau={t:<7g} {src}")
