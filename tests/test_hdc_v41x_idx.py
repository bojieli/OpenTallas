"""V4.1 lightning-indexer engine and HBM key stream (block `idx`): a fast subset of
tools/rtl_hdc_v41x_idx_campaign.py, plus the committed record's verdicts."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
REC = ROOT / "results/rtl/hdc_v41x_idx_campaign.json"


@pytest.fixture(scope="module")
def C():
    import rtl_hdc_v41x_idx_campaign as C
    return C


def test_codes_roundtrip(C):
    rng = np.random.default_rng(1)
    for _ in range(50):
        codes = rng.integers(0, 16, (3, 64))
        u = rng.integers(0, 253, (3, 2))
        v = C.values(codes, u)
        c2, u2 = C.to_codes(v)
        assert np.array_equal(C.values(c2, u2), v)


def test_golden_mirror_is_the_indexer(C):
    """The campaign's expected scores are Model.indexer's own lines (chunk8): check them against an
    independent float64 evaluation on a small token where nothing rounds but the golden's own steps."""
    rng = np.random.default_rng(2)
    t = C.finish(C.rand_token(rng, 32, 4, 50, "typical"))
    assert not t["fault"].any()
    q, k = C.values(t["qc"], t["qu"]), C.values(t["kc"], t["ku"])
    G = C.G
    s = G.to_bf16(G.reduce_rows(G.to_bf16(G.mul(np.maximum(G.to_bf16(G.dots_q4(q, k)), np.float32(0)),
                                                t["w"][:, None])).T, cls="idx"))
    assert np.array_equal((G.bits(s) >> 16).astype(np.int64), t["exp"])


@pytest.mark.skipif(shutil.which("verilator") is None, reason="needs verilator")
def test_rtl_reduced_quick(tmp_path):
    out = tmp_path / "rec.json"
    subprocess.run([sys.executable, str(ROOT / "tools/rtl_hdc_v41x_idx_campaign.py"), "--quick", "--nk", "2",
                    "--only", "reduced", "--work", str(tmp_path / "w"), "--output", str(out)],
                   check=True, cwd=ROOT, timeout=3600)
    r = json.loads(out.read_text())
    assert r["reduced"]["verdict"]["bit_exact"]
    assert r["reduced"]["back_to_back"]["keys_per_cycle"] == 2.0
    assert r["reduced"]["vehicle"]["keys"] > 0


def test_committed_record():
    r = json.loads(REC.read_text())
    assert "rtl/hdc/v41x/ot_hdc_v41x_idx_pool_finish.sv" in r["sources"]
    for shape in ("shipped", "reduced"):
        v = r[shape]["verdict"]
        assert v["bit_exact"] and v["throughput_ok"], shape
        assert r[shape]["mixed"]["errors"] == 0
    p = r["shipped"]["pooled_core_geometry"]
    assert p["tile"]["G"] == 4 and p["tile"]["M"] == 2
    assert p["bit_exact"] and p["split_mode_used"]
    assert r["shipped"]["pooled"]["bit_exact"]
    assert p["counters"]["refused"] == p["expected_refused"]
    assert r["reduced"]["vehicle"]["keys"] > 0
    h = r.get("hbm_scan")
    if h:
        assert h["verdict"]["bit_exact"]
