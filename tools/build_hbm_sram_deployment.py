#!/usr/bin/env python3
"""Build an ABI 3.0 deployment for the shared HBM/SRAM accelerator.

One command turns a published neutral Tensor Kernel IR v3 document into the
three artifacts a device is given -- ``deployment.json``, ``descriptors.bin``
and ``program.bin`` -- plus the backend's own physical plan and the lane's two
independent reports.

Usage
-----
::

    PYTHONPATH=. python3 tools/build_hbm_sram_deployment.py \\
        --ir build/ir-v3/qwen3-8b/kernel_ir.v3.json \\
        --profile single-chip \\
        --out build/abi3/qwen3-8b

The same command with ``--profile cluster-32`` targets exactly 32 identical
nodes.  Nothing else changes: the graph, the backend and the code path are the
same, which is the claim this lane exists to demonstrate.

Every build is deterministic, so ``--check-determinism`` rebuilds from the same
inputs in a second pass and compares the program bytes, the descriptor table and
the deployment digest.  The exit status is non-zero if the independent verifier
or the independent checker rejects the result.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.backends.hbm_sram.capability import capability_for  # noqa: E402
from compiler.backends.hbm_sram.check import check_deployment  # noqa: E402
from compiler.backends.hbm_sram.lower import lower_with_plan  # noqa: E402
from compiler.backends.hbm_sram.plan import (  # noqa: E402
    PlanError,
    TileConfig,
    read_kernel_graph,
)
from compiler.ir.v3.kernel_ir import IRError, check_neutral  # noqa: E402
from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--ir",
        required=True,
        type=Path,
        help="published Tensor Kernel IR v3 document",
    )
    parser.add_argument(
        "--profile",
        default="single-chip",
        choices=(
            "single-chip",
            "cluster-32",
            "cluster-32-speculative",
            "cluster-n",
        ),
        help=(
            "which shared-chip deployment profile to compile against; "
            "cluster-n is amendment AM-R1's class, whose node count is a "
            "capability value and therefore needs --nodes"
        ),
    )
    parser.add_argument(
        "--nodes",
        type=int,
        default=None,
        help=(
            "node count for --profile cluster-n.  Refused for every other "
            "profile: those name a fixed cardinality, and a count silently "
            "ignored against one of them would build for a machine nobody "
            "asked for"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="directory to write the deployment bundle into",
    )
    parser.add_argument(
        "--plan-out",
        type=Path,
        default=None,
        help="where to write the physical plan (defaults to <out>/physical_plan.json)",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=None,
        help="where to write the build report (defaults to <out>/build_report.json)",
    )
    parser.add_argument(
        "--capability",
        type=Path,
        default=None,
        help=(
            "compile against this capability record instead of the profile's "
            "own.  run_abi3_cycle.py admits a deployment only against the "
            "capability it was compiled for, so timing a DERIVED machine "
            "(tools/derive_cycle_machine.py) needs the deployment rebuilt "
            "against that machine's record.  This overrides the machine, "
            "never the lowering."
        ),
    )
    parser.add_argument("--tile-rows", type=int, default=64)
    parser.add_argument("--tile-cols", type=int, default=128)
    parser.add_argument("--tile-depth", type=int, default=128)
    parser.add_argument(
        "--token-block",
        type=int,
        default=None,
        help=(
            "tokens per iteration of the program's token-block loop; the "
            "default is the backend's, which is exact for every span"
        ),
    )
    parser.add_argument(
        "--check-determinism",
        action="store_true",
        help="build twice and require byte-identical artifacts",
    )
    parser.add_argument(
        "--json", action="store_true", help="print the report as JSON only"
    )
    return parser.parse_args(argv)


def build(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    graph = read_kernel_graph(args.ir)
    neutrality = check_neutral(graph)
    capability = (
        Capability.from_dict(json.loads(Path(args.capability).read_text()))
        if getattr(args, "capability", None) is not None
        else capability_for(args.profile, node_count=getattr(args, "nodes", None))
    )
    tile = TileConfig(
        rows=args.tile_rows,
        cols=args.tile_cols,
        depth=args.tile_depth,
        **({} if args.token_block is None else {"block": args.token_block}),
    )
    deployment, plan = lower_with_plan(graph, capability, tile=tile)
    verification = verify_deployment(deployment, capability)
    legality = check_deployment(graph, deployment, capability)

    identical = None
    if args.check_determinism:
        again, again_plan = lower_with_plan(graph, capability, tile=tile)
        identical = (
            again.program == deployment.program
            and again.table.encode() == deployment.table.encode()
            and again.deployment_digest == deployment.deployment_digest
            and again_plan.plan_id == plan.plan_id
        )

    out = args.out
    written: dict[str, str] = {}
    if out is not None:
        deployment.write(out)
        written["deployment"] = str(out)
        plan_path = args.plan_out or (out / "physical_plan.json")
        plan.write(plan_path)
        written["plan"] = str(plan_path)

    report: dict[str, Any] = {
        "ir": str(args.ir),
        "model_id": graph.model_id,
        "graph_id": graph.graph_id,
        "profile": args.profile,
        "capability_digest": capability.digest,
        "topology_class": deployment.topology_class,
        "node_count": plan.topology.node_count,
        "plan_id": plan.plan_id,
        "deployment_digest": deployment.deployment_digest.hex(),
        "neutrality_errors": neutrality,
        "program": {
            "instructions": verification.instruction_count,
            "descriptors": verification.descriptor_count,
            "objects": len(deployment.objects),
            "proved_retired_work": verification.proved_retired_work,
            "declared_retired_work": verification.declared_retired_work,
            "loop_depth": verification.loop_depth,
            "events": verification.event_count,
            "state_resources": verification.state_resources,
            "link_instructions": deployment.notes.get("link_instructions", 0),
        },
        "compression": {
            "kernels": len(graph.kernels),
            "layers": plan.proofs["layers_covered"],
            "bands": plan.proofs["bands"],
            "degraded_bands": plan.proofs["degraded_bands"],
            "token_block_rows": plan.proofs["token_block_rows"],
            "instructions_per_kernel": round(
                verification.instruction_count / max(len(graph.kernels), 1), 4
            ),
            "work_per_instruction": round(
                verification.proved_retired_work
                / max(verification.instruction_count, 1),
                2,
            ),
        },
        "placement": dict(plan.proofs),
        "verifier": verification.to_dict(),
        "checker": {
            "ok": legality["ok"],
            "errors": legality["errors"],
            "checks": legality["checks"],
            "expected": legality["expected"],
            "actual": legality["actual"],
        },
        "numeric_contract_substitutions": deployment.notes.get(
            "numeric_contract_substitutions", {}
        ),
        "plan_warnings": list(plan.warnings),
        "deterministic": identical,
        "written": written,
    }

    status = 0
    if neutrality:
        status = 2
    if not verification.admitted or not legality["ok"]:
        status = 1
    if identical is False:
        status = 3
    return report, status


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report, status = build(args)
    except (PlanError, IRError) as error:
        print(f"build failed: {error}", file=sys.stderr)
        return 4
    except KeyError as error:
        # A profile/node-count mismatch, which capability_for refuses by name.
        print(f"build failed: {error.args[0] if error.args else error}", file=sys.stderr)
        return 4
    except ValueError as error:
        # A node count the topology class cannot express -- 32 under CLUSTER_N,
        # or a count that is not a whole number of the fabric's domains.  The
        # capability record refuses it; this reports the refusal rather than
        # ending in a traceback.
        print(f"build failed: {error}", file=sys.stderr)
        return 4

    if args.report_out is not None or args.out is not None:
        path = args.report_out or (args.out / "build_report.json")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return status

    program = report["program"]
    compression = report["compression"]
    placement = report["placement"]
    print(f"model            {report['model_id']}  ({report['graph_id'][:16]})")
    print(f"profile          {report['profile']}  x{report['node_count']} node(s)")
    print(f"plan             {report['plan_id'][:16]}")
    print(f"deployment       {report['deployment_digest'][:16]}")
    print(
        f"program          {program['instructions']} instructions, "
        f"{program['descriptors']} descriptors, {program['objects']} objects"
    )
    print(
        f"work             {program['proved_retired_work']} retired "
        f"(bound {program['declared_retired_work']}), loop depth "
        f"{program['loop_depth']}"
    )
    print(
        f"compression      {compression['kernels']} kernels over "
        f"{compression['layers']} layers in {compression['bands']} band(s) -> "
        f"{program['instructions']} instructions"
    )
    print(
        f"weights          {placement['weight_objects']} objects, "
        f"{placement['weight_segments']} checkpoint ranges, "
        f"{placement['weight_bytes'] / 1e9:.2f} GB, zero-copy"
    )
    print(
        f"memory           HBM {placement['hbm_bytes_per_node'] / 1e9:.2f} GB / "
        f"{placement['hbm_available_per_node'] / 1e9:.2f} GB "
        f"({'fits' if placement['hbm_fits'] else 'DOES NOT FIT'}); "
        f"SRAM {placement['sram_bytes'] / 1e6:.1f} MB / "
        f"{placement['sram_available'] / 1e6:.1f} MB "
        f"({'fits' if placement['sram_fits'] else 'DOES NOT FIT'})"
    )
    if program["link_instructions"]:
        print(f"cluster          {program['link_instructions']} link instructions")
    print(
        f"verifier         {'ADMITTED' if report['verifier']['admitted'] else 'REJECTED'}"
    )
    print(f"checker          {'OK' if report['checker']['ok'] else 'FAILED'}")
    if report["deterministic"] is not None:
        print(
            f"determinism      "
            f"{'byte-identical' if report['deterministic'] else 'DIVERGED'}"
        )
    for warning in report["plan_warnings"][:10]:
        print(f"  warning: {warning}")
    for error in report["verifier"]["errors"][:10]:
        print(f"  verifier: {error}")
    for error in report["checker"]["errors"][:10]:
        print(f"  checker: {error}")
    if report["written"]:
        for name, path in sorted(report["written"].items()):
            print(f"wrote {name}: {path}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
