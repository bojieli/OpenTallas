#!/usr/bin/env python3
"""Run the shared ABI 3.0 cycle model and write a canonical JSON result.

Usage::

    PYTHONPATH=. python3 tools/run_abi3_cycle.py \
        --deployment build/qwen3-hbm \
        --capability build/qwen3-hbm/capability.json \
        --cost-table configs/hardware/abi3_cost_asap7_v1.json \
        --request configs/benchmarks/decode_one.json \
        --out results/tensor_accelerator/qwen3_hbm_cycle.json

The output path must not already exist unless ``--force`` is given: a timing
result is evidence, and silently overwriting evidence is how an unreproducible
number gets into a report.

The written document is canonical JSON -- sorted keys, compact separators,
ASCII, one trailing newline -- exactly like every other digest-bound document in
ABI 3.0, so two runs with the same inputs are byte-identical.
"""

from __future__ import annotations

import argparse
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
from runtime.cycle.machine import MachineError, load_cost_table  # noqa: E402
from runtime.cycle.model import CycleModel, CycleRequest, functional_counters  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_abi3_cycle",
        description="Time one ABI 3.0 deployment on the shared cycle model.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--deployment",
        type=Path,
        help="deployment root directory (deployment.json, descriptors.bin, program.bin)",
    )
    source.add_argument(
        "--fixture",
        choices=sorted(c.name.lower() for c in (StorageClass.HBM, StorageClass.ROM)),
        help="use the built-in ABI 3.0 conformance fixture in this storage class",
    )
    parser.add_argument(
        "--capability",
        type=Path,
        help="capability JSON; required with --deployment, optional with --fixture",
    )
    parser.add_argument(
        "--fixture-topology",
        choices=[t.name for t in TopologyClass],
        default=TopologyClass.SINGLE_CHIP.name,
        help="topology class for the built-in fixture capability",
    )
    parser.add_argument(
        "--cost-table",
        type=Path,
        required=True,
        help="cost table under configs/hardware/abi3_cost_*.json",
    )
    parser.add_argument(
        "--request",
        type=Path,
        help="request JSON: entrypoint_id, symbols, transactions, generation_policy_id",
    )
    parser.add_argument(
        "--entrypoint",
        type=int,
        default=0,
        help="entrypoint ID when no --request file is given",
    )
    parser.add_argument(
        "--transactions",
        type=int,
        default=1,
        help="number of device transactions to run when no --request file is given",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="bind one runtime symbol, e.g. --symbol SPAN_TOKENS=1 (repeatable)",
    )
    parser.add_argument("--out", type=Path, required=True, help="output JSON path")
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing output path",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="skip deployment admission (diagnostics only; never for evidence)",
    )
    parser.add_argument(
        "--check-functional-agreement",
        action="store_true",
        help=(
            "also run the plain functional device and record whether every "
            "non-timing counter matches"
        ),
    )
    return parser


def load_request(args: argparse.Namespace) -> CycleRequest:
    if args.request is not None:
        body = json.loads(args.request.read_text())
        return CycleRequest.from_dict(body)
    symbols: dict[int, int] = {}
    for item in args.symbol:
        if "=" not in item:
            raise SystemExit(f"--symbol expects NAME=VALUE, got {item!r}")
        name, _, value = item.partition("=")
        name = name.strip()
        try:
            key = int(Symbol[name]) if not name.isdigit() else int(name)
        except KeyError:
            raise SystemExit(
                f"unknown runtime symbol {name!r}; legal names are "
                f"{[s.name for s in Symbol]}"
            ) from None
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
        deployment = build_fixture(storage_class=storage, capability=capability)
        return deployment, capability, None
    if args.capability is None:
        raise SystemExit("--capability is required with --deployment")
    deployment = Deployment.read(args.deployment)
    capability = Capability.from_dict(json.loads(args.capability.read_text()))
    return deployment, capability, args.deployment


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out: Path = args.out
    if out.exists() and not args.force:
        raise SystemExit(
            f"{out} already exists; pass --force to overwrite a previous result"
        )

    deployment, capability, root = load_inputs(args)
    try:
        cost_table = load_cost_table(args.cost_table)
    except MachineError as exc:
        raise SystemExit(str(exc)) from None
    request = load_request(args)

    model = CycleModel(
        deployment,
        capability,
        cost_table,
        root=root,
        verify=not args.no_verify,
    )
    result = model.run(request)
    body: dict[str, Any] = result.to_dict()

    if args.check_functional_agreement:
        reference = functional_counters(
            deployment,
            capability,
            request,
            root=root,
            verify=not args.no_verify,
        )
        observed = result.architectural
        differences = {
            name: {
                "functional": reference.get(name, 0),
                "cycle_model": observed.get(name, 0),
            }
            for name in sorted(set(reference) | set(observed))
            if reference.get(name, 0) != observed.get(name, 0)
        }
        body["functional_agreement"] = {
            "checked": True,
            "agrees": not differences,
            "counters_compared": len(set(reference) | set(observed)),
            "differences": differences,
            "rule": body["counters"]["agreement_rule"],
        }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonical_json(body))

    timing = body["timing"]
    provenance = body["provenance"]
    print(f"wrote {out}")
    print(
        f"  status                {body['execution']['status']}"
        f" ({body['execution']['trap_class']})"
    )
    print(f"  total cycles          {timing['total_cycles']}")
    print(f"  seconds               {timing['seconds']}")
    print(f"  provenance class      {provenance['class']}")
    print(f"  parameters by class   {provenance['counts']}")
    if provenance["depends_on_assumed_values"]:
        print(
            "  NOTE: this result depends on assumed machine values and is not a "
            "performance claim"
        )
    if body.get("gaps"):
        print(f"  contract gaps         {len(body['gaps'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
