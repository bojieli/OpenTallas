"""Native B2 MTP swap dispatch groups, using allocator-supplied local descriptors.

The h group dispatches four linear DMA records together, one per own-stack
engine. Physical VM offsets belong to the live-record allocator; this pass
does not infer or repack them from logical word addresses.
"""
from __future__ import annotations

from dataclasses import dataclass, replace, asdict
from hgi_sim.records import MDesc, Rec


@dataclass(frozen=True)
class ClusterRecord:
    cluster: int
    record: Rec


@dataclass(frozen=True)
class DispatchGroup:
    records: tuple[ClusterRecord, ...]

    def export(self):
        return {"dispatch": "parallel", "records": [
            {"cluster": e.cluster, "record": asdict(e.record),
             "encoded": e.record.encode().hex()} for e in self.records]}


def _local(d: MDesc, n: int, m: int):
    # Addresses here are AFTER cmdproc slice/range decode, including the
    # local mirror at [65536,98304). The cluster travels beside the record.
    if (d.space != "VM" or d.fmt not in ("FP32", "U32") or
            (d.n, d.m) != (n, m) or d.istride not in (0, 1) or
            any((d.indexed, d.ibcast, d.n_sel, d.dyn_sel, d.dyn_mul,
                 d.lstride, d.l1stride)) or d.base % 64 or
            (m > 1 and (d.stride < n or d.stride % 64)) or
            d.base < 0 or d.base + (m - 1) * d.stride + n > 98304):
        raise ValueError("swap requires an aligned, resolved local-slice VM descriptor")


def lower_h(record: Rec, vm_by_cluster: dict[int, MDesc]) -> DispatchGroup:
    """Lower the production 320x64 STRIPE4 h record for one live allocation.

    vm_by_cluster[q] names rows q,q+4,...,q+316 in order in that
    cluster's current physical allocation (compact LOCAL or strided MIRROR).
    """
    if (record.unit, record.op) not in (("DMA", "LOAD"), ("DMA", "STORE")):
        raise ValueError("expected DMA LOAD/STORE")
    hb, vb = ("A", "O") if record.op == "LOAD" else ("O", "A")
    h = record.desc[hb]
    if (h.space != "HBM" or h.fmt not in ("FP32", "U32") or
            h.base >> 37 != 1 or (h.base >> 35) & 3 or
            (h.n, h.m, h.stride) != (64, 320, 64) or
            h.base % 32 or h.istride not in (0, 1) or
            any((h.indexed, h.ibcast, h.n_sel, h.lstride, h.l1stride)) or
            h.dyn_sel != 3 or h.dyn_mul != 131072):
        raise ValueError("expected production TOKEN-indexed STRIPE4 h swap")
    if set(vm_by_cluster) != set(range(4)):
        raise ValueError("all four own-stack VM allocations are required")
    out = []
    loc = h.base & ((1 << 35) - 1)
    if loc + 12 * h.dyn_mul + 319 * 64 + 256 > 1 << 35:
        raise ValueError("column slots cross the stack-local address boundary")
    for q in range(4):
        v = vm_by_cluster[q]
        _local(v, 64, 80)
        if v.fmt != h.fmt:
            raise ValueError("native swap preserves the raw payload format")
        desc = dict(record.desc)
        desc[vb] = v
        desc[hb] = replace(h, base=(q << 35) | (loc + q * 64),
                           m=80, stride=256)
        out.append(ClusterRecord(q, replace(record, desc=desc,
                                             tag=record.tag + f".b2.q{q}")))
    return DispatchGroup(tuple(out))


def lower_pre(record: Rec, cluster: int, vm: MDesc) -> DispatchGroup:
    """Keep PRE as one whole-sector transfer on its supplied home cluster."""
    if cluster not in range(4) or (record.unit, record.op) not in (
            ("DMA", "LOAD"), ("DMA", "STORE")):
        raise ValueError("invalid PRE home or operation")
    hb, vb = ("A", "O") if record.op == "LOAD" else ("O", "A")
    h = record.desc[hb]
    _local(vm, 8, 1)
    if (h.space != "HBM" or h.base >> 35 or h.base % 32 or
            (h.n, h.m) != (8, 1) or h.fmt != vm.fmt or
            h.dyn_sel != 3 or h.dyn_mul != 131072 or
            any((h.indexed, h.ibcast, h.n_sel, h.lstride, h.l1stride)) or
            h.istride not in (0, 1)):
        raise ValueError("expected production linear eight-word PRE transfer")
    desc = dict(record.desc)
    desc[vb] = vm
    # PRE keeps its legacy HBM home (stack zero); a nonzero source home
    # would need a measured ring move, so refuse it rather than hide traffic.
    if cluster != 0:
        raise ValueError("PRE native DMA must be local to legacy HBM stack zero")
    return DispatchGroup((ClusterRecord(cluster, replace(record, desc=desc)),))
