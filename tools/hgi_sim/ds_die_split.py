#!/usr/bin/env python3
"""HBM-ARRAY (owner question 10-16 ~21:40): price a SMALLER generic HBM die in a LARGER array.  32 SM / 4 stacks /
TP-96 is the baseline.  The candidates are 16 SM / 2 stacks / TP-192 (H-DIE plan A2P, 496 mm2) and 24 SM / 3 stacks /
TP-128 (H-DIE B24a geometry, 779 mm2, priced at 3 stacks).  The HBM bandwidth per SM stays at 99 B/cycle/SM.

METHOD.  Each record of the native DS programme (the AR token, the batched verify P = 6 of the MTP design point, and
the compiled R-row DSpark draft) and of the Qwen3-8B AR programme keeps its base price (ds_mtp_verify / timing.cost).
Two things are added: the relay-stage change of the target die (ds_relay_latency's per-class crossing rule,
v5carry -> the H-DIE eval of that die, absolute-leg SM rule) and the SPLIT TRANSFORM below.  The same S2 schedule is
then re-run.

SPLIT TRANSFORM (G0 = 96 -> G1 = 96 * 32 / SMs; s = 32 / SMs; the die bandwidth scales by 1 / s):
  SM.MATVEC, row-split matrices (every dense / expert / head matrix split by output rows over the group)
        unchanged: rows per die x 1/s, SMs x 1/s, bytes per die x 1/s, die bandwidth x 1/s
  SM head-aligned work (wq_b of head h on die h, the wo_a K-split of the die's head; 64 heads stay on 64 dies)
        variable part x s: c' = F + s (c - F), F = measured first access + SM overhead (+ drain)
  ATT (option B on the SM, one head per die)   + (s - 1) x the busiest SM's line stream of the span
        (b_measured_model kv_layout measured_lines_busiest qk 50 / pv 125 at 8 lines / 11 cycles, T 640; T 128 scaled
        by the measured component ratio)
  COLL.* (TU endpoint model, perf.coll_cycles)   delivery term (G - 1) f / lanes per crossing, f = ceil(bytes / G / 64)
        (= 23.75 f at G 96 with 4 lanes: the fit IS the 4-lane delivery bound); merges (index / candidate / argmax)
        carry G x their per-rank list, so their bytes scale with G
  COLL.ROW_GATHER  hardware form K F / lanes + 150;  bypass form re-priced at G1 with the max owned count M1 =
        ceil(m_owned x M0) (M0 = the bit-exact run's max owned at G 96; m_owned default 0.6)
  DMA.LOAD (incl. column swaps): replicated per die, so the stream part runs at 1/s of the die bandwidth:
        c' = FA + s_bw (c - FA)
  SU.VOP   unchanged with a full-width SU; with --su-half the SU depth model at half the lanes (A2P as drawn: 2 quarter
        cores)
  IDX.INDEX (keys per die x 1/s at 1/s the stacks), IDX.TOPK, IDX.OWNED, HC, FUSED, SFU, ARGMAX.LOCAL, CTL: unchanged
  switch: one tier (1 crossing) by default; --extra-crossings N adds N x 377.6 ns per crossing (a 2-tier Clos = +2)

    python3 -m hgi_sim.ds_die_split --stages STAGES.json --out REC.json [--jobs N]     (from tools/)
"""
from __future__ import annotations

import argparse
import copy
import datetime
import json
import math
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from hgi_sim import ds_relay_latency as RL  # noqa: E402  (installs its relay-knob cost_fn on ds_mtp_verify)
from hgi_sim import ds_mtp_verify as V  # noqa: E402
from hgi_sim import timing as T  # noqa: E402

CLK = 1.2e9
G0 = 96
LANES0 = 4
CROSS = 377.6e-9 * CLK
BM = json.loads((ROOT / "results/hbm_sm_attention_1015/b_measured_model.json").read_text())
LINES_BUSIEST = BM["kv_layout"]["measured_lines_busiest"]          # qk 50, pv 125 at T 640
LINE_CAD = 11 / 8                                                 # 8 lines / 11 cycles per SM (bench cadence)
COMP = BM["measured_comp"]

_SPLIT = {}            # active split transform (per worker process)


def sm_fixed():
    m = T.MEAS
    fa = m["hbm.first_access"]["value"] if "hbm.first_access" in m else T.cv("hbm", "first_access")
    ov = m.get("SM.overhead", {}).get("value", 78)
    dr = m.get("SM.drain", {}).get("value", 12)
    return fa + ov + dr


def first_access():
    return T.first_access()


def is_head_sm(tag):
    return tag.startswith("wq_b (head-aligned") or tag.startswith("wo_a K-split")


def deliver(f, G, lanes):
    return (G - 1) * f / lanes


def coll_delta(nbytes, k, G1, lanes, merge=False):
    """added cycles of one collective at G1 / lanes vs the G0 / 4-lane price (k crossings)"""
    nb1 = nbytes * (G1 / G0 if merge else 1.0)
    f0 = max(1, math.ceil(nbytes / G0 / 64))
    f1 = max(1, math.ceil(nb1 / G1 / 64))
    return k * (deliver(f1, G1, lanes) - deliver(f0, G0, LANES0))


def split_added(r, c, sp):
    """the split transform's added cycles for one priced record (cost c)"""
    if not sp:
        return 0.0
    s, G1, lanes = sp["s"], sp["G1"], sp["lanes"]
    u = r.unit
    op = getattr(r, "orig_op", f"{r.unit}.{r.op}")
    tag = r.tag or ""
    kind = getattr(r, "mtp_kind", "") or ""
    npos = getattr(r, "npos", 1) or 1
    add = 0.0
    if op == "SM.MATVEC" and (is_head_sm(tag) or sp.get("all_sm")):
        F = sm_fixed()
        if c > F:
            add += (s - 1) * (c - F)
    elif op.startswith("ATT."):
        Tn = "640"
        try:
            Tn = str(V.att_T(r))
        except Exception:
            pass
        which = r.op.lower() if r.op in ("QK", "PV") else op.split(".")[1].lower()
        which = which if which in ("qk", "pv") else "pv"
        lt = LINES_BUSIEST[which] * LINE_CAD * (COMP.get(Tn, COMP["640"])[which] / COMP["640"][which])
        reps = 1
        if kind.endswith("_rows"):
            reps = max(1, round(c / max(1.0, sp["bex"].get(Tn, sp["bex"]["640"])[which])))
        add += (s - 1) * lt * reps
    elif u == "COLL":
        o = r.op
        k = 2 if o in ("ALL_REDUCE_SUM", "GROUP_REDUCE_MCAST") else 1
        if o == "ROW_GATHER" and (r.param >> 8) & 1:
            K = r.imm_a or r.desc["I"].n
            S_ = -(-r.desc["A"].n * T.ESZ[r.desc["A"].fmt] * 8 // 256)
            F_ = -(-S_ // 2)
            add += K * F_ * (1 / lanes - 1 / LANES0)
        elif o == "ROW_GATHER" and getattr(r, "layer", None) in sp["rg"]:
            st = sp["rg"][r.layer]
            M0, k_ = st["max_owned"], st["k"]
            M1 = max(math.ceil(k_ / G1), math.ceil(sp["m_owned"] * M0))
            bw = T.cv("hbm", "bytes_per_cycle") / sp["s_bw"]
            bw0 = T.cv("hbm", "bytes_per_cycle")
            read0, read1 = M0 * 288 / bw0, M1 * 288 / bw
            g0 = deliver(max(1, math.ceil(G0 * M0 * 288 / G0 / 64)), G0, LANES0)
            g1 = deliver(max(1, math.ceil(G1 * M1 * 288 / G1 / 64)), G1, lanes)
            add += (read1 - read0) + (g1 - g0) + k_ * 288 * (1 / bw - 1 / bw0)
        else:
            es = 8 if o in ("ARGMAX_MERGE", "TOPK_MERGE") else 2
            n = r.desc["A"].n if "A" in r.desc else 1
            if o == "TOPK_MERGE":
                n *= G0                     # every rank's local top-k list (value, id) lands on every die
            m = max(1, getattr(r.desc.get("A"), "m", 1) or 1) if "A" in r.desc else 1
            pos = npos if kind in ("shared",) or kind == "egather" else 1
            merge = ("merge" in tag) or o in ("TOPK_MERGE", "ARGMAX_MERGE")
            add += coll_delta(n * m * es * pos, k, G1, lanes, merge)
        add += k * sp["xc"] * CROSS
    elif u == "IDX" and ("merge" in tag):
        # a merge over the G gathered local top-k lists: the list count scales with G
        add += (G1 / G0 - 1) * max(0.0, c - 20)
    elif op in ("DMA.LOAD", "DMA.SWAP") or (u == "DMA" and r.op == "LOAD"):
        if not (op == "DMA.SWAP" and "out" in tag):
            fa = first_access()
            if c > fa:
                add += (sp["s_bw"] - 1) * (c - fa)
    elif u == "SU" and sp.get("su_half"):
        try:
            dyn = T.Dyn(V.DT.POS)
            L = r.layer if isinstance(r.layer, int) else 0
            full = T.su_cost(r, dyn, L)[0]
            T.CAL.setdefault("floorplan", {})["su_lanes"] = dict(value=512)
            half = T.su_cost(r, dyn, L)[0]
            T.CAL["floorplan"].pop("su_lanes")
            add += c * (half / full - 1) if full > 0 else 0.0
        except Exception:
            pass
    return add


_PREV_CF = V.cost_fn             # ds_relay_latency's wrapper (relay knob in RL._KNOB)


def cost_fn(scale=None):
    base = _PREV_CF(scale)
    if not _SPLIT:
        return base

    def cf(r, dyn, L):
        c, g, how = base(r, dyn, L)
        return c + split_added(r, c, _SPLIT), g, how
    return cf


V.cost_fn = cost_fn


def set_variant(var, stages):
    RL._KNOB.clear()
    _SPLIT.clear()
    b = stages["v5"]
    o = stages[var["stages"]]
    RL._KNOB.update(RL._knob(b, o))
    if var.get("split"):
        sp = dict(var["split"])
        c = RL._ctx()
        sp["rg"] = c["cf"].rg
        sp["bex"] = {k: v for k, v in c["bex"].items()}
        _SPLIT.update(sp)


def _job(job):
    name, case, var, stages = job
    set_variant(var, stages)
    c = RL._ctx()
    if case == "draft_design":
        from hgi_sim import ds_mtp_draft as D
        d = D.draft_step(c["R"].cfg_of(RL.DESIGN_ITEMS), None)
        return name, dict(draft_cycles=d["draft_cycles"], seed_cycles=d["seed_cycles"])
    if case == "census":
        prog = RL.compile_case("AR")
        rows = {}
        cf = V.cost_fn(None)
        for x in prog:
            k = f"{x.orig_op}|{(x.tag or '')[:40]}"
            c0 = x.base_cost
            a = split_added(x, c0, _SPLIT) if _SPLIT else 0.0
            e = rows.setdefault(k, dict(n=0, base=0.0, added=0.0))
            e["n"] += 1
            e["base"] += c0
            e["added"] += a
        return name, dict(rows={k: {kk: round(vv, 1) for kk, vv in v.items()} for k, v in
                                sorted(rows.items(), key=lambda kv: -kv[1]["added"])})
    prog = RL.compile_case(case)
    r = V.run(prog, None)
    return name, dict(cycles=r["cycles"], records=r["records"], unit_busy=r.get("unit_busy"))


def _qwen_job(job):
    """Qwen3-8B AR (hgi_sim.qwen_compiler TP-4 programme, timing.cost, S2): relay knob + Qwen split.  16 SM: TP-8
    (rows per SM unchanged; the in-package all-reduce gains ranks: delivery delta); 24 SM: TP-4 kept on 24-SM dies
    (SM variable part x 4/3, DMA stream x 4/3)."""
    name, var, stages = job
    from hgi_sim import qwen_timing as QT
    cfg = json.loads(QT.CFG.read_text())
    recs = QT.QC.program(QT.QC.Geometry(cfg, 8192), QT.QC.qwen_params(cfg), cfg["num_hidden_layers"])
    kn = RL._knob(stages["v5"], stages[var["stages"]])
    q = var.get("qwen")
    fa = first_access()
    mf = T.MEAS.get("SM.overhead", {}).get("value", 0) + fa

    def cf(r, dyn, L):
        c, g, how = T.cost(r, dyn, L)
        c += RL.added(r, kn["delta"], False, None, kn["b"], kn["o"])
        if q:
            if r.unit in ("SM", "ATT") and q["sm_s"] != 1 and c > mf:
                c = mf + q["sm_s"] * (c - mf)
            elif r.unit == "DMA" and r.op == "LOAD" and c > fa:
                c = fa + q["bw_s"] * (c - fa)
            elif r.unit == "COLL":
                n = r.desc["A"].n if "A" in r.desc else 1
                k = 2 if r.op == "ALL_REDUCE_SUM" else 1
                f0 = max(1, math.ceil(n * 2 / q["G0"] / 64))
                f1 = max(1, math.ceil(n * 2 / q["G1"] / 64))
                c += k * (deliver(f1, q["G1"], q["lanes"]) - deliver(f0, q["G0"], LANES0)) + k * q.get("xc", 0) * CROSS
        return c, g, how
    s = T.schedule(recs, 8191, "S2", cost_fn=cf)
    return name, dict(cycles=round(s["total_cycles"], 1), tok_s=round(CLK / s["total_cycles"], 1))


def _any(job):
    return _qwen_job(job[1:]) if job[0] == "qwen" else _job(job[1:])


VARIANTS = {
    # 32 SM / 4 stacks / TP-96 on the current d4c 824.8 mm2 plan (reference: relay-only model ~1,973)
    "d4c_32sm_4st_tp96": dict(stages="d4c", split=None, qwen=None),
    # 16 SM / 2 stacks / TP-192 on A2P 496 mm2, FULL core (4 COLL delivery lanes, full SU, full VM)
    "a2p_16sm_2st_tp192_full": dict(stages="a2p", split=dict(s=2, s_bw=2, G1=192, lanes=4, xc=0, m_owned=0.6),
                                    qwen=dict(sm_s=1, bw_s=2, G0=4, G1=8, lanes=4)),
    # A2P as drawn: 2 COLL engines (2 delivery lanes) + 2 quarter SU cores
    "a2p_16sm_asdrawn_L2_suhalf": dict(stages="a2p", split=dict(s=2, s_bw=2, G1=192, lanes=2, xc=0, m_owned=0.6,
                                                                su_half=True),
                                       qwen=dict(sm_s=1, bw_s=2, G0=4, G1=8, lanes=2)),
    "a2p_16sm_L2_only": dict(stages="a2p", split=dict(s=2, s_bw=2, G1=192, lanes=2, xc=0, m_owned=0.6),
                             qwen=dict(sm_s=1, bw_s=2, G0=4, G1=8, lanes=2)),
    "a2p_16sm_suhalf_only": dict(stages="a2p", split=dict(s=2, s_bw=2, G1=192, lanes=4, xc=0, m_owned=0.6,
                                                          su_half=True), qwen=dict(sm_s=1, bw_s=2, G0=4, G1=8, lanes=4)),
    # full core, but a 2-tier switch (+2 crossings a collective)
    "a2p_16sm_full_2tier": dict(stages="a2p", split=dict(s=2, s_bw=2, G1=192, lanes=4, xc=2, m_owned=0.6),
                                qwen=dict(sm_s=1, bw_s=2, G0=4, G1=8, lanes=4, xc=0)),
    # full core, pessimistic bypass row-gather padding (M1 = M0)
    "a2p_16sm_full_m1": dict(stages="a2p", split=dict(s=2, s_bw=2, G1=192, lanes=4, xc=0, m_owned=1.0),
                             qwen=dict(sm_s=1, bw_s=2, G0=4, G1=8, lanes=4)),
    # DP = 2: two TP-96 groups of 16-SM dies (every SM record's variable part x 2), full core
    "a2p_16sm_tp96_dp2_full": dict(stages="a2p", split=dict(s=2, s_bw=2, G1=96, lanes=4, xc=0, m_owned=1.0,
                                                            all_sm=True),
                                   qwen=dict(sm_s=2, bw_s=2, G0=4, G1=4, lanes=4)),
    # ---- round 2 (d4f full core 618.1 mm2, H-DIE 871908680) ----
    "d4f_16sm_tp192_full": dict(stages="d4f", split=dict(s=2, s_bw=2, G1=192, lanes=4, xc=0, m_owned=0.6),
                                qwen=dict(sm_s=1, bw_s=2, G0=4, G1=8, lanes=4)),
    "d4f_16sm_tp192_suhalf": dict(stages="d4f", split=dict(s=2, s_bw=2, G1=192, lanes=4, xc=0, m_owned=0.6,
                                                           su_half=True), qwen=dict(sm_s=1, bw_s=2, G0=4, G1=8, lanes=4)),
    "d4f_16sm_tp192_opta": dict(stages="d4f_opta", split=dict(s=2, s_bw=2, G1=192, lanes=4, xc=0, m_owned=0.6),
                                qwen=dict(sm_s=1, bw_s=2, G0=4, G1=8, lanes=4)),
    "d4f_16sm_tp96_dp2_L2": dict(stages="d4f", split=dict(s=2, s_bw=2, G1=96, lanes=2, xc=0, m_owned=1.0,
                                                          all_sm=True), qwen=dict(sm_s=2, bw_s=2, G0=4, G1=4, lanes=2)),
    "d4f_16sm_tp96_dp2_full": dict(stages="d4f", split=dict(s=2, s_bw=2, G1=96, lanes=4, xc=0, m_owned=1.0,
                                                            all_sm=True), qwen=dict(sm_s=2, bw_s=2, G0=4, G1=4, lanes=4)),
    # attribution on the d4c geometry: the split alone (no relay change), and head-only work
    "split_only_tp192_d4cstages": dict(stages="d4c", split=dict(s=2, s_bw=2, G1=192, lanes=4, xc=0, m_owned=0.6),
                                       qwen=None),
    "a2p_relay_only": dict(stages="a2p", split=None, qwen=None),
    "d4f_relay_only": dict(stages="d4f", split=None, qwen=None),
    # 24 SM: Qwen at TP-8 (rows per SM x 2/3)
    "b24_24sm_tp128_qwen_tp8": dict(stages="b24a", split=dict(s=4 / 3, s_bw=4 / 3, G1=128, lanes=4, xc=0, m_owned=0.8),
                                    qwen=dict(sm_s=2 / 3, bw_s=4 / 3, G0=4, G1=8, lanes=4)),
    # 24 SM / 3 stacks / TP-128 (B24a geometry), full core
    "b24_24sm_3st_tp128_full": dict(stages="b24a", split=dict(s=4 / 3, s_bw=4 / 3, G1=128, lanes=4, xc=0,
                                                              m_owned=0.8),
                                    qwen=dict(sm_s=4 / 3, bw_s=4 / 3, G0=4, G1=4, lanes=4)),
}


def main():
    import multiprocessing as mp
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stages", type=Path, required=True, help="{v5|d4c|a2p|b24a: {class: stages_bw}}")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--only", default="")
    ap.add_argument("--census", action="store_true")
    a = ap.parse_args()
    stages = json.loads(a.stages.read_text())
    var = {k: v for k, v in VARIANTS.items() if not a.only or k in a.only.split(",")}
    jobs = [("ds", "base|AR", "AR", dict(stages="v5"), stages)]
    if a.census:
        jobs = [("ds", f"{k}|census", "census", v, stages) for k, v in var.items() if v.get("split")]
    else:
        jobs += [("ds", "base|MTP_design", "MTP_design", dict(stages="v5"), stages),
                 ("ds", "base|draft_design", "draft_design", dict(stages="v5"), stages),
                 ("qwen", "base|qwen", dict(stages="v5"), stages)]
        for k, v in var.items():
            for case in ("AR", "MTP_design", "draft_design"):
                jobs.append(("ds", f"{k}|{case}", case, v, stages))
            jobs.append(("qwen", f"{k}|qwen", v, stages))
    with mp.Pool(a.jobs) as pool:
        res = dict(pool.map(_any, jobs, chunksize=1))
    if a.census:
        out = res
        print(json.dumps({k: dict(list(v["rows"].items())[:25]) for k, v in res.items()}, indent=1))
    else:
        dref = json.loads((ROOT / "results/arch/hbm_mtp_1015/draft_rows/design.json").read_text())
        smt = dref["smallest_meeting_target"]["fixed"]
        mh_ctl = smt["step_cycles"] - smt["verify_cycles"] - smt["draft_cycles"] - smt["seed_cycles"]

        def row(k):
            ar = res[f"{k}|AR"]["cycles"]
            d = res[f"{k}|draft_design"]
            st_ = res[f"{k}|MTP_design"]["cycles"] + d["draft_cycles"] + d["seed_cycles"] + mh_ctl
            q = res[f"{k}|qwen"]["cycles"]
            return dict(ar_cycles=ar, ar_tok_s=round(CLK / ar, 1), mtp_step_cycles=round(st_, 1),
                        mtp_design_tok_s=round(V.TAU * CLK / st_, 1), qwen_ar_cycles=q, qwen_ar_tok_s=round(CLK / q, 1),
                        unit_busy_ar=res[f"{k}|AR"].get("unit_busy"))
        table = {"base_v5": row("base")}
        for k in var:
            table[k] = row(k)
        ref = table.get("d4c_32sm_4st_tp96")
        if ref:
            for k, t in table.items():
                t["vs_d4c_ar_pct"] = round(100 * (t["ar_tok_s"] / ref["ar_tok_s"] - 1), 2)
                t["vs_d4c_mtp_pct"] = round(100 * (t["mtp_design_tok_s"] / ref["mtp_design_tok_s"] - 1), 2)
                t["vs_d4c_qwen_pct"] = round(100 * (t["qwen_ar_tok_s"] / ref["qwen_ar_tok_s"] - 1), 2)
        out = dict(schema="opentallas.hbm_array_16sm_1016.die_split.v1",
                   generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   rule=__doc__, variants=var, stages_source=str(a.stages), table=table, runs=res)
        print(json.dumps({k: {x: y for x, y in v.items() if x != "unit_busy_ar"} for k, v in table.items()}, indent=1))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
