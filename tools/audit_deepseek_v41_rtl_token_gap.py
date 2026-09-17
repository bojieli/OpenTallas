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

Point 3 is what makes the number actionable -- but module existence is NOT the
same as a form match, and reporting it as one overstates how close the work is.
``ot_a3_vector_convert.sv`` says so in its own header: "This block implements the
unscaled, one-input/one-output form of CONVERT ... Block-scaled dequantisation
and two-output quantisation need more than this engine-array port exposes and
remain fail-closed."  Meanwhile 370 of the graph's 444 CONVERT kernels are
``bf16 -> (fp8_e4m3fn, e8m0)``: block quantisation with a scale plane, two
outputs.  A module that exists and cannot be asked for what the graph needs is
not a wiring away from working.

So the audit also measures the FORM each refused operation is asked for -- how
many operands, how many results, how many distinct numeric contracts -- and
compares it against what the engine array's ports carry.  That is what separates
an operation that needs an admission leg from one that needs port surface first.
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

ARRAY = ROOT / "rtl/abi3/ot_a3_engine_array.sv"


def array_port_surface() -> tuple[int, int]:
    """What one engine-array dispatch carries, counted from the array's ports.

    Read from the source rather than written down, because a constant here would
    go stale the moment a port is added and would then misreport the remaining
    work in the safe direction.

    ``cfg_input_valid(4'b0011)`` in the bridge is NOT this number: that is what
    the bridge currently *passes* for the engines it drives.  The array declares
    ``m0``..``m3``, and ``ot_a3_vector_mhc_post`` already reads all four
    (branch/residual/post/comb), so four operands are precedented.  The result
    side is one: every engine in the array writes through the single
    ``out_we``/``out_addr``/``out_data``, ``ot_a3_vector_compress_project``
    included, so a two-result operation needs a port that does not exist yet.
    """
    source = ARRAY.read_text(encoding="utf-8")
    header = source[source.index("module ot_a3_engine_array") : source.index("\n);")]
    operands = len(re.findall(r"input\s+wire\s+\[31:0\]\s+m(\d+)_rd_data", source))
    results = len(re.findall(r"output\s+wire\s+out_we", header)) or 1
    return max(operands, 1), results


ARRAY_OPERAND_PORTS, ARRAY_RESULT_PORTS = array_port_surface()


def bridge_result_bank_selectors() -> list[str]:
    """Which operand banks the BRIDGE can point at the result bank.

    A second surface, distinct from the array's port count and easy to miss.  The
    array reads four banks, but an operand that is a *produced plane* has to be
    read from the result bank the earlier operators wrote, and the bridge says
    which bank does that with one output per bank -- ``m0_reads_result``,
    ``m1_reads_result``.  There is no ``m2_reads_result``, and ``m2_rd_en`` is
    forced to zero for every ``mapped_family_q`` operator, so a mapped operator
    whose THIRD operand is a produced plane cannot read it today however complete
    its admission leg is.  ``VECTOR.INDEX_SCORE`` is exactly that shape: query,
    key and a head-weight plane, all three arena-resident.
    """
    source = BRIDGE.read_text(encoding="utf-8")
    return [
        f"m{index}_reads_result"
        for index in range(8)
        if f"output wire          m{index}_reads_result" in source
        or f"m{index}_reads_result," in source
    ]


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


def instantiation_sites(module: str) -> list[str]:
    """The RTL files that instantiate ``module``, excluding its own definition.

    A module that exists and is instantiated NOWHERE is further from working than
    one the engine array already holds, and the admission leg is not the whole of
    the difference: the engine has to be given a place to run, its operand and
    result ports connected to the array's banks, and its ``select_*`` term added.
    Five of the refused operations are already in ``ot_a3_engine_array.sv`` and the
    rest are in the tree and instantiated by nothing, which is worth separating.
    """
    stem = module.removesuffix(".sv")
    sites = []
    for path in sorted(RTL_DIR.glob("*.sv")):
        if path.name == module:
            continue
        if f"{stem} " in path.read_text(encoding="utf-8"):
            sites.append(path.name)
    return sites


#: Why a single leg cannot be qualified on its own today.
#:
#: The bridge's qualification harness is
#: ``tools/run_a3_operator_admission_rtl_campaign.py``, and every case it builds is
#: anchored to a *Qwen3 program counter* and compared against the shipped prefix's
#: golden write stream for that counter.  So an operator Qwen3 does not issue has
#: no PC and no golden, and the campaign cannot cover its leg however correct the
#: leg is.  Qwen3 issues none of the thirteen.
#:
#: Measured by writing the VECTOR.HADAMARD leg -- the cheapest of them: one
#: operand from ``m0``, one result, one contract, engine already instantiated in
#: ``ot_a3_engine_array.sv``.  Twenty-two sites across the bridge, and it
#: elaborates clean under Verilator.  It was then reverted rather than committed,
#: because an unqualified change to this file stales the five committed artifacts
#: that pin its digest -- including both operator-admission campaigns -- and buys
#: nothing until something can issue the operator.
#:
#: So the unblocking work is a harness, not a leg: a single-operator vehicle that
#: builds a deployment from a minimal graph naming one refused operator beside
#: admitted ones, drives it through the bridge, and checks the result against that
#: operator's reference. With it, all thirteen legs qualify one at a time. Without
#: it they qualify only once a whole DeepSeek program lowers, which needs all ten
#: of V4-Flash's or all thirteen of V4.1's at once.
LEG_QUALIFICATION_HARNESS = (
    "tools/run_a3_operator_admission_rtl_campaign.py anchors every case to a Qwen3 "
    "program counter and its golden write stream, so it cannot cover a leg for an "
    "operator Qwen3 does not issue -- which is all thirteen. Qualifying one leg at "
    "a time needs a single-operator vehicle that lowers a minimal graph naming one "
    "refused operator and checks it against that operator's reference; otherwise a "
    "leg is only exercisable once a whole DeepSeek program lowers, needing ten "
    "(V4-Flash) or thirteen (V4.1) legs at once."
)


def audit(ir_path: Path) -> dict[str, object]:
    graph = json.loads(ir_path.read_text(encoding="utf-8"))
    demand: collections.Counter[str] = collections.Counter()
    unmapped: collections.Counter[str] = collections.Counter()
    form: dict[str, dict[str, set]] = {}
    # ONE OPCODE CAN COVER TWO OPERATIONS.  ``VECTOR.MHC`` is both
    # ``HYPER_CONNECT_PRE`` (four operands, TWO results, a softmax-and-Sinkhorn
    # coefficient computation) and ``HYPER_CONNECT_POST`` (four operands, one
    # result, a multiply-add tree).  ``ot_a3_vector_mhc_post.sv`` implements the
    # second and says so -- "PRE and HEAD need correctly-rounded nonlinear
    # arithmetic and remain fail-closed" -- so grouping them under the opcode
    # reports one task where there are two of different sizes.  Kinds are tracked
    # beside operations for that reason.
    kinds: dict[str, dict[str, set]] = {}
    first_refusal: dict[str, int] = {}
    for index, kernel in enumerate(graph["kernels"]):
        engine = KERNEL_TO_ENGINE.get(kernel["kind"])
        if engine is None:
            unmapped[kernel["kind"]] += 1
            continue
        operation = operation_name(int(engine.family), int(engine.sub))
        demand[operation] += 1
        for table, key in ((form, operation), (kinds, kernel["kind"])):
            shape = table.setdefault(
                key,
                {"operands": set(), "results": set(), "contracts": set(),
                 "operation": {operation}, "count": set()},
            )
            shape["operands"].add(len(kernel["inputs"]))
            shape["results"].add(len(kernel["outputs"]))
            shape["contracts"].add(kernel["numeric_contract"])
            shape["operation"].add(operation)
        first_refusal.setdefault(kernel["kind"], index)

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
        shape = form[operation]
        operands = max(shape["operands"])
        results = max(shape["results"])
        sites = instantiation_sites(module) if module else []
        if module is None:
            blocked = "build a module"
        elif results > ARRAY_RESULT_PORTS or operands > ARRAY_OPERAND_PORTS:
            blocked = "widen the engine-array port surface, then instantiate and wire"
        elif not sites:
            blocked = "instantiate the module, then add the leg"
        elif len(shape["contracts"]) > 1:
            blocked = "add a multi-contract admission leg"
        else:
            blocked = "add an admission leg"
        rows.append(
            {
                "operation": operation,
                "kernels": demand[operation],
                "rtl_module": module,
                "instantiated_by": sites,
                "operands_needed": operands,
                "results_needed": results,
                "numeric_contracts_needed": len(shape["contracts"]),
                "blocked_on": blocked,
            }
        )
    rows.sort(key=lambda row: (-int(row["kernels"]), row["operation"]))

    # The program's own order, which is what makes this a plan rather than a list.
    # Nothing downstream of the first refusal can be reached, so the order the
    # kernels appear in fixes the order the work has to be done in.
    refused_ops = set(refused)
    by_order = []
    for kind, shape in sorted(kinds.items(), key=lambda item: first_refusal[item[0]]):
        operation = sorted(shape["operation"])[0]
        if operation not in refused_ops:
            continue
        by_order.append(
            {
                "position": first_refusal[kind],
                "kernel_kind": kind,
                "operation": operation,
                "operands_needed": max(shape["operands"]),
                "results_needed": max(shape["results"]),
                "numeric_contracts_needed": len(shape["contracts"]),
            }
        )
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
        "blocked_on": dict(
            collections.Counter(str(r["blocked_on"]) for r in rows)
        ),
        "array_operand_ports": ARRAY_OPERAND_PORTS,
        "array_result_ports": ARRAY_RESULT_PORTS,
        "bridge_result_bank_selectors": bridge_result_bank_selectors(),
        "leg_qualification_harness": LEG_QUALIFICATION_HARNESS,
        "bridge_result_bank_caveat": (
            "An operand that is a produced plane must be read from the result "
            "bank, and the bridge names one output per bank that may do so. Only "
            "m0 and m1 have one, and m2_rd_en is forced low for every mapped "
            "operator, so even an operation whose leg is otherwise complete "
            "cannot read a third produced operand -- VECTOR.INDEX_SCORE's query, "
            "key and head-weight planes are all three arena-resident."
        ),
        "admitted": [{"operation": o, "kernels": demand[o]} for o in
                     sorted(wired, key=lambda o: -demand[o])],
        "refused": rows,
        "unmapped_kernel_kinds": dict(unmapped),
        "forced_order": by_order,
        "forced_order_note": (
            "A refused operation stops the program, so no kernel after the first "
            "refusal is reachable and the program's own order fixes the order the "
            "work must be done in. The first entry is the whole critical path "
            "until it is done."
        ),
        "statement": (
            "A kernel naming an operation the bridge refuses raises "
            "TRAP_CAPABILITY, so the admitted set is exactly the subset of this "
            "graph the RTL can execute -- except for the families the bridge does "
            "not execute at all, which are listed separately rather than counted "
            "as gaps. Every refused operation has a module in rtl/abi3, but a "
            "module is not a form match: the engine array carries two operands "
            "and one result per dispatch, and an operation asking for more needs "
            "that surface widened before an admission leg can be written. "
            "ot_a3_vector_convert.sv states its own restriction in its header. "
            "Nor is a module in the tree necessarily instantiated: five of the "
            "thirteen are in ot_a3_engine_array.sv and the rest are instantiated "
            "by nothing, so they need a place to run before a leg means anything."
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
        f"{report['operations_refused']} refused"
    )
    for label, count in sorted(report["blocked_on"].items()):
        print(f"  {count:2d}  {label}")
    print()
    print("  forced order (program position -> kind):")
    for row in report["forced_order"]:
        print(
            f"    {row['position']:5d}  {row['kernel_kind']:<22} "
            f"{row['operands_needed']}in/{row['results_needed']}out "
            f"{row['numeric_contracts_needed']}c  ({row['operation']})"
        )
    print()
    for row in report["refused"]:
        print(
            f"  {row['operation']:<26} x{row['kernels']:<5} "
            f"{row['operands_needed']}in/{row['results_needed']}out "
            f"{row['numeric_contracts_needed']}c "
            f"{'inst' if row['instantiated_by'] else '----'}  {row['blocked_on']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
