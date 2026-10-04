#!/usr/bin/env python3
"""Compose the layer-parallel REAL_MEM full Qwen3-8B ROM token (E, L0..L35, head) at one position.

Input: a run root holding one directory per job (tools/qwen_rom_rt_token_w12_rm.py --result result.json and its
workdir w/token.log), each job one stage entered from the golden exit of the previous stage (the GPU position
oracle, tools/qwen_rom_position_oracle_gpu.py), plus optional chained jobs ("A+B+C") and --kv-ideal A/B twins
("<stage>-ideal").  Per stage: exactness (every die's X, the token K/V written back to HBM, the head token and
logit), cycles and memory stalls.  Chain links: the entry of stage k is byte-equal to the golden exit of k-1 (and
the golden itself is checked against the CPU golden by golden/crosscheck.json).  Composition: an isolated stage is
started by the wrapper (counted from cycle 7, sampled at 8) and so measures one cycle more than the same stage
entered by the host's h_start in a chained run; the chained jobs measure the actual chained cycles and the residue
of the previous stage's memory state (HBM refresh/row state, drained writes), and the composed token uses
    E + sum_k (isolated_k - 1) + one host cycle per stage switch + 7 (wrapper start)
exactly as tools/qwen_rom_layer_parallel_sim.py composes, reported beside the chained evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(job: Path):
    r = json.loads((job / "result.json").read_text()) if (job / "result.json").exists() else None
    log = (job / "w" / "token.log").read_text() if (job / "w" / "token.log").exists() else ""
    t = (job / "time.txt").read_text().split() if (job / "time.txt").exists() else []
    return r, log, t


def stage_info(r, log, name):
    s = r["stages"].get(name, {}) if r else {}
    mem = s.get("memory", {})
    ex = all(v["mismatches"] == 0 for k, v in r["layer_x_checks"].items() if k.startswith(name + "_")) if r else False
    kv = all(v["k_mismatches"] == 0 and v["v_mismatches"] == 0 for k, v in r["token_kv_writeback_checks"].items()
             if k == name or k.startswith(name + "_")) if r else False
    if name == "head":
        ex = bool(r and r.get("head_check") and r["head_check"]["exact"])
    m = re.search(rf"STAGE {re.escape(name)} done .*?seq_fault=(\d+) core_fault=(\d+) coll_fault=(\d+)", log)
    faults = [int(x) for x in m.groups()] if m else None
    keys = ("stall_kv", "stall_drain", "stall_bridge", "stall_mem", "stall_retire", "fill_cycles", "wr_lat_max")
    return {"cycles": s.get("cycles"), "exact": ex, "kv_writeback_exact": kv, "faults": faults,
            "memory_max_over_dies": {k: max((d.get(k, 0) for d in mem.values()), default=0) for k in keys}}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", type=Path, required=True, help="runs/P<P> directory")
    ap.add_argument("--gold", type=Path, required=True, help="golden P directory (L<nn>_die<d>_x.hex, head.json)")
    ap.add_argument("--pos", type=int, required=True)
    ap.add_argument("--ideal-token-cycles", type=int, default=144522,
                    help="ideal-memory AR256 full token (P0, layer-parallel, results/rtl/qwen_rom_TP4_allreduce_oneseg_fulltoken_20261003)")
    ap.add_argument("--ideal-layer-cycles", type=int, default=3930)
    ap.add_argument("--clock-ghz", type=float, default=1.2)
    ap.add_argument("--extra-job", type=Path, action="append", default=[], help="further job dirs (e.g. a chained run elsewhere)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    order = ["E"] + [f"L{n}" for n in range(36)] + ["head"]
    singles, chained, ideal = {}, {}, {}
    for job in sorted([p for p in a.runs.iterdir() if p.is_dir()] + list(a.extra_job)):
        r, log, t = load(job)
        rec = {"job": job.name, "status": r["status"] if r else None, "exit": (job / "exit").read_text().strip() if (job / "exit").exists() else None,
               "result_sha256": sha(job / "result.json") if r else None,
               "time_max_rss_kib_wall_user_sys": t, "x_entry_sha256": r.get("x_entry_sha256") if r else None,
               "simulate_wall_seconds": r.get("simulate_wall_seconds") if r else None,
               "binary_sha256": r.get("binary_sha256") if r else None, "ar256_enabled": r.get("ar256_enabled") if r else None,
               "stages": {n: stage_info(r, log, n) for n in (r["stages_run"] if r else [])}}
        if job.name.endswith("-ideal"):
            ideal[job.name[:-6]] = rec
        elif "+" in job.name:
            chained[job.name] = rec
        else:
            singles[job.name] = rec
    missing = [n for n in order if n not in singles]
    # chain links: entry of stage k == golden exit of k-1 (die 0; the job refuses dies that differ)
    links = {}
    for i, n in enumerate(order):
        if n not in singles or n == "E":
            continue
        entry = a.runs / n / "entry.hex"
        if n == "L0":
            want = (a.gold / "x_preload.hex").read_text()
        else:
            p = order[i - 1]
            want = "@1000\n" + (a.gold / f"L{int(p[1:]):02d}_die0_x.hex").read_text()
        links[n] = entry.exists() and entry.read_text() == want
    per = {n: singles[n]["stages"].get(n, {}) for n in order if n in singles}
    all_exact = not [n for n in missing if not n.startswith("L")] and all(per[n].get("exact") and per[n].get("faults") == [0, 0, 0] for n in order if n in per) \
        and all(per[n].get("kv_writeback_exact") for n in order if n.startswith("L") and n in per) and all(links.values()) \
        and all(singles[n]["status"] == "pass" for n in order if n in singles)
    composed = None
    # E is entered by the wrapper at cycle 7 in both the chained and the isolated run; every later stage is entered
    # by h_start in the chained run (one cycle fewer than isolated) after one host cycle of stage switch.
    # Owner rule (simulate the minimum component): the 36 layers have one shape, so a layer not simulated is
    # composed from the simulated layers (mean, and max as the bound), and is reported as such.
    meas = [per[f"L{n}"]["cycles"] for n in range(36) if f"L{n}" in per and per[f"L{n}"].get("cycles") and per[f"L{n}"].get("exact")]
    unmeasured = [f"L{n}" for n in range(36) if not (f"L{n}" in per and per[f"L{n}"].get("cycles") and per[f"L{n}"].get("exact"))]
    composed_bound = None
    if "E" in per and "head" in per and meas:
        base = 7 + per["E"]["cycles"] + (per["head"]["cycles"] - 1) + (len(order) - 1) + sum(c - 1 for c in meas)
        composed = base + round(len(unmeasured) * (sum(meas) / len(meas) - 1))
        composed_bound = base + len(unmeasured) * (max(meas) - 1)
    chain_cmp = {}
    for name, rec in chained.items():
        stages = name.split("+")
        cmp_ = {}
        for k, s in enumerate(stages):
            c = rec["stages"].get(s, {}).get("cycles")
            iso = per.get(s, {}).get("cycles")
            cmp_[s] = {"chained": c, "isolated": iso, "isolated_minus_chained": (iso - c) if (c and iso) else None,
                       "chained_exact": rec["stages"].get(s, {}).get("exact")}
        chain_cmp[name] = {"status": rec["status"], "stages": cmp_}
    layers = [per[f"L{n}"]["cycles"] for n in range(36) if f"L{n}" in per and per[f"L{n}"].get("cycles")]
    res = {
        "schema": "opentallas.qwen-rom-realmem-fulltoken.v1", "position": a.pos,
        "configuration": "REAL_MEM TP4 G6144 SW64, one-stream AR256 all-reduce (ENABLE_AR256=1, collective depth 256), "
                         "HBM model 36 layer regions, KV history from the GPU golden; async collective OFF",
        "golden": {"dir": str(a.gold), "head": json.loads((a.gold / "head.json").read_text())},
        "missing_stages": missing, "chain_links_entry_is_previous_golden_exit": links,
        "per_stage": per, "all_stages_exact": all_exact,
        "layer_cycles": {"min": min(layers) if layers else None, "max": max(layers) if layers else None,
                         "mean": round(sum(layers) / len(layers), 1) if layers else None, "sum": sum(layers)},
        "composed_token_cycles": composed, "composed_token_cycles_bound_max_layer": composed_bound,
        "layers_simulated_exact": len(meas), "layers_composed_from_representatives": unmeasured,
        "chained_validation": chain_cmp, "kv_ideal_twins": {k: {"stages": v["stages"], "status": v["status"]} for k, v in ideal.items()},
        "real_minus_ideal_layer_cycles": {k: (per[k]["cycles"] - v["stages"][k]["cycles"]) for k, v in ideal.items()
                                          if k in per and v["stages"].get(k, {}).get("cycles")},
        "ideal_memory_reference": {"token_cycles_P0": a.ideal_token_cycles, "layer_cycles_P0": a.ideal_layer_cycles,
                                   "source": "results/rtl/qwen_rom_TP4_allreduce_oneseg_fulltoken_20261003 (AR256, ideal memory, P0)"},
        "clock_ghz": a.clock_ghz,
        "ar_tok_per_s": round(a.clock_ghz * 1e9 / composed, 1) if composed else None,
        "ar_tok_per_s_bound": round(a.clock_ghz * 1e9 / composed_bound, 1) if composed_bound else None,
        "ideal_ar_tok_per_s_P0": round(a.clock_ghz * 1e9 / a.ideal_token_cycles, 1),
        "real_over_ideal_token": round(composed / a.ideal_token_cycles, 4) if composed else None,
        "jobs": {**singles, **chained, **{k + "-ideal": v for k, v in ideal.items()}},
        "claim_boundary": "Layer-parallel RTL simulation (Verilator) of the REAL_MEM TP4 runtime; per-stage exactness against the "
                          "GPU ISA golden; composed cycles. Not a physical sign-off; clock assumed 1.2 GHz.",
    }
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: res[k] for k in ("position", "all_stages_exact", "missing_stages", "layer_cycles",
                                           "composed_token_cycles", "composed_token_cycles_bound_max_layer", "layers_simulated_exact", "ar_tok_per_s_bound", "ar_tok_per_s", "real_over_ideal_token",
                                           "real_minus_ideal_layer_cycles")}, indent=1))
    print(json.dumps(chain_cmp, indent=1))


if __name__ == "__main__":
    main()
