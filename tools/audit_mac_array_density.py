#!/usr/bin/env python3
"""Is the MAC array's throughput per unit area comparable to a GPU at this node?

The design target is explicit: come within one order of magnitude of a
state-of-the-art part on the same process. ASAP7 is a 7 nm predictive PDK, so the
comparator is the NVIDIA A100 (TSMC N7), whose figures this repository already
records in ``configs/hardware/technology_inputs.json`` -- 312 TFLOP/s dense BF16
on an 826 mm² die.

WHY THIS COMPARISON IS EASY TO GET WRONG
----------------------------------------
A MAC array is not a GPU. Comparing an array's standard-cell area against a whole
die flatters the array by every square millimetre of cache, register file,
scheduler, memory controller and PHY the GPU carries and the array does not. Any
number produced that way is meaningless, and it will always look like a win.

So this tool reports THREE densities, at three different levels of inclusion, and
refuses to collapse them into one headline:

  array_level      the measured MAC array alone.  An UPPER BOUND on what a
                   complete design can do -- nothing else is present yet.
  logic_level      the A100's throughput over the standard-cell logic fraction
                   of its die (0.6, per configs/hardware/technology.json).  The
                   closest like-for-like comparator available, and still generous
                   to us because that 0.6 includes schedulers and register files.
  device_level     the A100's throughput over its whole die.  The number a
                   finished product must be judged against.

VERDICT RULE
------------
The array passes only if it clears logic_level, because a complete design adds
overhead and can only lose density from here. Clearing device_level alone is not
evidence of anything: array-only area against whole-die area is the comparison
this docstring exists to warn about.

FLOPs accounting: one MAC is counted as two floating-point operations, a multiply
and an add, matching how vendors quote dense BF16 throughput.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

#: Where this repository already records the comparator's published figures.
TECH_INPUTS = ROOT / "configs/hardware/technology_inputs.json"
TECHNOLOGY = ROOT / "configs/hardware/technology.json"

#: A100 80GB SXM, TSMC N7. Die area is not in technology_inputs.json's
#: source_facts block, so it is taken from the same file's recorded die figure.
A100_DIE_AREA_MM2 = 826.0

#: configs/hardware/technology.json records "0.6 of a published GPU die is
#: standard-cell logic; the remaining 0.4 is on-die memory". Used to build the
#: logic-level comparator rather than inventing a tensor-core area, which no
#: vendor publishes.
GPU_LOGIC_FRACTION = 0.6

#: One MAC retires a multiply and an add.
FLOPS_PER_MAC = 2


def git_state() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()

    return {
        "commit": run("rev-parse", "HEAD") or None,
        "worktree_dirty": bool(run("status", "--porcelain")),
    }


def comparator() -> dict[str, Any]:
    facts = json.loads(TECH_INPUTS.read_text())["source_facts"]["a100_sxm_80gb"]
    ops = float(facts["bf16_dense_ops_s"])
    logic_mm2 = A100_DIE_AREA_MM2 * GPU_LOGIC_FRACTION
    return {
        "part": "a100_sxm_80gb",
        "process": facts["process"],
        "bf16_dense_ops_s": ops,
        "die_area_mm2": A100_DIE_AREA_MM2,
        "logic_area_mm2": logic_mm2,
        "logic_fraction_assumed": GPU_LOGIC_FRACTION,
        "device_level_ops_s_per_mm2": ops / A100_DIE_AREA_MM2,
        "logic_level_ops_s_per_mm2": ops / logic_mm2,
        "source": str(TECH_INPUTS.relative_to(ROOT)),
    }


def array_density(record: Path, lanes: int) -> dict[str, Any]:
    body = json.loads(record.read_text())
    design = body.get("design") or {}
    pnr = (body.get("place_and_route") or {}).get("metrics") or {}
    git = body.get("git") or {}

    fmax_hz = pnr.get("fmax_hz") or design.get("fmax_hz")
    # Prefer the placed core area: standard-cell area alone ignores the
    # utilisation a real floorplan must leave, and would overstate density.
    core_um2 = pnr.get("core_area_um2")
    cell_um2 = pnr.get("standard_cell_area_um2") or design.get("area_um2")

    if not fmax_hz:
        raise SystemExit(f"{record}: no fmax recorded; run the pnr stage")

    out: dict[str, Any] = {
        "record": str(record),
        "record_git_commit": str(git.get("commit"))[:12] if git.get("commit") else None,
        "record_worktree_dirty": git.get("worktree_dirty"),
        "stages": body.get("stages_completed") or body.get("stages_requested"),
        "closed": design.get("closed"),
        "closed_reason": design.get("closed_reason"),
        "lanes": lanes,
        "fmax_hz": fmax_hz,
        "ops_s": lanes * FLOPS_PER_MAC * fmax_hz,
    }
    for name, um2 in (("core", core_um2), ("standard_cell", cell_um2)):
        if um2:
            mm2 = float(um2) / 1e6
            out[f"{name}_area_mm2"] = mm2
            out[f"array_level_ops_s_per_mm2_by_{name}"] = out["ops_s"] / mm2
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--record", type=Path, required=True,
                    help="a run_abi3_physical.py record that completed the pnr stage")
    ap.add_argument("--lanes", type=int, required=True,
                    help="MAC lanes in the measured array")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    ref = comparator()
    arr = array_density(args.record, args.lanes)

    basis = ("core" if "array_level_ops_s_per_mm2_by_core" in arr
             else "standard_cell")
    density = arr[f"array_level_ops_s_per_mm2_by_{basis}"]
    ratio_logic = density / ref["logic_level_ops_s_per_mm2"]
    ratio_device = density / ref["device_level_ops_s_per_mm2"]

    verdict = (
        "array clears the logic-level comparator"
        if ratio_logic >= 1.0
        else "array does NOT clear the logic-level comparator"
    )

    body = {
        "schema": "opentallas.audit.mac_array_density.v1",
        "question": (
            "Does the MAC array's throughput per unit area stand comparison with "
            "a same-node GPU, at matched levels of inclusion?"
        ),
        "git": git_state(),
        "comparator": ref,
        "array": arr,
        "area_basis_used": basis,
        "array_level_ops_s_per_mm2": density,
        "ratio_vs_logic_level": ratio_logic,
        "ratio_vs_device_level": ratio_device,
        "verdict": verdict,
        "refusals": [
            "not-a-device-claim: the array has no register file, shared memory, "
            "scheduler, interconnect or memory controller. Its density is an "
            "upper bound on a complete design, never a product figure.",
            "not-a-silicon-claim: ASAP7 is a predictive, non-manufacturable "
            "academic PDK. The comparator is fabricated silicon. The node family "
            "matches; the confidence does not.",
            "device-level-ratio-is-not-the-verdict: array-only area against "
            "whole-die area flatters the array by every mm2 of cache and PHY it "
            "does not have. The logic-level ratio is the one that means anything.",
        ],
    }

    print(f"comparator: {ref['part']} on {ref['process']}, "
          f"{ref['bf16_dense_ops_s']/1e12:.0f} TFLOP/s over {ref['die_area_mm2']:.0f} mm2")
    print(f"  device level : {ref['device_level_ops_s_per_mm2']/1e12:.3f} TFLOP/s per mm2")
    print(f"  logic level  : {ref['logic_level_ops_s_per_mm2']/1e12:.3f} TFLOP/s per mm2"
          f"  (die x {GPU_LOGIC_FRACTION})")
    print(f"array: {arr['lanes']} lanes at {arr['fmax_hz']/1e6:.0f} MHz, "
          f"{basis} area {arr[f'{basis}_area_mm2']*1e6:.0f} um2, closed={arr['closed']}")
    print(f"  array level  : {density/1e12:.3f} TFLOP/s per mm2")
    print(f"  vs logic level : {ratio_logic:.2f}x")
    print(f"  vs device level: {ratio_device:.2f}x   (not the verdict; see refusals)")
    print(f"verdict: {verdict}")

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
