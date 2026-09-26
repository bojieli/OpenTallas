"""Fast subset of the V4.1 attention-engine campaign (tools/rtl_hdc_v41x_attn_campaign.py).

* the engine's summation order (tile chunks + lane tree for q.k, TD-row blocks + binary-counter merge for p.v)
  equals the golden's R-ARITH csum bit for bit, in numpy, over random shapes and row counts;
* the stored-format dequantiser reference agrees with the golden's own qdq functions;
* RTL (Verilator): a small tile and a small engine configuration, bit-exact against the golden, and the p.v
  stream issuing one beat per cycle back to back;
* the committed campaign record passes.
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_attn_campaign as C  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402

HAVE_VERILATOR = C.VERILATOR5.is_file() or shutil.which("verilator") is not None


def test_engine_order_equals_golden_csum():
    r = C.check_order_model(np.random.default_rng(11), 16)
    assert r["mismatching_trials"] == 0, r


def test_dequantiser_reference_matches_golden_qdq():
    rng = np.random.default_rng(4)
    for _ in range(20):
        x = (rng.standard_normal(64) * np.exp2(rng.integers(-20, 20))).astype(np.float32)
        c, sc = C.fp8_row_codes(x)
        y = C.deq_value(np.zeros(64, dtype=np.int64), c, np.repeat(sc, 16))
        assert np.array_equal(C.u32(y), C.u32(V.qdq_fp8(x)))
        x = (rng.standard_normal(64) * np.exp2(rng.integers(-6, 6))).astype(np.float32)
        c, sc = C.fp4_row_codes(x)
        y = C.deq_value(np.ones(64, dtype=np.int64), c, np.repeat(sc, 16))
        assert np.array_equal(C.u32(y), C.u32(V.qdq_fp4_e4m3(x, 16)))


@pytest.mark.skipif(not HAVE_VERILATOR, reason="verilator not installed")
def test_tile_rtl_bit_exact(tmp_path):
    r = C.run_tile(tmp_path, H=4, TD=16, nbeats=40, seed=7)
    assert r["status"] == "pass", r


@pytest.mark.skipif(not HAVE_VERILATOR, reason="verilator not installed")
def test_small_engine_rtl_bit_exact_and_back_to_back(tmp_path):
    cfg = dict(H=4, D=32, TD=16, NL=2, TROWS=72)
    rng = np.random.default_rng(9)
    jobs = [C.random_job(rng, 4, 32, T, min(T, 40)) for T in (72, 1, 33)]
    r = C.run_engine(tmp_path, "small", cfg, jobs)
    assert r["bit_exact"], r
    big = r["per_job"][0]                       # T = 72: 36 q.k beats, 5 blocks x DPT p.v beats
    assert big["qk_beat_bubbles"] == 0 and big["pv_beat_bubbles"] == 0, big


def test_campaign_record_passes():
    rec = json.loads(C.OUT.read_text())
    assert rec["status"] == "pass", rec.get("failures")
