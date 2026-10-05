#!/usr/bin/env python3
"""HA3: assemble the measured record (results/rtl/hbm_accel_ha3_20261004/measured.json) from the system runs, their
per-collective section measurements, the epilogue gate and the physical in-context results, with the per-user gain
projection and the verdicts.  Inputs are the JSON files the other HA3 tools wrote (paths on the command line).

    python3 tools/hbm_accel_ha3_record.py --qwen-measure q.json --qwen-measure-f7 d.json --qwen-runs DIR --ds-runs DIR \
        --gate gate.json [--phys DIR] --out results/rtl/hbm_accel_ha3_20261004/measured.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F_SM = 1.2e9
# full-shape ablation model (claude/hbm-accelerator-study-20261003 ladder_model.py): DS AR token parts (us) and counts
DS_AR_US = dict(sm=70.58, barrier=22.29, collective=240.46, local=103.48, fetch=5.33)
DS_COLLECTIVES = 265
DS_MODEL_R3A_NS = 148 / 2 / 1.09864           # the transferred Qwen ROM cut-through figure, ns per collective
DS_MODEL_R3B_US = 6.1
QWEN_LAYERS, QWEN_AR_PER_LAYER = 36, 2


def load(p):
    return json.loads(Path(p).read_text())


def compose(runs, qm):
    """Per-collective saving from the measured system runs, then per-token analytically (full shape)."""
    st = lambda k: sum(x[3] for x in runs[k]["steps"])
    q0, qc, qe = st("qwen:A0"), st("qwen:C"), st("qwen:E")
    q1f7, qcf7, qef7 = st("qwen:A1f7"), st("qwen:Cf7"), st("qwen:Ef7")
    d0, dc = st("v41:A0"), st("v41:C")
    q_layers, q_steps, ds_layers, ds_steps = 4, 18, 40, 1
    q_per_ar = (q0 - qc) / (q_steps * q_layers * 2)
    ds_per_x = (d0 - dc) / (ds_steps * ds_layers * 3)
    b = qm["base_h0"]["breakdown_mean"]
    bar_per_ar = (b["ar_o_barrier_wait"] + b["ar_d_barrier_wait"]) / 2
    ns = lambda cyc: cyc / F_SM * 1e9
    lo_ns, hi_ns = ns(q_per_ar - bar_per_ar), ns(max(q_per_ar, ds_per_x))
    t_abl = sum(DS_AR_US.values())
    t_sw = t_abl - DS_AR_US["collective"] + DS_COLLECTIVES * 2 * 130e-3
    gain = lambda saved_us, t: 1 / (1 - saved_us / t) - 1
    ds_lo, ds_hi = DS_COLLECTIVES * lo_ns * 1e-3, DS_COLLECTIVES * hi_ns * 1e-3
    q_tok_us = 1e6 / 1051.0
    q_lo, q_hi = QWEN_LAYERS * QWEN_AR_PER_LAYER * lo_ns * 1e-3, QWEN_LAYERS * QWEN_AR_PER_LAYER * ns(q_per_ar) * 1e-3
    return dict(
        measured_reduced_system=dict(
            qwen_step_cycles=dict(base_ha3_0=q0, cut=qc, fuseo=qe, base_ha3_1_flat7=q1f7, cut_flat7=qcf7, fuseo_flat7=qef7),
            qwen_r3a_rate_gain=gain(q0 - qc, q0), qwen_r3a_flat7_rate_gain_vs_ha3_1_base=gain(q1f7 - qcf7, q1f7),
            qwen_r3b_over_r3a_rate_gain=gain(qc - qe, qc), qwen_r3b_over_r3a_flat7_rate_gain=gain(qcf7 - qef7, qcf7),
            ds_step_cycles=dict(base_ha3_0=d0, cut=dc), ds_r3a_rate_gain=gain(d0 - dc, d0),
            qwen_saved_cycles_per_all_reduce=round(q_per_ar, 1), ds_saved_cycles_per_exchange=round(ds_per_x, 1),
            qwen_barrier_wait_cycles_per_all_reduce_removed=round(bar_per_ar, 1),
            model_transferred_ns_per_collective=round(DS_MODEL_R3A_NS, 1),
            measured_ns_per_collective=dict(excluding_barriers=round(lo_ns, 1), qwen_all=round(ns(q_per_ar), 1),
                                            ds_exchange=round(ns(ds_per_x), 1))),
        full_shape_analytic=dict(
            basis="per-collective saving (measured, clk_sm 1.2 GHz) x collectives per token; the removed work is SM/L2 "
                  "side of the endpoint (store, fence, grid barrier, single-SM reload, result store, barrier, reload), "
                  "independent of the switch hop latency; low = barrier waits excluded (they overlap HA1/R1b's "
                  "boundary term), high = the measured saving whole",
            ds=dict(collectives=DS_COLLECTIVES, saved_us=[round(ds_lo, 1), round(ds_hi, 1)],
                    ablation_token_us=round(t_abl, 2),
                    rate_gain_vs_ablation=[round(gain(ds_lo, t_abl), 4), round(gain(ds_hi, t_abl), 4)],
                    switch130_token_us=round(t_sw, 2),
                    switch130_basis="ablation parts with the collective term replaced by 2 light-FEC hops of 130 ns "
                                    "per collective (the matched switch baseline)",
                    rate_gain_vs_switch130=[round(gain(ds_lo, t_sw), 4), round(gain(ds_hi, t_sw), 4)],
                    model_r3a_us=round(DS_COLLECTIVES * DS_MODEL_R3A_NS * 1e-3, 1)),
            qwen=dict(all_reduces=QWEN_LAYERS * QWEN_AR_PER_LAYER, saved_us=[round(q_lo, 1), round(q_hi, 1)],
                      token_us_model=round(q_tok_us, 1),
                      rate_gain=[round(gain(q_lo, q_tok_us), 4), round(gain(q_hi, q_tok_us), 4)],
                      caveat="W13b (f984ba8d) finds the full-shape Qwen HBM token HBM-bound with the bulk copy "
                             "prefetching through boundaries, which can hide dependent latency; the reduced system "
                             "does not hide it (measured +4.1%)")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qwen-measure", required=True)
    ap.add_argument("--qwen-measure-f7", required=True)
    ap.add_argument("--qwen-runs", required=True)
    ap.add_argument("--ds-runs", required=True)
    ap.add_argument("--gate", required=True)
    ap.add_argument("--phys")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    qm, dm, gate = load(a.qwen_measure), load(a.qwen_measure_f7), load(a.gate)
    runs = {}
    for d in (a.qwen_runs, a.ds_runs):
        for p in sorted(Path(d).glob("run_*.json")):
            r = load(p)
            runs[f"{r['model']}:{p.stem[4:]}"] = dict(
                mode=r["mode"], ha3=r["ha3"], flat=r.get("flat", 5), status=r["status"], clk_sm_cycles=r["clk_sm_cycles"],
                steps=[(s["pos"], s["next"], s["status"], s["step_cycles"]) for s in r["steps"]],
                expected=[(s["pos"], s["next"]) for s in r["expected_steps"]], wall_seconds=r["wall_seconds"],
                source_sha256=r["source_sha256"])
    rec = dict(schema="opentallas.hbm_accel.ha3_measured.v1",
               source_commit=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                            text=True).stdout.strip(),
               runs=runs, qwen_sections_flat5=qm, qwen_sections_flat7=dm,
               epilogue_gate=dict(status=gate["status"], counts=gate["counts"], n_cases=gate["n_cases"],
                                  resolves=gate["resolves"]))
    rec["composition"] = compose(runs, qm)
    if a.phys:
        rec["physical"] = {p.stem: load(p) for p in sorted(Path(a.phys).glob("*.json"))}
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
