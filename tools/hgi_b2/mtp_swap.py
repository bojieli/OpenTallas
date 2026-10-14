"""Native B2 MTP swap dispatch groups, using allocator-supplied local descriptors.

The h group dispatches four linear DMA records together, one per own-stack
engine. Physical VM offsets belong to the live-record allocator; this pass
does not infer or repack them from logical word addresses.

NATIVE LAYOUT (el1013-ds-mtp-lead item 4).  The B2 allocator keeps h where the
layer's split records compute on it: cluster q holds the CONTIGUOUS quarter,
logical rows 80q .. 80q + 79 (HC column q; committed DS L14 placement: LOCAL q,
physical 0, stride 64).  The column slot keeps the STRIPE4 footprint: stack q
holds 80 packed 256 B rows at stack-local COLB + slot x CSTR + 64q + 256j (the
slot's rows q + 4j).  The native swap places h on that footprint by OWNER:

    slot row q + 4j (stack q)  <-  logical h row 80q + j      (native_row)

so every cluster streams its own slice to its own stack and no h word crosses
the ring.  The legacy STRIPE4 record put logical row o on stack o mod 4, which
needs rows q + 4j resident in slice q: no placement the allocator produces for
a layer program has that, and a MIRROR h costs 20,480 of the 32,768 mirror
words.  The HBM image of a slot is therefore the legacy image with its rows
permuted (same sectors, same stacks); a slot written by one rule is NOT
readable by the other, so a program uses one rule for every swap (the group
records carry GRP in the header parameter, the legacy record carries the
STRIPE4 code: a reader cannot mistake one for the other).
"""
from __future__ import annotations

from dataclasses import dataclass, replace, asdict
from hgi_sim.records import MDesc, Rec

ROWS, QROWS, ROW_W = 320, 80, 64        # h: 320 rows of 64 words; 80 rows a cluster
GRP, GLAST = 1, 2                       # DMA header parameter bits: member of a native dispatch group / its last member


def native_row(o: int) -> tuple[int, int]:
    """(stack, slot row) of logical h row o in the native layout: owner q = o // 80, slot row q + 4 (o mod 80)."""
    if not 0 <= o < ROWS:
        raise ValueError("h row out of range")
    q, j = divmod(o, QROWS)
    return q, q + 4 * j


def group_param(k: int, n: int) -> int:
    """header parameter of member k of an n-member group (rtl ot_hgi_b2_swap_rec: param[0] GRP, param[1] GLAST)"""
    return GRP | (GLAST if k == n - 1 else 0)


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


def lower_h(record: Rec, vm_by_cluster: dict[int, MDesc], local: bool = True) -> DispatchGroup:
    """Lower the production 320x64 h swap record to the native four-cluster group.

    vm_by_cluster[q] names cluster q's quarter of h (logical rows 80q .. 80q + 79,
    in order) in that cluster's current physical allocation (compact LOCAL or
    strided MIRROR); it lands on stack q's 80 slot rows (native_row).
    local=False: the descriptors are LOGICAL VM addresses (the HGI simulator's one
    VM; the B2 pass resolves them through the placement like any record's).
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
        if local:
            _local(v, 64, 80)
        elif (v.space != "VM" or (v.n, v.m) != (64, 80) or v.stride < 64 or v.istride not in (0, 1) or
              any((v.indexed, v.ibcast, v.n_sel, v.dyn_sel, v.dyn_mul, v.lstride, v.l1stride))):
            raise ValueError("swap requires a plain 80 x 64-word VM quarter")
        if v.fmt != h.fmt:
            raise ValueError("native swap preserves the raw payload format")
        desc = dict(record.desc)
        desc[vb] = v
        desc[hb] = replace(h, base=(q << 35) | (loc + q * 64),
                           m=80, stride=256)
        out.append(ClusterRecord(q, replace(record, desc=desc, param=group_param(q, 4),
                                             tag=record.tag + f".b2.q{q}")))
    return DispatchGroup(tuple(out))


def logical_h(record: Rec) -> DispatchGroup:
    """The native group over the LOGICAL h of the legacy record: cluster q's quarter is rows 80q .. 80q + 79."""
    v = record.desc["A" if record.op == "STORE" else "O"]
    if (v.space != "VM" or (v.n, v.m, v.stride) != (64, 320, 64) or
            any((v.indexed, v.ibcast, v.n_sel, v.dyn_sel, v.dyn_mul, v.lstride, v.l1stride))):
        raise ValueError("expected the production 320 x 64-word VM h")
    return lower_h(record, {q: replace(v, base=v.base + q * QROWS * ROW_W, m=QROWS) for q in range(4)}, local=False)


def lower_pre(record: Rec, cluster: int, vm: MDesc | None = None) -> DispatchGroup:
    """Keep PRE as one whole-sector transfer on its supplied home cluster (a singleton group: GRP | GLAST).
    vm None: keep the record's own LOGICAL VM descriptor (the HGI simulator's one VM)."""
    if cluster not in range(4) or (record.unit, record.op) not in (
            ("DMA", "LOAD"), ("DMA", "STORE")):
        raise ValueError("invalid PRE home or operation")
    hb, vb = ("A", "O") if record.op == "LOAD" else ("O", "A")
    h = record.desc[hb]
    if vm is None:
        vm = record.desc[vb]
        if (vm.space != "VM" or (vm.n, vm.m) != (8, 1) or vm.base % 8 or
                any((vm.indexed, vm.ibcast, vm.n_sel, vm.dyn_sel, vm.dyn_mul, vm.lstride, vm.l1stride))):
            raise ValueError("expected the plain eight-word VM PRE sector")
    else:
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
    return DispatchGroup((ClusterRecord(cluster, replace(record, desc=desc, param=group_param(0, 1))),))


def group_cluster(rec: Rec):
    """The cluster of a native group member = its HBM-side base bits [36:35] (the encoding carries no cluster field);
    None for a record that is not a group member."""
    if rec.unit != "DMA" or rec.op not in ("LOAD", "STORE") or not rec.param & GRP:
        return None
    h = rec.desc["A" if rec.op == "LOAD" else "O"]
    if h.space != "HBM" or h.base >> 37:
        raise ValueError("a native group member has one linear HBM side")
    return (h.base >> 35) & 3


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
    address the allocator gave its quarter of the 320 x 64-word logical h at h_base (rows 80q .. 80q + 79, the
    native layout: where the layer's split records hold h), and it exists only if those 80 rows are resident in q's
    slice (LOCAL q or MIRROR) and affine there (one base, one row stride).
    PRE (8 words at pre_base, one whole sector) must be resident in cluster 0's slice.  Anything else is refused
    (ValueError): the native lowering is then not legal for that record lifetime and the legacy swap stays.
    """
    out, (cls, phys, key) = h_allocations_from_placement(placement, h_base, rank, fmt, _tables_out=True)
    pre = MDesc(space="VM", fmt=fmt, base=_resident(cls, phys, key, pre_base, 8, 0, "PRE"), n=8)
    _local(pre, 8, 1)
    return out, pre


def h_allocations_from_placement(placement, h_base: int, rank: int = 0, fmt: str = "FP32", _tables_out=False):
    """{cluster: MDesc} of h alone (allocations_from_placement's first value): a layer program's placement holds h
    without the swap's PRE sector."""
    import numpy as np
    cls, phys = _tables(placement, rank)
    placed = cls >= 0
    key = np.sort(cls[placed] * (1 << 32) + phys[placed])
    out = {}
    for q in range(_NQ):
        rows = [_resident(cls, phys, key, h_base + 64 * o, 64, q, f"h row {o}")
                for o in range(q * QROWS, (q + 1) * QROWS)]
        steps = set(np.diff(rows).tolist())
        if len(steps) != 1:
            raise ValueError(f"h rows of cluster {q} are not affine in physical space (row steps {sorted(steps)[:4]})")
        d = MDesc(space="VM", fmt=fmt, base=rows[0], n=64, m=80, stride=steps.pop())
        _local(d, 64, 80)
        out[q] = d
    return (out, (cls, phys, key)) if _tables_out else out
