#!/usr/bin/env python3
"""TOK-FUNC2-HBM-CX (10-21): CONNECTED component records inside the DS SW-slice layer emission (layer_images --cx).

Before: COLL.ALL_GATHER / GROUP_REDUCE_MCAST and HC.HC_MIX ran as relocated fixture probes (merge_layer_replay: one
finite SU epoch, then disjoint CP epochs, every component input/output on private sectors filled from fixtures).
Now each component is a record of the SAME layer compilation:

  * VM placement is the layer's own (layer_images.Placement, extended here): a component's output tensor is reserved
    as the contiguous physical run its engine writes (gq landing run dst + s*stride + j, HC store run osec..+2), and
    that reservation becomes the tensor's placement from its producer record onward, so
      - an emitted SU producer writes its result straight into the component's input sectors (no preload of the
        produced words: they are poisoned to 0 in the cycle-0 image so a pass proves the producer's write), and
      - the consumer SU record reads the component's output sectors (marked written: no preload).
    Words NOT produced inside the slice keep explicit provenance: other dies (cross-die all-gather leg, off-die),
    other quadrants (ring far ends at the slice boundary, as before), or a not-yet-emitted on-die producer
    (SM.MATVEC -> sibling lane TOK-FUNC2-HBM-SM; FUSED; HC projection) -- those enter as cycle-0 images and are
    listed per record (field cx.injected).
  * value versioning: when a record's ds_native input words differ from the last value the layer placed in a logical
    sector (an un-emitted producer rewrote it), the sector gets a FRESH physical placement for the new version, so
    two cycle-0 images never name one physical sector with different data (the default emission does: e.g. L0
    attn.res_copy / ffn.res_copy both image the residual sectors with different values).
  * one static timeline: SU programmes are split at every component (barrier); the SU epochs (finite owner-0 calendar
    of every bank, native_su_calendar.reserve_component form) and the component epochs (each component installs its
    own calendar_SW / gq / qhub / root programme through host_cp_ingress and launches) alternate on fixed edges.  No
    ready/credit anywhere: every edge is compiled.
  * parts (TB event depth NEV): a part is the union of the producer CONES (transitive VM writers) of the nodes it
    checks; cone members replay their drives and images but not their checks.  Every part therefore runs the real
    producer chain of every value it checks -- never an expected-value carry.

Component lowerings reused unchanged: coll_images.gather_record (gq + ring far ends + landing), hc_layer_lower_1021
.lower_mix_post (Codex: real hc_eng root programme/table from the SHA-pinned checkpoint, qhub gather/store, no result
drive).  Grade: RTL-functional (source assembly); execution_qualified False until the replays run.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from hbm_layer_vehicle import coll_images as CI
from hbm_layer_vehicle import hc_images as HI

NSEC = 1 << 13
COMP_GAP = 128            # stream edges after a component's last event before the next CP epoch (calendar run-out)
EPOCH_TAIL = 64           # SU epoch calendar covers the epoch's last SU event + this
CP_GUARD = 16
SU_START_GUARD = 33       # (4*start)//3 > launch + 32 (native_su_calendar.reserve_component)


def stream_of(s):
    return (4 * s + 2) // 3


def serial_of(t):
    return int(math.ceil(3 * t / 4))


def f2u(v):
    return int(np.float32(v).view(np.uint32))


class VPlacement:
    """mixin state for layer_images.Placement: liveness-reused SU output sectors, component runs, value versions.

    Two kinds of physical sectors: IMAGED (a cycle-0 image is read: SU operand images, COLL own-slice images, HC A) must
    be FRESH -- never written earlier in the replay, or the image would be clobbered before its reader; WRITE-FIRST
    (SU ':O' placements, COLL landing runs, HC store runs) may reuse a sector whose last reader (ds_native order) has
    passed.  The SU allocator keeps its bottom-up rows; component runs are allocated top-down (fresh) or from freed
    runs (write-first only)."""

    def cx_init(s):
        s.top = NSEC            # lowest sector ever given to a top-down run
        s.pool = [[] for _ in range(8)]   # freed physical sectors per port (write-first reuse)
        s.runs_free = []        # freed (base, n) runs in the top region (write-first reuse)
        s.reserved = {}         # logical -> physical of ACTIVE component tensors
        s.versions, s.reused, s.freed = [], {}, 0
        s.cur_i = None
        s.last_read = {}

    def _fresh_run(s, n, port0):
        base = s.top - n
        base -= (base - port0) % 8
        lowest = max(((r << 3) | p) for p, r in enumerate(s.nxt))
        if base <= lowest:
            raise ValueError(f"component run of {n} sectors collides with the SU placement (top {s.top})")
        s.top = base
        return base

    def alloc_run(s, n, port0=0, reuse=False):
        if reuse:
            for k_, (b, m) in enumerate(sorted(s.runs_free)):
                st = b + ((port0 - b) % 8)
                if st + n <= b + m:
                    s.runs_free.remove((b, m))
                    if st > b:
                        s.runs_free.append((b, st - b))
                    if st + n < b + m:
                        s.runs_free.append((st + n, b + m - st - n))
                    return (s.q << 13) | st
        return (s.q << 13) | s._fresh_run(n, port0)

    def free_run(s, base, n):
        s.runs_free.append((base & 0x1fff, n))
        s.freed += n

    def chapter_reset(s):
        """VM chapter boundary: the whole quarter slice starts empty again (no value carried in VM across it)."""
        s.map, s.nxt, s.written = {}, [0] * 8, set()
        s.top, s.pool, s.runs_free, s.reserved = NSEC, [[] for _ in range(8)], [], {}

    def free_logical(s, ls):
        ps = s.map.pop(ls)
        s.written.discard(ls)
        if ls not in s.reserved:
            s.pool[ps % 8].append(ps)
            s.freed += 1

    def new_version(s, ls, why):
        if ls in s.map and ls not in s.reserved:
            s.versions.append(dict(logical_sector=ls, old_physical=s.map[ls], at=why))
            s.free_logical(ls)


def make_placement(base_cls, q):
    class P(base_cls, VPlacement):
        def get(s, lsec, port, why):
            if lsec not in s.map and why.endswith(":O") and s.pool[port]:
                ps = s.pool[port].pop(0)
                s.map[lsec] = ps
                s.reused[ps] = s.cur_i
                return ps
            fresh = lsec not in s.map
            ps = base_cls.get(s, lsec, port, why)
            if fresh and (ps & 0x1fff) >= s.top:
                raise AssertionError(f"quarter VM slice full (SU placement reached the component runs: sector {ps & 0x1fff} top {s.top} why {why})")
            return ps
    p = P(q)
    p.cx_init()
    return p


def desc_vm_range(d):
    """[lo, hi) VM word range of a fixture descriptor (VM space only)."""
    if d[5] != "VM":
        return None
    base, n, m, st, ist = (int(x) for x in d[:5])
    hi = base + max((i * st + j * ist for i in range(m) for j in (0, n - 1)), default=0) + 1
    return base, hi


class Cx:
    def __init__(s, fixtures, rank, priced, place, *, contract, l12, checkpoint, boundary, ops, skip=(), chapters=(), hc_source_profile=None, coll_transport=None):
        s.meta, s.z, s.frecs = CI.load_fixture_records(fixtures, rank)
        if hc_source_profile is not None and (rank != 0 or int(s.meta["layer"]) != 0):
            raise ValueError("explicit SAFE2 HC profile covers only rank0/layer0/k31")
        s.place, s.bnd, s.ops = place, boundary, ops
        s.vm_rt = CI.vm_rt_from_contract(contract)
        s.coll_transport = coll_transport  # TOKg 10-23: coll_transport.load() profile (None = GEN2 timing)
        s.tim = HI.timing_from_contract(contract, l12)
        s.hc_source_profile, s.profile_contract = hc_source_profile, contract
        s.checkpoint = checkpoint
        s.seen = {}                  # logical VM word -> last value bits the layer holds there
        s.emitted_k = set()          # fixture records executed in this layer emission (SU emitted + components)
        s.last_writer = {}           # logical sector -> (fixture k, executed?) of its last writer so far
        s.vk = {}                    # logical sector -> writer k its current placement holds
        s.fpos = 0
        s.su_written = set()         # VM words written by emitted SU records in this slice
        s.comps = {}                 # priced i -> plan dict
        s.act, s.live = {}, []       # activation priced i -> [component i]; active component tensors
        s.built = []                 # built components (timeline order)
        s.injected_log = []
        by_k = {x["k"]: x for x in s.frecs}
        pri_of_k = {x["k"]: int(x["priced"][0]["i"]) for x in s.frecs if x.get("priced")}
        pri_hc = HI.priced_hc(s.meta, s.frecs)
        for x in s.frecs:
            op = x["op"]
            if op in ("COLL.ALL_GATHER", "COLL.GROUP_REDUCE_MCAST") and x.get("priced") and "COLL" in ops:
                i = int(x["priced"][0]["i"])
                s.comps[i] = dict(i=i, kind="coll", op=op, x=x)
            elif op == "HC.HC_MIX_POST" and "HC" in ops:
                base_tag = x["tag"][:-len(" post")] if x["tag"].endswith(" post") else x["tag"]
                if base_tag in pri_hc:
                    i = pri_hc[base_tag]
                    s.comps[i] = dict(i=i, kind="hc", op="HC.HC_MIX", x=x)
            elif op == "IDX.TOPK" and x.get("priced") and "IDX" in ops:
                i = int(x["priced"][0]["i"])
                s.comps[i] = dict(i=i, kind="idx", op=op, x=x, trole="A")
        s.idx_params = s._idx_params(contract, l12)
        # producer chain of the component's tensor (fixture order, backwards from the component): the in-place writers
        # (e.g. moe_sum.0 -> .2 -> .4 -> .6) up to the first record that only READS that range (older version).  The
        # reservation becomes the tensor's placement at the chain's FIRST writer; the last writer is the producer.
        from hbm_layer_vehicle.layer_images import desc_addrs
        # liveness counts only readers that EXECUTE in the slice (SU records, planned components): SM / DMA / ATT /
        # FUSED / IDX consumers read the fixture state, never this replay's VM
        s.last_read = place.last_read
        comp_k = {c["x"]["k"] for c in s.comps.values()}
        for y in s.frecs:
            if not (y["op"].startswith("SU.") or y["k"] in comp_k):
                continue
            for n_, d in y["desc"].items():
                if n_ != "O" and d[5] == "VM":
                    for a_ in desc_addrs(d):
                        s.last_read[a_ >> 3] = max(s.last_read.get(a_ >> 3, -1), y["k"])
        for i, c in s.comps.items():
            x = c["x"]
            tr = c.get("trole", "O")
            orng = set(desc_addrs(x["desc"][tr])) if x["desc"][tr][5] == "VM" else set()
            prod, first = None, None
            for y in reversed([y for y in s.frecs if y["k"] < x["k"]]):
                o = y["desc"].get("O")
                w = set(desc_addrs(o)) & orng if (o and o[5] == "VM") else set()
                rd = any(set(desc_addrs(d)) & orng for n_, d in y["desc"].items() if n_ != "O" and d[5] == "VM")
                if w:
                    prod = prod or y
                    first = y
                elif rd:
                    break
            c["producer_k"] = None if prod is None else prod["k"]
            c["producer"] = None if prod is None else dict(k=prod["k"], op=prod["op"], tag=prod["tag"],
                                                           priced_i=pri_of_k.get(prod["k"]))
            act = pri_of_k.get(first["k"]) if (first is not None and c["kind"] in ("coll", "idx")) else None
            c["activation"] = act if act is not None and act <= i else i
            # in-slice neighbours: an SU producer of the tensor, or an SU reader of this version of it
            cons = []
            for y in [y for y in s.frecs if y["k"] > x["k"]]:
                o = y["desc"].get("O")
                rd = any(set(desc_addrs(d)) & orng for n_, d in y["desc"].items() if n_ != "O" and d[5] == "VM")
                if rd and y["op"].startswith("SU."):
                    cons.append(dict(k=y["k"], tag=y["tag"], priced_i=pri_of_k.get(y["k"])))
                if o and o[5] == "VM" and set(desc_addrs(o)) & orng:
                    break
            c["su_consumers"] = cons
            c["isolated"] = not cons and not (prod is not None and prod["op"].startswith("SU."))
            if c["kind"] == "idx":
                c["isolated"] = False                  # always the layer's own placement (A from its producers)
            if c["isolated"]:
                c["O"] = np.asarray(s.z[x["outputs"]["O"]["array"]], np.uint32)
                c["n"] = len(c["O"])
                c["ls0"] = int(x["desc"]["O"][0]) // 8
            else:
                s._reserve(c)
        for i in skip:                       # VM capacity: run standalone, the consumers image its output (listed)
            c = s.comps.get(i)
            if c is None:
                continue
            for lst in s.act.values():
                if i in lst:
                    lst.remove(i)
            c.update(isolated=True, forced_standalone=True, O=np.asarray(s.z[c["x"]["outputs"]["O"]["array"]], np.uint32))
            c["n"] = len(c["O"])
        s.skipped = sorted(skip)
        s.chapters = sorted(chapters)
        s.chapter = 0
        s.chapter_carried = []
        s.iso_parts = []

    # ------------------------------------------------------------------------------------------------ placement
    def _reserve(s, c):
        """plan only (allocation happens at activation, when the tensor's chain starts)."""
        x = c["x"]
        if c["kind"] == "idx":
            A, O = (np.asarray(s.z[x[io][r]["array"]], np.uint32) for io, r in (("inputs", "A"), ("outputs", "O")))
            dA, dO = x["desc"]["A"], x["desc"]["O"]
            if int(dA[0]) % 8 or int(dA[2]) != 1 or int(dO[2]) != 1 or int(dO[0]) % 8 + len(O) > 8:
                c["refused"] = "IDX.TOPK: only one aligned A row and a single-sector O are lowered"
                return
            c.update(A=A, O=O, n=len(A), lsA=int(dA[0]) // 8, lsO=int(dO[0]) // 8, ls0=int(dA[0]) // 8)
            s.act.setdefault(c["activation"], []).append(c["i"])
            return
        base = int(x["desc"]["O"][0])
        if base % 8:
            c["refused"] = f"O base {base} not sector aligned"
            return
        c["ls0"] = base // 8
        c["O"] = np.asarray(s.z[x["outputs"]["O"]["array"]], np.uint32)
        c["n"] = len(c["O"])
        if c["kind"] == "coll" and c["n"] % 32:
            c["refused"] = f"n={c['n']}: quadrant slice not whole sectors"
            return
        s.act.setdefault(c["activation"], []).append(c["i"])

    def _activate(s, c):
        pl, ls0 = s.place, c["ls0"]
        if c["kind"] == "idx":
            ns = -(-c["n"] // 8)
            asec = pl.alloc_run(ns, c["lsA"] % 8) & 0x1fff             # A: partly imaged (other quarters) -> fresh
            osec = pl.alloc_run(1, c["lsO"] % 8) & 0x1fff              # O: zero-imaged neighbour words -> fresh
            mapping = {c["lsA"] + j: (pl.q << 13) | (asec + j) for j in range(ns)}
            mapping[c["lsO"]] = (pl.q << 13) | osec
            c.update(a_sector=asec, o_sector=osec, port_mismatch=[], mapping=mapping,
                     out_map={c["lsO"]: mapping[c["lsO"]]}, runs=[(asec, ns, False), (osec, 1, False)])
        elif c["kind"] == "coll":
            n = c["n"]
            F = n // 32
            stride = -(-F // 8) * 8
            src = pl.alloc_run(F, ls0 % 8) & 0x1fff                       # own slice: imaged -> fresh
            dst = pl.alloc_run(4 * stride, ls0 % 8, reuse=True) & 0x1fff  # landing: write-first -> reuse
            mapping, mism = {}, []
            for m in range(n // 8):
                sg, j = divmod(m, F)
                ph = (pl.q << 13) | ((src + j) if sg == 0 else (dst + sg * stride + j))
                if ph % 8 == (ls0 + m) % 8:
                    mapping[ls0 + m] = ph
                else:
                    mism.append(ls0 + m)
            c.update(F=F, stride=stride, src=src, dst=dst, port_mismatch=mism, mapping=mapping,
                     runs=[(src, F, False), (dst, 4 * stride, True)])
        else:
            dst = pl.alloc_run(3, ls0 % 8, reuse=True) & 0x1fff
            asec = pl.alloc_run(3, 0) & 0x1fff
            mapping = {ls0 + j: (pl.q << 13) | (dst + j) for j in range(3)}
            c.update(dst=dst, a_sector=asec, port_mismatch=[], mapping=mapping,
                     runs=[(dst, 3, True), (asec, 3, False)])
        for ls, ph in mapping.items():
            if ls in pl.map:
                pl.free_logical(ls) if ls not in pl.reserved else pl.map.pop(ls)
            pl.written.discard(ls)
            pl.map[ls] = ph
            pl.reserved[ls] = ph
        c["active"] = True
        s.live.append(c)

    def _free_dead(s, k):
        """free every placement whose last ds_native reader precedes fixture position k (and finished components)."""
        pl = s.place
        for c in list(s.live):
            if c["x"]["k"] < k and c.get("lowered") and all(s.last_read.get(ls, -1) < k for ls in c["mapping"]):
                for ls in c["mapping"]:
                    if pl.map.get(ls) == pl.reserved.get(ls):
                        pl.map.pop(ls, None)
                        pl.written.discard(ls)
                    pl.reserved.pop(ls, None)
                for base, n, wf in c["runs"]:
                    if wf:
                        pl.free_run(base, n)
                    else:                                  # imaged run: dead sectors serve SU write-first reuse
                        for j in range(n):
                            pl.pool[(base + j) % 8].append((pl.q << 13) | (base + j))
                s.live.remove(c)
        for ls in [ls for ls in pl.map if ls not in pl.reserved and s.last_read.get(ls, -1) < k]:
            pl.free_logical(ls)

    def before_record(s, i, fr, placed=True):
        """record i starts: activate reservations; every input sector whose last writer (ds_native order) is a record
        NOT executed in this emission gets a fresh placement for that version (its image then holds the new data)."""
        k = fr["k"] if fr else (s.comps[i]["x"]["k"] if i in s.comps else None)
        s.place.cur_i = i
        if s.chapter < len(s.chapters) and i >= s.chapters[s.chapter]:
            s.chapter += 1
            s.chapter_carried.append(dict(at=i, live_logical_sectors=len(s.place.map)))
            s.place.chapter_reset()
            s.live = []
        if k is not None:
            s._free_dead(k)
        for ci in s.act.get(i, []):
            if ci in s.comps and not s.comps[ci].get("refused"):
                try:
                    s._activate(s.comps[ci])
                except ValueError as ex:
                    s.comps[ci]["refused"] = str(ex)
        if k is None:
            return
        while s.fpos < len(s.frecs) and s.frecs[s.fpos]["k"] < k:
            y = s.frecs[s.fpos]
            s.fpos += 1
            o = y["desc"].get("O")
            if not o or o[5] != "VM":
                continue
            from hbm_layer_vehicle.layer_images import desc_addrs
            for ls in {a_ >> 3 for a_ in desc_addrs(o)}:
                s.last_writer[ls] = (y["k"], y["k"] in s.emitted_k)
        if not fr or not placed:
            return
        for ls in sorted({a_ >> 3 for a_ in fr["vm_in"]}):
            lw = s.last_writer.get(ls)
            if lw is None or lw[1]:
                continue
            if ls in s.place.map and s.vk.get(ls, -1) < lw[0]:
                s.place.new_version(ls, f"record {i}: writer k{lw[0]} not executed in the slice")
            s.vk[ls] = lw[0]

    def after_su(s, i, su, fr):
        if su.get("status") != "emitted" or not fr:
            return
        s.emitted_k.add(fr["k"])
        words = set()
        for x in su.get("expect", []):
            words.update(int(w) for w, v in zip(x.get("words", []), x.get("value") or []) if v is not None)
        for addr, v in fr["vm_out"].items():
            s.seen[addr] = int(v)
        s.su_written |= words

    # ------------------------------------------------------------------------------------------------ lowering
    def _iso(s, c, ent, cap):
        """no in-slice producer or consumer (SM / FUSED / HC-projection neighbours, sibling lanes): nothing to connect;
        the component runs in a standalone part on its own VM allocation, inputs imaged from the fixture."""
        def build(base):
            if c["kind"] == "coll":
                g = CI.gather_record(c["O"], c["i"], R=2, t_start=40, dst_idx=base, vm_rt=s.vm_rt, transport=s.coll_transport)
                if g["status"] != "emitted":
                    raise ValueError(g.get("reasons"))
                return g["events"] + g["chk_vm"] + g["chk_misc"] + g["chk_ring"], 4 * g["stride"]
            from hbm_layer_vehicle import hc_layer_lower_1021 as HL
            x = c["x"]
            A = np.asarray(s.z[x["inputs"]["A"]["array"]], np.uint32)
            params, _ = HL.checkpoint_parameters(s.checkpoint, int(s.meta["layer"]), "attn" if "attn" in x["tag"] else "ffn")
            real = HL.lower_mix_post(A, c["O"], params, s.tim, a_sector=base, o_sector=base + 8,
                                     component_allocation=True, record=c["i"], boundary=s.bnd, source_profile=s.hc_source_profile, profile_contract=s.profile_contract)
            return real["events"], 16
        P = s.iso_parts[-1] if s.iso_parts else None
        evs = nsec = None
        if P is not None:
            try:
                evs, nsec = build(P["bump"])
            except (AssertionError, ValueError):
                evs = None
            if evs is not None and (P["n"] + sum(e["k"] != "M" for e in evs) > cap or P["bump"] + nsec > NSEC):
                evs = None
        if evs is None:
            P = dict(bump=0x40, n=0, comps=[])
            s.iso_parts.append(P)
            evs, nsec = build(P["bump"])
        P["comps"].append(dict(i=c["i"], events=evs, base=P["bump"]))
        P["n"] += sum(e["k"] != "M" for e in evs)
        P["bump"] += -(-nsec // 64) * 64
        c["lowered"] = True
        ent.update(status="emitted_standalone", reasons=[
            ("--cx-skip (quarter VM capacity with cycle-0 imaging): standalone part; its SU neighbours image the "
             "tensor (fixture) -- NOT connected" if c.get("forced_standalone") else
             "no in-slice producer or consumer of this tensor (neighbours: SM/FUSED/HC projection, other lanes): runs "
             "in a standalone part on its own VM allocation, inputs imaged from the fixture")],
            lowering=dict(supported=True, connected=False, standalone=True),
            cx=dict(ent["cx"], standalone_part=len(s.iso_parts) - 1, sector_base=P["comps"][-1]["base"]))
        return ent, None

    def lower(s, i, cap=11650):
        c = s.comps[i]
        ent = dict(cx=dict(kind=c["kind"], producer=c["producer"], activation=c["activation"],
                           su_consumers=c.get("su_consumers"), reserved_sectors=len(c.get("mapping", {}))))
        if c.get("isolated"):
            try:
                return s._iso(c, ent, cap)
            except (AssertionError, ValueError) as ex:
                ent.update(status="cx_refused", reasons=[f"standalone {c['kind']}: {ex}"])
                return ent, None
        if c.get("refused"):
            ent.update(status="cx_refused", reasons=[c["refused"]])
            return ent, None
        try:
            g = s._coll(c) if c["kind"] == "coll" else (s._hc(c) if c["kind"] == "hc" else s._idx(c))
        except (AssertionError, ValueError) as ex:
            ent.update(status="cx_refused", reasons=[f"{c['kind']}: {ex}"])
            return ent, None
        if g.get("status") not in (None, "emitted", "source_assembly_only"):
            ent.update(status="cx_refused", reasons=g.get("reasons", [])[:3])
            return ent, None
        x = c["x"]
        c["lowered"] = True
        s.emitted_k.add(x["k"])
        lo = int(x["desc"]["O"][0])
        for m, w in enumerate(c["O"]):
            s.seen[lo + m] = int(w)
        for ls in c.get("out_map", c["mapping"]):
            s.place.written.add(ls)
        ent.update(status="emitted_connected", reasons=[], lowering=dict(supported=True, connected=True),
                   cx=dict(ent["cx"], **g["cx"]))
        comp = dict(i=i, kind=c["kind"], op=c["op"], events=g["events"], reads=g["reads"], writes=g["writes"],
                    meta=g["cx"])
        s.built.append(comp)
        return ent, comp

    def _own_image(s, c, ls, words_fix):
        """cycle-0 image of one input sector: produced-in-slice words poisoned (0), the rest with provenance."""
        val, src = 0, []
        for b in range(8):
            addr = 8 * ls + b
            if addr in s.su_written:
                src.append("su")
                continue
            val |= int(words_fix[b]) << (32 * b)
            src.append("img")
        return val, src

    def _coll(s, c):
        x, O = c["x"], c["O"]
        g = CI.gather_record(O, c["i"], R=2, t_start=40, dst_idx=c["dst"], vm_rt=s.vm_rt, src_idx=c["src"], transport=s.coll_transport)
        if g["status"] != "emitted":
            return g
        F, ls0 = c["F"], c["ls0"]
        evs, reads, writes, prov = [], set(), set(), dict(su_words=0, offdie_words=0, unemitted_words=0)
        from hbm_layer_vehicle.layer_images import desc_addrs
        pw = set()
        if c["producer"] is not None:
            pr = next(y for y in s.frecs if y["k"] == c["producer_k"])
            pw = set(desc_addrs(pr["desc"]["O"]))
        for e in g["events"]:
            if e["k"] == "M":
                ph = int(e["sector"]) & 0x1fff
                j = ph - c["src"]                      # own slice (segment 0): logical ls0 + j
                ls = ls0 + j
                val, src = s._own_image(c, ls, O[8 * j: 8 * j + 8])
                reads.add(ls)
                for b, t in enumerate(src):
                    addr = 8 * ls + b
                    if t == "su":
                        prov["su_words"] += 1
                    elif addr in pw:
                        prov["unemitted_words"] += 1
                    else:
                        prov["offdie_words"] += 1
                if all(t == "su" for t in src):
                    continue                           # wholly produced in the slice: no image at all
                e = dict(e, val=f"{val:064x}", src="image:cx_own_slice(" + "".join(
                    "P" if t == "su" else ("U" if 8 * ls + b in pw else "X")
                    for b, t in enumerate(src)) + ")")
            evs.append(e)
        writes = set(c["mapping"])
        evs += g["chk_vm"] + g["chk_misc"] + g["chk_ring"]
        return dict(events=evs, reads=reads, writes=writes,
                    cx=dict(F=F, stride=c["stride"], dst_sector=c["dst"], src_sector=c["src"], n_words=c["n"],
                            own_slice_word_sources=prov,
                            own_slice_legend="P = produced in-slice by the emitted SU producer (image word poisoned 0); "
                                             "U = un-emitted on-die producer (fixture image); X = other dies "
                                             "(cross-die all-gather leg, off-die, fixture image)",
                            consumer_port_mismatch_sectors=len(c["port_mismatch"]),
                            consumer_port_mismatch_note=("gq landing run dst+s*stride+j vs SU port rule lsec%8 with "
                                                         "F%8!=0: those sectors need a re-placement copy (open); the "
                                                         "consumer images them") if c["port_mismatch"] else None,
                            launch=g["launch_cyc"], check=g["check_cyc"], far_end_flits=g["far_end_flits"],
                            **({} if c['op']!='COLL.GROUP_REDUCE_MCAST' else dict(
                                global_reduction_qualified=False, on_die_transport_only=True,
                                tkm_endpoint_programme_qualified=False,
                                tkm_endpoint_obligation='source-only tkm_endpoint_1021.endpoint_plan@ca8bc89afd537729fc1f722306efa9cf8142c05b; '
                                    'real issuer-to-endpoint age/own+peer producers/qslots/writer/160-clock schedule unbound; '
                                    'PRE1 SETTLE136 candidate not adopted; current SETTLE104 source retained'))))

    def _idx_params(s, contract, l12):
        """hb_idx__ctl selected engine timing (contract) + l12 request pads: the TOPK engine runs with
        RT_EXTRA = 1 + VM_RT and ACK = 13 + CR_RT (ot_hbm_idx_rootctl_static_am.sv:112).  The proven pin schedule
        (hbm_idx_topk_static_vectors.schedule pin_in 1 = ot_hbm_idx_rootctl_static_am_pin, VM_RT 1 / CR_RT 1) is moved by
        the request-lane pad (bank grant R and everything after the capture) and the ACK by the cq/cr lanes."""
        c = json.loads(Path(contract).read_text())["instances"].get("hb_idx__ctl")
        if c is None:
            return None
        prm = c.get("params", {})
        vm_rt, cr_rt = int(prm.get("VM_RT", 0)), int(prm.get("CR_RT", 0))
        pads = json.loads(Path(l12).read_text())["pads"] if l12 else []
        rq = max([x["N"] for x in pads if x["pad"].startswith("l12p_hb_idx__ctl_vm_rq_vmb_")] or [0])
        return dict(master=c["master"], VM_RT=vm_rt, CR_RT=cr_rt, rq_pad=rq,
                    vm_shift=vm_rt - 1, ack_shift=cr_rt - 1,
                    consistent=(vm_rt - 1 == rq))

    def _idx(s, c):
        from hbm_layer_vehicle.layer_images import CpBus
        from hbm_layer_vehicle import idx_images as II
        import hbm_vm_static_calendar as C
        from hbm_idx_topk_static_vectors import schedule
        from hgi_sim.machine import topk_ids
        ins = {e["name"] for e in s.bnd["inputs"]}
        outs = {e["name"] for e in s.bnd["outputs"]}
        need_in, need_out = {"col_idx__rec", "col_idx__go"}, {"hb_idx__ctl__topk_busy", "hb_idx__ctl__topk_fault"}
        if not (need_in <= ins and need_out <= outs):
            raise ValueError("slice cut lacks the TOPK engine hb_idx__ctl (inputs col_idx__rec/go, outputs topk_*): "
                             "rerun with CX_IDX=1 (cut include hb_idx__ctl -> new slice.v / TB build)")
        P = s.idx_params
        if P is None or not P["consistent"]:
            raise ValueError(f"hb_idx__ctl timing not derivable from the contract/l12: {P}")
        A, O, n = c["A"], c["O"], c["n"]
        k = len(O)
        order = 1 if np.all(np.diff(O.astype(np.int64)) > 0) else 0
        gold = topk_ids(A.view(np.float32), k, bool(order)).astype(np.uint32)
        if not np.array_equal(gold, O):
            raise ValueError("topk golden != fixture O")
        a_w, o_w = c["a_sector"] * 8, c["o_sector"] * 8 + int(c["x"]["desc"]["O"][0]) % 8
        rec = dict(k=k, order=order, n=n, m=1, am=0, a=a_w, a_str=n, o=o_w, o_str=k, has_r=0, r=0, r_str=0)
        ev0, end0, legal = schedule(rec, 0, 1)
        if not legal:
            raise ValueError("illegal TOPK record")
        sh = P["vm_shift"]
        rel = [(kind, e + II.G_AFTER_E0 + sh, v) for kind, e, v in ev0]
        end0 = end0 + sh + P["ack_shift"]
        words = II.calendar_words(rel, 0)
        abi = json.loads((Path(CI.ROOT) / "results/arch/hbm_vm_static_1014/quadrant_abi.json").read_text())
        spec = C.layout(abi, "SW", universal=True)
        cal = C.compile_schedule(spec, dict(base=0, loops=1, cycles=words))
        bus = CpBus(16, src="image:CAL")
        bus.install(II.CAL_TGT, [int(w["data"], 16) for w in cal["configuration_writes"]], 0)
        bus.desc(II.CAL_TGT, 0, len(words), 1)
        bus.src = "image:launch"
        cL = bus.launch()
        E0 = cL + II.CAL_DELTA
        G = E0 + II.G_AFTER_E0
        end = G + end0
        rw = II.rec_word(k, order, n, 1, a_w, n, o_w, k)
        ev = list(bus.ev) + [
            dict(k="D", dom="stream", cyc=G - 1, port="col_idx__rec", val=f"{rw:x}", src="image:IDX_desc", rec=c["i"]),
            dict(k="D", dom="stream", cyc=G - 1, port="col_idx__go", val="1", src="image:IDX_go", rec=c["i"]),
            dict(k="D", dom="stream", cyc=G, port="col_idx__go", val="0", src="image:IDX_go", rec=c["i"]),
            dict(k="D", dom="stream", cyc=end + 8, port="col_idx__rec", val="0", src="image:IDX_desc", rec=c["i"])]
        prov = dict(su_words=0, outside_slice_words=0)
        reads = set()
        for j in range(-(-n // 8)):
            ls = c["lsA"] + j
            reads.add(ls)
            w8 = [int(x) for x in A[8 * j: 8 * j + 8]] + [0] * max(0, 8 * j + 8 - n)
            val, src = s._own_image(c, ls, w8)
            prov["su_words"] += src.count("su")
            prov["outside_slice_words"] += src.count("img")
            if all(t == "su" for t in src):
                continue
            sec = (s.place.q << 13) | (c["a_sector"] + j)
            ev.append(dict(k="M", dom="stream", cyc=0, mem="vm", quarter=0, sector=sec, bank=sec % 8,
                           row=(sec & 0x1fff) >> 3, val=f"{val:064x}", rec=c["i"],
                           src="image:cx_topk_A(" + "".join("P" if t == "su" else "X" for t in src) + ")"))
        osec = (s.place.q << 13) | c["o_sector"]
        ev.append(dict(k="M", dom="stream", cyc=0, mem="vm", quarter=0, sector=osec, bank=osec % 8,
                       row=(osec & 0x1fff) >> 3, val="0" * 64, src="image:O_zero", rec=c["i"]))
        T = end + II.VM_SETTLE
        ob = int(c["x"]["desc"]["O"][0]) % 8
        oval = sum(int(x) << (32 * (ob + b)) for b, x in enumerate(O))
        ev += [dict(k="C", dom="stream", cyc=T, port=f"vm:{osec:x}", val=f"{oval:064x}", mask="f" * 64,
                    src="golden:ds_native_fixture O (comparison only)", rec=c["i"]),
               dict(k="C", dom="stream", cyc=G + 4, port="hb_idx__ctl__topk_busy", val="1", src="check:busy", rec=c["i"]),
               dict(k="C", dom="stream", cyc=end + 4, port="hb_idx__ctl__topk_busy", val="0", src="check:busy",
                    rec=c["i"])]
        ev += [dict(k="C", dom="stream", cyc=T, port=p, val="0", src="check:no_fault", rec=c["i"])
               for p in II.FAULT_OUTS if p in outs]
        return dict(events=ev, reads=reads, writes=set(c["out_map"]),
                    cx=dict(n=n, k=k, order=order, a_sector=c["a_sector"], o_sector=c["o_sector"], rec_word=hex(rw),
                            engine=P, A_word_sources=prov,
                            A_legend="P = written in-slice by the emitted SW SU producer (image word 0); X = other SU "
                                     "quarters SE/NW/NE (outside the SW cut) or not produced in-slice (fixture image)",
                            schedule="hbm_idx_topk_static_vectors.schedule(pin_in 1) + contract VM_RT/CR_RT shifts"))

    def _hc(s, c):
        from hbm_layer_vehicle import hc_layer_lower_1021 as HL
        x = c["x"]
        A = np.asarray(s.z[x["inputs"]["A"]["array"]], np.uint32)
        which = "attn" if "attn" in x["tag"] else "ffn"
        params, prov = HL.checkpoint_parameters(s.checkpoint, int(s.meta["layer"]), which)
        real = HL.lower_mix_post(A, c["O"], params, s.tim, a_sector=c["a_sector"], o_sector=c["dst"],
                                 component_allocation=False, record=c["i"], boundary=s.bnd, source_profile=s.hc_source_profile, profile_contract=s.profile_contract)
        return dict(events=real["events"], reads=set(), writes=set(c["mapping"]),
                    cx=dict(a_sector=c["a_sector"], o_sector=c["dst"], root_schedule=real["root_schedule"],
                            checkpoint=prov, A_provenance="un-emitted upstream HC projection + mix gather (fixture image)",
                            root="actual hc_eng ot_hbm_hc_root_static (no result drive)"))


def iso_part_events(P):
    """standalone part: its components back to back on one CP stream (each installs its own calendar)."""
    t, out, place = 3, [], []
    for comp in P["comps"]:
        nm = [e["cyc"] for e in comp["events"] if e["k"] != "M"]
        sh = t + CP_GUARD - min(nm)
        for e in comp["events"]:
            e2 = dict(e, cx=comp["i"])
            if e2["k"] != "M":
                e2["cyc"] += sh
            out.append(e2)
        place.append(dict(i=comp["i"], start=min(nm) + sh, end=max(nm) + sh, events=len(nm), standalone=True))
        t = max(nm) + sh + COMP_GAP
    return out, place


def epoch_calendar(t_install, last_stream):
    """finite owner-0 reservation of all 8 SW banks from its launch through last_stream + EPOCH_TAIL."""
    from hbm_layer_vehicle.layer_images import cp_frames
    from hbm_layer_vehicle.sm_images import cal_word, prog_row
    words = [prog_row(0, cal_word(rslot_v=255, wslot_v=255, lg_local_read=255, lg_local_write=255), 187)]
    _, launch, _ = cp_frames(96, words, t_install, loops=1)
    loops = max(1, last_stream + EPOCH_TAIL - launch)
    if loops > 65535:
        raise ValueError(f"SU epoch of {loops} edges exceeds the calendar loop field")
    ev, launch, _ = cp_frames(96, words, t_install, loops=loops)
    for e in ev:
        e["src"] = "image:SU_epoch_calendar"
        e["cx_epoch"] = True
    return ev, launch, launch + 10 + loops


def epoch_launch(t_install):
    from hbm_layer_vehicle.layer_images import cp_frames
    from hbm_layer_vehicle.sm_images import cal_word, prog_row
    words = [prog_row(0, cal_word(rslot_v=255, wslot_v=255, lg_local_read=255, lg_local_write=255), 187)]
    return cp_frames(96, words, t_install, loops=1)[1]


def cones_parts(nodes, cap):
    """nodes: ordered list of dict(id, drives (list), checks (list), reads (set logical), writes (set logical)).
    Returns parts [dict(members, targets, events)] -- part = union of the producer cones of its target nodes."""
    writer, deps = {}, {}
    for n in nodes:
        deps[n["id"]] = {writer[ls] for ls in n["reads"] if ls in writer}
        for ls in n["writes"]:
            writer[ls] = n["id"]
    byid = {n["id"]: n for n in nodes}
    cone = {}
    for n in nodes:
        c = {n["id"]}
        for d in deps[n["id"]]:
            c |= cone[d]
        cone[n["id"]] = c
    nd = lambda ids: sum(len(byid[x]["drives"]) for x in ids)
    parts, cur = [], None
    for n in nodes:
        if not n["checks"] and any(n["id"] in p["members"] for p in parts):
            continue                       # check-less node already executed inside an earlier part's cone
        need = cone[n["id"]]
        if cur is not None and cur.get("chapter") == n.get("chapter"):
            mem = cur["members"] | need
            if nd(mem) + sum(len(byid[t]["checks"]) for t in cur["targets"] + [n["id"]]) <= cap:
                cur["members"], cur["targets"] = mem, cur["targets"] + [n["id"]]
                continue
        cur = dict(members=set(need), targets=[n["id"]], chapter=n.get("chapter"))
        parts.append(cur)
    for p in parts:
        p["drive_events"] = nd(p["members"])
        p["check_events"] = sum(len(byid[t]["checks"]) for t in p["targets"])
        p["fits"] = p["drive_events"] + p["check_events"] <= cap
    return parts, cone
