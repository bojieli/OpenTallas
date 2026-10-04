#!/usr/bin/env python3
"""Qwen3-8B HBM accelerator, one decode token at position 8,191 (8,192 positions of KV): the fully-measured view of
the exact stage jobs of results/rtl/qwen_hbmacc_p8191_20261004 (one RTL job per layer type + head, HA8 vehicle: W12
exact datapath + r14 weight/KV stream controller on timed HBM3E with REFpb, ot_rom_oneshot_allreduce collective
endpoint), the counterpart of tools/dshbm_1m_allmeasured.py.

Every stage time is a full RTL measurement.  This tool states what inside it is NOT RTL:
  * the collective link latency (ot_rom_oneshot_allreduce LAT: TP2 11 cycles in-package UCIe, TP4 339 cycles board
    link) -- a labelled PHY/link BUDGET; its exposure is bounded by LAT x the collective crossings of each stage
    (2 all-reduces a layer: attention out + FFN out; 1 for the head) -- an upper bound, since in HBM layers the
    collectives overlap the weight stream;
  * the embedding row fetch at token start (~60 cycles, not simulated) and the posted KV write-back (off path);
  * the HBM controller's PHY/NoC path constants inside the timed stream (bench values).
It also re-composes the token at the clocks the blocks close at today (inventory + screens): the HBM controller closes
(r8b, 1,209.6 MHz) and sets the stream; the collective endpoint (ot_rom_oneshot_die, 490 MHz screen) is the only
measured on-path core block that misses 1.2 GHz; the ME spine/array, tile logic, generated core, vstream and wstream
were never closed, so they stay at the target and are listed (the today-rate is an upper bound).

    python3 tools/qwen_hbmacc_p8191_allmeasured.py --out results/rtl/qwen_hbmacc_p8191_20261004/allmeasured.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/rtl/qwen_hbmacc_p8191_20261004"
FMAX = ROOT / "results/rtl/hbm_accel_fmax_inventory_20261004/inventory.json"
F = 1.2e9
DESIGNS = {
    "a_TP2_same_silicon": dict(lat=11, stages=[("L0", 1, "a_p8191/L0", 2), ("L1", 1, "a_p8191_w224/L1", 2),
                                               ("L2", 34, "a_p8191_w224/L2", 2), ("head", 1, "a_p8191_w224_head/head", 1)]),
    "b_TP4_iso_silicon": dict(lat=339, stages=[("L0", 5, "b_p8191_w224/L0", 2), ("L5", 1, "b_p8191_w224/L5", 2),
                                               ("L6", 1, "b_p8191_w224/L6", 2), ("L20", 29, "b_p8191_w224/L20", 2),
                                               ("head", 1, "b_p8191_w224/head", 1)]),
}
EMBED_CYC = 60          # embedding row fetch at token start: NOT simulated (HA8 / P8191 records: about 60 cycles)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def closing():
    inv = {r["module"]: r for r in json.loads(FMAX.read_text())["blocks"]}
    coll = inv["ot_rom_oneshot_die (Qwen collective endpoint)"]
    hbm = inv["ot_hbm_r14_stream_pc/stack r8b (WR_EN=0)"]
    never = [m for m, r in inv.items() if r["family"] in ("qwen-me", "qwen-core") and r["status"] == "never_measured"]
    return dict(coll_mhz=coll["fmax_mhz_equiv_ss"], coll_evidence=coll["evidence"] + " (" + coll["note"] + ")",
                hbm_mhz=hbm["fmax_mhz_equiv_ss"], hbm_evidence=hbm["evidence"],
                never_closed_at_target=never,
                tp_seq=inv["ot_qwen_tp_seq_w12 (N=4)"]["note"])


def stage(name, count, path, ncoll, lat, cl):
    r = json.loads((REC / path / "token_result.json").read_text())
    st = r["stages"][name]
    d = st["die0"]
    cyc = st["cycles"]
    exact = r["status"] == "pass" and sum(c["mismatches"] for c in r["layer_x_checks"].values()) == 0
    budget = min(ncoll * lat, d["collective"])                 # exposed link budget, upper bound
    # today: the endpoint's own collective cycles run at the endpoint's screen fmax; extra time hides in the measured
    # HBM wait (the stream, in its own closed CK/2 domain, is unchanged)
    coll_core = max(0, d["collective"] - budget)
    extra = coll_core * (F / (cl["coll_mhz"] * 1e6) - 1)
    today = cyc + max(0.0, extra - d["hbm_wait"])
    return dict(stage=name, count=count, cycles=cyc, exact=exact, rtl_token=r.get("rtl_token"),
                oracle_token=r.get("oracle_token"), attribution_die0={k: d[k] for k in (
                    "hbm_wait", "kv_wait", "matmul", "attention", "collective", "stream_unit", "other")},
                coll_link_budget_cycles_upper=budget, coll_crossings=ncoll, lat=lat,
                cycles_at_closing_clocks=round(today, 1), source=str((REC / path / "token_result.json").relative_to(ROOT)),
                source_sha256=sha(REC / path / "token_result.json"))


def design(name, spec, cl):
    rows = [stage(n, c, p, k, spec["lat"], cl) for n, c, p, k in spec["stages"]]
    n = sum(r["count"] for r in rows)
    total = 7 + sum(r["cycles"] * r["count"] for r in rows) + (n - 1)
    budget = sum(r["coll_link_budget_cycles_upper"] * r["count"] for r in rows)
    today = 7 + sum(r["cycles_at_closing_clocks"] * r["count"] for r in rows) + (n - 1)
    T = total + EMBED_CYC
    return dict(stages=rows, composed_cycles=total, us=round(total / F * 1e6, 2), ar_tok_s=round(F / total, 1),
                all_exact=all(r["exact"] for r in rows), head_token=rows[-1]["rtl_token"],
                with_embedding_estimate=dict(cycles=T, ar_tok_s=round(F / T, 1)),
                link_budget_cycles_upper=budget,
                measured_share_excl_budget_lower=round((total - budget) / T, 4),
                measured_share_incl_budget=round(total / T, 4),
                at_closing_clocks=dict(cycles=round(today, 1), us=round(today / F * 1e6, 2),
                                       ar_tok_s=round(F / today, 1)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=REC / "allmeasured.json")
    a = ap.parse_args()
    cl = closing()
    res = {k: design(k, v, cl) for k, v in DESIGNS.items()}
    rec = dict(schema="opentallas.hbm-accel-qwen-p8191-allmeasured.v1", position=8191, context=8192,
               base="results/rtl/qwen_hbmacc_p8191_20261004/measured_composition.json (w224 adopted)",
               designs=res, closing_clocks=cl,
               still_modelled=[
                   dict(term="collective link latency LAT (TP2 11 / TP4 339 cycles per crossing)",
                        why="PHY/link BUDGET inside ot_rom_oneshot_allreduce; exposure bounded above per stage"),
                   dict(term="embedding row fetch at token start", cycles=EMBED_CYC, why="not simulated"),
                   dict(term="HBM controller PHY/NoC path constants", why="bench values inside the timed stream"),
                   dict(term="posted KV write-back", why="off the critical path (posted); not simulated for Qwen"),
                   dict(term="window data content", why="arrival timed, data from the stage images"),
                   dict(term="preroll conventions (5,000 ctl cycles L1/L5/L6, 1,000 L20 vs measured tail 1,139)",
                        why="stage-entry convention, conservative"),
                   dict(term="speculative (DFlash/DSpark) rate", why="no measured Qwen HBM-accelerator verify/draft "
                        "record at P8191; not composed here")],
               closing_note="today-rate assumes the slower collective endpoint's extra cycles first hide in the "
                            "measured HBM wait of each stage; the ME/core/vstream/wstream blocks were never closed and "
                            "are kept at 1.2 GHz, so the today-rate is an UPPER bound",
               tool_sha256=sha(Path(__file__)))
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    for k, v in res.items():
        print(k, v["ar_tok_s"], v["with_embedding_estimate"], v["measured_share_excl_budget_lower"],
              v["at_closing_clocks"], v["all_exact"], v["head_token"])
    return rec


if __name__ == "__main__":
    main()
