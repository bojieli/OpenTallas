#!/usr/bin/env python3
"""Measure what operand reuse buys, in cycles, on the same gates and the same vectors.

THE QUESTION. ``ot_compute_unit`` reads one weight column per cycle and broadcasts
ONE activation across its lanes: a weight reuse factor of 1, two bytes of weight
traffic per multiply. ``ot_compute_unit_gemm`` holds the weight column and walks
NCOL activation columns against it. Both read the weight store at exactly one word
per cycle, so if the reuse argument is real the cycle count must not move while the
retired multiply-accumulates multiply by NCOL -- including when the weight bus is
starved, which is the regime ``tools/audit_kernel_refill_regimes.py`` is about.

WHAT IS MEASURED, and by whom. Every configuration is simulated by the pinned
Verilator 5.050 on vectors built by ``tools/build_gemm_unit_vectors.py`` from
``runtime.reference.mac_tile``. A run counts as evidence only if its bench prints
PASS, which requires every accumulator to be bit-identical to that reference and
every ``dropped`` bit to match; a cycle count from a unit computing the wrong
number is worthless and is refused rather than reported. The GEMV side runs
``rtl/test/tb_kernel_rom_vs_hbm.sv`` unchanged, so the numbers this tool records for
NCOL=1 are directly comparable with the four the refill audit already quotes
(46/0, 78/31, 142/95, 266/219).

WHAT IT DOES NOT MEASURE. Nothing here says anything about area, frequency or
energy -- those come from ``tools/run_abi3_physical.py`` post-route records and are
composed by ``tools/audit_gemm_operand_reuse.py``. Nor does it model the activation
store's fill traffic: NCOL columns of activations must be written before the pass,
and at NCOL=8 that is eight times the activation bytes for the same weight bytes.
That is the trade the design makes and it is stated, not hidden -- a GEMM is only
worth building when the activation tile is reused across many weight columns, which
is the other half of the tiling and is out of this bench's scope.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_gemm_unit_vectors import build as build_vectors  # noqa: E402

TOOLS_ROOT = Path(os.environ.get("OPENTALLAS_TOOL_ROOT",
                                 Path.home() / ".local/opentallas-tools"))
VERILATOR = TOOLS_ROOT / "verilator-5.050/bin/verilator"
PINNED_VERILATOR_VERSION = "5.050"

COMMON_SOURCES = (
    "rtl/abi3/ot_a3_asap7_fakeram_blackbox.sv",
    "rtl/proto/ot_mac_lane.sv",
    "rtl/proto/ot_mac_tile.sv",
)
GEMV = {"ncol": 1, "top": "tb_kernel_rom_vs_hbm",
        "sources": COMMON_SOURCES + ("rtl/proto/ot_compute_unit.sv",
                                     "rtl/test/tb_kernel_rom_vs_hbm.sv"),
        "block": "ot_compute_unit"}
GEMM = {"top": "tb_compute_unit_gemm",
        "sources": COMMON_SOURCES + ("rtl/proto/ot_compute_unit_gemm.sv",
                                     "rtl/test/tb_compute_unit_gemm.sv"),
        "block": "ot_compute_unit_gemm"}

PASS_RE = re.compile(r"PASS period=(\d+):.*?(\d+) cycles, (\d+) stall cycles")

#: ONE named warning is waived, not -Wno-fatal.  The shipped ot_compute_unit
#: indexes a 256-entry activation register file with the 9-bit column counter
#: (lines 115 and 119) and tb_kernel_rom_vs_hbm assigns a 32-bit localparam to a
#: 9-bit reg; both are WIDTHTRUNC and both are harmless truncations in RTL this
#: campaign must not modify, because it is the measurement baseline.  Waiving the
#: class by name keeps every OTHER warning fatal, which is the distinction the
#: Makefile's lint-strict comment draws: -Wno-fatal once hid a real SELRANGE fault
#: in ot_mac_lane_packed and a hung bench, and this does not repeat that.
WAIVED_WARNINGS = ("WIDTHTRUNC",)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_state() -> dict[str, Any]:
    def run(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD") or None,
            "worktree_dirty": bool(run("status", "--porcelain"))}


def verilator_version() -> str:
    out = subprocess.run([str(VERILATOR), "--version"], capture_output=True,
                         text=True, check=True).stdout
    return out.split()[1]


def compile_bench(cfg: dict[str, Any], ncol: int, workdir: Path,
                  k: int | None = None) -> Path:
    tag = f"n{ncol}" if k is None else f"n{ncol}_k{k}"
    obj = workdir / f"obj_{tag}"
    exe = obj / f"sim_{tag}"
    cmd = [str(VERILATOR), "--binary", "--timing",
           "-DOT_A3_FAKERAM_BEHAVIOURAL", f"-DOT_NCOL={ncol}",
           *([f"-DOT_K={k}"] if k is not None else []),
           *[f"-Wno-{w}" for w in WAIVED_WARNINGS],
           "-o", exe.name, "--top-module", cfg["top"],
           *[str(ROOT / s) for s in cfg["sources"]],
           "--Mdir", str(obj)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"verilator failed for NCOL={ncol}:\n{r.stdout}\n{r.stderr}")
    return exe


def run_period(exe: Path, vectors: Path, period: int, ncol: int) -> dict[str, Any]:
    args = [str(exe), f"+act={vectors/'act.hex'}", f"+wgt={vectors/'wgt.hex'}",
            f"+exp={vectors/'exp.hex'}", f"+period={period}"]
    if ncol > 1:
        args.append(f"+drop={vectors/'drop.hex'}")
    r = subprocess.run(args, capture_output=True, text=True)
    line = next((l for l in r.stdout.splitlines() if l.startswith(("PASS", "FAIL"))),
                "")
    m = PASS_RE.search(line)
    if not m:
        return {"refill_period": period, "passed": False, "output": line or r.stdout}
    return {"refill_period": period, "passed": True,
            "cycles": int(m.group(2)), "stall_cycles": int(m.group(3)),
            "bench_line": line}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=32)
    ap.add_argument("--lanes", type=int, default=16)
    ap.add_argument("--ncol", type=int, nargs="+", default=[1, 2, 4, 8])
    ap.add_argument("--period", type=int, nargs="+", default=[1, 2, 4, 8, 16])
    ap.add_argument("--seed", type=int, nargs="+", default=[20260914, 7])
    ap.add_argument("--corner-k", type=int, nargs="+", default=[1, 2, 33, 255, 256],
                    help="extra pass lengths the GEMM unit must still be bit-exact at; "
                         "1 and 2 are the shortest passes the drain can mishandle, 256 "
                         "is the full store depth and the widest cfg_k the address "
                         "width admits")
    ap.add_argument("--corner-period", type=int, default=3,
                    help="a refill period that is not a power of two, so the stall "
                         "pattern does not line up with the pass length")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()

    if not VERILATOR.exists():
        raise SystemExit(f"pinned Verilator {PINNED_VERILATOR_VERSION} not at {VERILATOR}")
    version = verilator_version()
    if version != PINNED_VERILATOR_VERSION:
        raise SystemExit(f"Verilator {version} is not the pinned {PINNED_VERILATOR_VERSION}")

    configs: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="ot-gemm-") as tmp:
        work = Path(tmp)
        for ncol in a.ncol:
            cfg = dict(GEMV) if ncol == 1 else dict(GEMM, ncol=ncol)
            vec_dir = work / f"vec_n{ncol}"
            vectors = build_vectors(a.k, a.lanes, ncol, 40, 240, a.seed[0], vec_dir)
            exe = compile_bench(cfg, ncol, work)
            runs = [run_period(exe, vec_dir, p, ncol) for p in a.period]
            mac = a.lanes * ncol * a.k
            for r in runs:
                if r["passed"]:
                    r["mac_retired"] = mac
                    r["mac_per_cycle"] = mac / r["cycles"]
            configs.append({
                "ncol": ncol, "block": cfg["block"], "bench": cfg["top"],
                "lanes": a.lanes, "k": a.k,
                "accumulators": a.lanes * ncol,
                "mac_per_pass": mac,
                "weight_bits_per_cycle": 16 * a.lanes,
                "activation_bits_per_cycle": 16 * ncol,
                "weight_bytes_per_mac": (16 * a.lanes / 8) / (a.lanes * ncol),
                "weight_reuse_factor": ncol,
                "vectors": vectors,
                "sources": {s: sha256_file(ROOT / s) for s in cfg["sources"]},
                "runs": runs,
                "all_passed": all(r["passed"] for r in runs),
            })

        #: The refill sweep above runs one pass length. A unit whose drain depth or
        #: address width were wrong would still pass it, so the GEMM unit is also
        #: checked at the shortest and longest passes its stores admit, on two
        #: independent vector seeds, at a refill period that is not a power of two.
        corners: list[dict[str, Any]] = []
        for ncol in [n for n in a.ncol if n > 1]:
            for k in a.corner_k:
                exe = compile_bench(GEMM, ncol, work, k=k)
                for seed in a.seed:
                    cdir = work / f"corner_n{ncol}_k{k}_s{seed}"
                    v = build_vectors(k, a.lanes, ncol, 40, 240, seed, cdir)
                    r = run_period(exe, cdir, a.corner_period, ncol)
                    corners.append({"ncol": ncol, "k": k, "seed": seed,
                                    "mac_per_pass": v["mac_per_pass"],
                                    "lanes_reporting_dropped": v["lanes_reporting_dropped"],
                                    **r})

    base = next(c for c in configs if c["ncol"] == 1)
    by_period = {r["refill_period"]: r for r in base["runs"] if r["passed"]}
    for c in configs:
        c["mac_per_cycle_vs_gemv"] = {}
        for r in c["runs"]:
            b = by_period.get(r["refill_period"])
            if r["passed"] and b:
                c["mac_per_cycle_vs_gemv"][str(r["refill_period"])] = round(
                    r["mac_per_cycle"] / b["mac_per_cycle"], 4)

    record = {
        "campaign_id": "opentallas-gemm-operand-reuse-v1",
        "schema_version": 1,
        "question": ("does holding a weight column across NCOL activation columns "
                     "multiply the retired MACs without moving the cycle count, at "
                     "every weight refill rate, while every accumulator stays "
                     "bit-identical to runtime.reference.mac_tile"),
        "reference": "runtime.reference.mac_tile.dot_product",
        "simulator": {"name": "verilator", "version": version,
                      "path": str(VERILATOR), "sha256": sha256_file(VERILATOR),
                      "warnings_fatal": True,
                      "waived_warning_classes": list(WAIVED_WARNINGS),
                      "waiver_reason": (
                          "WIDTHTRUNC only, for two pre-existing truncations in the "
                          "shipped ot_compute_unit and its bench, which are the "
                          "measurement baseline and must not be modified; -Wno-fatal "
                          "is NOT used")},
        "git": git_state(),
        "configurations": configs,
        "corner_cases": corners,
        "corners_all_passed": all(c["passed"] for c in corners),
        "status": ("pass" if all(c["all_passed"] for c in configs)
                   and all(c["passed"] for c in corners) else "fail"),
        "refusals": [
            "cycles only: no area, frequency or energy claim is made here",
            ("the activation store fill is not charged; NCOL columns of activations "
             "must be written before a pass, which is NCOL times the activation "
             "bytes for the same weight bytes"),
            ("the FakeRAM parts are plausible geometry with a black-box timing "
             "model, so no memory energy or array timing figure follows from them"),
        ],
    }
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")

    print(f"reference: {record['reference']}   simulator: verilator {version}")
    print(f"{'NCOL':>5} {'MAC/pass':>9} {'wgt B/MAC':>10} | "
          + " ".join(f"{'p=' + str(p):>16}" for p in a.period))
    for c in configs:
        cells = []
        for p in a.period:
            r = next((x for x in c["runs"] if x["refill_period"] == p), None)
            cells.append(f"{r['cycles']:>5}c {r['mac_per_cycle']:>8.2f}"
                         if r and r["passed"] else f"{'FAIL':>14}")
        print(f"{c['ncol']:>5} {c['mac_per_pass']:>9} {c['weight_bytes_per_mac']:>10.3f} | "
              + " ".join(f"{x:>16}" for x in cells))
    print("\nMAC per cycle against the GEMV unit at the same refill period:")
    for c in configs:
        if c["ncol"] == 1:
            continue
        print(f"  NCOL={c['ncol']:<2} " + "  ".join(
            f"p={p}: {c['mac_per_cycle_vs_gemv'].get(str(p), 'n/a')}x" for p in a.period))
    bad = [c for c in corners if not c["passed"]]
    print(f"\ncorner cases (pass length x seed, refill period {a.corner_period}): "
          f"{len(corners) - len(bad)}/{len(corners)} bit-identical to the reference"
          + ("" if not bad else f"  FAILED: {bad}"))
    print(f"\nstatus={record['status']}  wrote {out}")
    return 0 if record["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
