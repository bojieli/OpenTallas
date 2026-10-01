#!/usr/bin/env python3
"""W11: key writes during a 262,144-key scan through the ring K-port arbiter.

Runs rtl/test/tb_w11_idx_ring_concurrent.sv (Verilator; full-shape ring layout,
timed HBM models with backing storage, ot_hdc_v41x_idx_ring_port READ_FENCE=0)
in four write loads and writes results/rtl/w11_idx_ring_concurrent.json:

* saturated: the writer runs decode steps of another user back to back for the
  whole scan (about 1 step every 37 cycles -- far above any decode load);
* one_step / one_step_migration / two_steps: exactly one (two) of the other
  user's decode steps is issued after the scan starts; `migration` is the step
  that takes its count to a multiple of 32 (48 keys move a stack down).
Each run scans user 865's 262,144 keys alone and then again under the load,
every key checked, and finally scans the writing user's keys (every written key
checked).  The scan times are the reader rate with and without concurrent writes.
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/w11_idx_ring_concurrent.json"
V = "rtl/hdc/v41x/"
SOURCES = [V + f for f in (
    "ot_hdc_v41x_idx_hbm.sv", "ot_hdc_v41x_idx_kstream.sv", "ot_hdc_v41x_idx_kstream_ring.sv",
    "ot_hdc_v41x_idx_quarter_join.sv", "ot_hdc_v41x_idx_ring_ranges.sv", "ot_hdc_v41x_idx_ring_kwr.sv",
    "ot_hdc_v41x_idx_ring_port.sv", "ot_hdc_v41x_idx_kdata_m.sv")] + ["rtl/test/tb_w11_idx_ring_concurrent.sv", "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v", "rtl/hdc/ot_hdc_prefix.sv"]
CPP = "rtl/test/w11_idx_ring_concurrent.cpp"
TOP = "tb_w11_idx_ring_concurrent"
RUNS = {"saturated": {}, "one_step": {"LEAD_STEPS": 64, "DURING": 1},
        "one_step_migration": {"LEAD_STEPS": 63, "DURING": 1}, "two_steps": {"LEAD_STEPS": 62, "DURING": 2}}
DEFAULTS = {"AW": 30, "HW": 23, "RSB": 64, "RTAIL": 32, "KB": 7444668, "MEM_WORDS": 1055017, "UA": 865, "UB": 0,
            "NA": 262144, "WB": 128, "GA": 120, "CLK_PS": 967, "LEAD": 300, "LEAD_STEPS": 0, "DURING": 0}
CONC = re.compile(r"W11_CONC scan_alone=(\d+) scan_concurrent=(\d+) steps_during=(\d+) migrations_during=(\d+) "
                  r"sector_writes_during=(\d+) writer_requests_during=(\d+)")
CONC_UB = re.compile(r"W11_CONC_UB user=(\d+) keys=(\d+) scan=(\d+) migrations=(\d+) copied_sectors=(\d+) "
                     r"read_stall_cycles=(\d+)")
PASS = re.compile(r"W11_CONC_PASS na=(\d+) cycles=(\d+)")


def sources() -> dict[str, str]:
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
            for p in sorted({*SOURCES, CPP, "tools/w11_idx_ring_concurrent.py"})}


def run(name: str, params: dict, work: Path) -> dict:
    obj = work / f"obj_{name}"
    cmd = ["verilator", "--cc", "--exe", "--build", "-j", "4", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNOPTFLAT",
           "-Wno-WIDTHCONCAT", "--output-split", "20000", "--output-split-cfuncs", "10000", "--top-module", TOP,
           *[f"-G{k}={v}" for k, v in params.items()], "--Mdir", str(obj),
           *[str(ROOT / s) for s in SOURCES], str(ROOT / CPP)]
    b = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    if b.returncode:
        raise RuntimeError(f"{name}: build failed\n{b.stderr[-3000:]}")
    t0 = time.perf_counter()
    r = subprocess.run([str(obj / f"V{TOP}")], capture_output=True, text=True, timeout=7200)
    out = r.stdout + r.stderr
    m, mu, mp = CONC.search(out), CONC_UB.search(out), PASS.search(out)
    if r.returncode or not (m and mu and mp):
        raise RuntimeError(f"{name}: failed\n{out[-3000:]}")
    alone, conc, steps, migs, writes, reqs = map(int, m.groups())
    ub, ukeys, uscan, umigs, ucopied, rstall = map(int, mu.groups())
    sectors = 557056
    return {"name": name, "parameters": dict(DEFAULTS, **params), "passed": True,
            "scan_alone_cycles": alone, "scan_concurrent_cycles": conc,
            "sectors_per_cycle_alone": round(sectors / alone, 2), "sectors_per_cycle_concurrent": round(sectors / conc, 2),
            "slowdown": round(conc / alone - 1, 4),
            "during_scan": {"steps_issued": steps, "migrations": migs, "sector_writes_committed": writes,
                            "writer_requests": reqs},
            "writer_user": {"user": ub, "keys_written_and_checked": ukeys, "migrations": umigs,
                            "copied_sectors": ucopied},
            "simulation_wall_seconds": round(time.perf_counter() - t0, 1)}


def main() -> None:
    pins = sources()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="w11-conc-") as td:
        with cf.ThreadPoolExecutor(4) as ex:
            rows = list(ex.map(lambda kv: run(kv[0], kv[1], Path(td)), RUNS.items()))
    assert sources() == pins
    for r in rows:
        print(r["name"], r["scan_alone_cycles"], r["scan_concurrent_cycles"], r["slowdown"], r["during_scan"], flush=True)
    by = {r["name"]: r for r in rows}
    assert by["one_step_migration"]["during_scan"]["migrations"] >= 1
    rec = {
        "schema": "opentallas.w11-idx-ring-concurrent.v1",
        "status": "pass",
        "git_head": head,
        "simulator": "Verilator " + subprocess.run(["verilator", "--version"], capture_output=True,
                                                   text=True).stdout.split()[1],
        "arbiter": "ot_hdc_v41x_idx_ring_port READ_FENCE=0: per pseudo-channel port the writer's request wins, the "
                   "reader takes every other port-cycle; responses routed by tag bit 12",
        "cases": rows,
        "summary": {r["name"]: {"alone": r["scan_alone_cycles"], "concurrent": r["scan_concurrent_cycles"],
                                "slowdown": r["slowdown"]} for r in rows},
        "reading": ("A decode-rate write load (one or two steps of another user during the scan, with or without a "
                    "migration) leaves the scan time within the refresh-phase noise of the scan alone; a saturated "
                    "writer (a step every ~37 cycles, ~0.25 requests a cycle) slows it by the measured slowdown: "
                    "each write turns a pseudo-channel from reads to writes (tRTW / tWTR) and opens another row, "
                    "and the drain waits for the slowest channel."),
        "correctness_scope": ("Concurrent writes are safe for another user's ring, and for the same user's next "
                              "step (its new key and migrated keys land in slots outside every stack's current "
                              "range); a scan that must see a write needs the fence (READ_FENCE = 1, used in the die)."),
        "sources_sha256": pins,
    }
    if OUT.exists():
        raise SystemExit(f"{OUT} exists; records are never overwritten")
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
