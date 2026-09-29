"""W11 V4.1 indexer scoring array (NS=16 x NK=4): consistency of results/rtl/w11_idx_array.json and fast checks
of the gate's data preparation (tools/rtl_w11_idx_array.py)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
REC = ROOT / "results/rtl/w11_idx_array.json"


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


@pytest.fixture(scope="module")
def A():
    import rtl_w11_idx_array as A
    return A


def test_sources_pinned(rec):
    for p, h in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h, p
    assert not rec["sources_dirty_at_run"]


def test_small_n_exact(rec):
    seen = {(s["ns"], s["nk"]) for s in rec["small_n"]}
    assert {(4, 1), (2, 4)} <= seen
    for s in rec["small_n"]:
        assert s["exact"]
        for r in s["runs"]:
            assert r["errors"] == 0 and r["checked"] == s["keys"]
            assert r["faults_expected_and_raised"] == s["expected_faults"] > 0
            assert r["beats_in"] == r["beats_out"]
        assert any(r["out_stall"] > 0 for r in s["runs"])          # back-pressure exercised
        assert any(r["refused"] > 0 and r["masked"] > 0 for r in s["runs"])


def test_full_n_composed(rec):
    f = rec["full_n"]
    assert f["keys"] == 262144 and f["checked"] == 262144 and f["errors"] == 0 and f["exact"]
    assert len(f["per_share"]) == 16
    assert sorted(s["spec_slice"] for s in f["per_share"]) == list(range(16))
    assert all(s["keys"] == s["checked"] == 16384 and s["errors"] == 0 for s in f["per_share"])
    assert f["faults_expected_and_raised"] == f["data"]["expected_faults"]
    t = f["timing"]
    assert t["in_stall"] == 3 * len(f["runs"])          # query settle only, before the first accept
    assert t["accept_span_cycles"] == 4096 and t["measured_ii"] == 1.0
    assert t["composed_cycles_query_to_last_score"] <= t["model"]["reader_bound_cycles"]
    assert rec["verdict"]["pass_"]


def test_port_widths(rec):
    e, a = rec["element"], rec["array"]
    assert e["key_in_bits_per_cycle"] == 2176 and e["query_register_bits"] == 17920
    assert e["logical_fp4_macs_per_cycle"] == 16384 and e["metadata_fifo_bits"] == 2240
    assert a["beat_key_bits_per_cycle"] == 34816 == 64 * 544
    assert a["logical_fp4_macs_per_cycle"] == 262144 and a["keys_per_cycle"] == 64
    assert a["query_register_bits"] == 16 * 17920


def test_reader_layout(A):
    for n in (1, 31, 1000, 4097):
        m = A.reader_beats(n)
        assert sorted(m[m >= 0].tolist()) == list(range(n))
        # every NK=4 slice group holds consecutive indices
        for b in range(m.shape[0]):
            for g in range(16):
                v = m[b, 4 * g:4 * g + 4]
                v = v[v >= 0]
                assert np.array_equal(v, v[0] + np.arange(len(v))) if len(v) else True


def test_qdq_codes_match_golden(A):
    rng = np.random.default_rng(4)
    x = rng.standard_normal((5, 128)).astype(np.float32)
    c, u = A.qdq_codes(x)
    assert np.array_equal(A.C.values(c, u), A.G.qdq_fp4_e8m0(x.reshape(-1)).reshape(5, 128))
