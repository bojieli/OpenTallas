#!/usr/bin/env python3
"""Re-price the three headlines with the closure costs recorded on 2026-10-08 (stream reprice, OWNER request).

No new model.  Every number comes from an existing composition tool, driven with today's cycle items:
  DS ROM 1,792   tools/s81/field_phases_1792.py compose (the measured 1,792 field phases; per-field-phase items via its
                 --extra-wire, i.e. +N on every region's round trip = +N a phase) on top of
                 tools/dsrom_closure_cost_ledger.py (per-node items, LED.ITEMS convention).  BF both ways:
                 HALF_PHL = half_dedicated_ksplit / half_rate (120 stages), full rate = full_shared / full_rate_bf (98).
  DS ROM PQ      the owner-adopted PQ pricing (levers/qelem_pq.json, PENDING_SSFF) flipped to ADOPT in a scratch copy of
                 the recovery levers, composed by tools/dsrom_1m_allmeasured.py exactly as LED.compose does (85-stage
                 r8 geometry; ledger once-a-node convention).
  HBM DS 1M      unified_composition 'unified_candidate_contracts_rtl' + cycles x the per-token counts of the
                 matched-reference critical path (results/rtl/dshbm_matched_reference_20261005/composition.json path).
  Qwen ROM 8K    unified_composition token cycles + cycles x per-token counts (closure-ledger conventions).

    python3 tools/reprice_20261008.py            # writes results/arch/reprice_20261008/reprice.json
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/s81"))
import dsrom_closure_cost_ledger as LED  # noqa: E402
import field_phases_1792 as FP  # noqa: E402

OUT = ROOT / "results/arch/reprice_20261008"
UNI = ROOT / "results/arch/unified_composition_20261007/ledger.json"
HPATH = ROOT / "results/rtl/dshbm_matched_reference_20261005/composition.json"
CLK = 1.2e9
BASE_EXTRA_WIRE = 2          # composition_basis_39e424990: 2 PQ root-row return stations on the m221pq layer1 die
MAT = LED.MAT
HBM_NODES = LED.HBM
SEL = ["*.attn.idx.topk_local", "*.attn.cand.topk_local"]

# ---------------------------------------------------------------- DS ROM items (today's closures), cumulative order
# per_phase: cycles a field phase (1,792 basis: --extra-wire; PQ basis: once a MAT node, ledger convention)
# rows: LED-style (nodes, cycles, frac) per-node adds (both bases)
DS_ITEMS = [
    dict(item="svc_stations_180um",
         what="Service column stations 430 -> 180 um (s81-die-timing, main 4930ffbe4): chains Q0/Q1/Q2 34/22/11 stations "
              "(was 15/10/5) = +19/+12/+6 cycles each way. Charged at the worst chain Q0, both ways (+38) once per HBM-stream "
              "node (the ledger svc_io convention: one request round trip a node). Same closed dsfd_svc_stn tile "
              "(s81ph-dsfd_svc_stn-da50ce55a-lbc-tt CLOSED); bench tb_dsfd_svc_stn NS=34 PASS",
         per_phase=0, rows=[(k, 38, 0) for k in HBM_NODES], status="closed tile, die change on main"),
    dict(item="capture_kst1",
         what="Capture KST 1 (one dsfd_stnh_512x1 station each way on the 562 um ctl<->group hop): +1 cycle each way on "
              "t_k/f_sb/t_sn and +2 drain a phase. Upper bound +4 a field phase (both hops + drain serial). "
              "s81ph-dsfd_capt_ctl-df2ff7a97-kst1-tt CLOSED; capt_bench KST1 PASS",
         per_phase=4, rows=[], status="closed"),
    dict(item="hub_end_pinreg",
         what="Hub ends PINREG (redesign-s81; hx-W/hx-E/hq-SW l2r: +1 ck input pin flop + 1 cks on od; hcol/hsel/ha-SW "
              "r2l: +1 ck on o): one l2r end out + one r2l end back on every field round trip = +3 a field phase "
              "(upper bound); hsel +1 a selector segment. All six pinreg routes CLOSED at TT 10-08",
         per_phase=3, rows=[(k, 1, 0) for k in SEL], status="closed"),
    dict(item="head_elem_safe",
         what="lm_head element A/B SAFE (dshead-elemA/elemB-safe-b529ca8c9-tt CLOSED 10-08): +39 a bundle sweep "
              "(8,357 -> 8,396), on head.lm_head and the 5 draft head sweeps (+195). The CUT511/SPLIT9 'ss' variant "
              "(+57, ledger candidate head_elem) also closed; the cheaper SAFE variant is priced",
         per_phase=0, rows=[("head.lm_head", 39, 0), ("draft.total", 195, 0)], status="closed"),
    dict(item="pq_root_cam_a0",
         what="PQ root CAM adopted a0 (ot_s81_pq_ret_root_cam_p PAR 0 ASPLIT 0, s81b-pq-rc2-a0-h212-hm10-b761ac1c6 CLOSED "
              "TT +82.06 / FF +4.42): latency vs native complete/2-leaf/8-leaf = 2/4/8 (the priced B design: 1/2/4, i.e. "
              "+1 input cycle and +1 per root add level). Charged at the eight-leaf +8 on every field phase (the "
              "ledger / fieldphase upper-bound convention: every phase returns through one 8-leaf root)",
         per_phase=8, rows=[], status="closed, merged main 803962f5a"),
]
PQ_B = 4                      # the B design's eight-leaf delta (results/rtl/s81_pq_root_cam_20261007 measured_delta_cycles)

# NOT charged (recorded, but not closed / not adopted / not on the token path), listed in the record
DS_NOT_CHARGED = [
    dict(item="svcio_od_inq", cycles="+2 on od", why="s81ph-dsfd_svcio_od-inq-f1b64667d-tt NEEDS_HUMAN (not closed)"),
    dict(item="pq_root_cam_a7", cycles="2/7/18", why="closed but not adopted (a0 adopted)"),
    dict(item="coll_lane_e pipeline / head", cycles="+4 / +2", why="READY, not closed"),
    dict(item="cfifo column-side flops, --nxt-reach relays", cycles="0", why="no added cycles (same relay count)"),
    dict(item="swiglu esum", cycles="+6", why="pre-existing esum cycles in the measured su_swiglu lever; 0 added today"),
    dict(item="BF full-rate recut / deep4", cycles="+15 / +23 a BF16 phase", why="routes RUNNING; neither closed; the "
         "full-rate row below is the no-cost bound until one closes"),
]


def fp_compose(extra_wire, rows, tmp):
    """field_phases_1792 compose with LED.ITEMS + `rows` (per node) and --extra-wire; returns the compositions."""
    saved = list(LED.ITEMS)
    try:
        if rows:
            LED.ITEMS.append(("reprice_20261008", "today's per-node closure items", rows))
        a = argparse.Namespace(regions_dir=FP.OUT / "regions", geo_dir=FP.OUT / "geometry",
                               variants="half_dedicated_ksplit,full_shared", extra_wire=extra_wire, out=tmp)
        FP.cmd_compose(a)
    finally:
        LED.ITEMS[:] = saved
    d = json.loads(tmp.read_text())["variants"]
    c = lambda v, k: dict(AR_tok_s=d[v]["compositions"][k]["AR_tok_s"], MTP_tok_s=d[v]["compositions"][k]["MTP_tok_s"])
    return dict(half_phl=c("half_dedicated_ksplit", "half_rate"),
                full_rate_shared98=c("full_shared", "full_rate_bf"),
                full_rate_dedicated120=c("half_dedicated_ksplit", "full_rate_bf"))


def pq_compose(rows):
    """LED.compose with qelem_pq flipped to ADOPT (scratch copy of the recovery levers), all ledger items + rows."""
    with tempfile.TemporaryDirectory(prefix=".reprice-", dir=LED.OUT) as td:
        s = Path(td)
        shutil.copytree(LED.LEV.parent, s / "levers")
        q = s / "levers" / "qelem_pq.json"
        r = json.loads(q.read_text())
        r["verdict"] = "ADOPT"
        q.write_text(json.dumps(r, indent=1) + "\n")
        extra = [("reprice_20261008", "today's closure items", rows)] if rows else []
        (s / "levers" / LED.LEV.name).write_text(json.dumps(LED.lever([it for it, _, _ in LED.ITEMS], extra=extra), indent=1) + "\n")
        out = s / "composition.json"
        subprocess.run([sys.executable, str(ROOT / "tools/dsrom_1m_allmeasured.py"), "--recovery", str(s), "--out", str(out)],
                       check=True, capture_output=True)
        d = json.loads(out.read_text())
    return dict(AR_tok_s=d["AR_tok_s"], MTP_tok_s=d["MTP"]["MTP_tok_s"])


def pct(a, b):
    return round(100 * (a / b - 1), 3)


def ds_rom(tmpdir):
    steps, ew, rows = [], BASE_EXTRA_WIRE, []
    before = fp_compose(ew, rows, tmpdir / "fp_base.json")
    prev = before
    for it in DS_ITEMS:
        ew += it["per_phase"]
        rows = rows + it["rows"]
        cur = fp_compose(ew, rows, tmpdir / f"fp_{it['item']}.json")
        steps.append(dict(item=it["item"], what=it["what"], status=it["status"], per_field_phase=it["per_phase"],
                          per_node=[list(r) for r in it["rows"]],
                          rows={k: dict(cur[k], dAR_pct=pct(cur[k]["AR_tok_s"], prev[k]["AR_tok_s"]),
                                        dMTP_pct=pct(cur[k]["MTP_tok_s"], prev[k]["MTP_tok_s"])) for k in cur}))
        prev = cur
    # PQ root CAM at the B design's +4 (what the B pricing would have charged) for the itemised B -> a0 delta
    b_only = fp_compose(ew - DS_ITEMS[-1]["per_phase"] + PQ_B, rows, tmpdir / "fp_pqB.json")
    # PQ-adopted basis (85-stage r8 geometry, qelem_pq ADOPT): before = ledger + B root (+4 a MAT node); after = + today
    pq_before = pq_compose([(k, PQ_B, 0) for k in MAT])
    pq_steps, prow, pprev = [], [], pq_before
    for it in DS_ITEMS:
        if it["item"] == "pq_root_cam_a0":
            add = [(k, it["per_phase"] - PQ_B, 0) for k in MAT]       # B already in the before row
        else:
            add = [(k, it["per_phase"], 0) for k in MAT if it["per_phase"]] + it["rows"]
        prow = prow + add
        cur = pq_compose([(k, PQ_B, 0) for k in MAT] + prow)
        pq_steps.append(dict(item=it["item"], AR_tok_s=cur["AR_tok_s"], MTP_tok_s=cur["MTP_tok_s"],
                             dAR_pct=pct(cur["AR_tok_s"], pprev["AR_tok_s"]), dMTP_pct=pct(cur["MTP_tok_s"], pprev["MTP_tok_s"])))
        pprev = cur
    pq_no_root = pq_compose([])
    return dict(
        basis="1,792-pair S81 measured field phases (s81-fieldphase f42b1eb76, composition_basis_39e424990: extra_wire 2) "
              "+ the DS closure-cost ledger (39e424990 TOTAL 1,593.7 / 4,694.7 at 85 stages)",
        bf_cases=dict(half_phl="BF HALF_PHL (accepted closure path): half_dedicated_ksplit, 120 stages / 480 dies, BF16 "
                               "phases at 2 x (go->idle) + 2 (upper bound)",
                      full_rate_shared98="BF full rate (no BF cost; recut/deep4 still routing): full_shared, 98 stages / 392 dies",
                      full_rate_dedicated120="reference only: full-rate BF on the HALF dedicated mapping (120 stages), "
                                             "the 'full-rate shared reference' the ledger quotes"),
        before=before, items=steps, after=prev,
        delta_pct={k: dict(AR=pct(prev[k]["AR_tok_s"], before[k]["AR_tok_s"]), MTP=pct(prev[k]["MTP_tok_s"], before[k]["MTP_tok_s"]))
                   for k in before},
        pq_root_cam_B_vs_a0=dict(note="the same cumulative composition with the root CAM at the B design's +4 a phase "
                                      "instead of the adopted +8: the re-price of the CAM alone is a0 minus B",
                                 at_B=b_only, at_a0=prev,
                                 a0_minus_B_pct={k: dict(AR=pct(prev[k]["AR_tok_s"], b_only[k]["AR_tok_s"]),
                                                         MTP=pct(prev[k]["MTP_tok_s"], b_only[k]["MTP_tok_s"])) for k in prev}),
        pq_adopted_basis=dict(
            note="owner-adopted PQ priced as levers/qelem_pq.json (the 2,121.3 tok/s pricing of 2026-10-06, composed then "
                 "without the closure-cost ledger) flipped to ADOPT on today's ledger; 85-stage r8 geometry, full-rate BF "
                 "field (the 1,792 mapping has no PQ measurement); items charged once a MAT node (ledger convention)",
            qelem_pq_2121_pricing_2026_10_06=dict(AR_tok_s=2121.3),
            on_current_ledger_no_root_cam=pq_no_root, before_root_B=pq_before, items=pq_steps,
            after=dict(AR_tok_s=pprev["AR_tok_s"], MTP_tok_s=pprev["MTP_tok_s"]),
            delta_pct=dict(AR=pct(pprev["AR_tok_s"], pq_before["AR_tok_s"]), MTP=pct(pprev["MTP_tok_s"], pq_before["MTP_tok_s"]))),
        not_charged=DS_NOT_CHARGED)


# ---------------------------------------------------------------- HBM DS 1M
def hbm_counts():
    path = json.loads(HPATH.read_text())["path"]
    c = collections.Counter()
    for n in path:
        h, node = n.get("how", ""), n["node"]
        if node.startswith("coll:"):
            c["all_reduce" if "all_reduce" in h else "gather"] += 1
        if node.startswith("sufused:") and "norm" in node:
            c["norm"] += 1
    c["collective"] = c["all_reduce"] + c["gather"]
    return dict(c)


def hbm():
    u = json.loads(UNI.read_text())["targets"]["hbm_ds"]
    b = u["compositions"]["unified_candidate_contracts_rtl"]
    tau = b["tau"]
    n = hbm_counts()
    PASSES = 610           # unified cdc_refill_ii1: packet passes a token (2 cycles x 610)
    items = [
        dict(item="collective_sr_endpoint", lo=15 * n["all_reduce"] + 7 * n["gather"], hi=17 * n["all_reduce"] + 14 * n["gather"],
             what=f"HBM collective SRAM-queue endpoint (hfd_coll sr, drive-1443): all-reduce +15..+17, gather +7..+14 core "
                  f"cycles vs the flop endpoint; x {n['all_reduce']} all-reduces + {n['gather']} gathers/merges a token "
                  f"(matched-reference path, 265 collective terms). Routes RUNNING (sr3/srcdc3/srpd453/port)",
             status="priced, routes running"),
        dict(item="norm_split", lo=2 * n["norm"], hi=2 * n["norm"],
             what=f"Norm engine split (hbm-norm-split): rstd/y +1, q +2 (top capture flops; quant from y output flops); the "
                  f"fused norm nodes publish q: +2 x {n['norm']} norm nodes a token. grp8/grp16 routes in the loop",
             status="priced, routes running"),
        dict(item="truecredit_rx_pin", lo=n["collective"], hi=n["collective"],
             what=f"HA2 true-credit receiver pin capture (ha2_tcrxp_*_398750b79): +1 arrival cycle x {n['collective']} "
                  f"exposed owner reductions (ledger HA2 convention), on top of the priced ha2_truecredit increment",
             status="priced, routes running"),
        dict(item="packet_sram_ii1rw", lo=1 * PASSES, hi=4 * PASSES,
             what=f"Packet SRAM II=1 queue ii1rw (hbm_pkt_ii1rw-8a9a669df-tc CLOSED, merged): first flit +1 (WREG write "
                  f"edge) x {PASSES} passes over the priced refill; upper bound +4 a pass (first flit 2 -> 5 edges + WREG vs "
                  f"the 2-edge refill head). Input relays (ii1s IREL, +1 more) NOT adopted (NEEDS_HUMAN): 0",
             status="closed, merged"),
    ]
    out, ar, mtp = [], b["AR_us"], b["MTP_step_us"]
    for key in ("hi", "lo"):
        a_, m_ = b["AR_us"], b["MTP_step_us"]
        rows = []
        for it in items:
            us = it[key] / CLK * 1e6
            a0, m0 = 1e6 / a_, tau * 1e6 / m_
            a_, m_ = a_ + us, m_ + us
            rows.append(dict(item=it["item"], cycles=it[key], us=round(us, 3), AR_tok_s=round(1e6 / a_, 1),
                             MTP_tok_s=round(tau * 1e6 / m_, 1), dAR_pct=pct(1e6 / a_, a0), dMTP_pct=pct(tau * 1e6 / m_, m0)))
        out.append((key, rows, a_, m_))
    res = dict(basis="unified_composition unified_candidate_contracts_rtl (refill both, credit producer, clock-lock idle, "
                     "native SM->SU edge at RTL+bench): AR 1,733.1 / MTP 3,719.0; added cycles charged on the AR walk and "
                     "on every MTP verify step (unified convention)",
               counts=n, before=dict(AR_tok_s=b["AR_tok_s"], MTP_tok_s=b["MTP_tok_s"], AR_us=b["AR_us"], MTP_step_us=b["MTP_step_us"]),
               items=[dict(item=i["item"], what=i["what"], status=i["status"], cycles_lo=i["lo"], cycles_hi=i["hi"]) for i in items])
    for key, rows, a_, m_ in out:
        res["upper" if key == "hi" else "lower"] = dict(rows=rows, after=dict(AR_tok_s=round(1e6 / a_, 1), MTP_tok_s=round(tau * 1e6 / m_, 1),
                                                                               dAR_pct=pct(1e6 / a_, b["AR_tok_s"]), dMTP_pct=pct(tau * 1e6 / m_, b["MTP_tok_s"])))
    return res


# ---------------------------------------------------------------- Qwen ROM 8K
def qwen():
    u = json.loads(UNI.read_text())["targets"]["qwen_rom"]["compositions"]
    ME_MEAS, ME_UB, LEGS = 217, 325, 72      # ME ops a token (relay record / closure-ledger assumption); link legs a token
    items = [
        dict(item="serdes_pinreg", lo=LEGS, hi=LEGS,
             what=f"qfd_io_serdes PINREG (adopted, merged b88291363): +1 receive cycle a word = +1 latency a link traversal; "
                  f"{LEGS} link legs a token (2 all-reduce legs a layer x 36 layers, ledger hub_ps convention)", status="closed, merged"),
        dict(item="band_integrate", lo=7 * ME_MEAS, hi=7 * ME_UB,
             what=f"Band integrate (qwen-band-integrate 60ebc5345): +5 + 2*LNK edges a ME op result, CLNK free; LNK 1 (bench "
                  f"LNK1/CLNK2; die LNK open: each further LNK +2 a ME op) x {ME_MEAS} measured ME ops (upper {ME_UB})",
             status="RTL exact, TT routes queued"),
        dict(item="emb_root_lvt", lo=0, hi=0, what="Embedding root LVT: 0 cycles", status="0"),
    ]
    res = dict(basis="unified_composition qwen_rom (1.2 GHz, AR mode)", items=items, rows={})
    for base_key in ("unified_candidate", "unified_candidate_with_closure_upper"):
        cyc0 = u[base_key]["cycles"]
        for key in ("lo", "hi"):
            c, rows = cyc0, []
            for it in items:
                t0 = CLK / c
                c += it[key]
                rows.append(dict(item=it["item"], cycles=it[key], AR_tok_s=round(CLK / c, 1), dAR_pct=pct(CLK / c, t0)))
            res["rows"][f"{base_key}:{'upper' if key == 'hi' else 'lower'}"] = dict(
                before=dict(cycles=cyc0, AR_tok_s=round(CLK / cyc0, 1)), items=rows,
                after=dict(cycles=c, AR_tok_s=round(CLK / c, 1), dAR_pct=pct(CLK / c, CLK / cyc0)))
    return res


OPTIONAL_TARGETS = ("qwen_hbm",)


def optional_prices(namespace):
    """Include a target only after its composition implementation lands.

    This discovery does not supply a speculative acceptance rate or turn a
    design study into a measured composition.
    """
    return {name: namespace[name]() for name in OPTIONAL_TARGETS
            if callable(namespace.get(name))}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reprice-") as td:
        rec = dict(schema="opentallas.reprice.v1", date="2026-10-08", tool="tools/reprice_20261008.py",
                   rule="today's recorded closure cycle costs only, each itemised and composed cumulatively by the existing "
                        "composition tools; upper bounds where a cost's exposure is not measured; no physical adoption implied",
                   ds_rom=ds_rom(Path(td)), hbm_ds=hbm(), qwen_rom=qwen())
        rec.update(optional_prices(globals()))
    (OUT / "reprice.json").write_text(json.dumps(rec, indent=1) + "\n")
    d = rec["ds_rom"]
    for k in d["before"]:
        print(f"DS {k}: {d['before'][k]} -> {d['after'][k]} {d['delta_pct'][k]}")
    print("DS PQ basis:", d["pq_adopted_basis"]["before_root_B"], "->", d["pq_adopted_basis"]["after"])
    h = rec["hbm_ds"]
    print("HBM:", h["before"], "->", h["upper"]["after"], h["lower"]["after"])
    for k, v in rec["qwen_rom"]["rows"].items():
        print("Qwen", k, v["before"], "->", v["after"])


if __name__ == "__main__":
    main()
