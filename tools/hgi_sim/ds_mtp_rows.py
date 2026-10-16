#!/usr/bin/env python3
"""H-MTP2: DeepSeek-V4.1-Flash DSpark MTP on the generic HBM die at 1M -- the multi-position (P-row) record design,
ranked top-down from a throughput target, timed on the batched verify compiler (hgi_sim.ds_mtp_verify) with the
command processor modelled (timing.schedule S2, per layer segment).

TARGET (stated basis): >= 3,500 tok/s MTP at 1M context, tau 4.159 (DSpark gamma 5, owner 6-class blend; the DS ROM
basis), 1.2 GHz: one DSpark step <= tau x 1.2e9 / 3,500 = 1,426,029 cycles.  3,500 = 1.74 x the same die's AR
(2,010 tok/s, option B attention on the SM engines, same program and price table): MTP must pay at least the
accepted-cost ledger's worth over AR (owner: MTP is required and paying) with margin for the unpriced 4-PC service /
v15 VM costs; it is 83 % of the DS ROM design's 4,238 tok/s (the same tau).

ITEMS (hardware / ISA changes, each a P-row record family or an SM / VM / draft change; area = die-level ESTIMATE,
to be replaced by the owner's measured synthesis): every item is timed ALONE on top of the as-built die (SM without
a slot port, VM swap, row-serial draft) and ranked by cycles saved a step per mm2; the cumulative ladder adds them in
that order and records tok/s on the price table and on the current measured-unit sensitivity after each.

DRAFT row batching (H-MTP, compiler): the DSpark stage bodies (dsa / dsb, the sliding-layer lowering) take the 5
block rows as P = 5 rows; their cost is the row-serial draft x the batching ratio of a sliding main layer (layer 0
segment: verify(P = 5) / (5 x AR)) under the same item set -- a MODEL (ratio transfer), the lowered row-batched
stage bodies are the open compiler item; Markov stays serial (d_{i+1} depends on d_i), DHEAD's 5 LM-head rows share
the weight stream through the SM slots.

    python3 -m hgi_sim.ds_mtp_rows --out REC.json [--jobs N]        (from tools/; ~10 min at 32 jobs)
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from hgi_sim import ds_mtp_verify as V  # noqa: E402

TARGET = 3500.0
P = 6
DRAFT_SIM = ROOT / "results/arch/hbm_mtp_1015/sim1M_B/sim.json"
UNIT = ROOT / "results/rtl/hgi_unit_tput_20261010"

# the current measured unit ratios (measured / price), newest production-width bench per op; the 10-10 calibration
# (e2e_calibration.json, used by ds_mtp_verify's 'sensitivity') predates the LL FUSED engine (6.5x / 20x there)
CURRENT_MEASURED = {
    "FUSED.HC_PRE_NORM": (0.715, "fused/hc_pre_norm_d5120_ll/report.json (LL engine 464 cyc vs 649.4)"),
    "FUSED.HC_POST": (1.096, "fused/hc_post_d5120_ll/report.json (LL engine 244 vs 222.7)"),
    "FUSED.QDQ_FP8": (2.74, "qdq_wide/report.json (production width)"),
    "FUSED.QDQ_FP4_E8M0": (4.5, "qdq_wide/report.json"),
    "FUSED.QDQ_FP4_E4M3": (2.75, "qdq_wide/report.json"),
    "IDX.TOPK": (0.676, "idx/ds_L0_tput/report_topkw1_w8_r4.json (8-wide heap, production)"),
    "COLL.TOPK_MERGE": (1.057, "coll/tkm_tput_480f631d5.json"),
}

# one extra block-dot MAC set on every SM: 8 columns x 4 ot_gpu_bd_col (LB 2) a SM, results/physical_abi3/asap7/gpu/
# ot_gpu_bd_col_lb2_092/physical.json 5,474 um2 routed std cells -> 9,123 um2 at 0.6 utilisation; 32 SMs
BDSET = 32 * 32 * 5473.54 / 0.6 / 1e6
# item: (owner, change, area_mm2 estimate, area basis, config delta)
ITEMS = {
    "COLL": ("H-COLL", "COLL.ROW_GATHER / TOPK_MERGE / kv_gather / ARGMAX_MERGE take R = P rows: one message train of "
             "P payloads (I operand m = P id lists, O stride a row); the endpoint/crossing/tail paid once",
             0.02, "record decode row counter + descriptor stride adders in the COLL record adapter",
             dict(rows={"COLL"})),
    "SU_DMA": ("H-SU / H-DIE (DMA) / H-IDX (ARGMAX)", "indexed SU.VOP (route gathers), DMA.KVWB_DS (P rows, window ring "
               "256 slots), position-addressed DMA.LOAD rows, FUSED.QDQ, ARGMAX.LOCAL take R = P rows",
               0.05, "row counters + per-row I / dyn_sel stepping in four record adapters",
               dict(rows={"SU", "DMA", "FUSED.QDQ", "ARGMAX"})),
    "IDX": ("H-IDX", "IDX.TOPK route top-6 R = P rows (heap reset a row) + the verify expert-UNION record; IDX.INDEX "
            "P queries over ONE key stream (query slots x P, compute serial)",
            0.10, "P x 4,096-word query store (SRAM) + union bitmap 384 b + heap row reset",
            dict(rows={"IDX.TOPK", "IDX.INDEX"})),
    "FUSED": ("H-SU (FUSED owner)", "FUSED.HC_PRE_NORM / HC_POST R = P rows on the LL lanes: gain sectors kept "
              "across rows, two r slots (row p+1's phase A overlaps row p's csum / rsqrt tail), per-row scalar set "
              "(PRE 4 / POST 20 words a row)",
              0.10, "32 lanes x (x buffer 2 x 20 sectors + 6 x 20 scalar words) flops ~ 200k DFF x 0.486 um2",
              dict(rows={"FUSED.PRE", "FUSED.POST"})),
    "HC": ("H-SU (HC owner)", "HC.HC_MIX R = P rows: HCP streams P h rows against stationary mix weights (measured x6 "
           "mode, II 250), SU pre/post rows, Sinkhorn x 3 units (II 634 / 3 < 250)",
           0.15, "2 more ot_hdc_sinkhorn (16 quotient paths + 512-entry seed each, ~0.06 mm2) + row sequencing",
           dict(rows={"HC"})),
    "ATT": ("H-SM (SM attention)", "option-B attention records R = P query rows: fixed spans (first access, "
            "dispatch, publish, cross-SM merge) once, the KV line stream once per pass, component span x "
            "ceil(P / query slots) (query slots = the SM MAC slot sets)",
            0.64, "per SM: 6 query-slot stores (512 FP32 each, SRAM) + row tags; 32 SMs",
            dict(rows={"ATT"}, att_k=1)),
    "SM_HOLD": ("H-SM", "SM line hold (slot port k = 1): one HBM read of each weight line serves P slots in P issue "
                "passes (op_xb + slot field [4:2] + per-slot x base); never faster than the HBM share",
                0.32, "per SM one 136 B line held x IL 8 + slot tag; 32 SMs",
                dict(sm_mode="slots", sm_k=1)),
    "SM_K2": ("H-SM", "SM MAC slot sets k = 2 (the P-slot port of HGI-1 spec 6.7 at 2 slots a pass): ceil(6 / 2) = 3 "
              "passes, 3 / 1.374 of the HBM-bound line time",
              BDSET * 1 + 0.32, "1 more block-dot set a SM (32 ot_gpu_bd_col LB2 at 9,123 um2 = 5,474 um2 std cells "
              "routed / 0.6) x 32 SMs + the line hold -- ESTIMATE from the routed bd_col, H-SM to measure",
              dict(sm_mode="slots", sm_k=2, att_k=2)),
    "SM_K3": ("H-SM", "SM MAC slot sets k = 3 (spec 6.7 P-slot port at 3 slots a pass): ceil(6 / 3) = 2 passes, "
              "2 / 1.374 of the HBM-bound line time",
              BDSET * 2 + 0.32, "2 more block-dot sets a SM (same basis) -- ESTIMATE, H-SM to measure",
              dict(sm_mode="slots", sm_k=3, att_k=3)),
    "SM_K6": ("H-SM", "SM MAC slot sets k = 6 (one pass, spec 6.7 'issue unchanged')",
              BDSET * 5 + 0.32, "5 more block-dot sets a SM (same basis) -- ESTIMATE",
              dict(sm_mode="slots", sm_k=6, att_k=6)),
    "VM": ("H-DIE", "VM +150k words: the P verify columns' h / PRE resident (no per-layer column swap)",
           0.9, "+150k x 32 b SRAM at the VM's 1.5 mm2 / 256k-word density",
           dict(swap=False)),
}
ORDER_FIXED = ("SM_HOLD", "SM_K2", "SM_K3", "SM_K6")          # mutually exclusive SM options


def cfg_of(items):
    c = dict(sm_mode="serial", swap=True, rows=set(), att_k=None, sm_k=None)
    for it in items:
        d = ITEMS[it][4]
        for k, v in d.items():
            if k == "rows":
                c["rows"] = c["rows"] | v
            elif k == "att_k":
                c["att_k"] = max(c["att_k"] or 0, v)
            else:
                c[k] = v
    if "ATT" in c["rows"] and c["sm_k"]:
        c["att_k"] = max(c["att_k"] or 1, c["sm_k"])
    c["rows"] = tuple(sorted(c["rows"]))
    return c


_CTX = {}


def _ctx():
    if "recs" not in _CTX:
        _CTX["d"], _CTX["recs"], _CTX["cf"] = V.load()
        bm = json.loads(V.BMODEL.read_text())
        _CTX["bex"] = {T_: dict(qk=v["qk"], pv=v["pv"]) for T_, v in bm["exposed"]["per_record"].items()}
        _CTX["bcomp"] = bm["measured_comp"]
    return _CTX


def scales():
    calib = json.loads(V.CALIB.read_text())["result"]["sensitivity"]["ds_1M"]
    meas = set(calib["calibration_coverage"]["measured_ops"])
    old = {u: x for u, x in calib["scale_dma_full_bw"].items() if u in meas}
    cur = dict(old)
    cur.update({k: v[0] for k, v in CURRENT_MEASURED.items()})
    return dict(fixed=None, sens_1010=old, sens_current=cur)


def _job(job):
    name, items, P_, scale_name, layer = job
    c = _ctx()
    cfg = cfg_of(items)
    recs = c["recs"] if layer is None else [r for r in c["recs"] if r.layer == layer or (r.unit == "CTL" and r.op == "END")]
    prog, st = V.compile_verify(recs, c["cf"], P_, sm_mode=cfg["sm_mode"] if P_ > 1 else "pport", att="B",
                                bmodel=c["bex"], bcomp=c["bcomp"], swap=cfg["swap"] and P_ > 1, rows=cfg["rows"],
                                sm_k=cfg["sm_k"], att_k=cfg["att_k"])
    r = V.run(prog, scales()[scale_name])
    return name, dict(cycles=r["cycles"], records=r["records"], unit_busy=r["unit_busy"], compile=st)


def draft_terms():
    sim = json.loads(DRAFT_SIM.read_text())
    return V.draft_terms(DRAFT_SIM, P), sim.get("att_pricing")


def compose(verify, ar, ar_l0, v5_l0, draft, scale_k, batched):
    """step = verify + draft (+ seed + main-hidden stores + control); batched: dsa / dsb / dhead scaled by the layer-0
    P = 5 batching ratio the block rows' column swaps, demb and Markov kept serial"""
    d = draft["draft_by_kind"]
    r5 = v5_l0 / (5 * ar_l0)
    if batched:
        dr = (d["dsa"] + d["dsb"] + d["dhead"]) * r5 + d["demb"] + d["markov"] + d["swapin"] + d["swapout"]
    else:
        dr = sum(d.values())
    seed = draft["seed_cycles"] * (r5 if batched else 1.0)
    extra = (dr + seed + draft["mh_store_cycles"]) * scale_k
    ncmd = 40 + 1 + 1 + 3 + 1 + 5
    step = verify + extra + ncmd * V.CTL_CMD
    return dict(step_cycles=round(step, 1), verify_cycles=verify, draft_cycles=round(dr * scale_k, 1),
                seed_cycles=round(seed * scale_k, 1), r5=round(r5, 4), mtp_tok_s=round(V.TAU * V.CLK / step, 1),
                ar_tok_s=round(V.CLK / ar, 1), mtp_over_ar=round(V.TAU * ar / step, 3))


def main():
    import multiprocessing as mp
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args()
    base = ()
    single = [k for k in ITEMS]
    # 1) every item alone on the as-built die (fixed table), + the as-built and the predecessor's P-port headline
    jobs = [("asbuilt|fixed", base, P, "fixed", None), ("AR|fixed", (), 1, "fixed", None),
            ("AR|sens_current", (), 1, "sens_current", None), ("AR|sens_1010", (), 1, "sens_1010", None),
            ("AR_L0|fixed", (), 1, "fixed", 0), ("asbuilt_L0P5|fixed", base, 5, "fixed", 0)]
    for it in single:
        jobs.append((f"alone:{it}|fixed", (it,), P, "fixed", None))
        jobs.append((f"alone_L0P5:{it}|fixed", (it,), 5, "fixed", 0))
    with mp.Pool(a.jobs) as pool:
        res = dict(pool.map(_job, jobs))
    draft, att_pr = draft_terms()
    ar, ar_l0 = res["AR|fixed"]["cycles"], res["AR_L0|fixed"]["cycles"]
    asb = res["asbuilt|fixed"]["cycles"]
    rank = []
    for it in single:
        v = res[f"alone:{it}|fixed"]["cycles"]
        s0 = compose(asb, ar, ar_l0, res["asbuilt_L0P5|fixed"]["cycles"], draft, 1.0, False)["step_cycles"]
        s1 = compose(v, ar, ar_l0, res[f"alone_L0P5:{it}|fixed"]["cycles"], draft, 1.0, False)["step_cycles"]
        rank.append(dict(item=it, owner=ITEMS[it][0], saves_cycles=round(s0 - s1, 1), area_mm2=ITEMS[it][2],
                         cycles_per_mm2=round((s0 - s1) / ITEMS[it][2], 1)))
    rank.sort(key=lambda x: -x["cycles_per_mm2"])
    # 2) cumulative ladder in rank order (the SM options: hold, then k3 replaces hold, then k6 replaces k3); the
    #    draft row batching enters after the SM option it needs
    order = [x["item"] for x in rank if x["item"] not in ORDER_FIXED] + list(ORDER_FIXED)
    ladder, cur = [], []
    steps = []
    for it in order:
        if it in ORDER_FIXED:
            cur = [x for x in cur if x not in ORDER_FIXED]
        cur = cur + [it]
        steps.append(tuple(cur))
    jobs = []
    for st in steps:
        nm = "+".join(st)
        for sc in ("fixed", "sens_current", "sens_1010"):
            jobs.append((f"ladder:{nm}|{sc}", st, P, sc, None))
        jobs.append((f"ladderL0P5:{nm}|fixed", st, 5, "fixed", 0))
    with mp.Pool(a.jobs) as pool:
        res.update(dict(pool.map(_job, jobs)))
    for st in steps:
        nm = "+".join(st)
        row = dict(items=list(st), area_mm2=round(sum(ITEMS[i][2] for i in st), 2))
        v5 = res[f"ladderL0P5:{nm}|fixed"]["cycles"]
        for sc in ("fixed", "sens_current", "sens_1010"):
            k = res[f"AR|{sc}"]["cycles"] / ar if sc != "fixed" else 1.0
            for batched in (False, True):
                row[f"{sc}{'|draft_batched' if batched else ''}"] = compose(
                    res[f"ladder:{nm}|{sc}"]["cycles"], res[f"AR|{sc}"]["cycles"], ar_l0, v5, draft, k, batched)
        ladder.append(row)
    first = next((r for r in ladder if r["fixed|draft_batched"]["mtp_tok_s"] >= TARGET), None)
    # 3) the smallest set: for each SM option, the full cheap set and every leave-one-out (fixed table, batched draft)
    cheap = [x for x in order if x not in ORDER_FIXED]
    cand = []
    for smo in ("SM_K2", "SM_K3"):
        cand.append(tuple(cheap) + (smo,))
        for drop in cheap:
            cand.append(tuple(x for x in cheap if x != drop) + (smo,))
    jobs = []
    for st in cand:
        nm = "+".join(st)
        jobs += [(f"min:{nm}|fixed", st, P, "fixed", None), (f"minL0P5:{nm}|fixed", st, 5, "fixed", 0),
                 (f"min:{nm}|sens_current", st, P, "sens_current", None)]
    with mp.Pool(a.jobs) as pool:
        res.update(dict(pool.map(_job, jobs)))
    minimal = []
    for st in cand:
        nm = "+".join(st)
        f_ = compose(res[f"min:{nm}|fixed"]["cycles"], ar, ar_l0, res[f"minL0P5:{nm}|fixed"]["cycles"], draft, 1.0, True)
        k_ = res["AR|sens_current"]["cycles"] / ar
        s_ = compose(res[f"min:{nm}|sens_current"]["cycles"], res["AR|sens_current"]["cycles"], ar_l0,
                     res[f"minL0P5:{nm}|fixed"]["cycles"], draft, k_, True)
        minimal.append(dict(items=list(st), area_mm2=round(sum(ITEMS[i][2] for i in st), 2), fixed=f_, sens_current=s_))
    meet = sorted([m_ for m_ in minimal if m_["fixed"]["mtp_tok_s"] >= TARGET], key=lambda m_: m_["area_mm2"])
    rec = dict(schema="opentallas.hgi_sim.ds_mtp_rows.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               target=dict(tok_s=TARGET, step_cycles_max=round(V.TAU * V.CLK / TARGET), basis=__doc__.split("ITEMS")[0]),
               tau=V.TAU, P=P, clock_hz=V.CLK, position=V.DT.POS,
               program=str(V.PROGRAM.relative_to(ROOT)), program_sha256=hashlib.sha256(V.PROGRAM.read_bytes()).hexdigest(),
               source_sha256={f: hashlib.sha256((TOOLS / "hgi_sim" / f).read_bytes()).hexdigest()
                              for f in ("ds_mtp_verify.py", "ds_mtp_rows.py", "timing.py")},
               draft_source=str(DRAFT_SIM.relative_to(ROOT)), draft_att_pricing=att_pr, draft=draft,
               current_measured=CURRENT_MEASURED, scales=scales(),
               items={k: dict(owner=v[0], change=v[1], area_mm2=v[2], area_basis=v[3],
                              config={kk: (sorted(vv) if isinstance(vv, set) else vv) for kk, vv in v[4].items()})
                      for k, v in ITEMS.items()},
               ar_cycles=dict(fixed=ar, sens_current=res["AR|sens_current"]["cycles"],
                              sens_1010=res["AR|sens_1010"]["cycles"]),
               asbuilt_verify=asb, rank_alone=rank, ladder=ladder,
               first_meeting_target=first and dict(items=first["items"], area_mm2=first["area_mm2"],
                                                    **first["fixed|draft_batched"]),
               minimal_search=minimal, smallest_meeting_target=meet[0] if meet else None, runs=res)
    for r in ladder:
        print(f"{'+'.join(r['items']):60s} {r['area_mm2']:7.2f} mm2  fixed {r['fixed']['mtp_tok_s']:7.1f} "
              f"batched-draft {r['fixed|draft_batched']['mtp_tok_s']:7.1f}  sens_cur {r['sens_current|draft_batched']['mtp_tok_s']:7.1f}",
              flush=True)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(rec, indent=1, default=list) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
