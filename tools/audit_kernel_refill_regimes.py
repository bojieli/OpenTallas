#!/usr/bin/env python3
"""What weight refill rate does each design actually get, and what does it cost?

This is the ROM-versus-HBM comparison done at equal fidelity, which is the thing
gate C2 exists to protect. The compute datapath is IDENTICAL on both sides --
`rtl/proto/ot_compute_unit.sv`, one RTL, one place-and-route, one set of gates.
The only structural difference is where a weight column comes from, and that is
modelled as backpressure on one port rather than as an assumption fed into a
spreadsheet.

Measured by ``rtl/test/tb_kernel_rom_vs_hbm.sv`` on the same operands, all
producing correct results:

    refill period 1   46 cycles     0 stall cycles
    refill period 2   78 cycles    31 stall cycles
    refill period 4  142 cycles    95 stall cycles
    refill period 8  266 cycles   219 stall cycles

This tool turns a bandwidth figure into the refill period that bandwidth implies,
so the comparison is reproducible instead of asserted.

THE REUSE FACTOR IS THE WHOLE ARGUMENT
--------------------------------------
Bytes of weight per MAC is not a property of the memory, it is a property of how
often a weight is reused before being evicted. In a GEMM with batch B, one weight
column feeds B activation columns, so the refill cost per column falls by B. That
is why this project's own analysis is organised by batch regime, and why a
single-batch comparison flatters whichever side has the cheaper weight store.

So this tool reports the period **as a function of reuse**, and refuses to emit a
single headline number. A caller who wants one must state the batch.

WHAT IT DOES NOT MODEL
----------------------
Nothing here covers the activation path, the output write-back, the interconnect,
DRAM page behaviour, refresh, or contention between compute units. The HBM figure
is a peak-bandwidth divide, which is generous to the HBM side; a real memory
system delivers less. Recorded as a refusal rather than a caveat in prose.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TECH_INPUTS = ROOT / "configs/hardware/technology_inputs.json"

#: Measured by tb_kernel_rom_vs_hbm.sv: (refill period, cycles, stall cycles) for
#: K=32 over 16 lanes. All four runs produced bit-correct results, which is the
#: point -- the array must be right under starvation, not only when fed.
MEASURED = (
    {"refill_period": 1, "cycles": 46, "stall_cycles": 0},
    {"refill_period": 2, "cycles": 78, "stall_cycles": 31},
    {"refill_period": 4, "cycles": 142, "stall_cycles": 95},
    {"refill_period": 8, "cycles": 266, "stall_cycles": 219},
)

#: Bytes in one weight column of the measured tile, per weight format.
#: 16 lanes x the format's storage width.
COLUMN_BYTES = {"bf16": 16 * 2, "fp8_e4m3": 16 * 1, "mxfp4": 16 * 1 // 2}

#: A100 has 108 SMs; a single compute unit gets a share of device bandwidth.
#: Using the whole device figure for one unit would overstate the HBM side by
#: two orders of magnitude.
A100_COMPUTE_UNITS = 108


def git_state() -> dict[str, Any]:
    def run(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD") or None,
            "worktree_dirty": bool(run("status", "--porcelain"))}


def refill_period(column_bytes: int, bytes_per_cycle: float, reuse: int) -> float:
    """Cycles between weight columns, given per-unit bandwidth and reuse."""
    if bytes_per_cycle <= 0:
        return float("inf")
    return (column_bytes / reuse) / bytes_per_cycle


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--clock-hz", type=float, default=1.117e9,
                    help="the measured tile f_max (default: the placed 1,117 MHz)")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    facts = json.loads(TECH_INPUTS.read_text())["source_facts"]["a100_sxm_80gb"]
    hbm_bytes_s = float(facts["hbm_bandwidth_bytes_s"])
    device_bytes_cycle = hbm_bytes_s / args.clock_hz
    unit_bytes_cycle = device_bytes_cycle / A100_COMPUTE_UNITS

    rows = []
    for fmt, nbytes in COLUMN_BYTES.items():
        for reuse in (1, 8, 64, 256):
            rows.append({
                "weight_format": fmt,
                "column_bytes": nbytes,
                "reuse_factor": reuse,
                "hbm_refill_period_cycles": refill_period(nbytes, unit_bytes_cycle, reuse),
                # On-die mask ROM: the column is local, so a read costs the SRAM
                # latency the RTL already pays and never stalls the walk.
                "rom_refill_period_cycles": 1.0,
            })

    body = {
        "schema": "opentallas.audit.kernel_refill_regimes.v1",
        "question": ("At equal fidelity -- one RTL, one place-and-route -- what "
                     "refill rate does each weight store imply, and what does the "
                     "measured compute unit cost at that rate?"),
        "git": git_state(),
        "equal_fidelity_basis": {
            "rtl": "rtl/proto/ot_compute_unit.sv",
            "note": ("Both sides are the same gates. The only structural "
                     "difference is backpressure on refill_valid, so the cycle "
                     "count is the comparison rather than an input to it."),
        },
        "clock_hz": args.clock_hz,
        "hbm_reference": {
            "part": "a100_sxm_80gb",
            "bandwidth_bytes_s": hbm_bytes_s,
            "compute_units_assumed": A100_COMPUTE_UNITS,
            "device_bytes_per_cycle": device_bytes_cycle,
            "per_unit_bytes_per_cycle": unit_bytes_cycle,
        },
        "measured_cycles": list(MEASURED),
        "implied_periods": rows,
        "refusals": [
            "no-single-headline: the refill period depends on the reuse factor, "
            "which depends on batch. A one-number comparison silently picks a "
            "batch and flatters whichever side has the cheaper weight store.",
            "peak-bandwidth-is-generous-to-hbm: the HBM period is a peak-rate "
            "divide with no DRAM page behaviour, refresh or inter-unit "
            "contention. A real memory system delivers less than this.",
            "activation-and-output-paths-not-modelled: only weight refill is "
            "charged here. Activation supply and output write-back are absent.",
        ],
    }

    print(f"equal fidelity: {body['equal_fidelity_basis']['rtl']}, one RTL both sides")
    print(f"clock {args.clock_hz/1e6:.0f} MHz; "
          f"HBM {hbm_bytes_s/1e12:.1f} TB/s over {A100_COMPUTE_UNITS} units "
          f"= {unit_bytes_cycle:.1f} B/cycle per unit")
    print("\nmeasured on the placed compute unit (all bit-correct):")
    for m in MEASURED:
        print(f"  period {m['refill_period']:>2}  {m['cycles']:>4} cycles  "
              f"{m['stall_cycles']:>3} stall")
    print("\nimplied HBM refill period (ROM is 1.0 throughout):")
    print(f"  {'format':<10} {'reuse':>6} {'bytes/col':>10} {'period':>9}")
    for r in rows:
        print(f"  {r['weight_format']:<10} {r['reuse_factor']:>6} "
              f"{r['column_bytes']:>10} {r['hbm_refill_period_cycles']:>9.2f}")
    print("\nRead with the refusals: no single headline, and the HBM figure is a "
          "peak-rate divide.")

    if args.output:
        args.output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        try:
            shown = args.output.relative_to(ROOT)
        except ValueError:
            shown = args.output
        print(f"wrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
