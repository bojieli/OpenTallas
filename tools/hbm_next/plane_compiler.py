#!/usr/bin/env python3
"""HBM-NEXT-CMTP: the P-lane record compiler for the next HBM die (P = 4), on the D1 compiler / price chain.

Fork, not edit: tools/hgi_sim (d4g compiler ds_mtp_verify / ds_mtp_draft / hbm_plane_model, the D1 model) is used
UNCHANGED; this module wraps its record compile (V.compile_verify, called by the verify, the DSpark draft bodies and the
SEED) with the P = 4 rules below, and runs the re-time.  Every rule is opt-in (Knobs); with every knob at the D1
value the wrapper is the identity, which the re-time checks against the D1 / STUDY records (validation rows).

P = 4 RULES (results/arch/hbm_next_1019/cmtp/isa_rows.md, HGI-1R):
  rpl   SM remainder pass (R5): an N-row SM record on P lanes costs max(1, issues / 1.374) of the AR record, issues =
        isa_rows.best_rpl(N, P, nc, rows per SM) (idle / K-split / row-split, the cheapest; D1: ceil(N / P)).  nc = the
        record's csum chunk count (K / 32 / 8 block-dot, K / 8 BF16), rows per SM = ceil(B.m / 16).
  union MoE union grouped GEMM: a union expert with c_u routed rows costs max(1, issues(c_u) / 1.374), averaged over the
        MEASURED lane histogram (MTP-STATS: verify N = 6 decorrelated estimate; users: independent mixed workloads);
        D1: the mean P_e = 6 N / U, ceil(ceil(P_e) / P).  Draft bodies (no histogram): P_e as D1, with rpl.
  m1    x-load beats + lane-major publish (D2 model gap M1): an SM record over N rows loads N x-slots (2,048-b xw beat:
        ceil(K esz / 256) beats a row) and publishes N result rows on the unchanged result port (8 FP32 words a beat a
        SM: ceil(rows per SM / 8) beats a row).  Charged EXPOSED (no overlap credit): (N - 1) x the x beats once per
        distinct x in a layer segment (the x-slot store keeps it for the other records) + (N - 1) x the publish beats
        on every SM record.  PRICED estimate, labelled.
  coll  COLL delivery lanes L (STUDY (a): L = 5 adopted, the widest the SerDes feeds; D1 4).
  hc    HC further-row II: MEASURED 250.0 (HBM-NEXT-UNITS tb_hnx_hc_eng4, hnx RTL root + 4 ring quarters, Verilator
        5.050, bit-exact N = 1, 2, 3, 4, 6, 8: HC_MIX 998 + 250 (N - 1); results/arch/hbm_next_1019/units/hc/README.md).
        It replaces both the priced HCP x6 II (250, D1) and the stale measured static-engine II (4,385, codex 128-lane
        engine the die does not bind) in the d4g row_ii; 600 / 950 kept as sensitivities only.
  vm    VM-resident N columns (D1 / VM grown) or as-built column swaps (STUDY (b)).

    PYTHONPATH=tools python3 tools/hbm_next/plane_compiler.py retime --out DIR [--jobs N]   (fleet: ~20-40 min)
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import datetime
import hashlib
import json
import math
import multiprocessing as mp
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "hbm_next"))

import isa_rows as IR  # noqa: E402

NSM = 16                         # SMs a die (d4g; hbm_plane_model.NSM)
XW_BYTES = 256                   # 2,048-b x-write beat
RES_WORDS = 8                    # result port: 8 FP32 words a beat a SM (271-b window)
STATS = ROOT / "results/arch/hbm_mtp_next_1018/stats/summary.json"


@dataclasses.dataclass(frozen=True)
class Knobs:
    rpl: bool = False            # SM remainder-pass layouts (D1: ceil(N / P) passes)
    union_hist: bool = False     # measured lane histogram for the union experts (D1: mean P_e)
    m1: bool = False             # x-load + publish beats (D1: not priced)
    coll_lanes: int = 4          # D1 4, STUDY 5
    hc_ii: float = 250.0         # MEASURED (UNITS tb_hnx_hc_eng4, 250.0 cycles a further row); D1 priced the same 250
    vm_grown: bool = True        # D1: N columns VM-resident (grown VM); False = as-built column swaps
    # SM area options (step 2, SM4 lever table; defaults = the P = 4 headline, identity on every earlier case)
    P: int = 4                   # accumulator lanes a MAC column (= MTP / users lanes); P3a: 3
    bf16_lanes: int = 0          # lanes on the BF16 column (0 = P; option (b): 1 -> BF16 SM.MATVEC records (fmt 0) and
    #                              the SM attention (option B, on the BF16 column per ATT4 geometry) get 1 lane)
    meas: tuple = ()             # step 4: MEASURED unit row IIs flipped in (MEAS keys; () = the priced headline)
    att_single: str = "record"   # with 1 attention lane: "record" = each position / user its own single-query
    #                              record (the as-built d4g engine: N x the full measured span); "rows" = one row
    #                              record with the fixed spans once (optimistic sensitivity)

    def tag(self):
        return (f"rpl{int(self.rpl)}_uh{int(self.union_hist)}_m1{int(self.m1)}_L{self.coll_lanes}_hc{int(self.hc_ii)}"
                f"_vm{'G' if self.vm_grown else 'S'}_P{self.P}_bf{self.bf16_lanes or self.P}"
                + (f"_meas-{'-'.join(self.meas)}" if self.meas else ""))

    @property
    def att_lanes(self):
        return self.bf16_lanes or self.P


D1 = Knobs()
CUR = dict(knobs=D1, mode=None, hist=None)          # the job's knobs and histogram (set before the pool forks)
LOG = []


def lane_hists():
    d = json.loads(STATS.read_text())["deepseek_moe_union"]
    v = d["consecutive_verify"]["6"]["estimate_decorrelated"]["lane_hist_frac"]
    u = {int(k): x["lane_hist_frac"] for k, x in d["independent_users_mixed"].items() if isinstance(x, dict)
         and "lane_hist_frac" in x}
    return dict(verify6={int(k): float(x) for k, x in v.items()},
                users={n: {int(k): float(x) for k, x in h.items()} for n, h in u.items()},
                sha256=hashlib.sha256(STATS.read_bytes()).hexdigest())


def sm_issue_factor(N, lanes, nc, rows_sm, rpl):
    """max(1, issues / 1.374) of an N-row SM record on `lanes` lanes"""
    if N <= 1:
        return 1.0
    if rpl:
        issues = IR.best_rpl(N, lanes, nc, rows_sm)[1]
    else:
        issues = math.ceil(N / lanes)
    return max(1.0, issues / IR.HBM_LINE_RATIO)


def _sm_shape(c):
    a, b = c.desc["A"], c.desc["B"]
    K = int(a.n)
    fmt = c.param & 3
    nc = IR.csum_chunks(K, fmt)
    rows_sm = max(1, math.ceil(int(b.m) / NSM))
    esz = 1 if fmt in (1, 2) else 2
    return K, fmt, nc, rows_sm, esz


def post_sm(out, N, lanes, union, topk, kn: Knobs, hist):
    """re-price the SM records of a compile_verify programme under the P = 4 rules; returns notes"""
    from hgi_sim import ds_mtp_verify as V
    notes = dict(sm_shared=0, sm_expert=0, x_loads=0, m1_cycles=0.0, rpl_saved=0.0)
    if N <= 1 or lanes is None:
        return notes
    U = max(topk, int(round(union))) if union else topk * N
    pe = topk * N / U
    seen_x, seg = set(), None
    for c in out:
        if getattr(c, "orig_op", "") != "SM.MATVEC" or c.mtp_kind not in ("shared", "expert") or c.npos <= 1:
            continue
        key = c.layer if isinstance(c.layer, int) and c.layer < 40 else "head"
        if key != seg:
            seen_x, seg = set(), key
        K, fmt, nc, rows_sm, esz = _sm_shape(c)
        rl = kn.bf16_lanes if (fmt == 0 and kn.bf16_lanes) else lanes      # this record's lanes (option (b))
        if rl != lanes:
            notes["bf16_1lane"] = notes.get("bf16_1lane", 0) + 1
        if c.mtp_kind == "shared":
            f_d1 = max(1.0, math.ceil(N / lanes) / V.HBM_RATIO)
            base = c.base_cost / f_d1
            f = sm_issue_factor(N, rl, nc, rows_sm, kn.rpl)
            nrow = N
            notes["sm_shared"] += 1
        else:
            f_d1 = max(1.0, math.ceil(math.ceil(pe) / lanes) / V.HBM_RATIO)
            base = c.base_cost / f_d1
            if kn.union_hist and hist:
                f = sum(fr * sm_issue_factor(h, rl, nc, rows_sm, kn.rpl) for h, fr in hist.items())
                nrow = sum(fr * h for h, fr in hist.items())
            else:
                f = sm_issue_factor(math.ceil(pe), rl, nc, rows_sm, kn.rpl)
                nrow = pe
            notes["sm_expert"] += 1
        new = base * f
        if kn.m1:
            extra = (nrow - 1) * math.ceil(rows_sm / RES_WORDS)
            xk = (c.desc["A"].base, K)
            if xk not in seen_x:
                seen_x.add(xk)
                extra += (N - 1) * math.ceil(K * esz / XW_BYTES)
                notes["x_loads"] += 1
            notes["m1_cycles"] += extra
            new += extra
        notes["rpl_saved"] += c.base_cost - base * f
        c.base_cost = new
        c.cmtp = dict(f_d1=round(f_d1, 4), f=round(f, 4), nc=nc, rows_sm=rows_sm)
    notes["m1_cycles"] = round(notes["m1_cycles"], 1)
    notes["rpl_saved"] = round(notes["rpl_saved"], 1)
    return notes


def att_single(out, bmodel, kn: Knobs):
    """option (b) with att_single "record": an SM attention row record on ONE lane is N single-query records of the
    full measured span (the draft bodies; the verify / users records are re-priced in post_pass with the KV ratio)"""
    if kn.att_lanes != 1 or kn.att_single != "record" or not bmodel:
        return 0
    n = 0
    for c in out:
        m = re.match(r"att_B(\d+)_rows$", getattr(c, "mtp_kind", ""))
        if m and c.npos > 1:
            c.base_cost = c.npos * float(bmodel[m.group(1)][c.orig_op.split(".")[1].lower()])
            n += 1
    return n


# ---- step 4: MEASURED unit row IIs (HBM-NEXT-UNITS / ATT4 / SM4 benches, Verilator 5.050, all bit-exact) -------------
# Each key replaces one PRICED row II of the d4g row_ii (ds_mtp_verify.row_ii) by the measured one; the single-row
# cost c1 is kept (AR unchanged) unless the key says otherwise.  Sources (claude/hbm-next-1019 sub-lanes):
MEAS = {
    "idx_index": "IDX.INDEX further row = c1 x 953 / 658.9 (UNITS-IDX units/idx/README.md: measured 953 a row of the "
                 "1,397-cycle d4g frame vs the priced 152 of 658.9; the key stream is re-read a row, selector top-512 "
                 "binds); users: the same (no shared stream either way)",
    "idx_index_abs": "IDX.INDEX further row = 953 absolute (sensitivity: the measured row at the bench shape, not "
                     "scaled to the record's c1)",
    "idx_topk": "IDX.TOPK further row 49.2 (UNITS-IDX topk, priced 47.0)",
    "idx_union": "IDX.UNION record (the expert_union record, priced as a TOPK c1) = measured cycles(N) 48 / 67 / 90 / "
                 "101 / 142 at N = 1 / 2 / 3 / 4 / 6 (UNITS-IDX union; N = 5 interpolated)",
    "su_vop": "SU.VOP N-row (the un-indexed 'shared' SU records: norms, gates, residual ops) further row = (2k + 1) "
              "ceil(e / 512) + 2, k = per-row VM read operands (operands some record writes; constants broadcast), "
              "e = A elements a row (UNITS-SUDMA su_vop: AB 44 / ABC 72 at n 7,168, single store write port); the "
              "indexed route gather stays at its measured II 1 (= price)",
    "kvwb": "DMA.KVWB_DS further row 8 (+28 a ring wrap, amortised (N - 1) / 256 a record) (UNITS-SUDMA kvwb; priced 2)",
    "argmax": "ARGMAX.LOCAL further row 169 (UNITS-SUDMA argmax; priced 6)",
    "coll_rg": "COLL.ROW_GATHER further row = priced II x 623 / 1,449 (UNITS-COLL rows: measured II = R = 623 flits a "
               "rail at the DS verify shape where the model priced 1,449; payload-proportional for the other shapes)",
    "coll_am": "COLL.ARGMAX_MERGE further row 32 (UNITS-COLL rows; model 12.7)",
    "att4": "ATT PV row records: shared 4-lane merge PV span -40 cycles a pass (ATT4 a1: shared 385 / 529 / 745 / 1,089 "
            "vs base 401 / 569 / 785 / 1,129 at sigma 0 / 0.3 / 1 / disjoint; -40 at every overlap but full)",
    "sm4skew": "SM4 lane-major publish skew: +8 cycles a further lane a pass on every N-row SM.MATVEC record (hnx_rp4lp4 "
               "LSKEW 8; +24 a 4-lane pass); union experts by the measured lane histogram (1-lane experts: 0)",
}
MEAS_ALL = ("idx_index", "idx_topk", "idx_union", "su_vop", "kvwb", "argmax", "coll_rg", "coll_am", "att4", "sm4skew")
# step 5 (10-19 03:40): the redesigned units' MEASURED row IIs (claude/hbm-next-1019 @5bf6d2d50 / @a42351330 / @e70d3285a)
MEAS.update({
    "idxn": "IDX.INDEX further row = c1 x 232 / 658.9 (UNITS-IDXN units/idxn/README.md: key pass once a record, K = 8 "
            "row streams, 4 time-shared selectors; MEASURED 1,297 + 232 (N - 1), bit-exact N = 1..6; replaces idx_index)",
    "idx_frame": "IDX.INDEX first row c1 x 1,297 / 658.9 on EVERY record incl. AR (IDXN measured frame; the d4g frame "
                 "the release AR model prices at 658.9 measures 1,397) -- frame sensitivity, moves AR",
    "su_vop2": "SU.VOP N-row further row = 2 k ceil(e / 512) (k >= 1; k = 0: ceil(e / 512)) (UNITS-SUDMA2 units/sudma2: "
               "write-port split, AB 28 / ABC 56 at e = 7,168; replaces su_vop)",
    "argmax2": "ARGMAX.LOCAL further row 22 (UNITS-SUDMA2 wide ARGMAX ot_hnx_argmax_wide_rows; replaces argmax 169)",
    "fused": "FUSED.HC_PRE_NORM further row 81 (priced 160) and FUSED.HC_POST 103 (priced 100), KX = 4, rgap 0 "
             "(UNITS-FUSED units/fused/README.md, bit-exact N = 1/2/3/4/6)",
    "fused_frame": "FUSED.HC_PRE_NORM / HC_POST first row = MEASURED c1 404 / 196 (absolute, D 5,120) on every record "
                   "incl. AR -- frame sensitivity, moves AR",
})
MEAS_ALL2 = ("idxn", "idx_topk", "idx_union", "su_vop2", "kvwb", "argmax2", "coll_rg", "coll_am", "att4", "sm4skew",
             "fused")
IDXN_C1, IDXN_II = 1297.0, 232.0
FUSED_MEAS = {"FUSED.HC_PRE_NORM": (404.0, 81.0), "FUSED.HC_POST": (196.0, 103.0)}
IDX_II_MEAS, IDX_FRAME_PRICE = 953.0, 658.9
MODE5 = [False]
UNION_MEAS = {1: 48.0, 2: 67.0, 3: 90.0, 4: 101.0, 6: 142.0}
ROW_GATHER_MEAS, ROW_GATHER_PRICE = 623.0, 1449.0
LSKEW = 8.0


def union_cycles(n):
    if n in UNION_MEAS:
        return UNION_MEAS[n]
    ks = sorted(UNION_MEAS)
    lo = max(k for k in ks if k < n) if n > ks[0] else ks[0]
    hi = min((k for k in ks if k > n), default=ks[-1])
    if hi == lo:
        return UNION_MEAS[lo] + 18.6 * (n - lo)
    return UNION_MEAS[lo] + (UNION_MEAS[hi] - UNION_MEAS[lo]) * (n - lo) / (hi - lo)


def _written_vm(out):
    """copy-0 VM write intervals of a compiled programme (what some record produces; the rest are constants)"""
    from hgi_sim import ds_mtp_verify as V
    w = []
    for c in out:
        for iv in getattr(c, "fp", ([], []))[1]:
            if iv[0] == "VM" and iv[1] < V.VM_OFF:
                w.append((iv[1], iv[2]))
    w.sort()
    merged = []
    for a, b in w:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def _overlaps(merged, a, b):
    import bisect
    i = bisect.bisect_right([m[0] for m in merged], b - 1) - 1
    return i >= 0 and merged[i][1] > a


def su_meas_ii(r, written, dyn, wsplit=False):
    from hgi_sim import timing as T
    L = r.layer if isinstance(r.layer, int) else 0
    k = 0
    for opk in ("A", "B", "C", "D"):
        d = r.desc.get(opk)
        if d is None or d.space != "VM":
            continue
        if any(_overlaps(written, lo, hi) for sp, lo, hi in T.intervals(d, dyn, L) if sp == "VM"):
            k += 1
    _, n, m, _, _ = T.eff(r.desc["A"], dyn, L)
    e = n * max(1, m)
    if wsplit:
        return max(1, 2 * k) * math.ceil(e / 512), k, e
    return (2 * k + 1) * math.ceil(e / 512) + 2, k, e


def apply_meas(out, N, kn: Knobs, hist, lanes, pe=1.0):
    """re-cost the compiled records with the measured row IIs selected in kn.meas (compile_verify wrapper: every
    programme -- verify, users, draft bodies, seed).  ATT and IDX.INDEX are re-applied after post_pass (meas_post)."""
    from hgi_sim import ds_mtp_verify as V
    from hgi_sim import ds_native_timing as DT
    from hgi_sim import timing as T
    ms = set(kn.meas)
    notes = {}
    if not ms or N <= 1:
        return notes
    dyn = T.Dyn(DT.POS)
    written = _written_vm(out) if ("su_vop" in ms or "su_vop2" in ms) else None

    def add(key, d):
        notes[key] = round(notes.get(key, 0.0) + d, 1)
    for c in out:
        op, kind, npos = getattr(c, "orig_op", ""), getattr(c, "mtp_kind", ""), getattr(c, "npos", 1)
        if npos <= 1:
            continue
        old = c.base_cost
        if kind == "rows" and getattr(c, "ii", None) is not None:
            if op == "IDX.TOPK" and "idx_topk" in ms:
                c.base_cost = c.c1 + (npos - 1) * 49.2
            elif op == "DMA.KVWB_DS" and "kvwb" in ms:
                c.base_cost = c.c1 + (npos - 1) * 8.0 + 28.0 * (npos - 1) / 256.0
            elif op == "ARGMAX.LOCAL" and "argmax2" in ms:
                c.base_cost = c.c1 + (npos - 1) * 22.0
            elif op == "ARGMAX.LOCAL" and "argmax" in ms:
                c.base_cost = c.c1 + (npos - 1) * 169.0
            elif op in FUSED_MEAS and "fused" in ms:
                c.base_cost = c.c1 + (npos - 1) * FUSED_MEAS[op][1]
            elif op == "COLL.ROW_GATHER" and "coll_rg" in ms:
                c.base_cost = c.c1 + (npos - 1) * c.ii * ROW_GATHER_MEAS / ROW_GATHER_PRICE
            elif op == "COLL.ARGMAX_MERGE" and "coll_am" in ms:
                c.base_cost = c.c1 + (npos - 1) * 32.0
        elif kind == "expert_union" and "idx_union" in ms:
            c.base_cost = union_cycles(npos)
        elif kind == "shared" and op == "SU.VOP" and ("su_vop" in ms or "su_vop2" in ms) and "I" not in c.desc:
            L = c.layer if isinstance(c.layer, int) else 0
            r2 = copy.copy(c)
            r2.desc = {k: copy.copy(v) for k, v in c.desc.items()}
            for v in r2.desc.values():
                v.m = v.m * npos
            c1 = c.base_cost * T.su_cost(c, dyn, L)[0] / T.su_cost(r2, dyn, L)[0]
            ii, k, e = su_meas_ii(c, written, dyn, wsplit="su_vop2" in ms)
            c.base_cost = c1 + (npos - 1) * ii
            c.cmtp_su = dict(c1=round(c1, 1), ii=ii, k=k, e=e)
        elif op == "SM.MATVEC" and kind in ("shared", "expert") and "sm4skew" in ms:
            def skew(h):
                return LSKEW * (min(h, lanes) - 1) * math.ceil(h / lanes)
            if kind == "shared":
                c.base_cost += skew(npos)
            elif hist:
                c.base_cost += sum(fr * skew(h) for h, fr in hist.items())
            else:
                c.base_cost += skew(max(1, math.ceil(pe)))
        if c.base_cost != old:
            add(op + ("" if kind == "rows" else f" {kind}"), c.base_cost - old)
    return notes


def apply_frames(out, kn: Knobs):
    """step 5 frame sensitivities (every programme incl. the AR token): the MEASURED first-row cost c1 of IDX.INDEX
    (x 1,297 / 658.9, scaled like the row II) and FUSED.HC_PRE_NORM / HC_POST (404 / 196 absolute).  Row records keep
    their further rows ((npos - 1) x II, re-applied by apply_meas / meas_post from the new c1)."""
    ms = set(kn.meas)
    notes = {}
    if not ({"idx_frame", "fused_frame"} & ms):
        return notes
    for c in out:
        op = getattr(c, "orig_op", "")
        rows = getattr(c, "ii", None) is not None
        c1 = c.c1 if rows else c.base_cost
        if op == "IDX.INDEX" and "idx_frame" in ms:
            n1 = c1 * IDXN_C1 / IDX_FRAME_PRICE
        elif op in FUSED_MEAS and "fused_frame" in ms:
            n1 = FUSED_MEAS[op][0]
        else:
            continue
        d = n1 - c1
        if rows:
            c.c1 = n1
        c.base_cost += d
        notes[op] = round(notes.get(op, 0.0) + d, 1)
    return notes


def meas_post(prog, N, kn: Knobs, lanes):
    """after M.post_pass (it re-costs ATT rows and the users' IDX.INDEX): ATT4 shared merge, measured IDX.INDEX"""
    ms = set(kn.meas)
    notes = {}
    if not ms or N <= 1:
        return notes
    for r in prog:
        k = getattr(r, "mtp_kind", "")
        old = r.base_cost
        if "att4" in ms and k.startswith("att_B") and k.endswith("_rows") and r.orig_op == "ATT.PV":
            r.base_cost = max(1.0, r.base_cost - 40.0 * math.ceil(N / lanes))
        elif getattr(r, "ii", None) is not None and r.orig_op == "IDX.INDEX" and (
                "idx_index" in ms or "idx_index_abs" in ms or "idxn" in ms):
            if "idxn" in ms:      # r.c1 is the priced frame (or the measured one under idx_frame: undo that scale)
                c1p = r.c1 / (IDXN_C1 / IDX_FRAME_PRICE) if "idx_frame" in ms else r.c1
                ii = c1p * IDXN_II / IDX_FRAME_PRICE
            else:
                ii = IDX_II_MEAS if "idx_index_abs" in ms else r.c1 * IDX_II_MEAS / IDX_FRAME_PRICE
            r.base_cost = max(r.base_cost, r.c1 + (N - 1) * ii)
        if r.base_cost != old:
            notes[r.orig_op] = round(notes.get(r.orig_op, 0.0) + r.base_cost - old, 1)
    return notes


def install():
    """wrap V.compile_verify (verify, draft bodies, seed) and M.ds_compile (to know verify / users)"""
    from hgi_sim import ds_mtp_verify as V
    from hgi_sim import hbm_plane_model as M
    if getattr(V.compile_verify, "_cmtp", False):
        return
    orig_cv, orig_dc = V.compile_verify, M.ds_compile

    def compile_verify(recs, cf, P, **kw):
        out, st = orig_cv(recs, cf, P, **kw)
        kn = CUR["knobs"]
        fr = apply_frames(out, kn)
        if fr:
            st = dict(st, cmtp_frames=fr)
        if kw.get("sm_mode") == "slots" and P > 1:
            mode = CUR.get("mode")
            hist = None
            if mode == "verify" and P == 6:
                hist = CUR["hist"]["verify6"]
            elif mode == "users":
                hist = CUR["hist"]["users"].get(P)
            nt = post_sm(out, P, kw.get("sm_k"), kw.get("union"), kw.get("topk", 6), kn, hist)
            nt["att_single_records"] = att_single(out, kw.get("bmodel"), kn)
            tk = kw.get("topk", 6)
            U_ = max(tk, int(round(kw["union"]))) if kw.get("union") else tk * P
            nt["meas"] = apply_meas(out, P, kn, hist, kw.get("sm_k") or kn.P, pe=kw.get("topk", 6) * P / U_)
            st = dict(st, cmtp=nt)
        return out, st
    compile_verify._cmtp = True

    orig_pp = M.post_pass

    def post_pass(prog, N, P, kv, users, bex, bcomp):
        kn = CUR["knobs"]
        nt = orig_pp(prog, N, kn.att_lanes, kv, users, bex, bcomp)     # attention passes on the ATT lanes
        if kn.att_lanes == 1 and kn.att_single == "record" and N > 1:
            n = 0
            for r in prog:
                k = getattr(r, "mtp_kind", "")
                m = re.match(r"att_B(\d+)_rows$", k)
                if m:
                    T_ = int(m.group(1))
                    op = r.orig_op.split(".")[1].lower()
                    full, comp = float(bex[str(T_)][op]), float(bcomp[str(T_)][op])
                    r.base_cost = N * ((full - comp) + comp * M.kv_union_ratio(T_, 1, kv, users))
                    n += 1
            nt["att_single_record_rows"] = n
        nt["att_lanes"] = kn.att_lanes
        nt["meas_post"] = meas_post(prog, N, kn, kn.att_lanes)
        return nt
    post_pass._cmtp = True
    M.post_pass = post_pass

    orig_pc = M.plane_cfg

    def plane_cfg(P, rows_on=True, swap=None):
        cfg = orig_pc(P, rows_on, swap)
        if P > 1 and cfg.get("att_k"):
            cfg["att_k"] = CUR["knobs"].att_lanes
        return cfg
    M.plane_cfg = plane_cfg

    def ds_compile(N, cfg, union, kv="upper", users=False):
        prev = CUR.get("mode")
        CUR["mode"] = "users" if users else "verify"
        try:
            return orig_dc(N, cfg, union, kv, users)
        finally:
            CUR["mode"] = prev
    V.compile_verify = compile_verify
    M.ds_compile = ds_compile


def apply_knobs(kn: Knobs):
    """set the module-level knobs BEFORE the pool forks (fork context: children inherit; the fleet's Python 3.14
    default forkserver would drop them -- STUDY's process-pool bug)"""
    from hgi_sim import hbm_plane_model as M
    from hgi_sim import plan_study_price_1017 as PS
    from hgi_sim import ds_mtp_verify as V
    M.d4g_env()
    PS.VARIANTS["b"]["split"]["lanes"] = kn.coll_lanes
    M._ENV["kn"]["lanes"] = kn.coll_lanes
    M._ENV["vb"] = PS.VARIANTS["b"]
    V.HCP_II = float(kn.hc_ii)
    V.HC_STATIC_II = float(kn.hc_ii)     # the measured basis of row_ii HC = the bound hnx engine (not the 4,385 engine)
    CUR["knobs"] = kn
    install()


def users_union(uu, n):
    """mean union of n independent users' top-6 (MTP-STATS has n = 2, 4, 6, 8; odd n linearly interpolated, labelled)"""
    if n in uu:
        return uu[n]
    lo, hi = max(k for k in uu if k < n), min(k for k in uu if k > n)
    return uu[lo] + (uu[hi] - uu[lo]) * (n - lo) / (hi - lo)


def case_jobs(st, P=4, kn: Knobs = D1, mu_n=None):
    u6, uu = st["verify_union"][6]["mean"], st["users_union"]
    sw = None if kn.vm_grown else True
    mu_n = mu_n or P
    return [("ds", "AR", "verify", dict(P=1, N=1)),
            ("ds", "MTP", "verify", dict(P=P, N=6, union=u6, kv="upper", swap=sw)),
            ("ds", "draft", "draft", dict(P=P, overlap=True, union=u6)),
            ("ds", "MU", "verify", dict(P=P, N=mu_n, union=users_union(uu, mu_n), users=True, swap=sw))]


def _job(job):
    from hgi_sim import hbm_plane_model as M
    name, res = M._any(job)
    return name, res


def run_case(kn: Knobs, st, jobs_n, P=None, mu_n=None):
    from hgi_sim import hbm_plane_model as M
    P = P or kn.P
    mu_n = mu_n or P
    apply_knobs(kn)
    with mp.get_context("fork").Pool(jobs_n) as pool:
        res = dict(pool.imap_unordered(_job, case_jobs(st, P, kn, mu_n), chunksize=1))
    mh = M._mh_ctl()
    ar = res["AR"]["cycles"]
    d = res["draft"]
    v = res["MTP"]["cycles"]
    step = v + d["draft_cycles"] + d["seed_cycles"] + mh - d["overlap"]["credit"]
    mu = res["MU"]["cycles"]
    return dict(knobs=dataclasses.asdict(kn), ar_cycles=ar, ar_tok_s=round(M.CLK / ar, 1),
                mtp=dict(verify_cycles=v, draft_cycles=d["draft_cycles"], draft_by_kind=d["draft_by_kind"],
                         seed_cycles=d["seed_cycles"], mh_ctl_cycles=round(mh, 1),
                         overlap_credit=d["overlap"]["credit"], step_cycles=round(step, 1),
                         tok_s=round(M.TAU * M.CLK / step, 1), unit_busy=res["MTP"]["unit_busy"],
                         compile=res["MTP"].get("compile")),
                mu=dict(users=mu_n, step_cycles=mu, per_user_tok_s=round(M.CLK / mu, 1),
                        agg_tok_s=round(mu_n * M.CLK / mu, 1),
                        unit_busy=res["MU"]["unit_busy"], compile=res["MU"].get("compile")))


CASES = [
    ("D1 reproduction (L 4, D1 SM rule)", D1),
    ("STUDY L5 reproduction", Knobs(coll_lanes=5)),
    ("+ union histogram", Knobs(coll_lanes=5, union_hist=True)),
    ("+ M1 x-load / publish (cost)", Knobs(coll_lanes=5, union_hist=True, m1=True)),
    ("CMTP P4 headline: + rpl (K-/row-split), HC II 250 MEASURED", Knobs(coll_lanes=5, union_hist=True, m1=True, rpl=True)),
    ("headline, HC II 600 (sensitivity; old UNITS target)", Knobs(coll_lanes=5, union_hist=True, m1=True, rpl=True, hc_ii=600)),
    ("headline, HC II 950 (sensitivity; old UNITS gate)", Knobs(coll_lanes=5, union_hist=True, m1=True, rpl=True, hc_ii=950)),
    ("headline, VM as built (column swaps)", Knobs(coll_lanes=5, union_hist=True, m1=True, rpl=True, vm_grown=False)),
]


def retime(a):
    from hgi_sim import hbm_plane_model as M
    st = M.load_stats(STATS)
    CUR["hist"] = lane_hists()
    out = dict(schema="opentallas.hbm_next_1019.cmtp.retime.v1", generated_utc=datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), rule=__doc__, P=4, targets=dict(
        ds_ar=1905.4, ds_mtp=3363.5, mu_agg=4365.3, mu_per_user_floor=1000.0),
        study_refs=dict(D1_P4=dict(mtp=3363.5, mu_agg=4365.3, per_user=1091.3, ar=1905.4),
                        STUDY_L5_P4=dict(mtp=3459.9, mu_agg=4481.6, per_user=1120.4, ar=1949.7)),
        hist=CUR["hist"], cases={})
    sel = [c for c in CASES if not a.only or any(s in c[0] for s in a.only.split(","))]
    for name, kn in sel:
        r = run_case(kn, st, a.jobs)
        out["cases"][name] = r
        print(f"{name:45s} AR {r['ar_tok_s']:7.1f}  MTP {r['mtp']['tok_s']:7.1f} (verify {r['mtp']['verify_cycles']:.0f}"
              f", draft {r['mtp']['draft_cycles']:.0f})  MU agg {r['mu']['agg_tok_s']:7.1f} / user "
              f"{r['mu']['per_user_tok_s']:7.1f}", flush=True)
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "retime.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    srcs = ["tools/hbm_next/plane_compiler.py", "tools/hbm_next/isa_rows.py", "tools/hgi_sim/hbm_plane_model.py",
            "tools/hgi_sim/ds_mtp_verify.py", "tools/hgi_sim/ds_mtp_draft.py", "tools/hgi_sim/timing.py",
            "results/arch/hbm_mtp_next_1018/stats/summary.json"]
    out["sources_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in srcs}
    (a.out / "retime.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    return 0


# SM area options (SM4 results/arch/hbm_next_1019/sm4/geometry.json lever_table; owner decision input)
HEAD = dict(coll_lanes=5, union_hist=True, m1=True, rpl=True, hc_ii=250.0, vm_grown=True)
OPTIONS = [
    # (key, label, knobs, users in the multi-user step, lever_table row prefix)
    ("base", "base: P=4, 8 separate closed x stores (lever (a) is exact and cycle-neutral: same records as (a))",
     Knobs(**HEAD), 4, "base"),
    ("a", "(a) P=4 + shared 4-lane x store", Knobs(**HEAD), 4, "(a) P=4"),
    ("a_norpl", "(a) without the remainder-pass split (rpl 0: no 2-word lane-group supply / K-part combine in SM4)",
     Knobs(**dict(HEAD, rpl=False)), 4, "(a) P=4"),
    ("ab", "(a)+(b) P=4 on the block-dot column, BF16 column 1 lane (ATT single-query records)",
     Knobs(**HEAD, bf16_lanes=1, att_single="record"), 4, "(a)+(b)"),
    ("ab_rows", "(a)+(b) sensitivity: 1-lane ATT as one row record, fixed spans once (optimistic)",
     Knobs(**HEAD, bf16_lanes=1, att_single="rows"), 4, "(a)+(b)"),
    ("P3a_u3", "(P3a) P=3 + shared 3-lane x store, 3 users", Knobs(**HEAD, P=3), 3, "(P3a)"),
    ("P3a_u4", "(P3a) P=3 + shared 3-lane x store, 4 users on 3 lanes (2 passes)", Knobs(**HEAD, P=3), 4, "(P3a)"),
]
GEOM = ROOT / "results/arch/hbm_next_1019/sm4/geometry.json"


def options(a):
    from hgi_sim import hbm_plane_model as M
    st = M.load_stats(STATS)
    CUR["hist"] = lane_hists()
    lev = json.loads(GEOM.read_text())["lever_table"]
    out = dict(schema="opentallas.hbm_next_1019.cmtp.area_options.v1", generated_utc=datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), rule=__doc__, lever_basis=lev["basis"],
        users_union_note="users union mean for 3 users linearly interpolated between MTP-STATS n = 2 and 4",
        options={})
    sel = [o for o in OPTIONS if not a.only or o[0] in a.only.split(",")]
    for key, label, kn, mu_n, row in sel:
        r = run_case(kn, st, a.jobs, kn.P, mu_n)
        lv = next(x for x in lev["rows"] if x["option"].startswith(row))
        die = lv["die_mm2"]
        r.update(key=key, label=label, die_mm2=die, lever_row=lv["option"], per_mm2=dict(
            ar=round(r["ar_tok_s"] / die, 3), mtp=round(r["mtp"]["tok_s"] / die, 3),
            mu_agg=round(r["mu"]["agg_tok_s"] / die, 3)))
        out["options"][key] = r
        print(f"{key:8s} die {die:6.1f}  AR {r['ar_tok_s']:7.1f}  MTP {r['mtp']['tok_s']:7.1f} (verify "
              f"{r['mtp']['verify_cycles']:.0f}, draft {r['mtp']['draft_cycles']:.0f})  MU{mu_n} agg "
              f"{r['mu']['agg_tok_s']:7.1f} / user {r['mu']['per_user_tok_s']:7.1f}  /mm2 MTP {r['per_mm2']['mtp']}"
              f" agg {r['per_mm2']['mu_agg']}", flush=True)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    srcs = ["tools/hbm_next/plane_compiler.py", "tools/hbm_next/isa_rows.py", "tools/hgi_sim/hbm_plane_model.py",
            "tools/hgi_sim/ds_mtp_verify.py", "tools/hgi_sim/ds_mtp_draft.py", "tools/hgi_sim/timing.py",
            "results/arch/hbm_mtp_next_1018/stats/summary.json", "results/arch/hbm_next_1019/sm4/geometry.json"]
    out["sources_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in srcs}
    a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    return 0


# step 4: measured re-time per option (P = 4 (a) and P3+(a)); per-unit deltas so PROG can rank redesigns
MEAS_OPTIONS = [("P4a", "(a) P=4 + shared 4-lane x store (cycle-identical to base)", Knobs(**HEAD), 4),
                ("P3a_u4", "(P3a) P=3 + shared 3-lane x store, 4 users on 3 lanes", Knobs(**HEAD, P=3), 4),
                ("P3a_u3", "(P3a) P=3 + shared 3-lane x store, 3 users", Knobs(**HEAD, P=3), 3)]


MEAS_OPTIONS += [("P4a_rpl0", "(a) P=4 shared xs4, rpl 0 (no remainder split hardware; SM4 builds rpl 0 first)",
                  Knobs(**dict(HEAD, rpl=False)), 4)]
STEP5_CASES = ["priced", "idxn", "su_vop2", "argmax2", "fused", "idx_frame", "fused_frame",
               "ALL measured v2", "ALL measured v2 + frames"]


def meas_cases(key):
    if MODE5[0]:
        full = [("priced", ())] + [(m, (m,)) for m in ("idxn", "su_vop2", "argmax2", "fused", "idx_frame",
                                                         "fused_frame")] + [
            ("ALL measured v2", MEAS_ALL2), ("ALL measured v2 + frames", MEAS_ALL2 + ("idx_frame", "fused_frame"))]
        return full

    full = [("priced", ())] + [(m, (m,)) for m in MEAS_ALL + ("idx_index_abs",)] + [
        ("ALL measured", MEAS_ALL), ("ALL measured, IDX.INDEX 953 absolute",
                                     tuple(x for x in MEAS_ALL if x != "idx_index") + ("idx_index_abs",))]
    return full if key != "P3a_u3" else [full[0], full[-2]]


def meas(a):
    from hgi_sim import hbm_plane_model as M
    MODE5[0] = bool(getattr(a, "step5", False))
    st = M.load_stats(STATS)
    CUR["hist"] = lane_hists()
    out = dict(schema="opentallas.hbm_next_1019.cmtp.meas_retime.v1", generated_utc=datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), rule=__doc__, meas_keys=MEAS, options={})
    for key, label, kn0, mu_n in MEAS_OPTIONS:
        if a.only and key not in a.only.split(","):
            continue
        rows = {}
        for name, ms in meas_cases(key):
            if a.cases and name not in a.cases.split("|"):
                continue
            kn = dataclasses.replace(kn0, meas=tuple(ms))
            r = run_case(kn, st, a.jobs, kn.P, mu_n)
            rows[name] = r
            print(f"{key:7s} {name:40s} AR {r['ar_tok_s']:7.1f}  MTP {r['mtp']['tok_s']:7.1f} (verify "
                  f"{r['mtp']['verify_cycles']:.0f}, draft {r['mtp']['draft_cycles']:.0f})  MU{mu_n} agg "
                  f"{r['mu']['agg_tok_s']:7.1f} / user {r['mu']['per_user_tok_s']:7.1f}", flush=True)
            out["options"][key] = dict(label=label, users=mu_n, cases=rows)
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
        base = rows.get("priced")
        if base:
            d = {}
            for name, r in rows.items():
                d[name] = dict(
                    mtp_tok_s=r["mtp"]["tok_s"], d_mtp_tok_s=round(r["mtp"]["tok_s"] - base["mtp"]["tok_s"], 1),
                    d_mtp_pct=round(100 * (r["mtp"]["tok_s"] / base["mtp"]["tok_s"] - 1), 2),
                    d_step_cycles=round(r["mtp"]["step_cycles"] - base["mtp"]["step_cycles"], 1),
                    mu_agg=r["mu"]["agg_tok_s"], mu_per_user=r["mu"]["per_user_tok_s"],
                    d_mu_agg=round(r["mu"]["agg_tok_s"] - base["mu"]["agg_tok_s"], 1),
                    d_mu_pct=round(100 * (r["mu"]["agg_tok_s"] / base["mu"]["agg_tok_s"] - 1), 2),
                    d_mu_step_cycles=round(r["mu"]["step_cycles"] - base["mu"]["step_cycles"], 1),
                    ar_tok_s=r["ar_tok_s"])
            out["options"][key]["delta_vs_priced"] = d
    srcs = ["tools/hbm_next/plane_compiler.py", "tools/hbm_next/isa_rows.py", "tools/hgi_sim/hbm_plane_model.py",
            "tools/hgi_sim/ds_mtp_verify.py", "tools/hgi_sim/ds_mtp_draft.py", "tools/hgi_sim/timing.py",
            "results/arch/hbm_mtp_next_1018/stats/summary.json"]
    out["sources_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in srcs}
    a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("meas")
    q.add_argument("--out", type=Path, required=True)
    q.add_argument("--jobs", type=int, default=4)
    q.add_argument("--only", default="")
    q.add_argument("--cases", default="", help="'|'-separated case names")
    q.add_argument("--step5", action="store_true", help="step 5 case set (IDXN / SUDMA2 / FUSED + frames, v2 ALL)")
    o = sub.add_parser("options")
    o.add_argument("--out", type=Path, required=True)
    o.add_argument("--jobs", type=int, default=4)
    o.add_argument("--only", default="")
    r = sub.add_parser("retime")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--jobs", type=int, default=4)
    r.add_argument("--only", default="")
    a = ap.parse_args()
    return dict(options=options, retime=retime, meas=meas)[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
