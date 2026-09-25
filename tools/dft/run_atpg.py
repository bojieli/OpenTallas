#!/usr/bin/env python3
"""Stuck-at ATPG and fault coverage for a scan-inserted netlist.

    python3 tools/dft/run_atpg.py --netlist 1_2_yosys.scan.v --scan scan_chains.json \\
        --work DIR --output atpg.json

1. build the capture and shift models (tools/dft/atpg_model.py);
2. run otatpg (tools/dft/otatpg.cpp, compiled on demand) on the capture model:
   random patterns, PODEM with dynamic compaction, reverse-order compaction;
3. run otatpg's chain-test mode on the shift model for every fault the
   capture patterns left: a three-valued sequential simulation of a 0011 flush
   through every chain, from an unknown state; what it exposes is detected by
   the chain test;
4. confirm on the gate-level netlist in Icarus (tools/dft/gate_sim.py): a
   chain flush and a sample of patterns on the good machine, and a sample of
   capture-detected and chain-detected faults injected one at a time.

Fault classes (on the uncollapsed pin-fault list, clock pins included):
DT detected by a capture pattern, DS detected by the chain test, UT proved
untestable (redundant, tied, or blocked by a test constraint), AU aborted at
the backtrack limit.  Fault coverage = (DT+DS)/all; test coverage =
(DT+DS)/(all-UT).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dft import atpg_model  # noqa: E402
from dft import gate_sim  # noqa: E402
from dft import liberty as lib  # noqa: E402

HERE = Path(__file__).resolve().parent
SCHEMA = "opentallas.dft.atpg.v1"
STATUS = {0: "ND", 1: "DT", 2: "UT", 3: "AU"}


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def engine(build_dir: Path) -> Path:
    src = HERE / "otatpg.cpp"
    digest = sha256(src)[:16]
    exe = build_dir / f"otatpg_{digest}"
    if not exe.is_file():
        build_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["g++", "-O2", "-std=c++17", "-pthread", "-o", str(exe), str(src)], check=True
        )
    return exe


def run_engine(exe: Path, model: Path, faults: Path, out: Path, threads: int, extra: list[str]) -> dict[str, Any]:
    t0 = time.time()
    proc = subprocess.run(
        [str(exe), "--model", str(model), "--faults", str(faults), "--out", str(out),
         "--threads", str(threads), *extra],
        capture_output=True, text=True,
    )
    Path(str(out) + ".log").write_text(proc.stdout + proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"otatpg failed: {proc.stderr[-2000:]}")
    summary = json.loads(Path(str(out) + ".summary.json").read_text())
    summary["log"] = Path(str(out) + ".log").read_text().strip().splitlines()[-3:]
    summary["wall_seconds"] = round(time.time() - t0, 1)
    statuses = []
    for line in Path(str(out) + ".faults").read_text().splitlines():
        st, pat = line.split()
        statuses.append((int(st), int(pat)))
    return {"summary": summary, "statuses": statuses}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--netlist", required=True)
    ap.add_argument("--scan", required=True, help="scan_chains.json from the scan inserter")
    ap.add_argument("--work", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--block", default=None)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--backtrack-limit", type=int, default=256)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--sample-patterns", type=int, default=32,
                    help="patterns simulated on the gate-level good machine")
    ap.add_argument("--sample-faults", type=int, default=48,
                    help="capture-detected faults injected in gate-level simulation")
    ap.add_argument("--sample-chain-faults", type=int, default=16,
                    help="chain-test faults injected in gate-level simulation")
    ap.add_argument("--no-gate-sim", action="store_true")
    ap.add_argument("--liberty", action="append", default=None)
    args = ap.parse_args(argv)

    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    netlist = Path(args.netlist)
    scan = json.loads(Path(args.scan).read_text())
    lib_paths = [Path(p) for p in args.liberty] if args.liberty else lib.default_asap7_liberty()
    cells = lib.load_cells(lib_paths, work / "cache")
    started = time.time()

    model_info = atpg_model.build_models(netlist, scan, cells, work / "model")
    names = json.loads((work / "model/names.json").read_text())
    exe = engine(work / "bin")
    common = ["--backtrack-limit", str(args.backtrack_limit), "--seed", str(args.seed)]

    capture = run_engine(exe, work / "model/capture.model", work / "model/faults.txt",
                         work / "capture", args.threads, common)
    n_pin = len(capture["statuses"])
    hold_insts = names["hold_fault_instances"]
    leftover = [i for i, (st, _p) in enumerate(capture["statuses"]) if st != 1]
    leftover += list(range(n_pin, n_pin + 2 * len(hold_insts)))
    (work / "leftover.txt").write_text("\n".join(map(str, leftover)) + "\n")
    shift = run_engine(exe, work / "model/shift.model", work / "model/flush_faults.txt",
                       work / "shift", args.threads,
                       ["--flush", "--only-faults", str(work / "leftover.txt")])

    classes: list[str] = []
    for i, (st, _p) in enumerate(capture["statuses"]):
        if st == 1:
            classes.append("DT")
        elif shift["statuses"][i][0] == 1:
            classes.append("DS")
        else:
            classes.append(STATUS[st])
    # a clock pin stuck at either value is a cell that holds: detected when
    # the flush exposes the cell held at 0 and held at 1
    held = {}
    for j, inst in enumerate(hold_insts):
        held[inst] = shift["statuses"][n_pin + 2 * j][0] == 1 and shift["statuses"][n_pin + 2 * j + 1][0] == 1
    clock_classes = [
        "UT" if eff == "transparent" else ("DS" if held.get(inst) else "ND")
        for (inst, _pin, _v), eff in zip(names["clock_pin_faults"], names["clock_pin_effect"])
    ]
    counts = {k: classes.count(k) + clock_classes.count(k) for k in ("DT", "DS", "UT", "AU", "ND")}
    n_clock = len(clock_classes)
    total = len(classes) + n_clock
    detected = counts["DT"] + counts["DS"]
    fault_cov = detected / total if total else None
    test_cov = detected / (total - counts["UT"]) if total - counts["UT"] else None

    # untestable breakdown by pin role, for the report
    ut_by_pin: dict[str, int] = {}
    au_by_pin: dict[str, int] = {}
    for (inst, pin, _v), cls in zip(names["faults"], classes):
        if cls == "UT":
            ut_by_pin[pin] = ut_by_pin.get(pin, 0) + 1
        elif cls == "AU":
            au_by_pin[pin] = au_by_pin.get(pin, 0) + 1

    chains = scan["chains"]
    L = max(len(c["cells"]) for c in chains)
    P = capture["summary"]["patterns"]
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "block": args.block or scan["top"],
        "top": scan["top"],
        "netlist": {"path": str(netlist), "sha256": sha256(netlist)},
        "scan": {
            "chains": len(chains),
            "max_chain_length": L,
            "scan_cells": sum(len(c["cells"]) for c in chains),
            "capture_constraints": scan["capture_constraints"],
        },
        "model": {k: v for k, v in model_info.items() if k not in ("capture", "shift")},
        "fault_model": "single stuck-at, every pin of every cell (uncollapsed), clock pins included",
        "faults_total": total,
        "classes": counts,
        "fault_coverage": round(fault_cov, 6) if fault_cov is not None else None,
        "test_coverage": round(test_cov, 6) if test_cov is not None else None,
        "untestable_by_pin": dict(sorted(ut_by_pin.items(), key=lambda kv: -kv[1])[:12]),
        "aborted_by_pin": dict(sorted(au_by_pin.items(), key=lambda kv: -kv[1])[:12]),
        "patterns": {
            "capture": P,
            "chain_test": 1,
            "before_compaction": capture["summary"]["patterns_before_compaction"],
            "random_kept": capture["summary"]["random_patterns_kept"],
            "tester_cycles": (P + 1) * (L + 1) + L,
            "note": "tester cycles = one load/unload of the longest chain per pattern, overlapped, plus the capture cycle",
        },
        "engine": {
            "capture": capture["summary"],
            "shift": shift["summary"],
            "binary_source_sha256": sha256(HERE / "otatpg.cpp"),
        },
    }

    if not args.no_gate_sim:
        rng = random.Random(args.seed)
        srcs, obs = gate_sim.read_patterns(Path(str(work / "capture") + ".patterns"))
        dt_idx = [i for i, c in enumerate(classes) if c == "DT"]
        sample_f = rng.sample(dt_idx, min(args.sample_faults, len(dt_idx)))
        pats = list(range(min(args.sample_patterns, len(srcs))))
        for i in sample_f:
            p = capture["statuses"][i][1]
            if p not in pats:
                pats.append(p)
        out_pins = {}
        faults = []
        for i in sample_f:
            inst, pin, v = names["faults"][i]
            if (inst, pin) not in out_pins:
                out_pins[(inst, pin)] = pin not in _input_pins(netlist, inst, cells, scan)
            faults.append({"index": i, "inst": inst, "pin": pin, "value": v,
                           "pattern": capture["statuses"][i][1], "output": out_pins[(inst, pin)], "class": "DT"})
        ds_idx = [i for i, c in enumerate(classes) if c == "DS"]
        clock_faults = names["clock_pin_faults"]
        clock_ds = [j for j, c in enumerate(clock_classes) if c == "DS"]
        n_ds = min(args.sample_chain_faults, len(ds_idx) + len(clock_ds))
        pool = [("model", i) for i in ds_idx] + [("clock", j) for j in clock_ds]
        for kind, i in rng.sample(pool, n_ds):
            if kind == "model":
                inst, pin, v = names["faults"][i]
                outp = pin not in _input_pins(netlist, inst, cells, scan)
            else:
                inst, pin, v = clock_faults[i]
                outp = False
            faults.append({"index": i, "inst": inst, "pin": pin, "value": v, "pattern": None,
                           "output": outp, "class": "DS" if kind == "model" else "DS-clock"})
        bench = work / "gate"
        bench.mkdir(exist_ok=True)
        gate_sim.build_bench(bench, netlist, scan, names, cells, pats, srcs, obs, faults, scan["top"])
        t0 = time.time()
        res = gate_sim.run_bench(bench)
        confirmed = {"DT": [0, 0], "DS": [0, 0], "DS-clock": [0, 0]}
        misses = []
        for k, f in enumerate(faults):
            kind, mism = res["faults"].get(k, (None, 0))
            confirmed[f["class"]][1] += 1
            if mism > 0:
                confirmed[f["class"]][0] += 1
            else:
                misses.append({k2: f[k2] for k2 in ("inst", "pin", "value", "pattern", "class")})
        record["gate_level"] = {
            "simulator": "Icarus Verilog, cell models generated from Liberty",
            "good_machine_patterns": res["good_patterns"],
            "good_machine_mismatches": res["good_mismatches"],
            "capture_faults_injected": confirmed["DT"][1],
            "capture_faults_confirmed": confirmed["DT"][0],
            "chain_faults_injected": confirmed["DS"][1] + confirmed["DS-clock"][1],
            "chain_faults_confirmed": confirmed["DS"][0] + confirmed["DS-clock"][0],
            "unconfirmed": misses,
            "seconds": round(time.time() - t0, 1),
        }
    record["seconds"] = round(time.time() - started, 1)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print(
        f"{record['block']}: {total} faults, DT {counts['DT']} DS {counts['DS']} UT {counts['UT']} "
        f"AU {counts['AU']}; fault coverage {100 * fault_cov:.2f}%, test coverage {100 * test_cov:.2f}%, "
        f"{P} patterns"
    )
    if "gate_level" in record:
        g = record["gate_level"]
        print(
            f"  gate level: {g['good_machine_patterns']} patterns, {g['good_machine_mismatches']} mismatches; "
            f"capture faults {g['capture_faults_confirmed']}/{g['capture_faults_injected']}, "
            f"chain faults {g['chain_faults_confirmed']}/{g['chain_faults_injected']} confirmed"
        )
    return 0


_PIN_CACHE: dict[str, dict[str, str]] = {}


def _input_pins(netlist: Path, inst: str, cells, scan) -> set[str]:
    key = str(netlist)
    if key not in _PIN_CACHE:
        from dft import netlist as nl

        mod = nl.read_module(netlist, scan["top"])
        _PIN_CACHE[key] = {i.name: i.cell for i in mod.instances}
    cell = cells[_PIN_CACHE[key][inst]]
    return {p for p, info in cell["pins"].items() if info["direction"] == "input"}


if __name__ == "__main__":
    raise SystemExit(main())
