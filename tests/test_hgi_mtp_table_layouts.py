"""The layout of an HBM table is a property of the bytes at an address: the writer (ds_native.build_tables / the MTP
seed set) records it per region, and every reader -- the lowering refusal, the simulator's FUSED.HC_PRE_NORM unit --
resolves it by the record's own address.

Regression (2026-10-13): the layout was looked up by table NAME through the offsets of the LAST build_tables call.  The
MTP program keeps five table regions at once (L0, three DSpark stages, the seed set), so every relocated stage gain
read "linear" although its bytes were GPK-packed: all 15 DSpark stage rows, the drafts and four of five verify targets
were wrong while the single-region L0 columns stayed bit-exact.

No checkpoint: the REAL builders (build_tables, Kernels.tables_for) and the REAL unit over a synthetic model.
"""
import dataclasses
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from hgi_sim import ds_mtp_kernels as KM  # noqa: E402
from hgi_sim import ds_native as DN  # noqa: E402
from hgi_sim import machine as MC  # noqa: E402
from hgi_sim.qwen_compiler import Builder  # noqa: E402
from hgi_sim.records import MDesc, Rec  # noqa: E402

F = np.float32
SIZES = {"attn_norm.weight": 5120, "ffn_norm.weight": 5120, "attn.q_norm.weight": 1280, "attn.kv_norm.weight": 512,
         "norm.weight": 5120, "attn.attn_sink": DN.HEADS}


def gain(seed, n):
    """a BF16-exact, strongly non-uniform gain (a permuted read cannot give the same norm)"""
    return (np.random.default_rng(seed).integers(1, 64, n) / 8.0).astype(F)


def model():
    m = SimpleNamespace(L=40, eps=F(1e-6), n_exp=384, freqs_plain=np.ones(32, F), freqs_yarn=np.ones(32, F),
                        ratio=[0] * 43, kv_of=list(range(43)), engram=SimpleNamespace(layer_ids=[]),
                        P=lambda L: f"layers.{L}." if L < 40 else f"mtp.{L - 40}.")

    def lw(L, name):
        if name == "ffn.gate.bias":
            return np.zeros(m.n_exp, F)
        return gain(100 * L + sorted(SIZES).index(name), SIZES[name])
    m.lw = lw
    m.w = {"norm.weight": gain(7, 5120), "mtp.0.main_norm.weight": gain(8, 5120)}
    m.hc_pre = lambda h, pre: (np.asarray(h, F) * np.asarray(pre, F)[:, None]).sum(0).astype(F)
    return m


def kernels(m):
    K = KM.Kernels.__new__(KM.Kernels)
    KM.bind_vm_tail()
    K.DN, K.Rec, K.MDesc, K.Builder, K.m, K.TP = DN, Rec, MDesc, Builder, m, 1
    K.lay, K.man = DN.Layout(), DN.Manifest()
    K.low = DN.Lower(m, 1, K.lay, K.man)
    K.tabs = {}
    K.st0 = SimpleNamespace(win={L: np.zeros((127, 512), F) for L in (0, 40, 41, 42)}, slots={})
    return K


@pytest.fixture()
def built():
    """L0, stage 0 (128 experts: its offsets differ from L0's) and the seed set, built as Kernels.__init__ does"""
    DN.TABLE_LAYOUT_AT.clear()
    m = model()
    K = kernels(m)
    K.tables_for(0)
    off0 = dict(DN.TABLE_OFF)
    m.n_exp = 128
    K.tables_for(40)
    off40 = dict(DN.TABLE_OFF)
    m.n_exp = 384
    K.tables_for("seed")
    return m, K, off0, off40


def pre_norm(K, base, tag="t"):
    return Rec("FUSED", "HC_PRE_NORM", imm_a=0, desc=dict(
        A=K.V("h", 20480), B=K.H(base, 5120, fmt="BF16"), C=K.V("PRE", 4), O=K.V("x", 5120, fmt="BF16")), tag=tag)


def run_unit(m, K, rec, tabs):
    die = MC.Die(0, MC.Hbm())
    for region, buf in tabs.items():
        die.hbm.add(region, buf, f"T{region:#x}")
    rng = np.random.default_rng(3)
    h = rng.standard_normal(20480).astype(F)
    pre = np.array([0.5, 0.25, 1.0, 2.0], F)
    die.vm[K.lay.vm["h"]:K.lay.vm["h"] + 20480] = h.view(np.uint32)
    die.vm[K.lay.vm["PRE"]:K.lay.vm["PRE"] + 4] = pre.view(np.uint32)
    units = DN.ds_units(m, K.man, None)
    M = MC.Machine([die], units)
    M.cur = rec
    units[("FUSED", "HC_PRE_NORM")](M, rec, 0)
    return M.vm_read(rec.desc["O"], die, 0), h.reshape(4, 5120), pre


def test_layouts_are_recorded_per_region(built):
    m, K, off0, off40 = built
    assert DN.FUSED_HLL
    assert off0["norm.weight"] != off40["norm.weight"]          # the offsets differ between regions (BIAS 384 / 128)
    r0, r40, rs = K.table_region(0), K.table_region(40), K.table_region("seed")
    want = {r0 + off0[n] for n in ("layers.0.attn_norm.weight", "layers.0.ffn_norm.weight", "norm.weight")}
    want |= {r40 + off40[n] for n in ("mtp.0.attn_norm.weight", "mtp.0.ffn_norm.weight", "norm.weight")}
    want.add(rs + K.dnorm_off)
    assert set(DN.TABLE_LAYOUT_AT) == want and set(DN.TABLE_LAYOUT_AT.values()) == {"GPK"}
    # a rebuilt region replaces only its own entries
    m.n_exp = 128
    K.tables_for(40)
    assert set(DN.TABLE_LAYOUT_AT) == want


@pytest.mark.parametrize("which", ["L0 attn", "stage attn", "stage ffn", "head", "dhead"])
def test_unit_reads_every_region_by_its_address(built, which):
    """FUSED.HC_PRE_NORM computes with the checkpoint gain in every region, the relocated ones included"""
    m, K, off0, off40 = built
    tabs = {K.table_region(L): K.tabs[L][0] for L in (0, 40, "seed")}
    base, g = {
        "L0 attn": (K.table_region(0) + off0["layers.0.attn_norm.weight"], m.lw(0, "attn_norm.weight")),
        "stage attn": (K.table_region(40) + off40["mtp.0.attn_norm.weight"], m.lw(40, "attn_norm.weight")),
        "stage ffn": (K.table_region(40) + off40["mtp.0.ffn_norm.weight"], m.lw(40, "ffn_norm.weight")),
        "head": (K.table_region(0) + off0["norm.weight"], m.w["norm.weight"]),
        "dhead": (K.dhead_norm().desc["B"].base, m.lw(42, "norm.weight")),
    }[which]
    got, h, pre = run_unit(m, K, pre_norm(K, base), tabs)
    want = DN.V_.rmsnorm_fold(m.hc_pre(h, pre), g, m.eps)
    assert np.array_equal(np.asarray(got, F).view(np.uint32), MC.A.to_bf16(np.asarray(want, F)).view(np.uint32))
    # the permuted read (the 10-13 regression) is a different result: the comparison above can see it
    bad = DN.V_.rmsnorm_fold(m.hc_pre(h, pre), np.asarray(g)[np.argsort(DN.gpk_index(5120))], m.eps)
    assert not np.array_equal(np.asarray(bad, F), np.asarray(want, F))


def test_relocated_stage_record_passes_the_lowering_refusal(built):
    """the lowering checks the gain layout in the region the layer's tables were built for (table_region), although
    its descriptors are still at TBASE until relocate()"""
    m, K, off0, off40 = built
    K.low.table_region = K.table_region(40)
    rec = pre_norm(K, DN.TBASE + off40["mtp.0.attn_norm.weight"])
    DN.assert_fused_fast_path(rec, gain_layout=DN.table_layout_at(rec.desc["B"].base - DN.TBASE + K.low.table_region))
    K.relocate([rec], KM.TSLOT[40])
    assert DN.table_layout_at(rec.desc["B"].base) == "GPK"


def test_mutant_linear_image_faults(built):
    """MUTANT: a d = 5,120 HC_PRE_NORM whose gain image is linear (the seed set's SU-read main_norm gain, or a region
    whose layout record is missing) is refused by the lowering check and FAULTS in the unit -- never a wrong norm"""
    m, K, off0, off40 = built
    tabs = {K.table_region(L): K.tabs[L][0] for L in (0, 40, "seed")}
    lin = pre_norm(K, K.table_region("seed") + DN.TABLE_OFF["mtp.0.main_norm.weight"], "linear_gain")
    with pytest.raises(ValueError, match="not GPK"):
        DN.assert_fused_fast_path(lin, gain_layout=DN.table_layout_at(lin.desc["B"].base))
    with pytest.raises(MC.Fault, match="linear_gain.*is linear.*reads GPK"):
        run_unit(m, K, lin, tabs)
    # the regression itself: the stage region's layout record dropped (what a name / last-offset lookup answered)
    DN.set_table_layouts(K.table_region(40), {})
    with pytest.raises(MC.Fault, match="is linear"):
        run_unit(m, K, pre_norm(K, K.table_region(40) + off40["mtp.0.attn_norm.weight"]), tabs)


def test_mutant_packed_image_on_the_micro_op_path_faults(built, monkeypatch):
    """MUTANT: the micro-op path (a target without the lane-local engine) reads linear; a GPK image there faults"""
    m, K, off0, off40 = built
    tabs = {K.table_region(0): K.tabs[0][0]}
    monkeypatch.setattr(DN, "FUSED_HLL", False)
    with pytest.raises(MC.Fault, match="is GPK.*reads linear"):
        run_unit(m, K, pre_norm(K, K.table_region(0) + off0["layers.0.attn_norm.weight"]), tabs)
