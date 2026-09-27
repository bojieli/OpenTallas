"""Hyper-connection projection engine (rtl/hdc/v41x/ot_hdc_v41x_hcp.sv): the reduction order, the bank
layout, the golden stand-in, and the committed campaign and physical records."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import rtl_hdc_v41x_hcp_campaign as C  # noqa: E402

F = np.float32
PHYS = ROOT / "results/physical_abi3/asap7/hdc/v41x"


@pytest.fixture(autouse=True)
def chunk8():
    old = G.ARITH
    G.set_arith("chunk8")
    yield
    G.set_arith(old)


def engine_sum(prod, W, TL):
    """The engine's order, step by step: 8-term chunks sequential from +0, a W-leaf pairwise tree per run,
    then the tail (level l: bit l of r set -> add the stored sibling; clear -> store, unless last run)."""
    n = prod.shape[0]
    assert n % 8 == 0
    nch = n // 8
    R = -(-nch // W)
    assert R <= (1 << TL)
    ch = np.zeros(R * W, F)
    for c in range(nch):
        acc = F(0)
        for k in range(8):
            acc = G.add(acc, prod[8 * c + k])
        ch[c] = acc
    slots = [None] * TL
    out = None
    for r in range(R):
        v = ch[r * W:(r + 1) * W]
        while v.shape[0] > 1:
            v = G.add(v[0::2], v[1::2])
        v = F(v[0])
        last = r == R - 1
        for lv in range(TL):
            bit = (r >> lv) & 1
            if bit:
                v = G.add(slots[lv], v)
            elif last:
                v = G.add(F(0), v)
            else:
                slots[lv] = v
                break
        else:
            assert last
            out = v
    return out


@pytest.mark.parametrize("W,TL,n", [(8, 9, 640), (8, 9, 20480), (256, 4, 20480), (256, 4, 640), (2, 4, 8),
                                    (8, 4, 8 * 9), (4, 5, 8 * 77)])
def test_engine_order_is_csum(W, TL, n):
    rng = np.random.default_rng(n + W)
    prod = (rng.choice([-1, 1], n) * np.exp2(rng.uniform(-20, 20, n))).astype(F)
    assert G.bits(engine_sum(prod, W, TL)) == G.bits(G.csum(prod))


def test_bank_layout_holds_fn_and_x():
    rng = np.random.default_rng(3)
    case = {"fn": rng.standard_normal((5, 8 * 21)).astype(F),
            "x": G.to_bf16(rng.standard_normal((2, 8 * 21)).astype(F)), "scale": 0, "eps": 1e-6,
            "exp": np.zeros((2, 5), F)}
    W = 8
    wm, xm, cmds, exps = C.images([case], W)
    R = 3
    for o in range(5):
        for r in range(R):
            for k in range(8):
                for l in range(W):
                    c = r * W + l
                    if c < 21:
                        assert int(wm[k, o * R + r, l]) == int(G.bits(case["fn"][o, 8 * c + k]))
    assert int(xm[3, 1 * R + 0, 2]) == int(G.bits(case["x"][1, 8 * 2 + 3])) >> 16
    assert cmds[0][:4] == [2, 5, 21, 0] and len(exps) == 10


def test_stand_in_is_the_golden_call():
    rng = np.random.default_rng(5)
    fn = (rng.standard_normal((24, 64)) * 0.01).astype(F)
    x = G.to_bf16(rng.standard_normal((4, 16)).astype(F))
    raw, r, mixes = C.golden_mixes(fn, x, 1e-6)
    flat = x.reshape(-1)
    r2 = G.rsqrt(G.add(G.div(G.csum(G.mul(flat, flat)), F(flat.size)), F(1e-6)))
    assert G.bits(r) == G.bits(r2)
    assert np.array_equal(G.bits(mixes), G.bits(G.mul(G.csum(G.mul(fn, flat[None, :])), r2)))


def test_committed_record_passes_and_is_current():
    rec = json.loads(C.OUT.read_text())
    assert rec["status"] == "pass"
    for name, b in rec["benches"].items():
        assert b["run"]["pass"] and b["run"]["mismatches"] == 0 and b["run"]["faults"] == 0, name
    spec = rec["spec_check"]
    assert spec["lanes"]["met"] and spec["one_position_latency_cycles"]["met"]
    assert spec["six_positions_m2_4096_lanes"]["issue_bound"] == 750
    assert rec["fp_stand_in"]["identical_results_and_cycles"]
    assert all(m["caught"] != m["control"] for m in rec["mutations"])
    for p, digest in rec["input_sha256"].items():
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest, p


def test_physical_records_route_the_committed_sources():
    tops = sorted(PHYS.glob("ot_hdc_v41x_hcp*/physical.json"))
    assert tops
    for f in tops:
        body = json.loads(f.read_text())
        for src in body["design"]["sources"]:
            assert hashlib.sha256((ROOT / src["path"]).read_bytes()).hexdigest() == src["sha256"], src["path"]
