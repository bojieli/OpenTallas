"""hgi_sim timing: the transaction-level schedule of one doorbell on one die, with the command processor modelled.

THE COMMAND PROCESSOR (spec section 3.1; calibration.json "cp"):
  fetch     the program image is read from HBM in 64 B requests into a prefetch ring (issue interval, first-access
            latency); a LOOP body that fits the ring replays from it without refetch;
  decode    a record leaves the ring at one 32 B chunk a cycle (header + SUT + each MDESC), then the descriptor
            address arithmetic (base + L*lstride + DYN*dyn_mul) adds its latency;
  wait      a record is held until every unit in its `wait` mask has nothing outstanding; the retire report reaches
            the cmdproc `retire_wire` cycles after the unit finishes;
  dispatch  IN ORDER, one record a cycle, into a per-unit queue of `queue_depth`; a held record (wait mask or a full
            queue) blocks every record behind it, whatever its unit (HEAD-OF-LINE blocking);
  units     each unit runs its queue in order; a record starts `dispatch_wire` cycles after dispatch once the unit is
            free (pipelined units -- DMA -- start one every issue interval and retire in order).

SCHEDULES (same records, same unit costs):
  S0 ideal dataflow     only true data dependences (exact address footprints) and in-order units; no CP.
  S1 drain waits only   the compiler's wait masks, no CP cost, no HOL (an independent sequencer per unit).
  S2 full CP            the model above (the hardware as specified).
  S3 full CP, no fetch  S2 with fetch / decode free (separates CP throughput from HOL + drain waits).
S2 is the token's cycle count.  S1 - S0 is the overlap the drain-based waits give up; S2 - S1 the issue / HOL cost.

RACE CHECK.  In S2 every record must start after the end of each true producer (RAW) and each earlier reader of the
region it overwrites (WAR) and earlier writer (WAW).  A violation is a compiler wait bug: reported, never absorbed.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hbm_generic_iface as HGI  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402

from .records import ISTRIDE_BCAST, rec_bytes  # noqa: E402

CAL = json.loads((Path(__file__).with_name("calibration.json")).read_text())
ESZ = {"FP32": 4, "BF16": 2, "FP8E4M3": 1, "INT8": 1, "U32": 4, "UE8M0": 1, "FP4E2M1": 1}


def cv(sec, key):
    return CAL[sec][key]["value"]


# ----------------------------------------------------------------------------------------------------------------
# execution list and footprints
# ----------------------------------------------------------------------------------------------------------------
def expand(recs, pos, token=0, rank=0):
    """The executed record sequence of one doorbell: [(record index, L)] with LOOP replay and predicates."""
    out, pc, loop, L = [], 0, None, 0
    while pc < len(recs):
        r = recs[pc]
        p = r.pred
        if not (p == "ALWAYS" or (p == "POS0" and pos == 0) or (p == "NOT_POS0" and pos != 0)
                or (p == "LAST_ITER" and loop and L == loop[1] - 1)):
            pc += 1
            continue
        if r.unit == "CTL" and r.op == "LOOP":
            loop, L, pc = (pc + 1, r.param), 0, pc + 1
            continue
        if r.unit == "CTL" and r.op == "ENDLOOP":
            L += 1
            if L < loop[1]:
                pc = loop[0]
                continue
            loop, L, pc = None, 0, pc + 1
            continue
        out.append((pc, L))
        if r.unit == "CTL" and r.op == "END":
            break
        pc += 1
    return out


class Dyn:
    def __init__(self, pos, token=0, rank=0):
        self.v = [0, pos, pos + 1, token, 0, rank, 0, pos] + [0] * 24


def eff(d, dyn, L):
    base = d.base + L * d.lstride + dyn.v[d.dyn_sel] * d.dyn_mul
    n = dyn.v[d.n_sel] if d.n_sel else d.n
    ist = 0 if d.istride == ISTRIDE_BCAST else (d.istride or 1)
    return base, n, d.m, d.stride, ist


def interval(d, dyn, L):
    """(space, lo, hi) bounding the descriptor's elements (VM words / HBM bytes)."""
    base, n, m, st, ist = eff(d, dyn, L)
    if d.space == "VM":
        hi = base + max(0, m - 1) * st + max(0, n - 1) * ist + 1
        return ("VM", base, hi)
    es = ESZ[d.fmt]
    hi = base + max(0, m - 1) * st + (max(0, n - 1) * ist + 1) * es
    return ("HBM", base, hi)


def intervals(d, dyn, L):
    """Per outer row when there are few rows (strided head / plane rows), else the bounding interval."""
    base, n, m, st, ist = eff(d, dyn, L)
    if 1 < m <= 64 and st:
        out = []
        for o in range(m):
            sub = type(d)(**{**d.__dict__, "base": base + o * st, "m": 1, "lstride": 0, "dyn_sel": 0, "dyn_mul": 0,
                             "n_sel": 0, "n": n})
            out.append(interval(sub, dyn, 0))
        return out
    return [interval(d, dyn, L)]


def footprint(r, dyn, L):
    """Descriptor extents, plus the implicit state a native engine reads / writes (r.implicit: VM intervals the
    lowering declares for DS engines whose inputs are not all descriptors)."""
    reads, writes = [], []
    for kind, iv in getattr(r, "implicit", ()):
        (writes if kind == "w" else reads).append(iv)
    for k, d in r.desc.items():
        if d.space not in ("VM", "HBM"):
            continue
        (writes if k in ("O", "R") else reads).extend(intervals(d, dyn, L))
    if r.unit == "SU" and r.sut and r.sut.get("c_pair") and "A" in r.desc:
        pass                                             # partner lies inside A's head span (aligned)
    return reads, writes


def overlap(a, b):
    return a[0] == b[0] and a[1] < b[2] and b[1] < a[2]


# ----------------------------------------------------------------------------------------------------------------
# unit costs (1.2 GHz cycles)
# ----------------------------------------------------------------------------------------------------------------
_VC = None


def _su_model():
    global _VC
    if _VC is None:
        import rtl_hdc_v41x_vec_campaign as VC
        import hbm_su_c12 as S
        S.set_c12(VC)
        VC.BCAST, VC.RET = 7, 8
        _VC = VC
    return _VC


def su_cost(r, dyn, L):
    VC = _su_model()
    a = r.desc["A"]
    _, ni, no, ast, aist = eff(a, dyn, L)
    f = VC.op_defaults()
    t = r.sut
    f.update(nout=no, nin=ni, sfu=t["sfu"], m1=t["m1"], m2=t["m2"], qm=t["qm"], ad=t["ad"], e1=t["e1"],
             e2=t["e2"], rnd=t["rnd"], dst=t["dst"], red=t["red"], redsq=t["red_sq"], redwhole=t["red_whole"],
             redtree=t["red_tree"], bhalf=t["b_half"], cpair=t["c_pair"], aind=t["a_ind"])

    def strides(k, s):
        d = r.desc.get(k)
        if d is None:
            f[f"{s}so"], f[f"{s}si"] = (ni * 1) & 0xFFFFFF, 1
            return
        _, _, _, st, ist = eff(d, dyn, L)
        f[f"{s}so"], f[f"{s}si"] = st & 0xFFFFFF, ist & 0xFFFFFF
    for k, s in (("A", "a"), ("B", "b"), ("C", "c"), ("D", "d"), ("O", "o")):
        strides(k, s)
    if "R" in r.desc:
        f["rso"] = max(1, r.desc["R"].stride)
    lay = VC.layout(f, 1024, 256)
    depth = lay["dR"] if t["red"] else lay["dP"]
    return lay["nv"] + depth + cv("units", "SU.issue_overhead"), f"SU model nv {lay['nv']} + depth {depth}"


def cost(r, dyn, L, cfg=None):
    """(cycles, grade, how) of the record's unit work on one die."""
    bw = cv("hbm", "bytes_per_cycle")
    u, op = r.unit, r.op
    if u == "SM":
        b = r.desc["B"]
        _, n, m, st, _ = eff(b, dyn, L)
        nbytes = n * m * ESZ[b.fmt] * (cv("hbm", "fmt3_transport") if (r.param & 3) == 3 else 1.0)
        c = cv("units", "SM.first_access") + nbytes / bw + cv("units", "SM.drain")
        return c, "estimate", f"SM {m}x{n} {b.fmt}: {nbytes / 1e6:.2f} MB at {bw:.0f} B/cyc + first access"
    if u == "SU":
        c, how = su_cost(r, dyn, L)
        return c, "model", how
    if u == "FUSED":
        seg = r.param & 0xFF
        c = cv("units", "FUSED.ROW_NORM.seg128" if seg else "FUSED.ROW_NORM.d4096")
        return c, "estimate", f"ROW_NORM seg {seg}"
    if u == "SFU":
        return cv("units", "SFU.GLU"), "estimate", "GLU fast path"
    if u == "ATT":
        b = r.desc["B"]
        _, P, _, st, _ = eff(b, dyn, L)
        lanes = r.param & 0xF
        hd = 128
        nbytes = P * hd * ESZ[b.fmt]
        c = cv("hbm", "first_access") + nbytes / bw + cv("units", "ATT.fixed")
        return c, "estimate", f"ATT.{op} {P} rows x {hd} FP8 ({nbytes / 1e6:.2f} MB), {lanes} lanes"
    if u == "DMA":
        if op == "LOAD":
            a = r.desc["A"]
            _, n, m, _, _ = eff(a, dyn, L)
            return cv("hbm", "first_access") + n * m * ESZ[a.fmt] / bw, "estimate", "DMA load"
        if op == "STORE":
            return cv("units", "DMA.store_latency"), "estimate", "posted KV store"
        return cv("units", "DMA.fence"), "estimate", "fence"
    if u == "COLL":
        return cv("units", f"COLL.{op}"), CAL["units"][f"COLL.{op}"]["grade"], op
    if u == "ARGMAX":
        _, n, m, _, _ = eff(r.desc["A"], dyn, L)
        return 20 + n * m * cv("units", "ARGMAX.LOCAL.per_elem"), "estimate", "argmax"
    if u == "CTL":
        return 1, "estimate", "ctl"
    raise KeyError((u, op))


PIPELINED = {"DMA": cv("units", "DMA.load_issue")}


# ----------------------------------------------------------------------------------------------------------------
# the schedules
# ----------------------------------------------------------------------------------------------------------------
def schedule(recs, pos, mode="S2", token=0, cost_fn=cost, wires=True):
    """mode: S0 dataflow | S1 per-unit sequencers (drain waits, no HOL) | S2 the CP as specified | S3 S2 with free
    fetch / decode | SX S2 with dispatch skip-ahead (a held record blocks only later records it has a region hazard
    with, or of its own unit).  wires=False zeroes dispatch_wire / retire_wire."""
    dyn = Dyn(pos, token)
    ex = expand(recs, pos, token)
    n = len(ex)
    units = HGI.UNITS
    costs, fps = [], []
    for (k, L) in ex:
        r = recs[k]
        dyn.v[4] = L
        costs.append(cost_fn(r, dyn, L))
        fps.append(footprint(r, dyn, L))
    # true dependences (exact intervals): producer = last writer of an overlapping region (RAW / WAW), readers since
    deps = [[] for _ in range(n)]
    writers, readers = [], []          # (interval, j)
    for i in range(n):
        rd, wr = fps[i]
        for iv in rd:
            for (w, j) in writers:
                if overlap(iv, w):
                    deps[i].append(j)
        for iv in wr:
            for (w, j) in writers:
                if overlap(iv, w):
                    deps[i].append(j)
            for (x, j) in readers:
                if overlap(iv, x):
                    deps[i].append(j)
        for iv in wr:
            writers = [(w, j) for (w, j) in writers if not (w[0] == iv[0] and iv[1] <= w[1] and w[2] <= iv[2])]
            writers.append((iv, i))
            readers = [(x, j) for (x, j) in readers if not overlap(x, iv)]
        for iv in rd:
            readers.append((iv, i))
        deps[i] = sorted(set(deps[i]))
    cpc = CAL["cp"]
    fetch_lat, fetch_iss, req = cpc["fetch_latency"]["value"], cpc["fetch_issue_cycles"]["value"], \
        cpc["fetch_req_bytes"]["value"]
    ring = cpc["ring_bytes"]["value"]
    dwire, rwire, qd = cpc["dispatch_wire"]["value"], cpc["retire_wire"]["value"], cpc["queue_depth"]["value"]
    if not wires:
        dwire = rwire = 0
    nm_rd = [set(getattr(recs[k], "reads", ())) for k, _ in ex]
    nm_wr = [set(getattr(recs[k], "writes", ())) for k, _ in ex]
    # record byte offsets in the image (for fetch); loop replays hit the ring when the body fits
    offs, o = [], 0
    for r in recs:
        offs.append(o)
        o += rec_bytes(r)
    body = {}
    for k, r in enumerate(recs):
        if r.unit == "CTL" and r.op == "LOOP":
            e = next(j for j in range(k + 1, len(recs)) if recs[j].unit == "CTL" and recs[j].op == "ENDLOOP")
            body = dict(lo=k, hi=e, bytes=offs[e] - offs[k] + rec_bytes(recs[e]))
    fetched_at = {}

    def fetch_ready(i, k, L):
        if mode in ("S0", "S1", "S3"):
            return 0.0
        if body and body["lo"] < k <= body["hi"] and L > 0 and body["bytes"] <= ring:
            return 0.0                                         # replay from the ring
        key = (k, L if body and body["lo"] < k <= body["hi"] and body["bytes"] > ring else 0)
        if key not in fetched_at:
            end = offs[k] + rec_bytes(recs[k])
            nreq = math.ceil(end / req)
            fetched_at[key] = fetch_lat + nreq * fetch_iss    # streaming prefetch from the doorbell
        return fetched_at[key]
    start = [0.0] * n
    end = [0.0] * n
    disp = [0.0] * n
    unit_last = {}
    unit_starts = defaultdict(list)
    last_end_unit = defaultdict(float)
    outstanding_end = defaultdict(float)      # per unit: retire time of the last dispatched record
    cp_t = 0.0
    dec_t = 0.0
    hol_block = [0.0] * n
    wait_block = [0.0] * n
    cp_busy = 0.0
    for i, (k, L) in enumerate(ex):
        r = recs[k]
        c = costs[i][0]
        u = r.unit
        if mode == "S0":
            t0 = max([end[j] for j in deps[i]] + [last_end_unit[u] if u not in PIPELINED else 0.0])
            if u in PIPELINED and unit_starts[u]:
                t0 = max(t0, unit_starts[u][-1] + PIPELINED[u])
            start[i] = t0
        else:
            nch = (1 if r.sut is not None else 0) + len(r.descs_in_order())
            dcyc = 0.0 if mode in ("S1",) else cpc["decode_header"]["value"] + nch * cpc["decode_per_chunk"]["value"]
            alat = 0.0 if mode in ("S1",) else cpc["addr_latency"]["value"]
            f_r = fetch_ready(i, k, L)
            dec_t = max(dec_t + dcyc, f_r + dcyc) if mode in ("S2", "SX") else (dec_t + dcyc)
            ready = dec_t + alat
            wt = 0.0
            for b, un in enumerate(units):
                if r.wait >> b & 1:
                    wt = max(wt, outstanding_end[un] + rwire)
            q = unit_starts[u]
            qt = q[-qd] if len(q) >= qd else 0.0
            if mode == "S1":
                # per-unit sequencers, drain semantics: wait for every unit that produced an input to drain
                wt = max([outstanding_end[recs[ex[j][0]].unit] for j in deps[i]] + [0.0])
                d_t = max(ready, wt)
            elif mode == "SX":
                # skip-ahead: order only against earlier records with a region hazard, and the unit's own queue
                lim = qt
                for j in range(i - 1, max(-1, i - 64), -1):
                    if recs[ex[j][0]].unit == u or (nm_rd[i] & nm_wr[j]) or (nm_wr[i] & (nm_rd[j] | nm_wr[j])):
                        lim = max(lim, disp[j] + 1)
                d_t = max(ready, wt, lim)
                hol_block[i] = max(0.0, d_t - max(ready, wt, qt))
                cp_busy += dcyc + cpc["dispatch_cycles"]["value"]
            else:
                d_t = max(ready, cp_t + cpc["dispatch_cycles"]["value"], wt, qt)
                wait_block[i] = max(0.0, wt - max(ready, cp_t + 1, qt))
                hol_block[i] = max(0.0, d_t - max(ready, wt, qt))
                cp_busy += dcyc + cpc["dispatch_cycles"]["value"]
                cp_t = d_t
            disp[i] = d_t
            t0 = max(d_t + (dwire if mode != "S1" else 0.0), last_end_unit[u] if u not in PIPELINED else 0.0)
            if u in PIPELINED and q:
                t0 = max(t0, q[-1] + PIPELINED[u])
            start[i] = t0
        end[i] = start[i] + c
        if u in PIPELINED:
            end[i] = max(end[i], last_end_unit[u])         # in-order retire
        last_end_unit[u] = end[i]
        unit_starts[u].append(start[i])
        outstanding_end[u] = max(outstanding_end[u], end[i])
    total = max(end) if n else 0.0
    races = []
    if mode != "S0":
        for i in range(n):
            for j in deps[i]:
                if end[j] > start[i] + 1e-9 and not (recs[ex[i][0]].unit == recs[ex[j][0]].unit and j < i
                                                       and recs[ex[i][0]].unit not in PIPELINED):
                    races.append(dict(rec=ex[i][0], L=ex[i][1], tag=recs[ex[i][0]].tag, producer=recs[ex[j][0]].tag,
                                      early=round(end[j] - start[i], 1)))
    # per-unit busy / idle split: idle caused by true dependences vs by issue (CP, HOL, drain waits)
    per_unit = defaultdict(lambda: dict(busy=0.0, idle_true_dep=0.0, idle_issue=0.0, records=0))
    prev = defaultdict(float)
    for i, (k, L) in enumerate(ex):
        u = recs[k].unit
        pu = per_unit[u]
        pu["records"] += 1
        pu["busy"] += end[i] - start[i]
        e_true = max([prev[u]] + [end[j] for j in deps[i]])
        gap_true = max(0.0, e_true - prev[u])
        gap_issue = max(0.0, start[i] - max(e_true, prev[u]))
        pu["idle_true_dep"] += gap_true
        pu["idle_issue"] += gap_issue
        prev[u] = end[i]
    fam = defaultdict(float)
    for i, (k, L) in enumerate(ex):
        fam[recs[k].family or recs[k].tag] += end[i] - start[i]
    return dict(mode=mode, total_cycles=total, records_executed=n, deps=deps, start=start, end=end, disp=disp,
                costs=costs, ex=ex, races=races, per_unit={k: {a: round(b, 1) for a, b in v.items()}
                                                           for k, v in per_unit.items()},
                cp_busy=round(cp_busy, 1), hol_block=round(sum(hol_block), 1), wait_block=round(sum(wait_block), 1),
                family_unit_cycles={k: round(v, 1) for k, v in sorted(fam.items(), key=lambda x: -x[1])})


def critical_path(s, recs):
    """Walk back from the last record through whatever bound each start (a true producer, the unit, or dispatch)."""
    n = len(s["ex"])
    if not n:
        return []
    i = int(np.argmax(s["end"]))
    path = []
    seen = set()
    while i is not None and i not in seen:
        seen.add(i)
        k, L = s["ex"][i]
        path.append(dict(tag=recs[k].tag, L=L, unit=recs[k].unit, start=round(s["start"][i], 1),
                         end=round(s["end"][i], 1)))
        cands = [(s["end"][j], j) for j in s["deps"][i]]
        u = recs[k].unit
        for j in range(i - 1, -1, -1):
            if recs[s["ex"][j][0]].unit == u:
                cands.append((s["end"][j], j))
                break
        cands = [c for c in cands if c[0] <= s["start"][i] + 1e-6]
        if not cands:
            break
        bound, j = max(cands)
        if s["start"][i] - bound > 20 and s["disp"][i]:
            path[-1]["bound_by"] = "dispatch"
        i = j
    return list(reversed(path))


def reorder(recs, pos, cost_fn=cost, rebuild=None):
    """Compiler fix: within each straight-line segment (between CTL records; a LOOP body is one segment, ordered by
    its first iteration), issue records in the order of their ideal-dataflow (S0) start, then recompute the wait
    masks for the new order.  S0 start order respects every true dependence (a consumer never starts before its
    producer ends), so the program's results are unchanged."""
    s0 = schedule(recs, pos, "S0", cost_fn=cost_fn)
    first = {}
    for i, (k, L) in enumerate(s0["ex"]):
        first.setdefault(k, (s0["start"][i], s0["end"][i], i))
    out, seg = [], []

    def flush():
        seg.sort(key=lambda k: (first.get(k, (0, 0, k))[0], first.get(k, (0, 0, k))[2]))
        out.extend(seg)
        seg.clear()
    for k, r in enumerate(recs):
        if r.unit == "CTL":
            flush()
            out.append(k)
        else:
            seg.append(k)
    flush()
    new = [recs[k] for k in out]
    return rebuild(new) if rebuild else new


def rebuild_waits(recs):
    """Recompute wait masks for a reordered record list (the Builder's hazard rule over the records' region names)."""
    import copy as _c
    from .qwen_compiler import assign_waits
    out = [_c.copy(r) for r in recs]
    for r in out:
        r.reads, r.writes = list(getattr(r, "reads", ())), list(getattr(r, "writes", ()))
    return assign_waits(out)
