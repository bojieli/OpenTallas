"""The V4.1 vector stream unit (rtl/hdc/v41x/ot_hdc_v41x_vec*.sv): the reference, the layout, the reducer's
order claim, and the committed campaign and physical records (tools/rtl_hdc_v41x_vec_campaign.py)."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_vec_campaign as C  # noqa: E402

PHYSICAL = ROOT / "results/physical_abi3/asap7/hdc/v41x"


def test_lane_order_reproduces_csum():
    """Per-vector 8-lane chains, an aligned tree tapped at the slot's level and a streaming binary counter
    across vectors give hdc_golden_v41.csum bit for bit."""
    r = C.check_reducer_claim(np.random.default_rng(11), 150)
    assert r["mismatches"] == 0 and r["segments"] == 150


def test_reference_elements_equal_the_isa_simulator():
    rng = np.random.default_rng(3)
    ops, init = C.random_program(rng, 16, 8, 40, C.Alloc(64, (1 << C.VMA) - 64))
    m = C.fresh_mem(rng, init)
    seen = 0
    for f in ops:
        r = C.check_ref_vs_isa(f, m)
        assert r in (True, None)
        seen += r is True
        C.ref_op(dict(f), m)
    assert seen > 25


@pytest.mark.parametrize("N,M", [(16, 8), (64, 16), (1024, 256)])
def test_layout_covers_every_element_once(N, M):
    rng = np.random.default_rng(N)
    ops, _ = C.random_program(rng, min(N, 64), min(M, 16), 40, C.Alloc(64, (1 << C.VMA) - 64))
    for f in ops:
        lay = C.layout(f, N, M)
        if lay["bad"]:
            continue
        got = np.concatenate([oo * f["nin"] + ii for oo, ii in lay["vecs"]])
        assert np.array_equal(np.sort(got), np.arange(f["nout"] * f["nin"]))
        assert all(len(oo) <= lay["vw"] for oo, _ in lay["vecs"])


def test_committed_campaign_is_current_and_passes():
    rec = json.loads(C.OUT.read_text())
    for name, digest in rec["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    assert rec["sfu_equivalence"]["pass_"]
    for runs in rec["random"].values():
        assert all(r["pass_"] for r in runs)
    assert all(b["pass_"] for b in rec["vehicle"]["batches"])
    for key in ("perf_N64_M16", "perf_N1024_M256"):
        p = rec[key]
        for part in ("hc_post", "depths", "chain_ext", "mixed_classes"):
            assert p[part]["check"]["pass_"], (key, part)
    spec = rec["spec"]
    for row in spec["rows"]:
        if row.get("graded"):
            assert row["meets"] == row["expected_meets"], row["item"]


def test_physical_records_route_the_committed_sources():
    tops = sorted(p.name for p in PHYSICAL.iterdir() if (p / "physical.json").exists()) if PHYSICAL.exists() else []
    assert tops
    for top in tops:
        body = json.loads((PHYSICAL / top / "physical.json").read_text())
        assert body["design"]["top"] == top
        for src in body["design"]["sources"]:
            assert hashlib.sha256((ROOT / src["path"]).read_bytes()).hexdigest() == src["sha256"], src["path"]
