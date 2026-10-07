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
    ("collective_lane", "Collective slab v3 tiles: all-reduce 320 records +288 cycles over the C8 reference (measured, S81-PH "
                        "src_v3, no bit errors, lane channel 1 cycle; coll_price 2026-10-07).  Replaces x0.9003 = 2,329 / 2,587 "
                        "(absolute TB times incl. the 1,111-cycle preamble, bit-error injection on, against a node priced from "
                        "tb_w15b_v41_tp4).  All-gathers: PENDING-DEFECT (below)", [(k, 288, 0) for k in AR_]),
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

# PENDING-DEFECT (OWNER decision (b), 2026-10-07): measured but not in the headline until the slab is repaired
PENDING = [
    ("collective_ag", "S81 collective tile defects (credits 256 < RTT, ~900-cycle small-AG latency, AG256/1024 exactness "
                      "errors) under repair; measured as-is all-gathers over the C8 reference: 24 rec +914, 57 +922, "
                      "256 +273 (FAIL), 1024 +509 (FAIL), 1056 +516",
     [("*.attn.a_allgather", 922, 0), ("*.attn.idx.topk_merge", 273, 0), ("*.attn.cand.merge", 509, 0),
      ("*.attn.rows_allgather", 516, 0), ("*.ffn.router_allgather", 914, 0)]),
]


def lever(items, pending=False):
    src = ITEMS + (PENDING if pending else [])
    if pending and items is not None:
        items = list(items) + [it for it, _, _ in PENDING]
    adds = [dict(item=it, nodes=n, cycles=c, frac=f, source=desc) for it, desc, rows in src for n, c, f in rows]
    return dict(schema="opentallas.dsrom-recovery.addcycles.v1", lever="s81_die_tiles", verdict="ADOPT", items=items,
                note="S81 die integration + S81 tile closure costs (CLAUDE S81-RERUN), priced per operation on the measured "
                     "composition; the ledger is tools/dsrom_closure_cost_ledger.py", adds=adds)


def compose(items, pending=False):
    LEV.write_text(json.dumps(lever(items, pending), indent=1) + "\n")
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
    LEV.write_text(json.dumps(lever(None), indent=1) + "\n")      # all items (items = None)
    rec = dict(schema="opentallas.dsrom.closure_cost_ledger.v1", baseline=dict(ar_tok_s=ar0, mtp_tok_s=mtp0,
               basis="recovery composition without the S81 closure costs"), items=rows,
               total=dict(ar_tok_s=prev[0], mtp_tok_s=prev[1], ar_pct=rows[-1]["cum_ar_pct"], mtp_pct=rows[-1]["cum_mtp_pct"]),
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
    for it, d_, a_ in PENDING:
        L.append(f"| {it} (PENDING-DEFECT, not in the headline) | {d_} | | | | | |")
    L += ["", f"Measured as-is (PENDING-DEFECT included): AR {asis[0]:,.1f} ({100 * (asis[0] / ar0 - 1):+.2f} %), "
              f"MTP {asis[1]:,.1f} ({100 * (asis[1] / mtp0 - 1):+.2f} %).  The headline uses the table total."]
    (OUT / "ledger.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
