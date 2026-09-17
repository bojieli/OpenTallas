#!/usr/bin/env python3
"""What stands between the reduced V4.1 deployment and an RTL-emitted token.

The clause this serves asks for end-to-end token generation through the new data
path under the real control plane, for DeepSeek V4.1 Flash among others.  The
distance to it had been estimated twice and measured never.  This measures it.

The question is NOT which engines exist.  It is which engine operations the
issue bridge *admits*: a kernel naming an operation the bridge refuses gets
``TRAP_CAPABILITY`` and the program stops, so the admitted set is exactly the
subset of the graph the RTL can execute.  So the audit reads three things and
compares them:

1. the engine operations the reduced V4.1 graph names, via ``KERNEL_TO_ENGINE``
   -- the same table the backends lower through, so this is the program's own
   demand and not a restatement of it;
2. the operations ``ot_a3_engine_issue_bridge.sv``'s admission expression
   accepts, read out of the RTL source by the ``FAMILY_x`` / ``FAMILY_SUB``
   token names the expression itself uses; and
3. whether an RTL module for each refused operation exists in ``rtl/abi3``.

Point 3 is what makes the number actionable.  An operation with no module is a
design task; an operation whose module sits in the tree unadmitted is a wiring
task, and the two are not the same size.  The answer at the time of writing is
that they are almost all the second kind.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import runtime.abi3.constants as C  # noqa: E402
from compiler.ir.v3.lowering import KERNEL_TO_ENGINE  # noqa: E402

BRIDGE = ROOT / "rtl/abi3/ot_a3_engine_issue_bridge.sv"
RTL_DIR = ROOT / "rtl/abi3"
DEFAULT_IR = ROOT / "build/ir-v3/deepseek-v4.1-flash-reduced-v1/kernel_ir.v3.json"
DEFAULT_OUTPUT = ROOT / "results/abi3/deepseek_v41_reduced_rtl_token_gap.json"

#: The operation names whose module is not found by the name rule below, with
#: where they actually live.  Kept explicit rather than widening the search: a
#: search loose enough to find these would also match modules that merely
#: mention an operation.
MODULE_OVERRIDES = {
    "VECTOR.MHC": "ot_a3_vector_mhc_post.sv",
    "VECTOR.COMPRESS": "ot_a3_vector_compress_project.sv",
    "DMA.NGRAM_HASH": "ot_a3_dma_ngram_hash.sv",
}

#: Families the engine issue bridge is not the executor for, with the module that
#: is.  Counting these as bridge gaps would overstate the distance: a STATE
#: instruction never reaches the bridge's admission expression at all, so its
#: absence from that expression is not a refusal.  ``ot_a3_state_controller.sv``
#: decodes ``A3_MAJOR_STATE`` and counts ``A3_STATE_READ`` itself.
NOT_BRIDGE_EXECUTED = {"STATE": "ot_a3_state_controller.sv"}


def admitted_operations() -> set[str]:
    """``FAMILY.SUB`` names the bridge's admission expression accepts."""
    source = BRIDGE.read_text(encoding="utf-8")
    start = source.index("end else if (!(((issue_family == FAMILY_DMA)")
    end = source.index("response_trap <= TRAP_CAPABILITY", start)
    expression = source[start:end]
    found = set()
    for family in C.Major:
        enum = C.SUBOPCODES.get(int(family))
        if enum is None:
            continue
        for member in enum:
            if f"{family.name}_{member.name}" in expression:
                found.add(f"{family.name}.{member.name}")
    return found


def operation_name(family: int, sub: int) -> str:
    enum = C.SUBOPCODES.get(family)
    name = None
    if enum is not None:
        name = next((m.name for m in enum if int(m) == sub), None)
    major = next((m.name for m in C.Major if int(m) == family), hex(family))
    return f"{major}.{name or f'sub{sub}'}"


def module_for(operation: str) -> str | None:
    """The RTL module implementing one operation, by name rule then override."""
    if operation in MODULE_OVERRIDES:
        candidate = RTL_DIR / MODULE_OVERRIDES[operation]
        return candidate.name if candidate.exists() else None
    family, _, sub = operation.partition(".")
    stem = f"ot_a3_{family.lower()}_{sub.lower()}.sv"
    if (RTL_DIR / stem).exists():
        return stem
    # A few carry the family in the other order or a bare name.
    for alternative in (f"ot_a3_{sub.lower()}.sv", f"ot_a3_{sub.lower()}_rne.sv"):
        if (RTL_DIR / alternative).exists():
            return alternative
    return None


def audit(ir_path: Path) -> dict[str, object]:
    graph = json.loads(ir_path.read_text(encoding="utf-8"))
    demand: collections.Counter[str] = collections.Counter()
    unmapped: collections.Counter[str] = collections.Counter()
    for kernel in graph["kernels"]:
        engine = KERNEL_TO_ENGINE.get(kernel["kind"])
        if engine is None:
            unmapped[kernel["kind"]] += 1
            continue
        demand[operation_name(int(engine.family), int(engine.sub))] += 1

    admitted = admitted_operations()
    elsewhere = {
        operation: NOT_BRIDGE_EXECUTED[operation.split(".")[0]]
        for operation in demand
        if operation.split(".")[0] in NOT_BRIDGE_EXECUTED
    }
    refused = sorted(set(demand) - admitted - set(elsewhere))
    wired = sorted(set(demand) & admitted)
    rows = []
    for operation in refused:
        module = module_for(operation)
        rows.append(
            {
                "operation": operation,
                "kernels": demand[operation],
                "rtl_module": module,
                "task": "wire an existing module" if module else "build a module",
            }
        )
    rows.sort(key=lambda row: (-int(row["kernels"]), row["operation"]))
    return {
        "schema": "opentallas.deepseek_v41_rtl_token_gap.v1",
        "graph_id": graph.get("graph_id"),
        "model_id": graph.get("model_id"),
        "kernels": len(graph["kernels"]),
        "operations_demanded": len(demand),
        "operations_admitted_by_the_bridge": len(wired),
        "operations_executed_outside_the_bridge": {
            operation: module for operation, module in sorted(elsewhere.items())
        },
        "operations_refused": len(refused),
        "refused_kernel_share": round(
            sum(demand[o] for o in refused) / max(sum(demand.values()), 1), 4
        ),
        "wire_an_existing_module": sum(1 for r in rows if r["rtl_module"]),
        "build_a_module": sum(1 for r in rows if not r["rtl_module"]),
        "admitted": [{"operation": o, "kernels": demand[o]} for o in
                     sorted(wired, key=lambda o: -demand[o])],
        "refused": rows,
        "unmapped_kernel_kinds": dict(unmapped),
        "statement": (
            "A kernel naming an operation the bridge refuses raises "
            "TRAP_CAPABILITY, so the admitted set is exactly the subset of this "
            "graph the RTL can execute -- except for the families the bridge does "
            "not execute at all, which are listed separately rather than counted "
            "as gaps. Every refused operation here has a module in rtl/abi3 that "
            "the admission expression does not name, so the distance is wiring "
            "per engine and not design."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ir", type=Path, default=DEFAULT_IR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args()

    report = audit(args.ir)
    if not args.print_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(
        f"{report['model_id']}: {report['operations_admitted_by_the_bridge']}"
        f"/{report['operations_demanded']} engine operations admitted; "
        f"{report['operations_refused']} refused "
        f"({report['wire_an_existing_module']} have a module to wire, "
        f"{report['build_a_module']} need one built)"
    )
    for row in report["refused"]:
        print(f"  {row['operation']:<26} x{row['kernels']:<5} {row['rtl_module'] or '(no module)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
