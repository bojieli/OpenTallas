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

from .records import rec_bytes  # noqa: E402

CAL = json.loads((Path(__file__).with_name("calibration.json")).read_text())
ROOT = Path(__file__).resolve().parents[2]


def _measured():
    """Replace estimates with RTL / bench measurements wherever a committed record exists (pins recorded)."""
    out = {}
    try:
        s = json.loads((ROOT / "results/rtl/dshbm_1m_allmeasured_20261004/hbm_streams.json").read_text())["streams"]
        v = s["embedding_row_notice"]["complete_cycles_1p2GHz"]["max"]
        out["hbm.first_access"] = dict(value=v, grade="measured",
                                       source="results/rtl/dshbm_1m_allmeasured_20261004/hbm_streams.json "
                                              "embedding_row_notice worst of 64 refresh phases (static program: notice)")
    except Exception:
        pass
    try:
        import statistics
        rows = []
        for f in ("results/rtl/w19_sm_real_ops.json", "results/rtl/dshbm_baseline_measured_20261004/sm_real_ops.json"):
            for c in json.loads((ROOT / f).read_text())["cases"].get("ar", []):
                if c["fmt"] == "v41_bf16" and c["exact"]:
                    r = c["rtl"]
                    rows.append((c["K"], c["sm_rows"][1] - c["sm_rows"][0], r["lines"],
                                 r["drain_last_line_to_last_result"], r["cycles_start_to_done"]))
        rate = max(l / (R * K) for K, R, l, d, t in rows)
        out["SM.bf16_lines_per_row_k"] = dict(value=rate, grade="measured",
                                              source=f"ot_gpu_sm_v / sm_v BF16 lines on real operands ({len(rows)} cases)")
        out["SM.drain"] = dict(value=statistics.median(d for *_, d, t in rows), grade="measured", source="same, median")
        out["SM.overhead"] = dict(value=statistics.median(t - l - d for K, R, l, d, t in rows), grade="measured",
                                  source="same: start_to_done - lines - drain, median")
    except Exception:
        pass
    try:
        c = json.loads((ROOT / "results/rtl/hbm_su_c12_20261005/campaign_full.json").read_text())
        cls = c["perf_N64_M16"]["depths"]["classes"]
        ok = all(v["emit_to_write"] == v["model"] for v in cls.values())
        out["SU.model_check"] = dict(value=ok, grade="measured" if ok else "model",
                                     source="results/rtl/hbm_su_c12_20261005/campaign_full.json perf depths: RTL "
                                            "emit->write == depth model for every op class")
    except Exception:
        pass
    return out


MEAS = _measured()
ESZ = {"FP32": 4, "BF16": 2, "FP8E4M3": 1, "INT8": 1, "U32": 4, "UE8M0": 1, "FP4E2M1": 1}


def cv(sec, key):
    return CAL[sec][key]["value"]


# ----------------------------------------------------------------------------------------------------------------
# execution list and footprints
# ----------------------------------------------------------------------------------------------------------------
def expand(recs, pos, token=0, rank=0):
    """The executed record sequence of one doorbell: [(record index, L)] with LOOP replay (two levels: CTL.LOOP
    param[15:0] count, [16] level) and predicates.  L is the level-0 counter (L1 is not used by the cost model)."""
    out, pc, loops = [], 0, []
    while pc < len(recs):
        r = recs[pc]
        p = r.pred
        L = next((x[2] for x in reversed(loops) if x[3] == 0), 0)
        L1 = next((x[2] for x in reversed(loops) if x[3] == 1), 0)
        if not (p == "ALWAYS" or (p == "POS0" and pos == 0) or (p == "NOT_POS0" and pos != 0)
                or (p == "LAST_ITER" and loops and loops[-1][2] == loops[-1][1] - 1)):
            pc += 1
            continue
        if r.unit == "CTL" and r.op == "LOOP":
            loops.append([pc + 1, r.param & 0xFFFF, 0, (r.param >> 16) & 1])
            pc += 1
            continue
        if r.unit == "CTL" and r.op == "ENDLOOP":
            loops[-1][2] += 1
            if loops[-1][2] < loops[-1][1]:
                pc = loops[-1][0]
                continue
            loops.pop()
            pc += 1
            continue
        out.append((pc, L, L1))
        if r.unit == "CTL" and r.op == "END":
            break
        pc += 1
    return out


class Dyn:
    def __init__(self, pos, token=0, rank=0):
        self.v = [0, pos, pos + 1, token, 0, rank, 0, pos] + [0] * 24


def eff(d, dyn, L):
    if d.indexed:                             # C3b indexed descriptor: timing uses id 0 (values are not modelled)
        base = d.base + L * d.lstride + dyn.v[8] * d.l1stride
    else:
        base = d.base + L * d.lstride + dyn.v[8] * d.l1stride + dyn.v[d.dyn_sel] * d.dyn_mul
    n = dyn.v[d.n_sel] if 0 < d.n_sel < 63 else d.n
    ist = 0 if d.ibcast else (d.istride or 1)
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
            sub = type(d)(**{**d.__dict__, "base": base + o * st, "m": 1, "lstride": 0, "l1stride": 0, "dyn_sel": 0,
                             "dyn_mul": 0, "n_sel": 0, "n": n, "indexed": 0})
            out.append(interval(sub, dyn, 0))
        return out
    return [interval(d, dyn, L)]


def footprint(r, dyn, L):
    """Descriptor extents, plus the implicit state a native engine reads / writes (r.implicit: VM intervals the
    lowering declares for DS engines whose inputs are not all descriptors)."""
    reads, writes = [], []
    for kind, iv in getattr(r, "implicit", ()):
        (writes if kind == "w" else reads).append(iv)
    half = r.unit == "SU" and r.sut is not None and r.sut.get("b_half")
    for k, d in r.desc.items():
        if d.space not in ("VM", "HBM"):
            continue
        if half and k in ("B", "D") and not (0 < d.n_sel < 63):
            # b_half: B / D are read at inner index i >> 1 (adjacent-pair tables), so the span is ceil(n / 2)
            d = type(d)(**{**d.__dict__, "n": (d.n + 1) // 2})
        (writes if k in ("O", "R") else reads).extend(intervals(d, dyn, L))      # I (id table): a read
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
    hbm = any(d.space == "HBM" for d in r.desc.values())       # an HBM source pays the first access before row 0
    fa = first_access() if hbm else 0.0
    return lay["nv"] + depth + cv("units", "SU.issue_overhead") + fa, \
        f"SU model nv {lay['nv']} + depth {depth}" + (f" + HBM first access {fa:.0f}" if hbm else "")


TRANSPORT = cv("hbm", "fmt3_transport")       # bytes moved per code byte (fmt3 line stride / codes)
SM_RATE = 1.0                                   # fmt3 issue relative to the BF16 lanes (1.0 = 64 codes / cycle / SM)


def first_access():
    return MEAS["hbm.first_access"]["value"] if "hbm.first_access" in MEAS else cv("hbm", "first_access")


def cost(r, dyn, L, cfg=None):
    """(cycles, grade, how) of the record's unit work on one die."""
    bw = cv("hbm", "bytes_per_cycle")
    u, op = r.unit, r.op
    if u == "SM":
        b = r.desc["B"]
        _, n, m, st, _ = eff(b, dyn, L)
        tr = TRANSPORT if (r.param & 3) == 3 else 1.0
        nbytes = n * m * ESZ[b.fmt] * tr
        stream = nbytes / bw
        if "SM.bf16_lines_per_row_k" in MEAS:
            # fmt 0 and fmt 3 issue on the same BF16 lanes (fmt 3: a 128-code line in two 64-code beats)
            R = -(-m // 32)
            lines = math.ceil(MEAS["SM.bf16_lines_per_row_k"]["value"] * R * n * SM_RATE)
            comp = lines + MEAS["SM.drain"]["value"]
            fa = MEAS["hbm.first_access"]["value"] + MEAS["SM.overhead"]["value"]
            c = fa + max(comp, stream)
            return c, "measured", (f"SM {m}x{n} {b.fmt}: lines {lines} (+drain) vs stream {stream:.0f} "
                                   f"({nbytes / 1e6:.2f} MB, transport {tr}) -> {'SM' if comp > stream else 'HBM'}-bound")
        c = cv("units", "SM.first_access") + nbytes / bw + cv("units", "SM.drain")
        return c, "estimate", f"SM {m}x{n} {b.fmt}: {nbytes / 1e6:.2f} MB at {bw:.0f} B/cyc + first access"
    if u == "SU":
        c, how = su_cost(r, dyn, L)
        return c, ("measured_depth_model" if MEAS.get("SU.model_check", {}).get("value") else "model"), how
    if u == "FUSED":
        seg = (r.param >> 6) & 0xFF
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
        c = first_access() + nbytes / bw + cv("units", "ATT.fixed")
        return c, "estimate", f"ATT.{op} {P} rows x {hd} FP8 ({nbytes / 1e6:.2f} MB), {lanes} lanes"
    if u == "DMA":
        if op == "LOAD":
            a = r.desc["A"]
            _, n, m, _, _ = eff(a, dyn, L)
            return first_access() + n * m * ESZ[a.fmt] / bw, ("measured" if "hbm.first_access" in MEAS
                                                               else "estimate"), "DMA load"
        if op == "STORE":
            return cv("units", "DMA.store_latency"), "estimate", "posted KV store"
        return cv("units", "DMA.fence"), "estimate", "fence"
    if u == "COLL":
        return cv("units", f"COLL.{op}"), CAL["units"][f"COLL.{op}"]["grade"], op
    if u == "ARGMAX":
        a = r.desc["A"]
        _, n, m, _, _ = eff(a, dyn, L)
        if a.space == "STREAM":
            return 20 + n * m * cv("units", "ARGMAX.LOCAL.per_elem"), "estimate", "argmax on the streamed logits"
        return 20 + n * m * cv("units", "ARGMAX.LOCAL.vm_per_elem"), "measured", "argmax reading VM"
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
    for (k, L, L1) in ex:
        r = recs[k]
        dyn.v[4], dyn.v[8] = L, L1
        costs.append(cost_fn(r, dyn, L))
        fps.append(footprint(r, dyn, L))
    dread = []
    for (k, L, L1) in ex:
        r = recs[k]
        if "I" in r.desc and any(d.indexed for d in r.desc.values()):
            dyn.v[4], dyn.v[8] = L, L1
            dread.append([interval(r.desc["I"], dyn, L)])
        else:
            dread.append([])
    # true dependences (exact intervals): producer = last writer of an overlapping region (RAW / WAW), readers since
    deps = [[] for _ in range(n)]
    ddeps = [[] for _ in range(n)]     # WAR on an indexed record's I table: the id is read at dispatch (spec 2.2.4)
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
                    (ddeps if x in dread[j] else deps)[i].append(j)
        for iv in wr:
            writers = [(w, j) for (w, j) in writers if not (w[0] == iv[0] and iv[1] <= w[1] and w[2] <= iv[2])]
            writers.append((iv, i))
            readers = [(x, j) for (x, j) in readers if not overlap(x, iv)]
        for iv in rd:
            readers.append((iv, i))
        deps[i] = sorted(set(deps[i]))
        ddeps[i] = sorted(set(ddeps[i]) - set(deps[i]))
    # STREAM producer -> consumer pairs (credit-ordered: the consumer runs alongside its producer, no wait bit)
    tails = CAL["units"].get("STREAM.tail", {}).get("value", {})
    sdep, last_prod = [None] * n, {}
    for i, (k, *_) in enumerate(ex):
        r = recs[k]
        for key in ("A", "B", "C", "D"):
            d = r.desc.get(key)
            if d is not None and d.space == "STREAM" and d.base in last_prod:
                sdep[i] = last_prod[d.base]                 # every consumer of the stream rides its producer
        for key in ("O", "R"):
            d = r.desc.get(key)
            if d is not None and d.space == "STREAM":
                last_prod[d.base] = i
    cpc = CAL["cp"]
    fetch_lat, fetch_iss, req = cpc["fetch_latency"]["value"], cpc["fetch_issue_cycles"]["value"], \
        cpc["fetch_req_bytes"]["value"]
    ring = cpc["ring_bytes"]["value"]
    dwire, rwire, qd = cpc["dispatch_wire"]["value"], cpc["retire_wire"]["value"], cpc["queue_depth"]["value"]
    if not wires:
        dwire = rwire = 0
    edges = cpc.get("dispatch_edges", {}).get("value", {}) if wires else {}

    def wire_of(rec):
        """per-unit dispatch / retire wire stages (R25G floorplan edges where priced, else the estimate)"""
        if rec.unit == "FUSED" and rec.op.startswith("QDQ") and "FUSED.QDQ" in edges:
            return edges["FUSED.QDQ"]
        return edges.get(rec.unit, dwire)
    nm_rd = [set(getattr(recs[k], "reads", ())) for k, *_ in ex]
    nm_wr = [set(getattr(recs[k], "writes", ())) for k, *_ in ex]
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
    ret_w = defaultdict(lambda: float(rwire))             # retire wire of each unit's last record
    hol_block = [0.0] * n
    wait_block = [0.0] * n
    why = [None] * n                          # S2: (ready, wait, queue, cp, wait unit) of each dispatch
    cp_busy = 0.0
    for i, (k, L, *_) in enumerate(ex):
        r = recs[k]
        c = costs[i][0]
        u = r.unit
        if mode == "S0":
            t0 = max([end[j] for j in deps[i]] + [start[j] for j in ddeps[i]] +
                     [last_end_unit[u] if u not in PIPELINED else 0.0])
            if u in PIPELINED and unit_starts[u]:
                t0 = max(t0, unit_starts[u][-1] + PIPELINED[u])
            start[i] = t0
        else:
            nch = (1 if r.sut is not None else 0) + len(r.descs_in_order())
            dcyc = 0.0 if mode in ("S1",) else cpc["decode_header"]["value"] + nch * cpc["decode_per_chunk"]["value"]
            alat = 0.0 if mode in ("S1",) else cpc["addr_latency"]["value"]
            nidx = sum(1 for d in r.desc.values() if d.indexed)
            f_r = fetch_ready(i, k, L)
            dec_t = max(dec_t + dcyc, f_r + dcyc) if mode in ("S2", "SX") else (dec_t + dcyc)
            ready = dec_t + alat
            wt, wun = 0.0, None
            for b, un in enumerate(units):
                if r.wait >> b & 1 and outstanding_end[un] + ret_w[un] > wt:
                    wt, wun = outstanding_end[un] + ret_w[un], un
            q = unit_starts[u]
            qt = q[-qd] if len(q) >= qd else 0.0
            if nidx:
                # C3b: the dispatcher reads the index word only after its producer retired (the wait is satisfied)
                ivs = [interval(r.desc["I"], dyn, L)] if "I" in r.desc else []
                prod = max([end[j] + ret_w[recs[ex[j][0]].unit] for j in deps[i]
                            if any(overlap(w_, iv) for w_ in fps[j][1] for iv in ivs)] + [0.0])
                ready = max(ready, prod + cpc["indexed_read"]["value"] * nidx)
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
                why[i] = (ready, wt, qt, cp_t + cpc["dispatch_cycles"]["value"], wun)
                wait_block[i] = max(0.0, wt - max(ready, cp_t + 1, qt))
                hol_block[i] = max(0.0, d_t - max(ready, wt, qt))
                cp_busy += dcyc + cpc["dispatch_cycles"]["value"]
                cp_t = d_t
            disp[i] = d_t
            t0 = max(d_t + (wire_of(r) if mode != "S1" else 0.0), last_end_unit[u] if u not in PIPELINED else 0.0)
            if u in PIPELINED and q:
                t0 = max(t0, q[-1] + PIPELINED[u])
            start[i] = t0
        if sdep[i] is not None:
            j = sdep[i]
            start[i] = max(start[i], start[j])
            end[i] = max(start[i] + c, end[j] + tails.get(u, 20))
        else:
            end[i] = start[i] + c
        if mode not in ("S0", "S1"):
            ret_w[u] = wire_of(r) if wires else 0.0
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
            for j in ddeps[i]:
                if disp[j] > start[i] + 1e-9:
                    races.append(dict(rec=ex[i][0], L=ex[i][1], tag=recs[ex[i][0]].tag, producer=recs[ex[j][0]].tag,
                                      early=round(disp[j] - start[i], 1),
                                      kind="I table overwritten before the dispatcher read it"))
    # per-unit busy / idle split: idle caused by true dependences vs by issue (CP, HOL, drain waits)
    per_unit = defaultdict(lambda: dict(busy=0.0, idle_true_dep=0.0, idle_issue=0.0, records=0))
    prev = defaultdict(float)
    for i, (k, L, *_) in enumerate(ex):
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
    for i, (k, L, *_) in enumerate(ex):
        fam[recs[k].family or recs[k].tag] += end[i] - start[i]
    return dict(mode=mode, total_cycles=total, records_executed=n, deps=deps, start=start, end=end, disp=disp,
                costs=costs, ex=ex, races=races, per_unit={k: {a: round(b, 1) for a, b in v.items()}
                                                           for k, v in per_unit.items()},
                why=why, cp_busy=round(cp_busy, 1), hol_block=round(sum(hol_block), 1), wait_block=round(sum(wait_block), 1),
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
        k, L, *_ = s["ex"][i]
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
    for i, (k, L, *_) in enumerate(s0["ex"]):
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


def list_schedule(recs, pos, cost_fn=cost, alpha=0.0):
    """Compiler pass: CP-aware list scheduling of a straight-line record stream (no LOOP).  Records keep every
    program-order hazard edge (RAW / WAR / WAW on region names); among the records whose predecessors are all
    issued, issue next the one that would START earliest on the modelled command processor (in-order dispatch,
    drain waits, wires, unit queues), ties to the longest remaining dataflow path.  Waits are recomputed after."""
    import copy as _c
    from .qwen_compiler import Builder
    cpc = CAL["cp"]
    dw, rw, qd = cpc["dispatch_wire"]["value"], cpc["retire_wire"]["value"], cpc["queue_depth"]["value"]
    body = [r for r in recs if not (r.unit == "CTL" and r.op == "END")]
    tail = [r for r in recs if r.unit == "CTL" and r.op == "END"]
    n = len(body)
    dyn = Dyn(pos)
    cst = [cost_fn(r, dyn, 0)[0] for r in body]
    rd = [set(getattr(r, "reads", ())) for r in body]
    wr = [set(getattr(r, "writes", ())) for r in body]
    hrd = [set(_hz(r, "reads")) for r in body]           # legality (program-order hazard edges)
    hwr = [set(_hz(r, "writes")) for r in body]
    preds = [set() for _ in range(n)]
    last_w, readers = {}, {}
    for i in range(n):
        for x in hrd[i]:
            if x in last_w:
                preds[i].add(last_w[x])
        for x in hwr[i]:
            if x in last_w:
                preds[i].add(last_w[x])
            for j in readers.get(x, ()):
                preds[i].add(j)
        for x in hwr[i]:
            last_w[x] = i
            readers[x] = []
        for x in hrd[i]:
            readers.setdefault(x, []).append(i)
        if body[i].unit == "SU" and False:
            pass
    succ = [[] for _ in range(n)]
    for i in range(n):
        for j in preds[i]:
            succ[j].append(i)
    blev = [0.0] * n
    for i in range(n - 1, -1, -1):
        blev[i] = cst[i] + max([blev[j] for j in succ[i]] + [0.0])
    npred = [len(p) for p in preds]
    ready = [i for i in range(n) if npred[i] == 0]
    b = Builder(None)
    unit_end, out_end, cp_t = {}, {}, 0.0
    qstarts = {}
    order = []
    while ready:
        best = None
        for i in ready:
            r = body[i]
            mask_units = [u for u in HGI.UNITS if u != r.unit and
                          ((rd[i] & b.pwr[u]) or (wr[i] & (b.prd[u] | b.pwr[u])))]
            wt = max([out_end.get(u, 0.0) + rw for u in mask_units] + [0.0])
            q = qstarts.get(r.unit, [])
            qt = q[-qd] if len(q) >= qd else 0.0
            d_t = max(cp_t + 1, wt, qt)
            st = max(d_t + dw, unit_end.get(r.unit, 0.0))
            key = (st - alpha * blev[i], -blev[i], i)
            if best is None or key < best[0]:
                best = (key, i, d_t, st)
        _, i, d_t, st = best
        ready.remove(i)
        r2 = _c.copy(body[i])
        b.add(r2, rd[i], wr[i])
        for a in ("implicit", "src"):
            if hasattr(body[i], a):
                setattr(r2, a, getattr(body[i], a))
        cp_t = d_t
        e = st + cst[i]
        unit_end[r2.unit] = e
        out_end[r2.unit] = max(out_end.get(r2.unit, 0.0), e)
        qstarts.setdefault(r2.unit, []).append(st)
        order.append(i)
        for j in succ[i]:
            npred[j] -= 1
            if npred[j] == 0:
                ready.append(j)
    assert len(order) == n
    for r in tail:
        r2 = _c.copy(r)
        b.add(r2, getattr(r, "reads", ()), getattr(r, "writes", ()))
        if hasattr(r, "src"):
            r2.src = r.src
    return b.recs


def _hz(r, k):
    """legality names: hz_reads / hz_writes when the caller set them (e.g. the union over per-die images), else the
    record's own region names (which also set its wait mask); plus the STREAM ids the record pushes / pops (a stream
    orders its producer before its consumer by credits, without a wait bit, but a reorder must keep that order)"""
    base = getattr(r, "hz_" + k, None)
    base = list(base if base is not None else getattr(r, k, ()))
    keys = ("O", "R") if k == "writes" else ("A", "B", "C", "D")
    return base + [f"~STREAM{d.base}" for kk, d in r.desc.items() if kk in keys and d.space == "STREAM"]


def _hazard(a, b):
    """Region-name hazard between two records (RAW / WAR / WAW); CTL records other than NOP are barriers."""
    if (a.unit == "CTL" and a.op != "NOP") or (b.unit == "CTL" and b.op != "NOP"):
        return True
    ra, wa = set(_hz(a, "reads")), set(_hz(a, "writes"))
    rb, wb = set(_hz(b, "reads")), set(_hz(b, "writes"))
    return bool(wa & (rb | wb)) or bool(ra & wb)


def asap_seed(recs):
    """A restart point: each record (in program order) placed directly after the last earlier record it has a hazard
    with (CTL barriers stay), so every producer -> consumer chain starts at its earliest legal slot."""
    out = []
    for r in recs:
        p = len(out)
        while p > 0 and not _hazard(out[p - 1], r):
            p -= 1
        out.insert(p, r)
    return out


def improve_order(recs, pos, cost_fn=cost, rounds=6, seeds=("given", "asap"), ils=True, **kw):
    """The compiler's CP-aware order: improve_order_seed from each seed (the given order; the ASAP re-seed), the
    cheaper kept; then one iterated-local-search sweep (each record relocated to its ASAP slot, a short re-search,
    kept when the objective drops) to leave the local optimum."""
    for i, r in enumerate(recs):                 # ids of the INPUT order (the caller maps the permutation by them)
        r._cid = i
    best = None
    for sd in seeds:
        start = list(recs) if sd == "given" else asap_seed(list(recs))
        o, info = improve_order_seed(start, pos, cost_fn=cost_fn, rounds=rounds, **kw)
        info = dict(info, seed=sd)
        if best is None or info["output_cycles"] < best[1]["output_cycles"] - 0.5:
            best = (o, info)
    order, info = best
    if ils:
        bt, moved = info["output_cycles"], 0
        cf = info.pop("_cf")
        idx = 0
        while idx < len(order):
            r = order[idx]
            p = idx
            if not (r.unit == "CTL" and r.op != "NOP"):
                while p > 0 and not _hazard(order[p - 1], r):
                    p -= 1
            if p < idx:
                o = order[:p] + [r] + order[p:idx] + order[idx + 1:]
                o2, i2 = improve_order_once(o, pos, cost_fn=cf, passes=2, alphas=(), **kw)
                if i2["output_cycles"] < bt - 0.5:
                    order, bt, moved = [x for x in o2], i2["output_cycles"], moved + 1
            idx += 1
        info = dict(info, ils_moves=moved, output_cycles=bt)
        order = rebuild_waits(order)
    info.pop("_cf", None)
    return order, info


def improve_order_seed(recs, pos, cost_fn=cost, rounds=6, **kw):
    """improve_order_once repeated on its own output until a round gains < 1 cycle (the list schedules restart from
    the improved order, so a later round can escape the previous round's local optimum)."""
    out, info = improve_order_once(recs, pos, cost_fn=cost_fn, **kw)
    first = info["input_cycles"]
    hist = [info["output_cycles"]]
    for _ in range(rounds - 1):
        o2, i2 = improve_order_once(out, pos, cost_fn=cost_fn, **kw)
        if i2["output_cycles"] > hist[-1] - 1.0:
            break
        out, info = o2, i2
        hist.append(i2["output_cycles"])
    info = dict(info, input_cycles=first, rounds=hist, _cf=info.get("_cf"))
    return out, info


def improve_order_once(recs, pos, cost_fn=cost, passes=16, alphas=(0.05, 0.2, 1.0), exhaustive=False, steady=True):
    """Compiler pass after list scheduling: CP-aware local search on a straight-line record stream.

    Start from the best list schedule over `alphas`, then repeatedly try to hoist each record to the earliest slot it
    may legally occupy (just after the last earlier record it has a region hazard with) or to just after its unit's
    previous record; keep a move when the modelled S2 time of the stream (waits recomputed) drops.  A hoist is the
    fix for a drain over-wait: a consumer placed right behind its producer drains that unit before the next,
    independent record of the unit is dispatched.  Only hazard-free moves are made, so the results are unchanged
    (and the race check of `schedule` re-verifies every dependence on exact address intervals).
    Returns (records with waits rebuilt, dict of the search)."""
    memo = {}

    def cf(r, dyn, L):
        k = getattr(r, "_cid", None)
        if k is None:
            return cost_fn(r, dyn, L)
        if (k, L) not in memo:
            memo[(k, L)] = cost_fn(r, dyn, L)
        return memo[(k, L)]
    base = [r for r in recs]
    for i, r in enumerate(base):
        if getattr(r, "_cid", None) is None:
            r._cid = i

    import copy as _cp

    def total(order):
        """steady: the cost of the stream run twice back to back (a layer followed by the next layer of its type),
        so an order that overlaps its tail with the next layer's head is preferred; else one copy"""
        seq = order + [_cp.copy(x) for x in order] if steady else order
        return schedule(rebuild_waits(seq), pos, "S2", cost_fn=cf)["total_cycles"]
    t_in = total(base)
    best, bt, ba = base, t_in, None
    for a in alphas:
        o = [x for x in list_schedule(rebuild_waits(base), pos, cost_fn=cf, alpha=a)]
        t = total(o)
        if t < bt:
            best, bt, ba = o, t, a
    order = list(best)
    moves = 0
    for _ in range(passes):
        improved = False
        i = 1
        while i < len(order):
            r = order[i]
            if r.unit == "CTL" and r.op != "NOP":
                i += 1
                continue
            e = i
            while e > 0 and not _hazard(order[e - 1], r):
                e -= 1
            cands = set(range(e, i)) if exhaustive else {e}
            for j in range(i - 1, e - 1, -1):
                if order[j].unit == r.unit:
                    cands.add(j + 1)
                    break
            done = False
            for p in sorted(cands):
                if p >= i:
                    continue
                o2 = order[:p] + [r] + order[p:i] + order[i + 1:]
                t2 = total(o2)
                if t2 < bt - 0.5:
                    order, bt, moves, improved, done = o2, t2, moves + 1, True, True
                    break
            i += 1
        if not improved:
            break
    return rebuild_waits(order), dict(input_cycles=round(t_in, 1), list_alpha=ba, moves=moves,
                                      output_cycles=round(bt, 1), _cf=cf)
