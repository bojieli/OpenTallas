#!/usr/bin/env python3
"""DS closure-cost ledger (CLAUDE S81-RERUN, 2026-10-07): the S81 die + tile closure costs priced into the DS headline,
one item at a time, cumulative, like the HBM ledger.  Writes results/rtl/dsrom_recovery_20261004/levers/s81_die_tiles.json
(addcycles schema, every item enabled) and results/rtl/dsrom_closure_cost_ledger_20261007/ledger.{json,md}.

    python3 tools/dsrom_closure_cost_ledger.py
"""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
LEV = ROOT / "results/rtl/dsrom_recovery_20261004/levers/s81_die_tiles.json"
OUT = ROOT / "results/rtl/dsrom_closure_cost_ledger_20261007"
MAT = ["*.attn.a_proj", "*.attn.wq_b", "*.attn.cmp.wk", "*.attn.wo_a", "*.attn.wo_b", "*.ffn.router", "*.ffn.shared_gu",
       "*.ffn.experts_gu", "*.ffn.down"]                         # ROM field phases (one VM read / gather / capture each)
HBM = ["*.attn.idx.score", "*.attn.scores", "*.attn.pv"]          # HBM stream reads through the controller tiles
AR_ = ["*.attn.out_allreduce", "*.ffn.combine_allreduce"]
AG_ = ["*.attn.a_allgather", "*.attn.idx.topk_merge", "*.attn.cand.merge", "*.attn.rows_allgather", "*.ffn.router_allgather"]
# (item, description, [(nodes, cycles, frac)])
ITEMS = [
    ("s81_die", "S81 v6b die: field round trip 165 vs 137 at the same frame, less the meso d8g1 term (+24): hub stations, "
                "q banks, column relays, 215 um common-clock hops, budget-sheet hop stations, column FIFO v2 (+2)",
     [(k, 24, 0) for k in MAT]),
    ("meso_d8g1", "meso FIFOs d8g1 (DEPTH 8 / OFFSET 4 / GUARD_LO 1): +1 per crossing over d8, +2 over d4: 2 crossings a field "
                  "round trip (+4)", [(k, 4, 0) for k in MAT]),
    ("ctrl_status", "CTRL status chain: +1 cycle per column (HBM stream reads)", [(k, 1, 0) for k in HBM]),
    ("collective_lane", "Collective slab v4 tiles (S81-PH f4b4e0a71: EDEPTH 512, link-up gate; bench_v4 coll_price, trained "
                        "links, no bit errors, lane channel 1 cycle) over the C8 reference: all-reduce 320 rec +131 (CHB 251: "
                        "709 vs w15b 690); all-gather 24 rec +38, 57 +50, 256 +113, 1024 +348, 1056 +361",
     [(k, 131, 0) for k in AR_] + [("*.attn.a_allgather", 50, 0), ("*.attn.idx.topk_merge", 113, 0),
                                   ("*.attn.cand.merge", 348, 0), ("*.attn.rows_allgather", 361, 0),
                                   ("*.ffn.router_allgather", 38, 0)]),
    ("link_split", "SerDes tx / rx through two 256-b half-span stations (--link-split; 1,122 um pin span, last hop <= 281 "
                   "um): +1 cycle per direction per traversal: stage hops +2, token return 8 traversals +16, TP4 "
                   "all-reduce 2 traversals +4, all-gather +2",
     [("*.substage_hop0", 2, 0), ("*.substage_hop1", 2, 0), ("head.hop", 2, 0), ("token.return", 16, 0)]
     + [(k, 4, 0) for k in AR_] + [(k, 2, 0) for k in AG_]),
    ("sel_xstg", "Selector / collector crossing stages (--sel-xstg: d8g1 meso FIFO with registered pins on the end block "
                 "-> band block buses, 382-385 ps crossings): +6 cycles per selector segment / collector job",
     [(k, 6, 0) for k in ("*.attn.idx.topk_local", "*.attn.cand.topk_local", "*.attn.gather")]),
    ("vm_bank_group", "VM bank-group chain: read latency 10 -> 18 (+8 a field phase)", [(k, 8, 0) for k in MAT]),
    ("gather_root_v4", "Gather root v4: +6 cycles per phase", [(k, 6, 0) for k in MAT]),
    ("capture", "Capture tiles: VM write +3 a phase", [(k, 3, 0) for k in MAT]),
    ("selector", "Selector tiles: +20 a segment (mean; +15 max)", [(k, 20, 0) for k in ("*.attn.idx.topk_local", "*.attn.cand.topk_local")]),
    ("collector", "Collector tiles: +2 a job", [("*.attn.gather", 2, 0)]),
    ("svc_io", "Scan service IO hub / per-PC tiles: one register each way (+2 a request)", [(k, 2, 0) for k in HBM]),
    ("softmax_safe_div", "Softmax SAFE divider: +29 on normalize", [("*.attn.normalize", 29, 0)]),
    # code_pair (LAT_DELTA 11 a field phase) removed 2026-10-07: ot_qwen_hbm_code_pair_margin is a Qwen HBM-accelerator
    # code-tile block, not on the DS ROM path (no DS ROM / S81 instance)
    ("bf_rowfix", "BF rowfix: +1 per push (a field phase)", [(k, 1, 0) for k in MAT]),
    ("pq_qelem", "PQ q-element: decode stage +0.17 % node time (field phases)", [(k, 0, 0.0017) for k in MAT]),
]

def su_xing_nodes():
    """non-hop nodes with a dependency in the other clock domain (uarch_model SLOW_KINDS rule, as apply_cdc)"""
    sys.path.insert(0, str(ROOT / "tools"))
    import dsrom_1m_allmeasured as A
    import uarch_model as u
    _, g, _ = A.base_graph()
    out = []
    for n, nd in g.nodes.items():
        if nd.get("kind") in ("hop", "join"):
            continue
        sl = nd["kind"] in u.SLOW_KINDS
        if any((g.nodes[d]["kind"] in u.SLOW_KINDS) != sl for d in nd["deps"] if g.nodes[d]["kind"] != "join"):
            out.append(n)
    return sorted(out)


ITEMS.append(("su_meso_d8g1", "SU crossings through the d8g1 meso FIFO (fullsys_recheck_20261007/ds_su_xing, 64/64 phases "
                              "exact): +2.5 ns (+3 fast cycles) each way vs the d4 crossing in su_cdc, on every slow<->fast "
                              "edge consumer", [(n, 3, 0) for n in su_xing_nodes()]))


# PENDING-DEFECT (OWNER decision (b), 2026-10-07): measured but not in the headline until the slab is repaired
PENDING = []   # collective all-gathers lifted 2026-10-07 (slab v4 fixes the three coll_price defects)
# CANDIDATES: closure fixes priced but not adopted (each composed alone on top of every adopted item)
CANDIDATES = [
    ("fh_half", "DSpark fused head SAFE half-rate backstop (whole draft-core domain on the die clock / 2; gold4 OT_FH_HALF "
                "EXACT 126,310 die cycles vs 63,153, claude/takeover-ds-head-20261006 7d63728a0): draft head occupancy x2 "
                "(+8,387 cyc = 6.9892 us a draft position); adopt only for a view whose full-rate route misses",
     [("draft.head_occ", 8387, 0)]),
    ("head_elem", "lm_head element A/B (ot_dsrom_head_elem IOREG + SAFE argmax + CUT 511 + fadd SPLIT9): bundle EXACT "
                  "8,357 -> 8,414 (+57 a sweep); on head.lm_head and on every draft head sweep (elemB CLOSED 9adbc6104; elemA routing)",
     [("head.lm_head", 57, 0), ("draft.head_occ", 57, 0)]),
    ("fused_head", "DSpark fused head r4 structure (8 hquad LRET + ctl SAFE2 + endpoint FPIPE3, QPIN): gold4 EXACT "
                   "63,028 -> 63,153 (+125 per gamma-5 draft = +25 a draft position; ctl/ep/hquad views routing)", [("draft.head_occ", 25, 0)]),
    ("bf_half", "BF SAFE B: element at half rate (ot_s81_bf_native HALF=1, claude/dsrom-bf-rowfix-20261007 61c1cf230, "
                "exact PASS; closure-loop bf_half_61c1cf230): BF16 field phases doubled (upper bound; fracs = BF16 phase "
                "share (go->idle+1)/node, field_qelem_qx10.json, a_proj max over layer types); adopt only if B closes "
                "first (variant A re-cut is the target).  UNDER-PRICED: BF pairs also hold 20.6 % of the q words, so HALF=1 on "
                "shared pairs doubles those q phases too (the BF-dedicated-pair plan of the BF doubling agent replaces it)",
     [("*.attn.wo_a", 0, 0.8789), ("*.ffn.router", 0, 0.8976), ("*.attn.a_proj", 0, 0.7037), ("*.attn.cmp.wk", 0, 0.7748)]),
    ("bf_recut", "BF re-cut A (ot_s81_bf_native RECUT=2, claude/dsrom-bf-rowfix-20261007 260869fd0; exact record e2d358837; "
                 "closure-loop bf_recut_260869fd0): latency only, transaction lag per partial 4 / 7.9 / 15; upper bound "
                 "+15 per field phase (wo_a 4 phases, a_proj 3)",
     [("*.attn.wo_a", 60, 0), ("*.attn.a_proj", 45, 0), ("*.ffn.router", 15, 0), ("*.attn.cmp.wk", 15, 0),
      ("*.attn.wq_b", 15, 0), ("*.attn.wo_b", 15, 0), ("*.ffn.shared_gu", 15, 0), ("*.ffn.experts_gu", 15, 0),
      ("*.ffn.down", 15, 0)]),
    ("bf_unroll", "BF unroll-by-2 (ot_s81_bf_native RECUT=3, claude/dsrom-bf-rowfix-20261007 9cf64047e; exact record c394c0ace; "
                  "closure-loop bf_unroll_9cf64047e): re-cut A + lane chains unrolled by 2 on a half-rate gated clock, latency "
                  "only, lag per partial 4 / 8.8 / 18; upper bound +18 per field phase",
     [("*.attn.wo_a", 72, 0), ("*.attn.a_proj", 54, 0), ("*.ffn.router", 18, 0), ("*.attn.cmp.wk", 18, 0),
      ("*.attn.wq_b", 18, 0), ("*.attn.wo_b", 18, 0), ("*.ffn.shared_gu", 18, 0), ("*.ffn.experts_gu", 18, 0),
      ("*.ffn.down", 18, 0)]),
]


def lever(items, pending=False, extra=()):
    src = ITEMS + (PENDING if pending else []) + list(extra)
    if pending and items is not None:
        items = list(items) + [it for it, _, _ in PENDING]
    if extra and items is not None:
        items = list(items) + [it for it, _, _ in extra]
    adds = [dict(item=it, nodes=n, cycles=c, frac=f, source=desc) for it, desc, rows in src for n, c, f in rows]
    return dict(schema="opentallas.dsrom-recovery.addcycles.v1", lever="s81_die_tiles", verdict="ADOPT", items=items,
                note="S81 die integration + S81 tile closure costs (CLAUDE S81-RERUN), priced per operation on the measured "
                     "composition; the ledger is tools/dsrom_closure_cost_ledger.py", adds=adds)


def compose(items, pending=False, extra=()):
    LEV.write_text(json.dumps(lever(items, pending, extra), indent=1) + "\n")
    tmp = OUT / "tmp.json"
    subprocess.run([sys.executable, str(ROOT / "tools/dsrom_1m_allmeasured.py"), "--out", str(tmp)], check=True,
                   capture_output=True)
    d = json.loads(tmp.read_text()); tmp.unlink()
    return d["AR_tok_s"], d["MTP"]["MTP_tok_s"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ar0, mtp0 = compose([])
    rows, en, prev = [], [], (ar0, mtp0)
    for it, desc, adds in ITEMS:
        en.append(it)
        ar, mtp = compose(list(en))
        rows.append(dict(item=it, description=desc, cycles=sorted({(n, c, round(f, 4)) for n, c, f in adds})[:3],
                         ar_tok_s=ar, mtp_tok_s=mtp, ar_pct=round(100 * (ar / prev[0] - 1), 3),
                         mtp_pct=round(100 * (mtp / prev[1] - 1), 3), cum_ar_pct=round(100 * (ar / ar0 - 1), 3),
                         cum_mtp_pct=round(100 * (mtp / mtp0 - 1), 3)))
        prev = (ar, mtp)
    asis = compose([it for it, _, _ in ITEMS], pending=True)
    cand = {c[0]: compose([it for it, _, _ in ITEMS], extra=[c]) for c in CANDIDATES}
    LEV.write_text(json.dumps(lever(None), indent=1) + "\n")      # all items (items = None)
    rec = dict(schema="opentallas.dsrom.closure_cost_ledger.v1", baseline=dict(ar_tok_s=ar0, mtp_tok_s=mtp0,
               basis="recovery composition without the S81 closure costs"), items=rows,
               total=dict(ar_tok_s=prev[0], mtp_tok_s=prev[1], ar_pct=rows[-1]["cum_ar_pct"], mtp_pct=rows[-1]["cum_mtp_pct"]),
               candidates=[dict(item=it, description=d_, adds=a_, ar_tok_s=cand[it][0], mtp_tok_s=cand[it][1],
                                ar_pct_vs_total=round(100 * (cand[it][0] / prev[0] - 1), 3),
                                mtp_pct_vs_total=round(100 * (cand[it][1] / prev[1] - 1), 3)) for it, d_, a_ in CANDIDATES],
               pending_defect=[dict(item=it, description=d_, adds=a_) for it, d_, a_ in PENDING],
               as_is=dict(ar_tok_s=asis[0], mtp_tok_s=asis[1], ar_pct=round(100 * (asis[0] / ar0 - 1), 3),
                          mtp_pct=round(100 * (asis[1] / mtp0 - 1), 3), basis="every item + the PENDING-DEFECT all-gathers"))
    (OUT / "ledger.json").write_text(json.dumps(rec, indent=1) + "\n")
    L = ["# DS closure-cost ledger (S81 die + tiles)", "", f"Pre-closure DS AR {ar0:,.1f} tok/s, MTP {mtp0:,.1f} tok/s.", "",
         "| item | cost | AR tok/s | AR % | MTP % | cum AR % | cum MTP % |", "|---|---|---:|---:|---:|---:|---:|"]
    for r in rows:
        L.append(f"| {r['item']} | {r['description']} | {r['ar_tok_s']:,.1f} | {r['ar_pct']:+.2f} | {r['mtp_pct']:+.2f} | "
                 f"{r['cum_ar_pct']:+.2f} | {r['cum_mtp_pct']:+.2f} |")
    L.append(f"| **TOTAL** | | **{prev[0]:,.1f}** (MTP {prev[1]:,.1f}) | | | **{rows[-1]['cum_ar_pct']:+.2f}** | "
             f"**{rows[-1]['cum_mtp_pct']:+.2f}** |")
    for it, d_, a_ in CANDIDATES:
        ar_, mt_ = cand[it]
        L.append(f"| {it} (CANDIDATE, not adopted) | {d_} | {ar_:,.1f} | {100 * (ar_ / prev[0] - 1):+.2f} | "
                 f"{100 * (mt_ / prev[1] - 1):+.2f} | | |")
    for it, d_, a_ in PENDING:
        L.append(f"| {it} (PENDING-DEFECT, not in the headline) | {d_} | | | | | |")
    L += ["", f"Measured as-is (PENDING-DEFECT included): AR {asis[0]:,.1f} ({100 * (asis[0] / ar0 - 1):+.2f} %), "
              f"MTP {asis[1]:,.1f} ({100 * (asis[1] / mtp0 - 1):+.2f} %).  The headline uses the table total."]
    (OUT / "ledger.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
