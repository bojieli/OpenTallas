"""Production-sized native swap descriptors against an independent oracle of the native slot layout
(cluster q's quarter, logical rows 80q .. 80q + 79, on stack q's slot rows q + 4j) and against the legacy STRIPE4
image (same sectors, rows permuted by owner)."""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from hgi_b2.mtp_swap import lower_h, lower_pre
from hgi_sim.records import MDesc, Rec
from hgi_sim.machine import Hbm, Die, Machine, Fault, u_dma_load, u_dma_store

COLB, CSTR = (20 << 30) + (256 << 20), 1 << 17


def legacy(op):
    h = MDesc(space="HBM", base=(1 << 37) | COLB, n=64, m=320,
              stride=64, dyn_sel=3, dyn_mul=CSTR)
    v = MDesc(base=0, n=64, m=320, stride=64)
    return Rec("DMA", op, wait=0xFFFE,
               desc=dict(A=v, O=h) if op == "STORE" else dict(A=h, O=v), tag="swap.h")


def memory():
    h = Hbm()
    for q in range(4):
        h.add((q << 35) | COLB, np.zeros(13 * CSTR, np.uint8))
    return h


def execute(rec, die):
    m = Machine([die])
    m.cur = rec
    (u_dma_store if rec.op == "STORE" else u_dma_load)(m, rec, 0)


def check_stripe4(hbm, values, slot):
    # the legacy STRIPE4 rule: logical row o on stack o mod 4 at slot row o
    for o in range(320):
        address = ((o % 4) << 35) + COLB + slot * CSTR + o * 64
        assert np.array_equal(hbm.view(address, 256).view(np.uint32), values[o].view(np.uint32))


def check_oracle(hbm, values, slot):
    # The native layout rule written out by hand (not mtp_swap.native_row, not the linear sub-descriptors under
    # test): logical row 80q + j on stack q, 256 B rows packed from stack-local COLB + slot * CSTR + 64q.
    for q in range(4):
        for j in range(80):
            address = (q << 35) + COLB + slot * CSTR + 64 * q + 256 * j
            assert np.array_equal(hbm.view(address, 256).view(np.uint32), values[80 * q + j].view(np.uint32))


def test_native_image_is_the_stripe4_image_with_rows_permuted_by_owner():
    from hgi_b2.mtp_swap import native_row, group_param, GRP, GLAST
    assert sorted(native_row(o) for o in range(320)) == sorted((r % 4, r) for r in range(320))   # same footprint
    assert [native_row(o) for o in (0, 1, 79, 80, 319)] == [(0, 0), (0, 4), (0, 316), (1, 1), (3, 319)]
    assert [group_param(k, 4) for k in range(4)] == [GRP, GRP, GRP, GRP | GLAST] and group_param(0, 1) == 3
    values = np.arange(20480, dtype=np.float32).reshape(320, 64) + 7
    a, b = memory(), memory()
    d = Die(0, a)
    d.vm[:20480] = values.reshape(-1).view(np.uint32)
    execute(legacy("STORE"), d)
    for e in lower_h(legacy("STORE"), {q: MDesc(base=128, n=64, m=80, stride=64) for q in range(4)}).records:
        d = Die(e.cluster, b)
        d.vm[128:5248] = values[80 * e.cluster:80 * e.cluster + 80].reshape(-1).view(np.uint32)
        execute(e.record, d)
    check_stripe4(a, values, 0)
    check_oracle(b, values, 0)
    with pytest.raises(AssertionError):
        check_stripe4(b, values, 0)             # one image is not readable by the other rule
    perm = np.array([native_row(o)[1] for o in range(320)])
    check_stripe4(b, values[np.argsort(perm)], 0)    # slot row r holds logical row perm^-1(r)


@pytest.mark.parametrize("mirror", [False, True])
def test_production_native_swap_all_column_slots(mirror):
    hbm = memory()
    allocations = {q: MDesc(base=65536 + q * 64 if mirror else 128 + q * 64,
                            n=64, m=80, stride=256 if mirror else 64) for q in range(4)}
    stores, loads = lower_h(legacy("STORE"), allocations), lower_h(legacy("LOAD"), allocations)
    assert len(stores.export()["records"]) == 4
    assert stores.export()["dispatch"] == "parallel"
    for slot in range(13):
        values = np.arange(20480, dtype=np.float32).reshape(320, 64) + slot * 32768
        for e in stores.records:
            d = Die(e.cluster, hbm)
            d.vm.fill(0x7F812345)  # poison every word outside the supplied allocation
            d.dyn[3] = slot
            a = e.record.desc["A"]
            for j, row in enumerate(values[80 * e.cluster:80 * e.cluster + 80]):
                d.vm[a.base + j * a.stride:a.base + j * a.stride + 64] = row.view(np.uint32)
            execute(e.record, d)
        check_oracle(hbm, values, slot)
        for e in loads.records:
            d = Die(e.cluster, hbm)
            d.dyn[3] = slot
            execute(e.record, d)
            a = e.record.desc["O"]
            for j, want in enumerate(values[80 * e.cluster:80 * e.cluster + 80]):
                assert np.array_equal(d.vm[a.base + j * a.stride:a.base + j * a.stride + 64], want.view(np.uint32))
    # PRE is one whole sector, addressed exactly as legacy on every slot.
    pre = Rec("DMA", "STORE", desc=dict(
        A=MDesc(base=1024, n=8),
        O=MDesc(space="HBM", base=COLB + 81920, n=8, dyn_sel=3, dyn_mul=CSTR)))
    emitted = lower_pre(pre, 0, MDesc(base=32768, n=8)).records[0]
    for slot in range(13):
        d = Die(0, hbm)
        d.dyn[3] = slot
        words = np.arange(8, dtype=np.float32) + slot * 8
        d.vm[32768:32776] = words.view(np.uint32)
        execute(emitted.record, d)
        assert np.array_equal(hbm.view(COLB + slot * CSTR + 81920, 32).view(np.uint32), words.view(np.uint32))
        load = replace(pre, op="LOAD", desc=dict(A=pre.desc["O"], O=pre.desc["A"]))
        native_load = lower_pre(load, 0, MDesc(base=32768, n=8)).records[0]
        d.vm[32768:32776] = 0
        execute(native_load.record, d)
        assert np.array_equal(d.vm[32768:32776], words.view(np.uint32))


def test_legacy_stripe_store_accepted_and_bad_operands_refused():
    h = memory()
    d = Die(0, h)
    values = np.arange(20480, dtype=np.float32).reshape(320, 64)
    d.vm[:20480] = values.reshape(-1).view(np.uint32)
    rec = legacy("STORE")
    execute(rec, d)
    check_stripe4(h, values, 0)
    m = Machine([d])
    m.cur = Rec("SM", "MATVEC", desc=dict(B=rec.desc["O"]))
    with pytest.raises(Fault):
        m.eff(rec.desc["O"], d, 0)
    m.cur = rec
    with pytest.raises(Fault):
        m.eff(replace(rec.desc["O"], base=(2 << 37) | COLB), d, 0)


@pytest.mark.parametrize("mutant", ["stack", "row", "early_fence"])
def test_native_swap_mutants_detected(mutant):
    hbm = memory()
    values = np.arange(20480, dtype=np.float32).reshape(320, 64) + 1
    group = lower_h(legacy("STORE"), {q: MDesc(base=128, n=64, m=80, stride=64) for q in range(4)})
    for e in group.records:
        if mutant == "early_fence" and e.cluster == 3:
            continue  # fence exposes slot while stack three still has posted sectors
        r = e.record
        if e.cluster == 1 and mutant in ("stack", "row"):
            o = r.desc["O"]
            base = (o.base & ((1 << 35) - 1)) if mutant == "stack" else o.base + 32
            r = replace(r, desc={**r.desc, "O": replace(o, base=base)})
        d = Die(e.cluster, hbm)
        d.vm[128:5248] = values[80 * e.cluster:80 * e.cluster + 80].reshape(-1).view(np.uint32)
        execute(r, d)
    with pytest.raises(AssertionError):
        check_oracle(hbm, values, 0)


def test_refuses_missing_cluster_or_nonlocal_allocation():
    vm = {q: MDesc(base=128, n=64, m=80, stride=64) for q in range(4)}
    with pytest.raises(ValueError):
        lower_h(legacy("STORE"), {q: v for q, v in vm.items() if q != 3})
    with pytest.raises(ValueError):
        lower_h(legacy("STORE"), {**vm, 3: replace(vm[3], base=98304)})
    with pytest.raises(ValueError):
        lower_h(legacy("STORE"), {**vm, 0: replace(vm[0], indexed=1)})
    with pytest.raises(ValueError):
        lower_h(legacy("STORE"), {**vm, 0: replace(vm[0], base=65472)})


def test_kernel_entry_retains_fence_and_end_after_parallel_group():
    from types import SimpleNamespace
    from hgi_sim.ds_mtp_kernels import Kernels
    pre = Rec("DMA", "STORE", desc=dict(A=MDesc(base=32768, n=8),
              O=MDesc(space="HBM", base=COLB + 81920, n=8, dyn_sel=3, dyn_mul=CSTR)))
    fence, end = Rec("CTL", "FENCE"), Rec("CTL", "END")
    holder = SimpleNamespace(swap=lambda into: [legacy("STORE"), pre, fence, end])
    result = Kernels.swap_b2(holder, False,
                            {q: MDesc(base=128, n=64, m=80, stride=64) for q in range(4)},
                            MDesc(base=32768, n=8))
    assert len(result[0].records) == 4 and len(result[1].records) == 1
    assert result[2:] == [fence, end]
