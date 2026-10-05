"""Invariants of the measured speculative acceptance artifact and of the arithmetic that builds it.

The artifact is ``results/speculative/acceptance_tau.json`` from
``tools/measure_speculative_acceptance.py``.  Nothing here re-runs a model; the GPU
measurement is the tool's job.  What is checked is that every published tau is the
statistic its own histogram says it is, stays inside [1, gamma+1], and that the
survival curve that yields the derived (truncated) tau values is monotone.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "results" / "speculative" / "acceptance_tau.json"
PROFILES = ROOT / "configs" / "studies" / "speculative_profiles.json"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("msa", ROOT / "tools" / "measure_speculative_acceptance.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def artifact():
    return json.loads(ARTIFACT.read_text())


def test_histogram_statistics_are_self_consistent(tool):
    # committed lengths 1,1,2,4 at gamma 3 (block 4): tau = 8/4 = 2
    hist = tool._hist_from_lengths([1, 1, 2, 4], 4)
    st = tool._stats_from_hist(hist, 3)
    assert st["tau_mean"] == 2.0
    assert st["survival_by_position"] == [0.5, 0.25, 0.25]
    # 1 + sum of the survival curve is the mean again
    assert 1 + sum(st["survival_by_position"]) == pytest.approx(st["tau_mean"])


def test_vllm_per_position_counters_rebuild_the_same_histogram(tool):
    """vLLM publishes per-position accepted counts; greedy acceptance is a prefix, so
    the committed-length histogram is the difference of adjacent counts."""
    lengths = [1, 1, 2, 4, 3, 4]
    k = 3
    drafts = len(lengths)
    per_pos = [sum(1 for L in lengths if L - 1 >= i + 1) for i in range(k)]
    hist = [0] * (k + 2)
    prev = drafts
    for a in range(k):
        hist[a + 1] = prev - per_pos[a]
        prev = per_pos[a]
    hist[k + 1] = prev
    assert hist == tool._hist_from_lengths(lengths, k + 1)


def _entries(artifact):
    for run_id, run in artifact["qwen3_8b"].items():
        for workload, st in run["workloads"].items():
            yield run_id, run, workload, st


def test_every_measured_tau_is_inside_its_cap_and_matches_its_histogram(artifact):
    seen = 0
    for run_id, run, workload, st in _entries(artifact):
        gamma = run["gamma"]
        hist = st["histogram_committed_length"]
        cycles = sum(hist)
        assert cycles == st["cycles"] > 0, (run_id, workload)
        tau = sum(L * c for L, c in enumerate(hist)) / cycles
        assert st["tau_mean"] == pytest.approx(tau, abs=1e-4), (run_id, workload)
        assert 1.0 <= st["tau_mean"] <= gamma + 1, (run_id, workload)
        assert hist[0] == 0 and len(hist) == gamma + 2
        surv = st["survival_by_position"]
        assert all(a >= b for a, b in zip(surv, surv[1:])), (run_id, workload)
        assert 1 + sum(surv) == pytest.approx(st["tau_mean"], abs=1e-3)
        for g, t in st["derived_tau_by_truncation"].items():
            assert 1.0 <= t <= int(g) + 1
        seen += 1
    assert seen > 0


def test_every_measured_run_names_its_raw_records_and_hardware(artifact):
    for run_id, run in artifact["qwen3_8b"].items():
        assert run["grade"] == "executed"
        assert len(run["raw_records_sha256"]) == 64
        assert run["environment"].get("gpu"), run_id


def test_lossless_check_is_recorded_for_every_workload(artifact):
    """Every emitted DFlash token is teacher-forced through the target.  bf16 recomputation
    admits near-ties, so the check is that deficits beyond the tie tolerance stay a vanishing
    fraction -- and that the artifact states the count rather than hiding it."""
    above = tokens = 0
    for run_id, run, workload, st in _entries(artifact):
        tf = st["lossless"].get("teacher_forced_every_token")
        if tf is not None:
            assert tf["tokens"] > 0
            above += tf["deficit_above_tol"]
            tokens += tf["tokens"]
        assert "versus_plain_greedy" in st["lossless"] or "identical_samples" in st["lossless"]
    assert tokens > 0
    assert above / tokens < 1e-4


def test_profiles_carry_the_executed_points_without_dropping_published_ones():
    config = json.loads(PROFILES.read_text())
    sota = config["profiles"]["sota_block_diffusion"]
    # the published Table 1 points are still there, untouched
    assert [p["value"] for p in sota["acceptance_length"]["points"]] == [6.54, 7.87, 7.08, 6.5, 5.95, 7.27, 4.24]
    executed = sota["executed_acceptance_by_workload"]
    assert executed["grade"] == "executed"
    assert (ROOT / executed["artifact"]).is_file()
    body = json.loads((ROOT / executed["artifact"]).read_text())
    run = body["qwen3_8b"][executed["run_id"]]
    for point in executed["points"]:
        assert point["value"] == run["workloads"][point["workload"]]["tau_mean"]
