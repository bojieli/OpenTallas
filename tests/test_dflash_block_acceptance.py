"""DFlash acceptance measured per block size, and the serial draft/verify/commit step built on it.

Artifacts: results/speculative/dflash_block_acceptance.json (tools/measure_speculative_acceptance.py
block-sweep) and results/speculative/dflash_step_timing.json (tools/dflash_step_timing.py).  No model
is run here.
"""

from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ACC = ROOT / "results/speculative/dflash_block_acceptance.json"
TIMING = ROOT / "results/speculative/dflash_step_timing.json"
REF_RAW = ROOT / "results/speculative/raw/dflash_b16_hf_spec.jsonl.gz"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def acc():
    return json.loads(ACC.read_text())


@pytest.fixture(scope="module")
def timing_tool():
    return _load("dst", ROOT / "tools/dflash_step_timing.py")


def test_every_block_is_complete_and_inside_its_cap(acc):
    assert {"2", "3", "4", "6", "8", "16"} <= set(acc["blocks"])
    for B, e in acc["blocks"].items():
        B = int(B)
        for w, st in e["workloads"].items():
            assert st["complete"], (B, w)
            hist = st["histogram_committed_length"]
            assert len(hist) == B + 1 and hist[0] == 0
            tau = sum(L * c for L, c in enumerate(hist)) / sum(hist)
            assert st["tau_direct"] == pytest.approx(tau, abs=1e-4)
            assert 1.0 <= st["tau_direct"] <= B
            assert 1.0 <= st["tau_truncated_from_block16"] <= B
            # greedy speculation is lossless: nothing above the bf16 near-tie tolerance except the few the
            # block-16 artifact already records
            assert st["teacher_forced_every_token"]["deficit_above_tol"] <= 3, (B, w)


def test_truncation_is_recomputed_from_the_committed_block16_records(acc):
    ref = [json.loads(l) for l in gzip.open(REF_RAW, "rt")]
    by = {}
    for r in ref:
        by.setdefault(r["workload"], []).append(r)
    for B, e in acc["blocks"].items():
        B = int(B)
        for w, st in e["workloads"].items():
            L = [a for r in by[w] for a in r["acceptance_lengths"]]
            assert st["tau_truncated_from_block16"] == pytest.approx(sum(min(a, B) for a in L) / len(L), abs=1e-4)
    b16 = acc["blocks"]["16"]["pooled"]["primary"]
    assert b16["tau_direct_cycle_weighted"] == b16["tau_truncated_cycle_weighted"]


def test_step_model_reproduces_the_atlas_sweep_then_reprices_it(timing_tool, acc):
    """The step arithmetic reproduces the earlier atlas lineage's sweep from its pinned basis (the legacy checks),
    then prices the two-reticle package (tools/arch_budget_qwen3.timing_basis) with the drafter's forward serial."""
    basis = timing_tool.design_basis()
    res = timing_tool.evaluate(basis, acc)
    assert res["checks"]["all"], res["checks"]
    committed = json.loads(TIMING.read_text())
    assert committed["rom"] == res["rom"] and committed["hbm"] == res["hbm"]
    assert res["basis"]["dies"] == 2 and res["basis"]["groups"] == 12288 and res["basis"]["hbm_stacks"] == 8
    m = basis["lane_multiplier_m"]
    top = res["rom"][f"8192/fp8/m{m}"]
    for r in top["sweep"]:
        if r["block"] > 1:
            # the drafter's forward is on the critical path, never free
            assert r["step_cycles"] == r["draft_cycles"] + r["verify_cycles"] + r["commit_cycles"]
            assert r["draft_cycles"] > r["draft_detail"]["chain_latency_only"] > 0
    assert top["best"]["block"] > 1 and top["best"]["speedup"] > 1.3
