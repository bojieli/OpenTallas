"""The MTP swap caller path: Kernels.swap_bodies(b2_swap=...) fed by the REAL B2 record-liveness allocator.

What is real: the swap-body records are Kernels.swap's own (the production descriptors over ds_native.Layout), the
placement is hgi_b2.b2.Collect + allocate run on those records in the HGI simulator, and the per-cluster physical
descriptors are read from that placement by allocations_from_placement (nothing hand-written).
What is a stand-in: the Kernels object is built without the model (object.__new__ + the four attributes swap needs;
a full Kernels needs the DeepSeek weights), and the record that makes h MIRROR is ONE SM.MATVEC reading h whole
(the production layer bodies need the weights).

NATIVE LAYOUT (hgi_b2.mtp_swap): cluster q moves its CONTIGUOUS quarter of h (logical rows 80q .. 80q + 79) to stack
q's slot rows q + 4j.  That is where the allocator holds h: the native program's own records place quarter q LOCAL q
(B2 mode NATIVE), the committed DS L14 layer placement holds quarter q LOCAL q at physical 0, and a whole-h reader
makes it MIRROR (still resident in every slice).  The LEGACY STRIPE4 records alone put all of h LOCAL to cluster 0
(DMA = a central ring client), which the native lowering refuses.
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

COLB, CSTR = (20 << 30) + (256 << 20), 1 << 17      # independent of ds_mtp_kernels (asserted equal below)
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


def program(K, consumer, native):
    sw = K.swap_native if native else K.swap
    return sw(True)[:-1] + consumer + sw(False)


def allocator_run(K, consumer, native=True):
    """hgi_b2 pass 1 (Collect) over swapin -> consumer -> swapout on one die; returns the PlacementSet."""
    hbm = memory()
    hbm.add(WB, np.zeros(8 * 20480 * 2, np.uint8))
    C = B.Collect()
    M = Machine([Die(0, hbm)], {k: C.wrap(k, f) for k, f in UNITS.items()})
    M.run(b"", 3, 0, recs=program(K, consumer, native), hash_bufs=False)
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
    # the native layout rule by hand: logical row 80q + j on stack q, 256 B rows packed from stack-local
    # COLB + slot * CSTR + 64q (the slot's rows q + 4j); PRE on stack 0
    for q in range(4):
        for j in range(80):
            address = (q << 35) + COLB + slot * CSTR + 64 * q + 256 * j
            assert np.array_equal(hbm.view(address, 256).view(np.uint32), values[80 * q + j].view(np.uint32))
    assert np.array_equal(hbm.view(COLB + slot * CSTR + 81920, 32).view(np.uint32), pre.view(np.uint32))


def test_constants_match_the_allocator_and_the_kernels():
    assert (S._NQ, S._MIR, S._LOCAL_W) == (B.NQ, B.MIR, B.LOCAL_W)
    assert (KM.COLB, KM.CSTR, KM.SLOT) == (COLB, CSTR, (("h", 0, 20480), ("PRE", 81920, 8)))


def test_real_allocator_yields_mirror_h_and_local0_pre(live):
    K, ps, C = live
    assert dict(C.modes) == {("DMA", "NATIVE"): 10, ("SM", "ESPLIT"): 1}
    hb, pb = K.lay.vm["h"], K.lay.vm["PRE"]
    pl = ps.of(0)
    assert set(pl.cls[hb:hb + 20480].tolist()) == {B.MIR}          # read whole by a split record -> MIRROR
    assert set(pl.cls[pb:pb + 8].tolist()) == {0}                  # the PRE singleton's sector -> LOCAL 0
    hs, pre = allocations_from_placement(ps, hb, pb)
    m0 = int(pl.phys[hb])
    assert m0 >= B.LOCAL_W
    assert hs == {q: MDesc(base=m0 + 5120 * q, n=64, m=80, stride=64) for q in range(4)}
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
            mine = pl.phys[hrows[80 * q:80 * q + 80]].reshape(-1)
            assert np.array_equal(got[q][mine], values[80 * q:80 * q + 80].reshape(-1).view(np.uint32))
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


def test_native_records_alone_place_every_quarter_local_to_its_cluster():
    """The native program's own records are the allocator's evidence: quarter q is needed by cluster q only."""
    K = kernels()
    ps, C = allocator_run(K, [])
    hb, pb = K.lay.vm["h"], K.lay.vm["PRE"]
    pl = ps.of(0)
    assert dict(C.modes) == {("DMA", "NATIVE"): 10}
    for q in range(4):
        assert set(pl.cls[hb + 5120 * q:hb + 5120 * (q + 1)].tolist()) == {q}
    hs, pre = allocations_from_placement(ps, hb, pb)
    assert hs == {q: MDesc(base=int(pl.phys[hb + 5120 * q]), n=64, m=80, stride=64) for q in range(4)}
    assert all(d.base + 5120 <= B.LOCAL_W for d in hs.values()) and pre == MDesc(base=int(pl.phys[pb]), n=8)


def run_check(K, ps, consumer=(), native=True):
    hbm = memory()
    hbm.add(WB, np.zeros(8 * 20480 * 2, np.uint8))
    chk = B.Check(ps, None)
    M = Machine([Die(0, hbm)], {k: chk.wrap(k, f) for k, f in UNITS.items()})
    M.run(b"", 3, 0, recs=program(K, list(consumer), native), hash_bufs=False)
    return chk


def test_b2_check_dispatches_native_members_with_no_ring_word(live):
    K, ps, _ = live
    for pset, consumer in ((allocator_run(K, [])[0], []), (ps, whole_h_reader(K))):
        chk = run_check(K, pset, consumer)
        assert chk.finish()["violations"] == 0, chk.viol
        nat = [e for e in chk.recs if e["mode"] == "NATIVE"]
        assert [e["cluster"] for e in nat] == [0, 1, 2, 3, 0] * 2
        assert [e["group_last"] for e in nat] == [False, False, False, True, True] * 2
        assert all(e["ring_read"] == e["ring_write"] == 0 for e in nat)
        hs, pre = allocations_from_placement(pset, K.lay.vm["h"], K.lay.vm["PRE"])
        for e in nat[:4]:                           # the swap-in group: O is the cluster's quarter
            d = hs[e["cluster"]]
            assert e["sub"][f"O{e['cluster']}"]["phys"] == [d.base, 64, 80, d.stride, 1]
        assert nat[4]["sub"]["O0"]["phys"][:3] == [pre.base, 8, 1]
        assert chk.ring["central_remote_read"] == chk.ring["central_remote_write"] == 0


def test_b2_check_refuses_a_native_member_on_another_clusters_words():
    """the check's teeth: quarter 1 placed LOCAL to cluster 2 -> cluster 1's member is refused"""
    K = kernels()
    ps, _ = allocator_run(K, [])
    hb = K.lay.vm["h"]
    pl = _mutable(ps)
    pl.cls[hb + 5120:hb + 10240] = 2
    pl.phys[hb + 5120:hb + 10240] = 30000 + np.arange(5120)
    chk = run_check(K, pl)
    assert any("native member of cluster 1 touches 5120 words outside slice 1" in v for v in chk.viol), chk.viol


def test_legacy_swap_records_alone_are_refused():
    """The STRIPE4 record is a CENTRAL ring client: with only the legacy swap records the allocator puts ALL of h
    LOCAL to cluster 0, and the native lowering is not legal on that placement."""
    K = kernels()
    ps, C = allocator_run(K, [], native=False)
    hb, pb = K.lay.vm["h"], K.lay.vm["PRE"]
    assert dict(C.modes) == {("DMA", "CENTRAL"): 4}
    assert set(ps.of(0).cls[hb:hb + 20480].tolist()) == {0}
    with pytest.raises(ValueError, match="h row 80: not resident in cluster 1"):
        allocations_from_placement(ps, hb, pb)
    with pytest.raises(ValueError):                 # the opt-in never falls back silently
        K.swap_bodies(0, lambda r: allocations_from_placement(ps, hb, pb, rank=r))


def test_committed_ds_l14_placement_holds_h_in_the_native_layout():
    """The committed DS layer-14 B2 placement holds h as CONTIGUOUS quarters (cluster q = rows 80q .. 80q + 79,
    LOCAL q, physical 0, stride 64): exactly the native layout's owner rule, so the h group lowers on it as it
    stands.  (That layer program has no swap, so PRE's whole sector is not placed: the PRE descriptor needs the
    MTP program's placement.)"""
    t = json.loads((ROOT / "results/rtl/hbm_b2_1012/v8_ds_L14/placement.json").read_text())
    lay = DN.Layout()
    hb, pb = lay.vm["h"], lay.vm["PRE"]
    assert [s[:4] for s in t["segments"] if hb <= s[0] < hb + 20480] == [[hb + 5120 * q, 5120, q, 0] for q in range(4)]
    assert S.h_allocations_from_placement(t, hb) == {q: MDesc(base=0, n=64, m=80, stride=64) for q in range(4)}
    with pytest.raises(ValueError, match="PRE: not resident in cluster 0"):
        allocations_from_placement(t, hb, pb)


def test_logical_native_program_writes_the_native_image_and_round_trips():
    """What the HGI simulator runs (Kernels.swap_native on the one logical VM): same image as the per-slice groups."""
    K = kernels()
    hb, pb = K.lay.vm["h"], K.lay.vm["PRE"]
    swapin, swapout = K.swap_bodies(0, "native")
    assert [(r.unit, r.op, r.param) for r in swapout] == [("DMA", "STORE", 1)] * 3 + [
        ("DMA", "STORE", 3), ("DMA", "STORE", 3), ("CTL", "FENCE", 0), ("CTL", "END", 0)]
    assert [S.group_cluster(r) for r in swapin[:5]] == [0, 1, 2, 3, 0]
    encode_program(swapin), encode_program(swapout)
    hbm = memory()
    for slot in (0, 5, 12):
        values = np.arange(20480, dtype=np.float32).reshape(320, 64) + slot * 32768 + 1
        pre = np.arange(8, dtype=np.float32) + slot * 8 + 0.5
        d = Die(0, hbm)
        d.dyn[3] = slot
        d.vm[hb:hb + 20480] = values.reshape(-1).view(np.uint32)
        d.vm[pb:pb + 8] = pre.view(np.uint32)
        for r in swapout[:5]:
            execute(r, d)
        check_oracle(hbm, values, pre, slot)
        d.vm[hb:hb + 20480] = 0
        d.vm[pb:pb + 8] = 0
        for r in swapin[:5]:
            execute(r, d)
        assert np.array_equal(d.vm[hb:hb + 20480], values.reshape(-1).view(np.uint32))
        assert np.array_equal(d.vm[pb:pb + 8], pre.view(np.uint32))


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
        for o in range(240, 320):
            pl.cls[row(o)] = -1
    elif mutant == "non_affine":           # two of cluster 2's rows exchanged in physical space
        a, b = pl.phys[row(162)].copy(), pl.phys[row(166)].copy()
        pl.phys[row(162)], pl.phys[row(166)] = b, a
    elif mutant == "wrong_slice":          # one row of cluster 1 LOCAL to cluster 2
        pl.cls[row(121)], pl.phys[row(121)] = 2, 4096 + np.arange(64)
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
    # the encoded legacy bodies: origin/main 6e5c22c1c's Kernels.swap with ONE change, the column slot base COLB moved
    # from stack-local 6 GiB (inside the weight manifest on stack 2) into the reserved data window (20.25 GiB; 2026-10-13); nothing else differs
    assert hashlib.sha256(encode_program(swapin)).hexdigest() == LEGACY_SHA["in"]
    assert hashlib.sha256(encode_program(swapout)).hexdigest() == LEGACY_SHA["out"]


LEGACY_SHA = {"in": "13be167c893993ba4832fcf542cbd141383fefe8a189e254431e5b3f6b31c3ba", "out": "0396f34b90d3e15f44543a6d73f5e3d305d0a870c2d73e74cc369ac3867712d1"}
