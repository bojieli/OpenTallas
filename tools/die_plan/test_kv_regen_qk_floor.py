#!/usr/bin/env python3
"""DIE-KV-2 10-27: main kv_regen.py carries the QK_CONSUME floor 34 of the b3 bind (blob 0ceb0d1a50):
QK_ISSUE_AGE = max(34, RESPONSE_LAT + 11).  A re-bind from main must reproduce bound_b3/param_regen.json.
    python3 -m pytest tools/die_plan/test_kv_regen_qk_floor.py
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[2]
BIND = ROOT / "physical" / "die_plan" / "qwen_kvsys" / "bind"
sys.path.insert(0, str(BIND))
import kv_regen as KR  # noqa: E402


def _ctx(krq, krs, frames=("ectl_EN_0", "ectl_WS_3")):
    cells = [NS(module="qkd_ectl3_kiss_st_x", path=p, params={}) for p in frames]
    legs = {}
    for ci, p in enumerate(frames):
        legs[(len(frames) + ci, "kreq", 0)] = (p, "req_k", krq, krq)   # ectl.req_* -> slg.kreq
        legs[(ci, "rsp_k", 0)] = (f"slg{ci}", "krsp", krs, krs)          # slg.krsp -> ectl.rsp_*
    return NS(F=NS(cells=cells)), legs


def _run(krq, krs, monkeypatch):
    ctx, legs = _ctx(krq, krs)
    monkeypatch.setattr(KR, "_legs", lambda c: legs)
    return KR.regen(ctx)


def test_floor_applies_b3(monkeypatch):
    out = _run(2, 2, monkeypatch)           # RESPONSE_LAT 12 (b3) -> 12 + 11 = 23 < 34 -> 34
    for p in ("ectl_EN_0", "ectl_WS_3"):
        assert out["params"][p] == dict(RESPONSE_LAT=12, QK_ISSUE_AGE=34)
    assert out["record"]["ectl"]["QK_ISSUE_AGE"] == 34
    assert "max(34" in out["record"]["ectl"]["rule"]


def test_above_floor_unchanged_rule(monkeypatch):
    out = _run(10, 12, monkeypatch)         # RESPONSE_LAT 30 -> 41 > 34
    assert out["params"]["ectl_EN_0"] == dict(RESPONSE_LAT=30, QK_ISSUE_AGE=41)


def test_qk_issue_age_edges():
    assert KR.QK_CONSUME_FLOOR == 34 and KR.QK_WRITE_BEFORE_READ == 11
    assert [KR.qk_issue_age(r) for r in (0, 12, 22, 23, 24, 80)] == [34, 34, 34, 34, 35, 91]


def test_reproduces_bound_b3_param_regen():
    pr = json.loads((BIND / "bound_b3" / "param_regen.json").read_text())
    by = {}
    for c in pr["changed"]:
        if c["param"] in ("RESPONSE_LAT", "QK_ISSUE_AGE"):
            by.setdefault(c["inst"], {})[c["param"]] = int(c["bound"])
    ectl = {k: v for k, v in by.items() if "QK_ISSUE_AGE" in v}
    assert len(ectl) >= 16, len(ectl)  # every b3 ECTL frame
    for inst, v in ectl.items():
        assert v["QK_ISSUE_AGE"] == KR.qk_issue_age(v["RESPONSE_LAT"]), inst
