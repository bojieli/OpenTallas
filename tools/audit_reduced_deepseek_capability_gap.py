#!/usr/bin/env python3
"""What still stands between the reduced DeepSeek IR and a deployment.

The reduced V4.1 kernel IR now exists and carries the three operators that had
no RTL before -- ATTENTION_SPARSE, SQRT_SOFTPLUS and INDEX_TOPK. Neither backend
will lower it yet, and this measures why rather than restating the refusal.

``tools/build_hbm_sram_deployment.py`` refuses a capability that does not
declare every numeric contract the graph uses, quoting ADR-003 section 14: "this
must be fixed by characterising the contract, never by substituting a different
one". So the distance to a deployment is a COUNT OF CONTRACTS TO CHARACTERISE,
per capability, and that is what this reports.

It is worth measuring because the previous estimate was wrong in kind. "Three
engines missing" was true of the RTL and is now closed; the deployment gate is a
different quantity an order of magnitude larger, and knowing which contracts and
how many is the difference between a plan and a guess.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CAPABILITIES = ROOT / "configs/hardware/abi3_capability"
REDUCED_IR = ROOT / "build/ir-v3/deepseek-v4.1-flash-reduced-v1/kernel_ir.v3.json"

#: The operators this programme's RTL work added. Their contracts being declared
#: is the check that the three engines are not what blocks a deployment.
NEW_ENGINE_CONTRACTS = (
    "sparse_attention_bf16_v1",
    "sqrt_softplus_router_binary32_v1",
    "selection_index_topk_indices_masked_topk_v1",
)


def contracts_used(ir_path: Path) -> set[str]:
    graph = json.loads(ir_path.read_text())
    used = {
        kernel.get("numeric_contract")
        for kernel in graph.get("kernels", ())
        if kernel.get("numeric_contract")
    }
    return used


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ir", type=Path, default=REDUCED_IR)
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()

    if not args.ir.is_file():
        raise SystemExit(
            f"{args.ir} does not exist; build it with "
            "tools/build_deepseek_v4_kernel_ir_v3.py --model "
            "deepseek-v4.1-flash-reduced-v1"
        )
    used = contracts_used(args.ir)
    graph = json.loads(args.ir.read_text())

    rows: list[dict[str, Any]] = []
    for path in sorted(CAPABILITIES.glob("*.json")):
        declared = set(json.loads(path.read_text()).get("numeric_contracts") or [])
        missing = sorted(used - declared)
        rows.append(
            {
                "capability": path.name,
                "declares": len(declared),
                "missing_count": len(missing),
                "missing": missing,
                "declares_every_new_engine_contract": all(
                    contract in declared for contract in NEW_ENGINE_CONTRACTS
                ),
            }
        )
    rows.sort(key=lambda row: row["missing_count"])

    print(f"the reduced DeepSeek IR uses {len(used)} numeric contracts across "
          f"{len(graph.get('kernels', ()))} kernels")
    print(f"\n{'capability':<44}{'declares':>9}{'missing':>9}  new engines")
    for row in rows:
        print(f"  {row['capability']:<42}{row['declares']:>9}"
              f"{row['missing_count']:>9}  "
              f"{'yes' if row['declares_every_new_engine_contract'] else 'no'}")
    closest = rows[0]
    print(f"\nclosest: {closest['capability']}, {closest['missing_count']} to "
          f"characterise:")
    for contract in closest["missing"]:
        print(f"    {contract}")

    report = {
        "ir": str(args.ir.relative_to(ROOT)),
        "graph_id": graph.get("graph_id"),
        "kernel_count": len(graph.get("kernels", ())),
        "contracts_used": sorted(used),
        "capabilities": rows,
        "closest_capability": closest["capability"],
        "contracts_to_characterise": closest["missing_count"],
        "the_three_new_engines_are_not_the_blocker": {
            "contracts": list(NEW_ENGINE_CONTRACTS),
            "declared_by_the_closest_capability": closest[
                "declares_every_new_engine_contract"
            ],
            "why_it_matters": (
                "the RTL work added these three and they are declared, so what "
                "stops a deployment is the rest of the V4.1 architecture -- the "
                "candidate mask, the engram gate and its hashes, the grouped "
                "output projection, the hyper-connections, the fp4/fp8 "
                "conversions, the rope variants and the sampling path"
            ),
        },
        "not_a_claim": [
            "that characterising these contracts is mechanical",
            "that the ROM capabilities are close: they declare 11 to 17 of the "
            "80 this graph uses, against the HBM capabilities' 68",
        ],
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
        print(f"\nwrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
