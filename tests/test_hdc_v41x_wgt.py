"""V4.1x weight engines (block `wgt`): a fast subset of tools/rtl_hdc_v41x_wgt_campaign.py.

Builds the Verilator bench of the quantised tile (G = 1, m = 2: the MTP lane multiplier) and the BF16/FP32 tile
(G = 8, m = 1) and checks, against the golden (chunk8), bit-exactness on random and reduced-vehicle operands,
one beat per cycle sustained back to back, and the spec latency on the isolated ops.  Also checks the golden-side
invariants the engines rely on and the committed campaign record."""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
C = pytest.importorskip("rtl_hdc_v41x_wgt_campaign")
V = C.V
F = np.float32

needs_verilator = pytest.mark.skipif(shutil.which("verilator") is None, reason="verilator not installed")


def tree(parts):
    parts = [F(p) for p in parts]
    while len(parts) & (len(parts) - 1):
        parts.append(F(0))
    while len(parts) > 1:
        parts = [V.add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
    return parts[0]


@pytest.mark.parametrize("n,P", [(160, 8), (160, 32), (72, 8), (40, 8), (256, 64), (5, 8), (640, 256)])
def test_segment_beats_then_padded_tree_is_csum(n, P):
    """The tile's order: a beat's segment of P terms (zero-padded) summed as csum, beats by the padded tree."""
    rng = np.random.default_rng(n + P)
    t = (rng.standard_normal(n) * np.exp2(rng.integers(-30, 30, n))).astype(F)
    beats = [V.csum(np.concatenate([t[i:i + P], np.zeros(max(0, i + P - n), F)])) for i in range(0, n, P)]
    assert F(tree(beats)).tobytes() == F(V.csum(t)).tobytes()


def test_chain_first_add_equals_plus_zero_start():
    """t0 + t1 == (+0 + t0) + t1, including signed zeros and subnormals."""
    vals = [F(0.0), F(-0.0), F(1e-45), F(-1e-45), F(1.5), F(-1.5), F(3e38)]
    for a in vals:
        for b in vals:
            with np.errstate(over="ignore"):
                assert V.add(a, b).tobytes() == V.add(V.add(F(0), a), b).tobytes()


@needs_verilator
@pytest.mark.parametrize("name", ["q_g1_m2", "m_g8_m1"])
def test_tile_bench_fast(name, tmp_path):
    calls = C.capture_real(2)
    r = C.run_cfg(C.CONFIGS[name], tmp_path, 7, calls, quick=True)
    assert r["error_lines"] == []
    assert r["status"] == "pass", r
    assert r["throughput"]["no_bubble"]          # one beat per cycle but for the depth gaps owed between ops
    assert r["vectors"]["real_ops"]
    assert all(x["meets"] for x in r["latency"])


def test_campaign_record():
    p = ROOT / "results/rtl/hdc_v41x_wgt_campaign.json"
    if not p.exists():
        pytest.skip("campaign record not generated")
    rec = json.loads(p.read_text())
    assert rec["status"] == "pass"
    assert rec["arith"] == "chunk8"
    for c in rec["configs"].values():
        assert c["status"] == "pass"
        assert c["throughput"]["no_bubble"]
        assert all(x["meets"] for x in c["latency"])
