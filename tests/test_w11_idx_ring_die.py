"""W11 ring layout follow-ups: die gate, concurrent writes, prefill sizing -- records current (fast)."""

import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from record_currency_support import assert_current_or_marked_stale  # noqa: E402

from tools import w11_idx_ring_concurrent as conc
from tools import w11_idx_ring_prefill_sizing as pre

ROOT = Path(__file__).resolve().parents[1]
DIE = ROOT / "results/rtl/w11_die_idx_ring_gate.json"


def test_die_gate_passes_and_pins_are_current():
    rec = json.loads(DIE.read_text())
    assert rec["status"] == "pass"
    assert_current_or_marked_stale(rec, rec["sources_sha256"], str(DIE))
    for case in rec["cases"]:
        assert case["ring"]["status"] == case["replicated_reference"]["status"] == "pass"
        assert case["token_identical"]
    ctx = next(c for c in rec["cases"] if c["image"] == "ctx64")
    assert ctx["ring"]["ring"]["migrations"] > 0


def test_concurrent_record_current():
    rec = json.loads(conc.OUT.read_text())
    assert rec["status"] == "pass" and rec["sources_sha256"] == conc.sources()
    by = {c["name"]: c for c in rec["cases"]}
    for name in ("one_step", "one_step_migration", "two_steps"):
        assert by[name]["slowdown"] < 0.01
    assert by["one_step_migration"]["during_scan"]["migrations"] >= 1


def test_prefill_sizing_matches_rebuild():
    rec = json.loads(pre.OUT.read_text())
    assert rec == json.loads(json.dumps(pre.build()))
    assert rec["verdict"]["binds"] is False
