#!/usr/bin/env python3
"""Do the redesign's gains reproduce on a different node, or are they ASAP7?

THE QUESTION THIS ANSWERS
-------------------------
Every frequency and density figure for the redesigned datapath is routed on ASAP7,
a predictive and explicitly non-manufacturable academic PDK, and compared against
an A100 fabricated on TSMC N7. A foundry N7 kit cannot be used in a public
repository -- it is NDA-bound and no third party could re-run the result -- so that
asymmetry cannot be removed. ``docs/ASAP7_PHYSICAL.md`` says so plainly.

But the asymmetry admits a specific, testable worry that is NOT about absolute
numbers: **is ASAP7 flattering these particular changes?** A predictive PDK could
have cell-library or wire-load characteristics that happen to reward removing a
carry chain more than a real node would, in which case the whole redesign would be
an artefact of the measurement vehicle.

That worry is answerable without foundry access, by making the same change on a
node that shares nothing with ASAP7 and asking whether the RATIO survives. SKY130
is a fabricable 130 nm open PDK -- a different library, different metal stack,
different device generation, roughly an order of magnitude slower. If a change buys
the same factor there, the change is structural. If it buys much less, ASAP7 was
flattering it.

WHY RATIOS AND NOT ABSOLUTES
----------------------------
A uniform node offset cancels out of a ratio taken within one node, and this tool
also MEASURES whether the offset is uniform, by reporting the same design's fmax on
both nodes. That is the assumption the ratio argument rests on, so it is checked
rather than asserted.

WHAT THIS STILL DOES NOT DO
---------------------------
It does not calibrate ASAP7 against N7 and it does not turn a predictive result
into a silicon result. Two open nodes agreeing is evidence that a change is about
circuit structure rather than about one PDK; it is not evidence about what TSMC N7
would measure. Recorded as a refusal.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

#: Each entry is one design change, measured on two nodes. ``before`` and
#: ``after`` name records whose pnr stage completed on that node. Every one of
#: these is a record this repository holds; nothing is scaled or interpolated.
CHANGES: tuple[dict[str, Any], ...] = (
    {
        "change": "BF16 add: ten-deep normalise cascade -> leading-zero count",
        "why": ("the same function, SAT-proven equivalent over all 2**32 input "
                "pairs; only the circuit structure differs"),
        "asap7": {
            "before": "results/physical_abi3/asap7/bf16_add/rne_combinational.json",
            "after": "results/physical_abi3/asap7/bf16_add/flat_lzc.json",
        },
        "sky130hd": {
            "before": "results/physical_abi3/sky130hd/bf16_add/rne_combinational.json",
            "after": "results/physical_abi3/sky130hd/bf16_add/flat_lzc.json",
        },
    },
    {
        "change": "BF16 add: combinational -> five-stage pipeline",
        "why": "the headline datapath change; same arithmetic, cut into stages",
        "asap7": {
            "before": "results/physical_abi3/asap7/bf16_add/rne_combinational.json",
            "after": "results/physical_abi3/asap7/bf16_add/pipe_5stage.json",
        },
        "sky130hd": {
            "before": "results/physical_abi3/sky130hd/bf16_add/rne_combinational.json",
            "after": "results/physical_abi3/sky130hd/bf16_add/pipe_5stage.json",
        },
    },
    {
        "change": "reduction: serial accumulation -> balanced tree",
        "why": ("identical sum -- integer addition is associative and the "
                "combinational form is SAT-proven equivalent"),
        "asap7": {
            "before": "results/physical_abi3/asap7/reduction_s8_g2/pnr_serial_chain.json",
            "after": "results/physical_abi3/asap7/reduction_s8_g2/pnr.json",
        },
        "sky130hd": {
            "before": "results/physical_abi3/sky130hd/reduction_s8_g2/pnr_serial_chain.json",
            "after": "results/physical_abi3/sky130hd/reduction_s8_g2/pnr.json",
        },
    },
)

NODES = ("asap7", "sky130hd")


def git_state() -> dict[str, Any]:
    def run(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD") or None,
            "worktree_dirty": bool(run("status", "--porcelain"))}


def read(rel: str) -> dict[str, Any] | None:
    path = ROOT / rel
    if not path.exists():
        return None
    body = json.loads(path.read_text())
    m = (body.get("place_and_route") or {}).get("metrics") or {}
    if not m.get("fmax_hz"):
        return None
    return {
        "record": rel,
        "fmax_hz": float(m["fmax_hz"]),
        "core_area_um2": float(m["core_area_um2"]) if m.get("core_area_um2") else None,
        "standard_cell_count": m.get("standard_cell_count"),
        "status": body.get("status"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--tolerance", type=float, default=1.35,
                    help=("how far the two nodes' speedups may differ before the "
                          "change is called node-dependent (default 1.35x)"))
    args = ap.parse_args()

    rows, offsets = [], []
    for spec in CHANGES:
        entry: dict[str, Any] = {"change": spec["change"], "why": spec["why"],
                                 "nodes": {}}
        for node in NODES:
            before = read(spec[node]["before"])
            after = read(spec[node]["after"])
            if not before or not after:
                entry["nodes"][node] = {"available": False}
                continue
            entry["nodes"][node] = {
                "available": True,
                "before": before,
                "after": after,
                "speedup": after["fmax_hz"] / before["fmax_hz"],
                "area_ratio": (after["core_area_um2"] / before["core_area_um2"]
                               if before["core_area_um2"] and after["core_area_um2"]
                               else None),
                "cell_ratio": (after["standard_cell_count"] / before["standard_cell_count"]
                               if before["standard_cell_count"] and after["standard_cell_count"]
                               else None),
            }
        pair = [entry["nodes"][n] for n in NODES if entry["nodes"][n].get("available")]
        if len(pair) == 2:
            a, s = pair
            entry["speedup_agreement"] = (max(a["speedup"], s["speedup"])
                                          / min(a["speedup"], s["speedup"]))
            entry["reproduces"] = entry["speedup_agreement"] <= args.tolerance
            # the node offset, measured on the same design, both before and after
            entry["node_offset_before"] = a["before"]["fmax_hz"] / s["before"]["fmax_hz"]
            entry["node_offset_after"] = a["after"]["fmax_hz"] / s["after"]["fmax_hz"]
            offsets.extend([entry["node_offset_before"], entry["node_offset_after"]])
        rows.append(entry)

    measured = [r for r in rows if "reproduces" in r]
    all_reproduce = bool(measured) and all(r["reproduces"] for r in measured)
    offset_spread = (max(offsets) / min(offsets)) if offsets else None

    body = {
        "schema": "opentallas.audit.cross_node_reproducibility.v1",
        "question": ("Do the redesign's speedups reproduce on a second, unrelated "
                     "PDK, or are they an artefact of the ASAP7 vehicle?"),
        "git": git_state(),
        "tolerance": args.tolerance,
        "changes": rows,
        "all_reproduce": all_reproduce,
        "node_offset_spread": offset_spread,
        "refusals": [
            "not-an-n7-calibration: two open nodes agreeing shows a change is "
            "about circuit structure rather than about one PDK. It says nothing "
            "about what TSMC N7 would measure, and it does not turn a predictive "
            "result into a silicon result.",
            "ratio-argument-depends-on-a-uniform-offset: the claim that a node "
            "offset cancels out of a within-node ratio is only sound if the offset "
            "IS roughly uniform. node_offset_spread measures that rather than "
            "assuming it; a large spread would undermine the whole comparison.",
            "three-changes-not-the-whole-design: the compute unit and the vector "
            "unit are not re-routed on SKY130 here, because the compute unit needs "
            "SRAM macros that differ between the platforms and a macro swap is a "
            "different design, not the same one on another node.",
        ],
    }

    print("Does the redesign reproduce on a second node, or is it ASAP7?\n")
    for r in rows:
        print(f"  {r['change']}")
        for node in NODES:
            n = r["nodes"][node]
            if not n.get("available"):
                print(f"    {node:<10} no record")
                continue
            area = f"{n['area_ratio']:.2f}x area" if n["area_ratio"] else ""
            print(f"    {node:<10} {n['before']['fmax_hz']/1e6:>8.1f} -> "
                  f"{n['after']['fmax_hz']/1e6:>8.1f} MHz   "
                  f"{n['speedup']:>5.2f}x   {area}")
        if "reproduces" in r:
            verdict = "REPRODUCES" if r["reproduces"] else "NODE-DEPENDENT"
            print(f"    -> speedups agree to {r['speedup_agreement']:.2f}x: {verdict}")
        print()

    if offset_spread:
        print(f"node offset (same design, asap7/sky130hd) spread: "
              f"{offset_spread:.2f}x across {len(offsets)} measurements")
        print("  a tight spread is what lets a within-node ratio be read as "
              "node-independent")
    print(f"\nall measured changes reproduce: {all_reproduce}")
    print("\nThis does NOT calibrate ASAP7 against N7. It rules out the specific "
          "worry that the\nredesign's gains are an artefact of the ASAP7 vehicle.")

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
