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
    end = d.base + (m - 1) * d.stride + n
    if (d.space != "VM" or d.fmt not in ("FP32", "U32") or
            (d.n, d.m) != (n, m) or d.istride not in (0, 1) or
            any((d.indexed, d.ibcast, d.n_sel, d.dyn_sel, d.dyn_mul,
                 d.lstride, d.l1stride)) or d.base % 64 or
            (m > 1 and (d.stride < n or d.stride % 64)) or
            d.base < 0 or end > 98304 or d.base < 65536 < end):
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


# ---------------------------------------------------------------------------- record-live allocator -> descriptors
_NQ, _MIR, _LOCAL_W = 4, 4, 65536     # hgi_b2.b2 NQ / MIR / LOCAL_W (asserted against b2 in the caller tests)


def _tables(placement, rank):
    """(cls, phys) logical-word tables of ONE die from the allocator's own output: a b2.PlacementSet (its rank's
    Placement), a b2.Placement, or an exported placement table (b2.Placement.table(): the segment list)."""
    import numpy as np
    if isinstance(placement, dict):
        segs = placement.get("segments")
        if placement.get("schema") != "opentallas.hgi_b2.placement.v1" or segs is None:
            raise ValueError("not an hgi_b2 placement table")
        if (placement["nq"], placement["local_w"], placement["mirror_phys_base"]) != (_NQ, _LOCAL_W, _LOCAL_W):
            raise ValueError("placement table of another slice geometry")
        if rank != 0:
            raise ValueError("an exported placement table is rank 0's die only")
        cls = np.full(placement["vm_words"], -1, np.int64)
        phys = np.full(placement["vm_words"], -1, np.int64)
        for lo, n, c, ph, *_ in segs:
            cls[lo:lo + n] = c
            phys[lo:lo + n] = ph + np.arange(n)
        return cls, phys
    if hasattr(placement, "by_rank"):
        if rank not in placement.by_rank:
            raise ValueError(f"the allocator placed no die of rank {rank}")
        placement = placement.by_rank[rank]
    elif rank != 0:
        raise ValueError("one Placement is one die: pass the PlacementSet for another rank")
    return np.asarray(placement.cls, np.int64), np.asarray(placement.phys, np.int64)


def _resident(cls, phys, key, lo, n, cluster, what):
    """Physical base of logical words [lo, lo + n) in `cluster`'s slice, exactly as the allocator placed them: every
    word LOCAL to that cluster or MIRROR, one region, contiguous, and sharing its physical words with no other
    logical word (an aliased word's owner depends on the record clock, which a placement table does not carry)."""
    import numpy as np
    if lo < 0 or lo + n > cls.size:
        raise ValueError(f"{what}: logical words outside the VM")
    c, p = cls[lo:lo + n], phys[lo:lo + n]
    if c[0] not in (cluster, _MIR) or np.any(c != c[0]):
        raise ValueError(f"{what}: not resident in cluster {cluster}'s slice (classes {sorted(set(c.tolist()))}; "
                         f"need LOCAL {cluster} or MIRROR)")
    if np.any(p != p[0] + np.arange(n)):
        raise ValueError(f"{what}: not contiguous in physical space")
    if (p[0] >= _LOCAL_W) != (c[0] == _MIR):
        raise ValueError(f"{what}: physical offset {int(p[0])} outside its class's region")
    k = c * (1 << 32) + p
    if np.searchsorted(key, k, "right").sum() - np.searchsorted(key, k, "left").sum() != n:
        raise ValueError(f"{what}: physical words aliased with another logical word (lifetime-dependent)")
    return int(p[0])


def allocations_from_placement(placement, h_base: int, pre_base: int, rank: int = 0, fmt: str = "FP32"):
    """({cluster: MDesc}, PRE MDesc) for swap_b2, READ from the record-liveness allocator's placement of this die.

    Nothing is computed from a logical address and nothing is repacked: cluster q's descriptor is the physical
    address the allocator gave rows q, q + 4, ..., q + 316 of the 320 x 64-word logical h at h_base, and it exists
    only if those 80 rows are resident in q's slice (LOCAL q or MIRROR) and affine there (one base, one row stride).
    PRE (8 words at pre_base, one whole sector) must be resident in cluster 0's slice.  Anything else is refused
    (ValueError): the native lowering is then not legal for that record lifetime and the legacy swap stays.
    """
    import numpy as np
    cls, phys = _tables(placement, rank)
    placed = cls >= 0
    key = np.sort(cls[placed] * (1 << 32) + phys[placed])
    out = {}
    for q in range(_NQ):
        rows = [_resident(cls, phys, key, h_base + 64 * o, 64, q, f"h row {o}") for o in range(q, 320, 4)]
        steps = set(np.diff(rows).tolist())
        if len(steps) != 1:
            raise ValueError(f"h rows of cluster {q} are not affine in physical space (row steps {sorted(steps)[:4]})")
        d = MDesc(space="VM", fmt=fmt, base=rows[0], n=64, m=80, stride=steps.pop())
        _local(d, 64, 80)
        out[q] = d
    pre = MDesc(space="VM", fmt=fmt, base=_resident(cls, phys, key, pre_base, 8, 0, "PRE"), n=8)
    _local(pre, 8, 1)
    return out, pre
