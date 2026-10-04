#!/usr/bin/env python3
"""Dual-clock campaign of rtl/common/ot_meso_fifo.sv (bench rtl/test/meso/tb_meso_fifo.cpp).

Builds the bench per configuration (DEPTH/OFFSET/guards/credits), sweeps the static phase 0..T between the two
equal-frequency clocks, adds sinusoidal wander placed at its extreme at alignment (so the excursion after placement
is the full 2w peak to peak), drift ramps that must fail closed before any window violation, unilateral resets,
backpressure and streaming, and three mutants that must be caught.  Every run is a digital simulation with a
physical window checker (see the bench header); it is not an MTBF or analog phase proof.

Measured outputs: words, errors, window violations, the placed lag range against the guard thresholds, the
crossing latency (accept edge -> consumer take edge) against the 1-period register stage it replaces, the
round-trip delta (A->B data lag + B->A credit lag - 2T) and streaming throughput.

    python3 tools/meso_fifo_campaign.py --work /path/scratch --out results/uarch/meso_fifo_20261004/campaign.json
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = 1e12 / 1.2e9
RTL = "rtl/common/ot_meso_fifo.sv"
BENCH = "rtl/test/meso/tb_meso_fifo.cpp"
BUILD = "rtl/test/meso/build_tb.sh"

# wander_ps is the one-sided amplitude w of tools/rom_die_clocking_model.py (5 % of non-shared insertion); the
# excursion after placement is 2w.  Placement window OFFSET -+ 0.5 periods; guards at GUARD_LO + 0.5 and
# GUARD_HI - 0.5: margins (OFFSET - GUARD_LO - 1) T and (GUARD_HI - OFFSET - 1) T must exceed 2w plus resolution.
CONFIGS = {
    "d4_central": dict(depth=4, offset=2, glo=0, ghi=4, credits=8, wander=192.0, phases=32, cycles=1_000_000),
    "d8_tt_routed": dict(depth=8, offset=3, glo=0, ghi=6, credits=16, wander=774.0, phases=16, cycles=400_000),
    "d16_bound_ss": dict(depth=16, offset=5, glo=0, ghi=10, credits=16, wander=1452.5, phases=16, cycles=400_000),
}
OUT_REG_PERIODS = 1          # r_d is registered (the crossing's capture register)
MUTANTS = {"OFFSET": "random", "NO_GUARD": "drift", "EARLY_CREDIT": "bp"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build(work: Path, name: str, c: dict, define: str = "") -> Path:
    out = work / name
    subprocess.run([str(ROOT / BUILD), str(out), str(c["depth"]), str(c["offset"]), str(c["glo"]), str(c["ghi"]),
                    str(c["credits"]), define], check=True, capture_output=True)
    return out / "tb"


def run(tb: Path, **kw) -> dict:
    args = [str(tb)] + [f"+{k}={v}" for k, v in kw.items()]
    p = subprocess.run(args, capture_output=True, text=True)
    lines = [l for l in p.stdout.splitlines() if l.startswith("{")]
    rec = json.loads(lines[-1]) if lines else dict(errors=-1)
    rec["rc"] = p.returncode
    rec["args"] = kw
    rec["error_lines"] = [l for l in p.stdout.splitlines() if l.startswith("ERROR")][:3]
    return rec


def phases(n: int) -> list:
    base = [round(i * T / n, 3) for i in range(n)]
    return sorted(set(base + [1.0, 4.0, 12.0, round(T - 12, 3), round(T - 4, 3)]))


def plan(cfg: dict) -> list:
    jobs = []
    w = cfg["wander"]
    for i, ph in enumerate(phases(cfg["phases"])):
        wph = math.pi / 2 if i % 2 == 0 else -math.pi / 2          # wander at +w or -w when the pointer is placed
        for mode in ("sparse", "stream", "random", "bp", "reset"):
            cyc = cfg["cycles"] if mode != "sparse" else cfg["cycles"] // 2
            jobs.append(dict(kind="nominal", mode=mode, phase=ph, wander=0, cycles=cyc, seed=11 + i, credits=cfg["credits"]))
            jobs.append(dict(kind="nominal", mode=mode, phase=ph, wander=w, wph=round(wph, 6),
                             wperiod=20000 if mode != "stream" else 200000, cycles=cyc, seed=101 + i,
                             credits=cfg["credits"]))
    for i, ph in enumerate(phases(8)):
        for dr in (0.02, -0.02, 0.5, -0.5, 2.0, -2.0):
            cyc = int(min(4_000_000, max(50_000, 3.5 * T * (cfg["ghi"] + 1) / abs(dr))))
            jobs.append(dict(kind="drift", mode="drift", phase=ph, drift=dr, expfault=1, cycles=cyc, seed=201 + i,
                             credits=cfg["credits"]))
    return jobs


def summarise(cfg: dict, recs: list) -> dict:
    nom = [r for r in recs if r["kind"] == "nominal"]
    drf = [r for r in recs if r["kind"] == "drift"]
    lag_lo_guard = (cfg["glo"] + 0.5) * T
    lag_hi_guard = (cfg["ghi"] - 0.5) * T
    dl = [r["data_lag_ps"] for r in nom] + [r["credit_lag_ps"] for r in nom]
    lags = [x for pair in dl for x in pair if abs(x) < 1e17]
    sparse = [r for r in nom if r["mode"] == "sparse" and r["latency_periods"]["n"] > 0]
    s0 = [r for r in sparse if r["wander_ps"] == 0]
    sw = [r for r in sparse if r["wander_ps"] != 0]

    def lat(rs):
        d = [r["latency_periods"]["mean"] - 1.0 for r in rs]
        mn = [r["latency_periods"]["min"] - 1.0 for r in rs]
        mx = [r["latency_periods"]["max"] - 1.0 for r in rs]
        edges = {}
        for r in rs:
            for k, v in r["latency_edges"].items():
                edges[k] = edges.get(k, 0) + v
        tot = sum(edges.values())
        return dict(runs=len(rs), delta_periods_mean_over_phases=round(sum(d) / len(d), 4),
                    delta_periods_min=round(min(mn), 4), delta_periods_max=round(max(mx), 4),
                    consumer_edges_histogram=edges,
                    delta_edges_mean=round(sum((int(k) - 1) * v for k, v in edges.items()) / tot, 4) if tot else None)

    # round trip A->B->A: the two ring lags plus one output (capture) register period on each side, against the two
    # register stages it replaces; consistent with the measured crossing latency = ring lag + 1 period
    rt = [round((r["data_lag0_ps"] + r["credit_lag0_ps"]) / T + 2 * OUT_REG_PERIODS - 2.0, 3) for r in s0]
    rt_int = {}
    for x in rt:
        k = str(round(x))
        rt_int[k] = rt_int.get(k, 0) + 1
    streams = [r["throughput_words_per_cycle"] for r in nom if r["mode"] == "stream"]
    return dict(
        config=cfg,
        guards_ps=dict(low_trip_below=round(lag_lo_guard, 1), high_trip_above=round(lag_hi_guard, 1),
                       data_arc_budget_ps=round(lag_lo_guard - 60, 3)),
        nominal=dict(runs=len(nom), words_delivered=sum(r["delivered"] for r in nom),
                     cycles=sum(r["cycles"] for r in nom),
                     errors=sum(max(r["errors"], 0) for r in nom) + sum(1 for r in nom if r["errors"] < 0),
                     failing_runs=[dict(args=r["args"], err=r["error_lines"]) for r in nom if r["rc"] != 0][:5],
                     window_checks=sum(r["window_checks"] for r in nom),
                     window_violations=sum(r["window_violations"] for r in nom),
                     faults=sum(r["fault"] for r in nom), resets=sum(r["resets"] for r in nom),
                     lag_ps_range=[round(min(lags), 1), round(max(lags), 1)],
                     margin_to_low_guard_ps=round(min(lags) - lag_lo_guard, 1),
                     margin_to_high_guard_ps=round(lag_hi_guard - max(lags), 1),
                     stream_throughput_min=min(streams)),
        latency_no_wander=lat(s0), latency_wander=lat(sw),
        round_trip_delta_periods=dict(values=sorted(rt), integer_histogram=rt_int,
                                      mean=round(sum(rt) / len(rt), 4), max=max(rt), min=min(rt)),
        drift=dict(runs=len(drf), all_faulted=all(r["fault"] == 1 for r in drf),
                   violation_before_fault=sum(1 for r in drf if r["t_first_violation_ps"] >= 0 and
                                              (r["t_fault_ps"] < 0 or r["t_first_violation_ps"] < r["t_fault_ps"])),
                   errors=sum(max(r["errors"], 0) for r in drf),
                   failing_runs=[dict(args=r["args"], err=r["error_lines"]) for r in drf if r["rc"] != 0][:5],
                   lag_ps_range_before_fault=[round(min(x for r in drf for x in (r["data_lag_ps"][0], r["credit_lag_ps"][0])), 1),
                                              round(max(x for r in drf for x in (r["data_lag_ps"][1], r["credit_lag_ps"][1]) if x < 1e17), 1)]),
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=max(4, (os.cpu_count() or 8) // 2))
    ap.add_argument("--configs", default=",".join(CONFIGS))
    a = ap.parse_args(argv)
    a.work.mkdir(parents=True, exist_ok=True)
    out = dict(schema="opentallas.meso_fifo.campaign.v1", scope="DIGITAL_ONLY dual-clock RTL simulation with a "
               "physical lag-window checker; edges closer than 20 ps processed in random order; not an MTBF proof",
               period_ps=round(T, 3), sources={p: sha(ROOT / p) for p in (RTL, BENCH, BUILD, "tools/meso_fifo_campaign.py")},
               configs={}, mutants={})
    git = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", RTL, BENCH, BUILD],
                           capture_output=True, text=True).stdout.strip()
    out["git"] = dict(head=git, sources_dirty=bool(dirty))
    for name in a.configs.split(","):
        cfg = CONFIGS[name]
        tb = build(a.work, name, cfg)
        jobs = plan(cfg)
        with ThreadPoolExecutor(a.jobs) as ex:
            recs = list(ex.map(lambda j: {**run(tb, **{k: v for k, v in j.items() if k != "kind"}), "kind": j["kind"]}, jobs))
        (a.work / f"{name}_runs.json").write_text(json.dumps(recs))
        out["configs"][name] = summarise(cfg, recs)
        print(name, json.dumps(out["configs"][name]["nominal"]), flush=True)
    cfg = CONFIGS["d4_central"]
    for mut, mode in MUTANTS.items():
        tb = build(a.work, f"mut_{mut}", cfg, f"OT_MESO_MUTANT_{mut}")
        recs = []
        for i, ph in enumerate(phases(8)):
            kw = dict(mode=mode, phase=ph, cycles=200000, seed=301 + i, credits=cfg["credits"])
            if mode == "drift":
                kw.update(drift=0.5, expfault=1)
            else:
                kw.update(wander=cfg["wander"])
            recs.append(run(tb, **kw))
        caught = sum(1 for r in recs if r["rc"] != 0)
        out["mutants"][mut] = dict(mode=mode, runs=len(recs), caught=caught, all_caught=caught == len(recs),
                                   example=recs[0]["error_lines"][:2])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["mutants"]))


if __name__ == "__main__":
    main()
