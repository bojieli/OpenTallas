"""ds_native refuses a d = 5120 FUSED HC_PRE_NORM / HC_POST record that would miss the lane-local fast path
(ot_hgi_fused_record hce_ok / hgp_ok: bank phase rule A, GPK gain rule B)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from hgi_sim import ds_native as DN  # noqa: E402
from hgi_sim.records import MDesc, Rec  # noqa: E402

D = DN.FUSED_HCD
pytestmark = pytest.mark.skipif(not DN.FUSED_HLL, reason="HGI_FUSED_HLL=0: no lane-local target")


def vm(base, n, fmt="FP32"):
    return MDesc(space="VM", fmt=fmt, base=base, n=n)


def pre_norm(a=0, o=41216, gb=DN.TBASE):
    return Rec("FUSED", "HC_PRE_NORM", desc=dict(A=vm(a, 4 * D), B=MDesc(space="HBM", fmt="BF16", base=gb, n=D),
                                                 C=vm(30000, 4), O=vm(o, D, "BF16")), tag="t")


def post(a=0, b=8192, o=51200):
    return Rec("FUSED", "HC_POST", desc=dict(A=vm(a, D), B=vm(b, 4 * D), C=vm(40000, 20), O=vm(o, 4 * D)), tag="t")


def test_conforming_records_pass():
    DN.assert_fused_fast_path(pre_norm(), scratch=245760, gain_layout="GPK")
    DN.assert_fused_fast_path(post())


@pytest.mark.parametrize("rec,kw", [
    (pre_norm(o=41152), dict(gain_layout="GPK")),            # O at bank phase 24 (the old 64-word layout)
    (pre_norm(a=4), dict(gain_layout="GPK")),                 # A not sector aligned
    (pre_norm(), dict(scratch=245760 + 8, gain_layout="GPK")),  # scratch off O's bank phase
    (pre_norm(), dict(gain_layout=None)),                     # gain stored linear, not GPK
    (pre_norm(gb=DN.TBASE + 2), dict(gain_layout="GPK")),     # gain not 4-byte aligned
    (post(b=8200), {}),                                       # B at another bank phase
    (post(o=51264), {}),                                      # O at another bank phase
])
def test_violating_records_raise(rec, kw):
    with pytest.raises(ValueError, match="fast path"):
        DN.assert_fused_fast_path(rec, **kw)


def test_other_d_not_checked():
    r = Rec("FUSED", "HC_POST", desc=dict(A=vm(0, 4096), B=vm(8, 4 * 4096), O=vm(16, 4 * 4096)))
    DN.assert_fused_fast_path(r)


def test_layout_and_gpk():
    lay = DN.Layout()
    assert {DN.vm_phase(lay.V(k, 1)) for k in DN.HC_BANK_BUFS} == {0}
    assert all(lay.vm[k] % 8 == 0 for k in DN.HC_BANK_BUFS)
    p = DN.gpk_index(D)
    assert sorted(p.tolist()) == list(range(D))
    # data sector s -> packed sector (s mod 32) + 32 floor(s / 64), half (s / 32) mod 2 (fused_bench FUSED_HLL image)
    for s in (0, 31, 32, 33, 63, 64, 639):
        assert p[8 * s] == 16 * ((s % 32) + 32 * (s // 64)) + 8 * ((s // 32) % 2)
    g = np.arange(D, dtype=np.float32)
    pk = np.empty_like(g)
    pk[p] = g
    assert np.array_equal(pk[p], g)
