#!/usr/bin/env python3
"""Time one ABI 3.0 deployment under several cost tables and diff the result.

This is the *rerun* half of W9.5.  Feeding characterized values back into the
cycle model is only a result if somebody states what changed, and a single
timing run cannot state that: the number it prints is meaningless without the
number it replaced.  So this tool runs one deployment and one request under N
cost tables in one process, checks the property that makes the comparison legal
-- every architectural counter identical across all of them -- and writes one
canonical document holding both timings, their ratio, and the provenance census
of each.

The architectural-counter identity is checked, not assumed.  Two cost tables
applied to one deployment must give two timings and one architecture; if they
do not, the difference between the timings is not a cost-table effect and the
tool refuses to report a ratio.

Usage::

    PYTHONPATH=. python3 tools/run_abi3_cycle_sweep.py \\
        --deployment build/abi3/qwen3-8b-single-chip-w95 \\
        --capability configs/hardware/abi3_capability/hbm_sram_single_chip.json \\
        --baseline configs/hardware/abi3_cost_asap7_v1.json \\
        --cost-table configs/hardware/abi3_cost_asap7_v2.json \\
        --symbol SPAN_TOKENS=1 --symbol POSITION_START=0 \\
        --out results/abi3/cycle_characterization_feedback.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.abi3.capability import Capability, canonical_json  # noqa: E402
from runtime.abi3.constants import StorageClass, TopologyClass  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import Symbol  # noqa: E402
from runtime.abi3.fixture import build_fixture, fixture_capability  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402
from runtime.cycle.machine import MachineError, load_cost_table  # noqa: E402
from runtime.cycle.model import CycleModel, CycleRequest  # noqa: E402

SWEEP_SCHEMA = "opentallas.abi3.cycle_sweep.v1"

CLAIM_BOUNDARY = [
    "This is a cycle model reading a cost table, not a simulated chip.  It "
    "establishes what the model says, not what silicon does.",
    "A characterized rate here is one engine instance's measured cycle "
    "behaviour under a behavioural memory model, or one block's post-route "
    "fmax.  Neither is a measurement of the modelled machine, which "
    "replicates that engine as many times as the capability advertises.",
    "Engine lane counts come from the capability record and no routed block "
    "supports them; a per-lane rate becoming honest does not make the lane "
    "count honest.",
    "No cost table here contains a ROM or SRAM macro.  Memory bandwidth and "
    "latency remain assumed in every view.",
    "A ratio between two tables is a ratio between two models.  It is not a "
    "speedup, a regression, or a claim about any part.",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run_abi3_cycle_sweep", description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--deployment", type=Path, help="deployment root directory")
    source.add_argument(
        "--fixture",
        choices=sorted(c.name.lower() for c in (StorageClass.HBM, StorageClass.ROM)),
        help="use the built-in ABI 3.0 conformance fixture",
    )
    parser.add_argument("--capability", type=Path)
    parser.add_argument(
        "--fixture-topology",
        choices=[t.name for t in TopologyClass],
        default=TopologyClass.SINGLE_CHIP.name,
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="the cost table every other table is compared against",
    )
    parser.add_argument(
        "--cost-table",
        type=Path,
        action="append",
        default=[],
        required=True,
        help="a cost table to compare against the baseline (repeatable)",
    )
    parser.add_argument("--entrypoint", type=int, default=0)
    parser.add_argument("--transactions", type=int, default=1)
    parser.add_argument("--symbol", action="append", default=[], metavar="NAME=VALUE")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--note",
        default="",
        help="one line recording what this sweep was run to answer",
    )
    return parser


def load_request(args: argparse.Namespace) -> CycleRequest:
    symbols: dict[int, int] = {}
    for item in args.symbol:
        name, _, value = item.partition("=")
        name = name.strip()
        if not _:
            raise SystemExit(f"--symbol expects NAME=VALUE, got {item!r}")
        try:
            key = int(Symbol[name]) if not name.isdigit() else int(name)
        except KeyError:
            raise SystemExit(f"unknown runtime symbol {name!r}") from None
        symbols[key] = int(value)
    return CycleRequest(
        entrypoint_id=args.entrypoint,
        symbols=symbols,
        transactions=args.transactions,
    )


def load_inputs(args: argparse.Namespace) -> tuple[Deployment, Capability, Path | None]:
    if args.fixture is not None:
        topology = TopologyClass[args.fixture_topology]
        capability = (
            Capability.from_dict(json.loads(args.capability.read_text()))
            if args.capability is not None
            else fixture_capability(topology)
        )
        storage = StorageClass[args.fixture.upper()]
        return build_fixture(storage_class=storage, capability=capability), capability, None
    if args.capability is None:
        raise SystemExit("--capability is required with --deployment")
    deployment = Deployment.read(args.deployment)
    capability = Capability.from_dict(json.loads(args.capability.read_text()))
    return deployment, capability, args.deployment


def summarise(body: dict[str, Any], table_path: Path) -> dict[str, Any]:
    raw = table_path.read_bytes()
    table = json.loads(raw)
    characterized = sorted(
        name
        for name, entry in table["parameters"].items()
        if entry.get("provenance") == "characterized"
    )
    engines = {
        family: {
            "busy_cycles": block["busy_cycles"],
            "issued_tile_work": block.get("issued_tile_work", 0),
            "operations": block.get("operations", 0),
            "lanes": block["structure"]["lanes"],
            "work_per_lane_cycle": block["structure"]["work_per_lane_cycle"],
        }
        for family, block in sorted(body["engines"].items())
        if block.get("operations")
    }
    return {
        "cost_table": str(table_path),
        "cost_table_id": table["cost_table_id"],
        "cost_table_sha256": hashlib.sha256(raw).hexdigest(),
        "cost_table_version": table.get("version", ""),
        "technology_view": table.get("technology_view", ""),
        "status": body["execution"]["status"],
        "total_cycles": body["timing"]["total_cycles"],
        "clock_frequency_hz": body["timing"]["clock_frequency_hz"],
        "seconds": body["timing"]["seconds"],
        "provenance_class": body["provenance"]["class"],
        "provenance_counts": body["provenance"]["counts"],
        "characterized_parameters_in_table": characterized,
        "engines": engines,
        "tiling": {
            "tile_launches": body["tiling"]["tile_launches"],
            "issued_tile_work": body["tiling"]["issued_tile_work"],
            "useful_work": body["tiling"]["useful_work"],
            "padding_fraction": body["tiling"]["padding_fraction"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out: Path = args.out
    if out.exists() and not args.force:
        raise SystemExit(f"{out} already exists; pass --force to overwrite")

    load_engines()
    deployment, capability, root = load_inputs(args)
    request = load_request(args)

    tables = [args.baseline, *args.cost_table]
    summaries: list[dict[str, Any]] = []
    architectural: dict[str, dict[str, int]] = {}
    for path in tables:
        try:
            cost_table = load_cost_table(path)
        except MachineError as exc:
            raise SystemExit(str(exc)) from None
        result = CycleModel(deployment, capability, cost_table, root=root).run(request)
        summaries.append(summarise(result.to_dict(), path))
        architectural[str(path)] = result.architectural

    reference = architectural[str(args.baseline)]
    disagreements = {
        str(path): {
            name: {
                "baseline": reference.get(name, 0),
                "table": architectural[str(path)].get(name, 0),
            }
            for name in sorted(set(reference) | set(architectural[str(path)]))
            if reference.get(name, 0) != architectural[str(path)].get(name, 0)
        }
        for path in tables[1:]
    }
    disagreements = {k: v for k, v in disagreements.items() if v}
    if disagreements:
        print(
            "REFUSED: the architectural counters differ between cost tables, so "
            "the timing difference is not a cost-table effect:\n"
            + json.dumps(disagreements, indent=2),
            file=sys.stderr,
        )
        return 4

    base = summaries[0]
    comparisons = []
    for row in summaries[1:]:
        comparisons.append(
            {
                "cost_table_id": row["cost_table_id"],
                "baseline_cost_table_id": base["cost_table_id"],
                "cycles_ratio": row["total_cycles"] / base["total_cycles"],
                "seconds_ratio": row["seconds"] / base["seconds"],
                "clock_ratio": row["clock_frequency_hz"] / base["clock_frequency_hz"],
                "engine_busy_cycle_ratio": {
                    family: (
                        row["engines"][family]["busy_cycles"]
                        / base["engines"][family]["busy_cycles"]
                    )
                    for family in sorted(row["engines"])
                    if base["engines"].get(family, {}).get("busy_cycles")
                },
                "characterized_parameters_gained": sorted(
                    set(row["characterized_parameters_in_table"])
                    - set(base["characterized_parameters_in_table"])
                ),
                "characterized_parameters_lost": sorted(
                    set(base["characterized_parameters_in_table"])
                    - set(row["characterized_parameters_in_table"])
                ),
            }
        )

    body = {
        "schema": SWEEP_SCHEMA,
        "note": args.note,
        # A deployment root lives under build/ and is not in the repository, so
        # the document has to carry the command that makes it again.  Without
        # this the digests below name an artifact a reader cannot rebuild.
        "reproduce": {
            "this_command": ["tools/run_abi3_cycle_sweep.py", *(argv if argv is not None else sys.argv[1:])],
            "deployment_is_built_not_committed": bool(args.deployment),
        },
        "workload": {
            "deployment": str(args.deployment) if args.deployment else "",
            "fixture": args.fixture or "",
            "capability": str(args.capability) if args.capability else "built-in fixture",
            "capability_digest": capability.digest,
            "deployment_digest": deployment.deployment_digest.hex(),
            "entrypoint_id": args.entrypoint,
            "transactions": args.transactions,
            "symbols": {Symbol(k).name: v for k, v in sorted(request.symbols.items())},
        },
        "architectural_counters_identical_across_tables": True,
        "architectural_counters_compared": len(reference),
        "architectural_counters": dict(sorted(reference.items())),
        "runs": summaries,
        "comparisons": comparisons,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonical_json(body))

    print(f"wrote {out}")
    print(
        f"  architectural counters identical across {len(tables)} tables "
        f"({len(reference)} counters)"
    )
    for row in summaries:
        print(
            f"  {row['cost_table_id']:26s} {row['total_cycles']:>16,d} cycles "
            f"@ {row['clock_frequency_hz']:>13,.0f} Hz = {row['seconds']:>12.4f} s "
            f"[{row['provenance_class']}]"
        )
    for row in comparisons:
        print(
            f"  {row['cost_table_id']:26s} vs baseline: "
            f"cycles x{row['cycles_ratio']:.4f}, seconds x{row['seconds_ratio']:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
