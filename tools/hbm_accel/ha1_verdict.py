#!/usr/bin/env python3
"""HA1 (R1b) gate record: joins the system-context runs (tools/hbm_accel/run_ha1_system.py: reduced Qwen3 and
DeepSeek-V4.1 HBM system tops, base node vs tx-count counters) with the full-die boundary measurement
(tools/hbm_accel/run_ha1_die.py) and prices the measured saving per token on the study's boundary count.

    python3 tools/hbm_accel/ha1_verdict.py --dir results/rtl/hbm_accel_ha1_20261004
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

F = 1.2e9
# results/uarch/hbm_accelerator_study_20261003/ladder_model.py (claude/hbm-accelerator-study-20261003 6a968005d):
# W19_AR barrier 22.29 us at W19_BOUNDARY_CYC 78 -> boundaries on the DS-V4.1 1M AR critical path
N_BOUNDARIES = 22.29 / (78 / F * 1e6)
TOKEN_BASES = {"ablation_2261.7": 2261.7, "ablation_R0c_2188": 2188.0, "model_full_ladder_3015": 3015.0}


def gain(saved_cycles):
    us = N_BOUNDARIES * saved_cycles / F * 1e6
    return dict(saved_us_per_token=round(us, 3),
                per_user_gain_pct={k: round(100 * (1 / (1 / v - us * 1e-6) / v - 1), 3) for k, v in TOKEN_BASES.items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    a = ap.parse_args()
    d = Path(a.dir)
    die = json.loads((d / "die_boundary.json").read_text())
    sysr = {}
    for m in ("qwen", "ds"):
        recs = {k: json.loads((d / f"{m}_{k}.json").read_text()) for k in ("base", "tx") if (d / f"{m}_{k}.json").exists()}
        if len(recs) < 2:
            sysr[m] = dict(status="NOT_RUN", have=sorted(recs), note="whole-system DS runs stopped under the owner minimum-component rule (2026-10-04); exactness rests on the Qwen e2e + unit bench, latency on the die bench")
            continue
        b, t = recs["base"], recs["tx"]
        bb = {x["inst"]: x for x in b["barrier_monitor"]}
        tb = {x["inst"]: x for x in t["barrier_monitor"]}
        sysr[m] = dict(
            exact=dict(base=b["status"], txcount=t["status"],
                       steps=len(t["steps"]), mismatches=sum(1 for s in t["steps"] if s["status"] != "OK")),
            clk_sm_cycles=dict(base=b["clk_sm_cycles"], txcount=t["clk_sm_cycles"],
                               delta=t["clk_sm_cycles"] - b["clk_sm_cycles"]),
            barriers={i: dict(count=bb[i]["barriers"], boundary_sum_base=bb[i]["boundary_sum"],
                              boundary_sum_txcount=tb[i]["boundary_sum"], wait_sum_base=bb[i]["wait_sum"],
                              wait_sum_txcount=tb[i]["wait_sum"]) for i in bb})
    data_saved = die["saved_cycles_per_boundary"]["with_x_data"]
    sync_runs = {r["variant"]: r for r in die["runs"]}
    sync_saved_mean = round(sync_runs[2]["mean"] - sync_runs[1]["mean"], 2)
    rec = dict(
        schema="opentallas.hbm_accel.ha1_verdict.v1", rung="HA1 / R1b tx-count arrival counters (mbarrier-style)",
        price=dict(boundary_cycles=78, target_cycles=47, saved_cycles=31, modelled_saved_us=8.9,
                   source="claude/hbm-accelerator-study-20261003 ladder_model.py (W19_BARRIER_RELEASE_CYC 31)"),
        boundaries_per_token=round(N_BOUNDARIES, 1),
        G_exact=sysr,
        G_latency=dict(die_boundary_cycles=die["boundary_cycles"],
                       measured_boundary_with_x=die["boundary_cycles"]["txcount_x"],
                       target=47, pass_=die["boundary_cycles"]["txcount_x"] <= 47,
                       saved_cycles_with_x=data_saved, saved_cycles_sync_only_max=die["saved_cycles_per_boundary"]["sync_only"],
                       saved_cycles_sync_only_mean=sync_saved_mean),
        G_gain=dict(measured_with_x=gain(data_saved), upper_bound_sync_only_mean=gain(sync_saved_mean),
                    priced=gain(31), pass_=gain(data_saved)["per_user_gain_pct"]["model_full_ladder_3015"] >= 1.0),
        G_area=dict(counter_um2_per_sm_asap7_ss_synth=62.4, counters_um2_per_die=round(62.4 * 32, 1),
                    a2a_link_stage_flops_per_die=die["pair"]["link_stage_flops"],
                    tree_stage_flops_per_die=die["pair"]["tree_stage_flops"], links_per_die=die["pair"]["links"],
                    status="yosys ASAP7 SS cell area of ot_hbm_txcount_arrival K=32 (499 cells, 45 flops); "
                           "link stages counted, not placed"),
        G_route="NOT_RUN (gate order: latency/gain failed first; addendum forbids P&R before the measurement gate passes)",
        G_timing="NOT_RUN (same); the W6 SECDED fence 429 MHz cone is not on this rung's path in the base system "
                 "(W6 is not integrated there) and remains with HA6",
        why=("The release broadcast is not removable latency on this die: every boundary must deliver the next op's x "
             "block from the hub to every SM, over the same root->SM distance the release travels (pipelined with it). "
             "tx-count turns the release into a byte count of that data, which saves only the two AND-node registers "
             "on the up path (79 -> 77). Even a sync-only boundary cannot reach 47: the farthest SM pair is 28.56 mm "
             "Manhattan = 57 stages at 504 um, vs 62 for the tree; the 31-cycle price assumed the down leg vanishes."),
        verdict="REJECT",
        source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.glob("*.json"))
                       if p.name != "verdict.json"})
    (d / "verdict.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("G_latency", "G_gain", "verdict")}, indent=1))
    print(json.dumps(sysr, indent=1)[:3000])


if __name__ == "__main__":
    main()
