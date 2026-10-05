"""Block `sel` of the V4.1x die: the streaming-filter index select and the candidate-block
select (rtl/hdc/v41x/ot_hdc_v41x_sel*.sv).  The committed campaign records must be current
and meet the spec rows; a reduced configuration of each unit is re-run under Verilator."""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_sel_campaign as sel  # noqa: E402
import rtl_hdc_v41x_sel_cand_campaign as cand  # noqa: E402
from record_currency_support import assert_current_or_marked_stale  # noqa: E402

HAVE_VERILATOR = Path(sel.VERILATOR).exists() or shutil.which("verilator") is not None


def _current(record, files):
    pins = {name: digest for group in files for name, digest in record[group].items()}
    assert_current_or_marked_stale(record, pins)


def test_sel_record_is_current_and_meets_the_spec():
    rec = json.loads(sel.OUT.read_text())
    assert rec["status"] == "pass" and not rec["quick"]
    _current(rec, ("rtl", "bench", "tools"))
    spec = rec["spec"]
    assert spec["exact_golden_equality"]["met"]
    assert spec["ingest_scores_per_cycle"]["met"] and spec["ingest_scores_per_cycle"]["stall_cycles"] == 0
    assert spec["tail_1m_per_die"]["met"] and spec["tail_1m_per_die"]["measured_max"] <= 181
    assert spec["tail_200k_per_die"]["met"] and spec["tail_200k_per_die"]["measured_max"] <= 155
    assert any(r["ovf"] for r in spec["overflow_fallback"]["measured"])     # the replay path ran at shipped size
    muts = rec["mutations"]
    assert any(m["mutation"] == "control" and m["pass"] for m in muts)
    assert all(m["pass"] is False for m in muts if m["mutation"] != "control" and m["applied"])


def test_cand_record_is_current_and_meets_the_spec():
    rec = json.loads(cand.OUT.read_text())
    assert rec["status"] == "pass" and not rec["quick"]
    _current(rec, ("rtl", "bench", "tools"))
    assert rec["spec"]["done_within_20us_at_1m"]["met"]
    assert rec["spec"]["ingest_scores_per_cycle"]["met"]


def test_golden_semantics_of_the_vectors():
    v = np.array([1.0, 3.0, -0.0, 3.0, 0.0, -np.inf, 3.0])
    bits = sel.bf16_bits(v)
    rng = np.random.default_rng(1)
    beats, k, exps, _ = sel.segment(rng, bits, 6, 16, 2, 4, "even", True)
    got = [p for e in exps for (p, _, _) in e]
    assert got == [0, 1, 2, 3, 4, 6]                  # -0 ties +0, ties to the lower index, -inf last
    beats, k, exps, _ = sel.segment(rng, bits, 7, 16, 2, 4, "even", True)
    assert [ni for e in exps for (_, _, ni) in e] == [0, 0, 0, 0, 0, 1, 0]
    # candidate blocks: newest block pinned, -inf blocks dropped
    b = sel.bf16_bits(np.concatenate([np.full(8, -np.inf), np.arange(8.0), np.full(3, -1.0)]))
    assert cand.golden_blocks(b, 8, 3) == [1, 2]


@pytest.mark.skipif(not HAVE_VERILATOR, reason="needs Verilator")
def test_sel_reduced_configuration(tmp_path):
    rng = np.random.default_rng(5)
    pool = sel.bf16_bits(rng.standard_normal(500))
    segs, labs = sel.coverage_segments(rng, 80, 16, 4, 4, 16, 3, pool)
    for f in ("ascending", "ties", "masked_few"):              # ascending overflows the 8-line memories
        segs.append(sel.segment(rng, sel.family(rng, f, 400, 16), 16, 16, 4, 4, "even", True))
        labs.append(f)
    res = sel.run_config("t", 4, 4, 16, 16, 3, segs, labs, tmp_path, runs=((0, 0, 1), (15, 40, 2)))
    assert res["pass"], [r.get("log") for r in res["runs"]]
    assert res["runs"][0]["stall_cycles"] == 0
    assert any(p["ovf"] for p in res["runs"][0]["per_segment"])        # tiny memories exercise the replay


@pytest.mark.skipif(not HAVE_VERILATOR, reason="needs Verilator")
def test_cand_reduced_configuration(tmp_path):
    rng = np.random.default_rng(6)
    segs, labs = [], []
    for _ in range(40):
        n = int(rng.integers(1, 3000))
        k = int(rng.integers(0, 80))
        b = sel.family(rng, ["normal", "ties", "masked_few", "ascending"][int(rng.integers(0, 4))], n, max(k, 1))
        segs.append(cand.segment(rng, b, k, 16, 4, "random", K=64))
        labs.append("x")
    res = cand.run_config("t", 4, 16, 16, 64, 6, segs, labs, tmp_path, runs=((0, 0, 1), (15, 40, 2)))
    assert res["pass"], [r.get("log") for r in res["runs"]]
