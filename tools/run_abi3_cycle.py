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
import hashlib
import json
import math
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CYCLE_PRODUCER_SCHEMA = "opentallas.abi3.cycle_producer.v1"
CYCLE_PRODUCER_EVIDENCE_CLASS = "cycle_model_measurement"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.abi3.capability import Capability, canonical_json  # noqa: E402
from runtime.abi3.constants import StorageClass, TopologyClass  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import Symbol  # noqa: E402
from runtime.abi3.fixture import build_fixture, fixture_capability  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402
from runtime.cycle.machine import MachineError, load_cost_table  # noqa: E402
from runtime.cycle.model import (  # noqa: E402
    CycleModel,
    CycleRequest,
    ScheduleError,
    functional_counters,
)
from tools.abi3_comparison_boundary import (  # noqa: E402
    BoundaryError,
    build_boundary,
    validate_boundary,
)


#: Every directory whose Python source decides what a cycle costs.  The driver
#: script's own hash says nothing about these, and they are exactly what moved
#: under a pair of runs that were then compared as if they were comparable.
CYCLE_MODEL_SOURCE_ROOTS = ("runtime/cycle", "runtime/sim/engines")


def cycle_model_identity() -> dict[str, Any]:
    """Digest the loaded cycle-model implementation and engine registry.

    A cycle count is a function of the machine description *and* of the code
    that walks it.  Recording only ``tools/run_abi3_cycle.py`` pins the caller
    and leaves the model itself unnamed, so two artifacts produced by two
    different cost models are indistinguishable to a later reader -- which is
    how a 15.5% shift in one deployment's total was read as a measurement
    rather than as a changed model.

    Call this *after* ``load_engines()``: the registry decides which engine
    modules are resident, and an engine that never loaded cannot have priced
    anything.
    """
    modules: dict[str, str] = {}
    for module in list(sys.modules.values()):
        origin = getattr(module, "__file__", None)
        if not origin:
            continue
        try:
            relative = Path(origin).resolve().relative_to(REPO_ROOT)
        except ValueError:
            continue
        text = relative.as_posix()
        if not any(
            text == root or text.startswith(root + "/")
            for root in CYCLE_MODEL_SOURCE_ROOTS
        ):
            continue
        try:
            modules[text] = hashlib.sha256(
                (REPO_ROOT / relative).read_bytes()
            ).hexdigest()
        except OSError:
            continue
    payload = json.dumps(modules, sort_keys=True, separators=(",", ":")).encode()
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "roots": list(CYCLE_MODEL_SOURCE_ROOTS),
        "modules": modules,
    }


def require_comparable(current: Mapping[str, Any], prior: Mapping[str, Any]) -> None:
    """Refuse to relate two results the same cost model did not produce."""
    prior_inputs = prior.get("inputs")
    prior_identity = (
        prior_inputs.get("cycle_model") if isinstance(prior_inputs, Mapping) else None
    )
    prior_digest = (
        prior_identity.get("sha256") if isinstance(prior_identity, Mapping) else None
    )
    if not prior_digest:
        raise SystemExit(
            "the earlier result records no cycle-model identity, so it cannot "
            "be shown comparable with this one; re-run it with a driver that "
            "writes inputs.cycle_model before comparing the two"
        )
    if prior_digest != current["sha256"]:
        moved = sorted(
            path
            for path, digest in current["modules"].items()
            if isinstance(prior_identity.get("modules"), Mapping)
            and prior_identity["modules"].get(path) != digest
        )
        raise SystemExit(
            "cycle-model mismatch: the earlier result was produced by model "
            f"{prior_digest[:16]} and this run by {current['sha256'][:16]}; "
            "the two totals are not comparable"
            + (f" (changed: {', '.join(moved)})" if moved else "")
        )


def bandwidth_floor(body: Mapping[str, Any]) -> dict[str, Any]:
    """How far the reported total sits above the bytes it moved.

    A run cannot finish sooner than its own traffic divided by its own declared
    peak bandwidth.  That floor is the cheapest available sanity check on a
    cycle total, and it is computed from numbers the result already carries --
    yet nothing recomputed it, so a total sitting 11,558x above its floor at
    0.02% bandwidth utilisation was read as a per-token latency.  A run that far
    above its floor is measuring the memory-conflict model, not the program, and
    a ratio built on it says nothing about the workload.
    """
    timing = body.get("timing", {})
    total = int(timing.get("total_cycles", 0) or 0)
    stores: dict[str, Any] = {}
    binding_name, binding_floor = None, 0
    for name, store in (body.get("memory") or {}).items():
        if not isinstance(store, Mapping):
            continue
        peak = store.get("peak_bytes_per_cycle")
        moved = store.get("bytes_total", store.get("bytes_read"))
        if not peak or not moved:
            continue
        floor = math.ceil(float(moved) / float(peak))
        ratio = (total / floor) if floor else 0.0
        stores[name] = {
            "bytes_moved": int(moved),
            "peak_bytes_per_cycle": float(peak),
            "floor_cycles": int(floor),
            "total_over_floor": ratio,
            "bandwidth_utilisation": store.get("bandwidth_utilisation"),
            "conflict_cycles": store.get("conflict_cycles"),
        }
        # The BINDING floor is the tightest lower bound the run has to clear,
        # which is the store that moved the most cycles' worth of traffic --
        # not the store with the widest ratio, which is always whichever store
        # was barely touched.
        if floor > binding_floor:
            binding_name, binding_floor = name, int(floor)
    wait = int(timing.get("wait_stall_cycles", 0) or 0)
    return {
        "stores": stores,
        "binding_store": binding_name,
        "binding_floor_cycles": binding_floor,
        "total_over_binding_floor": (
            (total / binding_floor) if binding_floor else 0.0
        ),
        "wait_stall_share": (wait / total) if total else 0.0,
        "rule": (
            "total_cycles / (bytes_moved / peak_bytes_per_cycle); a total far "
            "above this floor is dominated by the conflict and stall model, "
            "not by the program's work"
        ),
    }


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
        "--compare-with",
        type=Path,
        help=(
            "an earlier cycle result to relate this one to; the run fails "
            "closed unless that result names the same cycle-model digest, "
            "because a total taken under a different cost model is not a "
            "comparable number"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing output path",
    )
    parser.add_argument(
        "--no-load-engines",
        action="store_true",
        help=(
            "do not register the engine implementations; every engine "
            "operation then traps, which is a legitimate diagnostic run"
        ),
    )
    parser.add_argument(
        "--permissive-schedules",
        action="store_true",
        help=(
            "time the deployment even though some operator has no tile "
            "mapping; the operators that lack one still fail closed when "
            "they execute"
        ),
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
    parser.add_argument(
        "--comparison-id",
        help=(
            "governed comparison identifier; requires --workload and causes the "
            "result to carry a source-revalidated comparison boundary"
        ),
    )
    parser.add_argument(
        "--workload",
        type=Path,
        help=(
            "governed workload JSON; requires --comparison-id and binds both its "
            "content SHA-256 and declared workload digest"
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
    governed = args.comparison_id is not None or args.workload is not None
    if (args.comparison_id is None) != (args.workload is None):
        raise SystemExit("--comparison-id and --workload must be supplied together")
    if governed and args.deployment is None:
        raise SystemExit("a governed comparison requires --deployment, not --fixture")
    if governed and args.no_verify:
        raise SystemExit("a governed comparison cannot use --no-verify")
    if governed and args.permissive_schedules:
        raise SystemExit("a governed comparison cannot use --permissive-schedules")
    if governed and args.no_load_engines:
        raise SystemExit("a governed comparison cannot use --no-load-engines")
    out: Path = args.out
    if out.exists() and not args.force:
        raise SystemExit(
            f"{out} already exists; pass --force to overwrite a previous result"
        )

    if not args.no_load_engines:
        load_engines()
    model_identity = cycle_model_identity()
    if args.compare_with is not None:
        try:
            prior = json.loads(args.compare_with.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"cannot read {args.compare_with}: {exc}") from None
        if not isinstance(prior, Mapping):
            raise SystemExit(f"{args.compare_with} is not a cycle result document")
        require_comparable(model_identity, prior)
    deployment, capability, root = load_inputs(args)
    try:
        cost_table = load_cost_table(args.cost_table)
    except MachineError as exc:
        raise SystemExit(str(exc)) from None
    request = load_request(args)
    comparison_boundary: dict[str, Any] | None = None
    if governed:
        try:
            comparison_boundary = build_boundary(
                comparison_id=args.comparison_id,
                deployment=deployment,
                deployment_path=args.deployment,
                capability=capability,
                capability_path=args.capability,
                cost_table=cost_table,
                cost_table_path=args.cost_table,
                workload_path=args.workload,
                request=request.to_dict(),
            )
        except (BoundaryError, OSError, ValueError, json.JSONDecodeError) as exc:
            raise SystemExit(f"invalid comparison boundary: {exc}") from None

    try:
        model = CycleModel(
            deployment,
            capability,
            cost_table,
            root=root,
            verify=not args.no_verify,
            strict_schedules=not args.permissive_schedules,
        )
        result = model.run(request)
    except ScheduleError as exc:
        raise SystemExit(f"tile mapping is incomplete: {exc}") from None
    body: dict[str, Any] = result.to_dict()
    body["producer"] = {
        "schema": CYCLE_PRODUCER_SCHEMA,
        "tool": "tools/run_abi3_cycle.py",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "evidence_class": CYCLE_PRODUCER_EVIDENCE_CLASS,
    }
    # The producer block above pins the caller, and its four keys are a frozen
    # shape -- tools/audit_abi3_asap7_comparison_readiness.py admits a result
    # only when ``set(producer)`` is exactly those four.  What decides the cycle
    # count is not the caller but the cost model, and that belongs beside the
    # cost table it walks: both are inputs this run consumed.  Recording only
    # the driver left two artifacts from two different cost models
    # indistinguishable to every later reader, which is how a 15.5% shift in one
    # deployment's total was read as a measurement rather than as a changed
    # model.
    body["inputs"]["cycle_model"] = model_identity

    if args.check_functional_agreement or governed:
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

    if comparison_boundary is not None:
        workload = comparison_boundary["workload"]
        target = comparison_boundary["target"]
        body["inputs"].update(
            {
                "model_digest": comparison_boundary["model_digest"],
                "workload": workload,
                "node_count": target["node_count"],
                "comparison_digest": comparison_boundary["comparison_sha256"],
                "comparison_contract_digest": comparison_boundary[
                    "comparison_contract"
                ]["sha256"],
                "comparison_workload_sha256": comparison_boundary[
                    "comparison_workload_sha256"
                ],
                "comparison_execution_scope": comparison_boundary[
                    "execution_scope"
                ],
                "comparison_boundary_digest": comparison_boundary["boundary_sha256"],
            }
        )
        body["workload_execution"] = {
            "scope": "measurement_slice",
            "full_workload_consumed": False,
            "terminal_condition_proved": False,
            "phases_completed": [],
            "input_workload_digest": None,
            "input_token_count": 0,
            "batch": None,
            "concurrency": None,
            "generated_token_ids": [],
            "generated_token_count": 0,
            "stop_reason": "not_applicable_measurement_slice",
            "post_eos_transactions": 0,
            "functional_artifact": None,
            "external_oracle": None,
        }
        body["comparison_boundary"] = comparison_boundary
        validation = validate_boundary(
            comparison_boundary,
            cycle_inputs=body["inputs"],
        )
        acceptance_checks = {
            "boundary_source_validation": validation["valid"],
            "full_workload_scope": (
                comparison_boundary["execution_scope"] == "full_workload"
                and body["workload_execution"]["scope"] == "full_workload"
                and body["workload_execution"]["full_workload_consumed"] is True
                and body["workload_execution"]["terminal_condition_proved"] is True
            ),
            "execution_status_success": body["execution"]["status"] == "SUCCESS",
            "execution_trap_none": body["execution"]["trap_class"] == "NONE",
            "execution_transactions_complete": (
                body["execution"]["transactions"]
                == body["inputs"]["request"]["transactions"]
                and body["execution"]["transactions"] > 0
            ),
            "schedule_audit_complete": (
                body["schedule_audit"]["complete"] is True
                and body["schedule_audit"]["findings"] == []
            ),
            "contract_gaps_empty": body.get("gaps") == [],
            "functional_counter_agreement": (
                body["functional_agreement"]["checked"] is True
                and body["functional_agreement"]["agrees"] is True
            ),
        }
        body["comparison_boundary_validation"] = {
            **validation,
            "acceptance_checks": acceptance_checks,
            "admissible": validation["valid"] and all(acceptance_checks.values()),
        }

    body["plausibility"] = bandwidth_floor(body)

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
    tiling = body["tiling"]
    print(f"  tile launches         {tiling['tile_launches']}")
    print(
        f"  tile padding          {tiling['padding_work']}"
        f" of {tiling['issued_tile_work']} work units"
    )
    floor = body["plausibility"]
    if floor["binding_store"] is not None:
        store = floor["stores"][floor["binding_store"]]
        print(
            f"  bandwidth floor       {floor['binding_store']} moved "
            f"{store['bytes_moved']} B, so no run can finish under "
            f"{store['floor_cycles']} cycles"
        )
        print(
            f"  total over that floor {store['total_over_floor']:.1f}x at "
            f"{store['bandwidth_utilisation']} utilisation, "
            f"{floor['wait_stall_share']:.4%} wait stall"
        )
    if body.get("gaps"):
        print(f"  contract gaps         {len(body['gaps'])}")
    if not body["schedule_audit"]["complete"]:
        print(
            f"  operators without a tile mapping "
            f"{len(body['schedule_audit']['findings'])}"
        )
    if comparison_boundary is not None:
        admitted = body["comparison_boundary_validation"]["admissible"]
        print(f"  comparison boundary  {'admissible' if admitted else 'refused'}")
        if not admitted:
            return 4
    return 0


def _main_with_clean_errors() -> int:
    """Report a refusal as a diagnosis, not a stack trace.

    Both a verification refusal and a schedule refusal are ordinary,
    informative outcomes here -- the tool is meant to fail closed on a
    deployment it cannot honestly time. A traceback would bury the reason.
    """
    from runtime.abi3.verifier import VerificationError
    from runtime.cycle import ScheduleError

    try:
        return main()
    except VerificationError as exc:
        print(f"deployment refused at admission:\n{exc}", file=sys.stderr)
        return 2
    except ScheduleError as exc:
        print(f"deployment cannot be timed: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(_main_with_clean_errors())
