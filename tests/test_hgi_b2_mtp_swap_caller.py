"""The MTP swap caller path: Kernels.swap_bodies(b2_swap=...) fed by the REAL B2 record-liveness allocator.

What is real: the swap-body records are Kernels.swap's own (the production descriptors over ds_native.Layout), the
placement is hgi_b2.b2.Collect + allocate run on those records in the HGI simulator, and the per-cluster physical
descriptors are read from that placement by allocations_from_placement (nothing hand-written).
What is a stand-in: the Kernels object is built without the model (object.__new__ + the four attributes swap needs;
a full Kernels needs the DeepSeek weights), and the record that makes h MIRROR is ONE SM.MATVEC reading h whole
(the production layer bodies need the weights).  With the swap records alone, and in the committed DS L14 placement,
the allocator does NOT place h as rows q + 4j per cluster, and the native lowering is refused (tests below).
"""
import hashlib
import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from hgi_b2 import b2 as B
from hgi_b2 import mtp_swap as S
from hgi_b2.mtp_swap import DispatchGroup, allocations_from_placement
from hgi_sim import ds_native as DN, ds_mtp_kernels as KM
from hgi_sim.records import MDesc, Rec, encode_program
from hgi_sim.qwen_compiler import Builder
from hgi_sim.machine import Hbm, Die, Machine, UNITS, u_dma_load, u_dma_store

COLB, CSTR = 0x180000000, 1 << 17      # independent of ds_mtp_kernels (asserted equal below)
WB = 0x100000                          # the stand-in consumer's weight rows
POISON = 0x7F812345


def kernels():
    """Kernels without the model: exactly what swap / swap_b2 / swap_bodies read."""
    K = object.__new__(KM.Kernels)
    K.MDesc, K.Rec, K.Builder, K.lay = MDesc, Rec, Builder, DN.Layout()
    KM.bind_vm_tail()
    return K


def memory():
    h = Hbm()
    for q in range(4):
        h.add((q << 35) | COLB, np.zeros(13 * CSTR, np.uint8))
    return h


def allocator_run(K, consumer):
    """hgi_b2 pass 1 (Collect) over swapin -> consumer -> swapout on one die; returns the PlacementSet."""
    hbm = memory()
    hbm.add(WB, np.zeros(8 * 20480 * 2, np.uint8))
    C = B.Collect()
    M = Machine([Die(0, hbm)], {k: C.wrap(k, f) for k, f in UNITS.items()})
    M.run(b"", 3, 0, recs=K.swap(True)[:-1] + consumer + K.swap(False), hash_bufs=False)
    ps = C.placement()
    assert ps.proof == [] and ps.capacity()["fits"]
    return ps, C


def whole_h_reader(K):
    return [Rec("SM", "MATVEC", param=0, desc=dict(
        A=K.V("h", 20480), B=K.H(WB, 20480, fmt="BF16", m=8, stride=40960), O=K.V("x", 8)), tag="standin.h_whole")]


@pytest.fixture(scope="module")
def live():
    K = kernels()
    ps, C = allocator_run(K, whole_h_reader(K))
    return K, ps, C


def execute(rec, die):
    m = Machine([die])
    m.cur = rec
    (u_dma_store if rec.op == "STORE" else u_dma_load)(m, rec, 0)


def check_oracle(hbm, values, pre, slot):
    # the logical STRIPE4 rule: row o on stack o mod 4 at stack-local COLB + slot * CSTR + o * 64; PRE on stack 0
    for o in range(320):
        address = ((o % 4) << 35) + COLB + slot * CSTR + o * 64
        assert np.array_equal(hbm.view(address, 256).view(np.uint32), values[o].view(np.uint32))
    assert np.array_equal(hbm.view(COLB + slot * CSTR + 81920, 32).view(np.uint32), pre.view(np.uint32))


def test_constants_match_the_allocator_and_the_kernels():
    assert (S._NQ, S._MIR, S._LOCAL_W) == (B.NQ, B.MIR, B.LOCAL_W)
    assert (KM.COLB, KM.CSTR, KM.SLOT) == (COLB, CSTR, (("h", 0, 20480), ("PRE", 81920, 8)))


def test_real_allocator_yields_mirror_h_and_local0_pre(live):
    K, ps, C = live
    assert dict(C.modes) == {("DMA", "CENTRAL"): 4, ("SM", "ESPLIT"): 1}
    hb, pb = K.lay.vm["h"], K.lay.vm["PRE"]
    pl = ps.of(0)
    assert set(pl.cls[hb:hb + 20480].tolist()) == {B.MIR}          # read whole by a split record -> MIRROR
    assert set(pl.cls[pb:pb + 8].tolist()) == {0}                  # central-only -> LOCAL to the home cluster
    hs, pre = allocations_from_placement(ps, hb, pb)
    m0 = int(pl.phys[hb])
    assert m0 >= B.LOCAL_W
    assert hs == {q: MDesc(base=m0 + 64 * q, n=64, m=80, stride=256) for q in range(4)}
    assert pre == MDesc(base=int(pl.phys[pb]), n=8)
    # the exported table (placement.json's form) resolves to the same descriptors
    assert allocations_from_placement(json.loads(json.dumps(pl.table(), default=int)), hb, pb) == (hs, pre)


def test_caller_path_writes_the_legacy_image_all_slots(live):
    K, ps, _ = live
    hb, pb = K.lay.vm["h"], K.lay.vm["PRE"]
    pl = ps.of(0)
    asked = []

    def b2_swap(rank):
        asked.append(rank)
        return allocations_from_placement(ps, hb, pb, rank=rank)

    swapin, swapout = K.swap_bodies(0, b2_swap)
    assert asked == [0]
    for body, op, tail in ((swapin, "LOAD", ["END"]), (swapout, "STORE", ["FENCE", "END"])):
        assert isinstance(body[0], DispatchGroup) and isinstance(body[1], DispatchGroup)
        assert [e.cluster for e in body[0].records] == [0, 1, 2, 3]
        assert [e.cluster for e in body[1].records] == [0]
        assert {e.record.op for g in body[:2] for e in g.records} == {op}
        assert [e.record.tag.split(".")[1] for e in body[0].records] == ["h"] * 4
        assert body[1].records[0].record.tag.endswith(".PRE")
        assert [(r.unit, r.op) for r in body[2:]] == [("CTL", t) for t in tail]
    hbm = memory()
    hrows = (hb + 64 * np.arange(320)[:, None] + np.arange(64)[None, :])
    for slot in range(13):
        values = np.arange(20480, dtype=np.float32).reshape(320, 64) + slot * 32768
        pre = np.arange(8, dtype=np.float32) + slot * 8 + 0.5
        logical = np.zeros(B.VMW, np.uint32)
        logical[hb:hb + 20480] = values.reshape(-1).view(np.uint32)
        logical[pb:pb + 8] = pre.view(np.uint32)
        # STORE: every cluster's slice is the ALLOCATOR's image of the logical VM (Placement.slice_image), not the
        # descriptor under test; everything above the slice is poison
        for g in swapout[:2]:
            for e in g.records:
                d = Die(e.cluster, hbm)
                d.vm.fill(POISON)
                d.vm[:B.SLICE_W] = pl.slice_image(logical, e.cluster)
                d.dyn[3] = slot
                execute(e.record, d)
        check_oracle(hbm, values, pre, slot)
        # LOAD: each cluster writes only its own rows; the four writes together are the allocator's image of h
        # (MIRROR: the mirror-write broadcast makes every slice's copy whole), cluster 0 also holds PRE
        got = np.full((4, B.SLICE_W), POISON, np.uint32)
        for g in swapin[:2]:
            for e in g.records:
                d = Die(e.cluster, hbm)
                d.vm.fill(POISON)
                d.dyn[3] = slot
                execute(e.record, d)
                assert np.all(d.vm[B.SLICE_W:] == POISON)
                w = d.vm[:B.SLICE_W] != POISON
                got[e.cluster][w] = d.vm[:B.SLICE_W][w]
        for q in range(4):
            mine = pl.phys[hrows[q::4]].reshape(-1)
            assert np.array_equal(got[q][mine], values[q::4].reshape(-1).view(np.uint32))
        union = np.full(B.SLICE_W, POISON, np.uint32)
        for q in range(4):
            w = got[q] != POISON
            union[w] = got[q][w]
        want = pl.slice_image(logical, 0)
        touched = np.concatenate([pl.phys[hb:hb + 20480], pl.phys[pb:pb + 8]])
        assert np.array_equal(union[touched], want[touched])
        rest = np.ones(B.SLICE_W, bool)
        rest[touched] = False
        assert np.all(union[rest] == POISON)


def test_swap_records_alone_are_refused():
    """DMA is a CENTRAL ring client: with only the swap records the allocator puts ALL of h LOCAL to cluster 0."""
    K = kernels()
    ps, C = allocator_run(K, [])
    hb, pb = K.lay.vm["h"], K.lay.vm["PRE"]
    assert dict(C.modes) == {("DMA", "CENTRAL"): 4}
    assert set(ps.of(0).cls[hb:hb + 20480].tolist()) == {0}
    with pytest.raises(ValueError, match="h row 1: not resident in cluster 1"):
        allocations_from_placement(ps, hb, pb)
    with pytest.raises(ValueError):                 # the opt-in never falls back silently
        K.swap_bodies(0, lambda r: allocations_from_placement(ps, hb, pb, rank=r))


def test_committed_ds_l14_placement_is_refused():
    """The committed DS layer-14 B2 placement holds h as CONTIGUOUS quarters (cluster q = rows 80q .. 80q + 79,
    LOCAL q, physical 0, stride 64), not rows q + 4j: the STRIPE4 own-stack lowering is not legal on it."""
    t = json.loads((ROOT / "results/rtl/hbm_b2_1012/v8_ds_L14/placement.json").read_text())
    lay = DN.Layout()
    hb, pb = lay.vm["h"], lay.vm["PRE"]
    assert [s[:4] for s in t["segments"] if hb <= s[0] < hb + 20480] == [[hb + 5120 * q, 5120, q, 0] for q in range(4)]
    with pytest.raises(ValueError, match="h row 80: not resident in cluster 0"):
        allocations_from_placement(t, hb, pb)


def _mutable(ps):
    pl = ps.of(0)
    return B.Placement(pl.cls.copy(), pl.phys.copy(), dict(pl.use), dict(pl.peak))


@pytest.mark.parametrize("mutant", ["missing_cluster", "non_affine", "wrong_slice", "pre_wrong_slice", "pre_split",
                                    "aliased", "unaligned", "other_rank"])
def test_allocations_the_allocator_did_not_produce_are_refused(live, mutant):
    K, ps, _ = live
    hb, pb = K.lay.vm["h"], K.lay.vm["PRE"]
    pl = _mutable(ps)
    row = lambda o: slice(hb + 64 * o, hb + 64 * o + 64)       # noqa: E731
    rank = 0
    if mutant == "missing_cluster":        # cluster 3's rows unplaced
        for o in range(3, 320, 4):
            pl.cls[row(o)] = -1
    elif mutant == "non_affine":           # two of cluster 2's rows exchanged in physical space
        a, b = pl.phys[row(2)].copy(), pl.phys[row(6)].copy()
        pl.phys[row(2)], pl.phys[row(6)] = b, a
    elif mutant == "wrong_slice":          # one row of cluster 1 LOCAL to cluster 2
        pl.cls[row(41)], pl.phys[row(41)] = 2, 4096 + np.arange(64)
    elif mutant == "pre_wrong_slice":
        pl.cls[pb:pb + 8] = 1
    elif mutant == "pre_split":            # half the sector elsewhere
        pl.phys[pb + 4:pb + 8] += 60
    elif mutant == "aliased":              # another logical word shares one of h's physical words
        pl.cls[200000], pl.phys[200000] = pl.cls[hb + 64 * 5], pl.phys[hb + 64 * 5]
    elif mutant == "unaligned":            # the whole mirror block moved by 8 words
        pl.phys[hb:hb + 20480] += 8
    elif mutant == "other_rank":           # a die the allocator never placed
        pl, rank = ps, 7
    with pytest.raises(ValueError):
        allocations_from_placement(pl, hb, pb, rank=rank)
    if mutant != "other_rank":
        allocations_from_placement(_mutable(ps), hb, pb)      # the unmutated copy is accepted


def test_default_path_is_the_legacy_swap_byte_for_byte():
    K = kernels()
    assert inspect.signature(KM.Kernels.__init__).parameters["b2_swap"].default is None
    assert inspect.signature(KM.Kernels.swap_bodies).parameters["b2_swap"].default is None
    assert "self.swap_bodies(r, b2_swap)" in inspect.getsource(KM.Kernels.__init__)
    calls = []
    real = KM.Kernels.swap
    K.swap = lambda into: calls.append(into) or real(K, into)
    K.swap_b2 = lambda *a: pytest.fail("the default path must not lower")
    swapin, swapout = K.swap_bodies(0)
    assert calls == [True, False]
    assert [(r.unit, r.op, r.tag) for r in swapin] == [
        ("DMA", "LOAD", "swapin.h"), ("DMA", "LOAD", "swapin.PRE"), ("CTL", "END", "end")]
    assert [(r.unit, r.op, r.tag) for r in swapout] == [
        ("DMA", "STORE", "swapout.h"), ("DMA", "STORE", "swapout.PRE"), ("CTL", "FENCE", "fence"), ("CTL", "END", "end")]
    assert encode_program(swapin) == encode_program(real(K, True))
    assert encode_program(swapout) == encode_program(real(K, False))
    # the encoded legacy bodies as origin/main 6e5c22c1c emits them (digests taken from that tree's Kernels.swap)
    assert hashlib.sha256(encode_program(swapin)).hexdigest() == LEGACY_SHA["in"]
    assert hashlib.sha256(encode_program(swapout)).hexdigest() == LEGACY_SHA["out"]


LEGACY_SHA = {"in": "f5eb36cbcc35c9ba53b612ef8499e0b48a39392e6199e5d37c6554160f2e14af", "out": "9d0fd1f7de9c135ab7ecc2a30fd2cbff119f6cac8961b01edcd0836d5507c160"}
