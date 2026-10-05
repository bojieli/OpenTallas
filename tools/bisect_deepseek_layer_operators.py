#!/usr/bin/env python3
"""Locate the first operator-output mismatch inside one DeepSeek layer.

The residual-boundary diagnostic can identify the layer that creates a lane
difference, but a complete P32 transaction is expensive and activation buffers
are reused after the layer.  This tool observes operator outputs in flight and
raises a private completion signal as soon as the next layer consumes the
result.  The target transaction is not committed and no token claim is made;
when tracing decode, earlier transactions necessarily commit so the target sees
the real session state.

HBM may lower one graph kernel to several operators around a collective.  The
comparison therefore uses the final lowered descriptor for each
``(source_kernel_id, output_slot)`` pair.  If that descriptor is invoked more
than once by a dynamic row loop, every terminal invocation is compared in
order; all earlier auxiliary observations remain inspectable in the artifact.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import gc
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sys
import time
from typing import Any

# The blocked GEMM association is part of the numeric implementation identity.
# Establish the governed default before NumPy (or any runtime module importing
# it) loads; an explicit caller setting remains authoritative.
for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
):
    os.environ.setdefault(_thread_variable, "8")

import numpy as np  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.ir.v3.kernel_ir import KernelGraph  # noqa: E402
from runtime.abi3.capability import Capability, canonical_json  # noqa: E402
from runtime.abi3.constants import DType, NO_ID  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.driver import GenerationDriver  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402
from tools.bisect_deepseek_lane_activations import (  # noqa: E402
    DEFAULT_IR,
    DEFAULT_SNAPSHOT,
    LANES,
    RUNTIME_SOURCES,
    _boundary_kind,
    _sha256,
)

SCHEMA = "opentallas.deepseek_v4_layer_operator_bisect.v1"
DEFAULT_WORKLOAD = (
    REPO / "build/workloads/deepseek-v4-flash-0731-prefix/TA-DS-CHAT-1-P32.json"
)


class _TraceComplete(Exception):
    """Private non-failure signal used to stop before the next layer runs."""


def _payload(
    view: Any, ctx: Any, *, hash_leading_slices: bool = False
) -> dict[str, Any]:
    raw = np.ascontiguousarray(np.asarray(ctx.read(view)))
    payload = {
        "dtype": DType(int(view.dtype)).name,
        "shape": list(raw.shape),
        "elements": int(raw.size),
        "payload_sha256": hashlib.sha256(raw.tobytes()).hexdigest(),
    }
    if hash_leading_slices and raw.ndim > 1:
        payload["leading_slice_sha256"] = [
            hashlib.sha256(np.ascontiguousarray(row).tobytes()).hexdigest()
            for row in raw
        ]
    return payload


def _implementation_identity() -> dict[str, Any]:
    try:
        from runtime.sim.backend import get_backend

        return dict(get_backend().implementation_identity())
    except Exception as exc:
        return {"unavailable": f"{type(exc).__name__}: {exc}"}


def _run_lane(
    name: str,
    deployment_path: Path,
    capability_path: Path,
    graph: KernelGraph,
    snapshot: Path,
    prompt: list[int],
    max_new_tokens: int,
    layer: int,
    stop_boundary: int,
    trace_output_boundary: int | None,
    trace_input_sources: frozenset[int],
) -> dict[str, Any]:
    deployment = Deployment.read(deployment_path)
    capability = Capability.from_dict(json.loads(capability_path.read_text()))
    records: list[dict[str, Any]] = []
    input_records: list[dict[str, Any]] = []
    boundaries: list[dict[str, Any]] = []
    boundary_index = 0

    def hook(pc: int, instruction: Any, family: Any, ctx: Any) -> None:
        nonlocal boundary_index
        try:
            operator = ctx.operator(instruction.descriptor_id)
        except Exception:
            return
        source = int(operator.payload.get("source_kernel_id", -1))
        if not 0 <= source < len(graph.kernels):
            return
        kernel = graph.kernels[source]
        boundary_kind = _boundary_kind(kernel)
        at_stop_boundary = boundary_kind is not None and boundary_index == stop_boundary
        trace_active = (
            trace_output_boundary is None or boundary_index == trace_output_boundary
        ) and not at_stop_boundary
        if trace_active and source in trace_input_sources:
            for slot in range(4):
                view_id = int(operator.payload[f"input_view_{slot}"])
                if view_id == NO_ID:
                    continue
                try:
                    view = ctx.input_view(operator, slot)
                    payload = _payload(view, ctx, hash_leading_slices=True)
                except Exception as exc:
                    payload = {"unreadable": f"{type(exc).__name__}: {exc}"}
                input_records.append(
                    {
                        "observation": len(input_records),
                        "source_kernel_id": source,
                        "kernel_id": kernel.kernel_id,
                        "kind": kernel.kind,
                        "pc": pc,
                        "operator_descriptor_id": operator.descriptor_id,
                        "engine_family": int(operator.payload["engine_family"]),
                        "engine_sub": int(operator.payload["engine_sub"]),
                        "input_slot": slot,
                        **payload,
                    }
                )
        if trace_active and kernel.layer == layer:
            for slot in range(2):
                view_id = int(operator.payload[f"output_view_{slot}"])
                if view_id == NO_ID:
                    continue
                try:
                    view = ctx.output_view(operator, slot)
                    payload = _payload(view, ctx)
                except Exception as exc:
                    payload = {"unreadable": f"{type(exc).__name__}: {exc}"}
                records.append(
                    {
                        "observation": len(records),
                        "source_kernel_id": source,
                        "kernel_id": kernel.kernel_id,
                        "kind": kernel.kind,
                        "pc": pc,
                        "operator_descriptor_id": operator.descriptor_id,
                        "engine_family": int(operator.payload["engine_family"]),
                        "engine_sub": int(operator.payload["engine_sub"]),
                        "output_slot": slot,
                        **payload,
                    }
                )
        if boundary_kind is None:
            return
        view = ctx.input_view(operator, 0)
        boundaries.append(
            {
                "boundary": boundary_index,
                "boundary_kind": boundary_kind,
                "source_kernel_id": source,
                "kernel_id": kernel.kernel_id,
                **_payload(view, ctx),
            }
        )
        if boundary_index == stop_boundary:
            raise _TraceComplete
        boundary_index += 1

    device = Device(
        deployment,
        capability,
        root=snapshot,
        verify=False,
        on_issue=hook,
    )
    started = time.perf_counter()
    stopped = False
    result = None
    try:
        result = GenerationDriver(device).generate(
            prompt, max_new_tokens=max_new_tokens
        )
    except _TraceComplete:
        stopped = True
    wall = time.perf_counter() - started
    lane = {
        "lane": name,
        "deployment": str(deployment_path.relative_to(REPO)),
        "deployment_digest": deployment.deployment_digest.hex(),
        "deployment_json_sha256": _sha256(deployment_path / "deployment.json"),
        "capability": str(capability_path.relative_to(REPO)),
        "capability_digest": capability.digest,
        "node_count": device.node_count,
        "requested_token_count": max_new_tokens,
        "stopped_at_requested_boundary": stopped,
        "wall_seconds": round(wall, 6),
        "boundary_count": len(boundaries),
        "boundaries": boundaries,
        "operator_output_count": len(records),
        "operator_outputs": records,
        "operator_input_count": len(input_records),
        "operator_inputs": input_records,
        "trace_output_boundary": trace_output_boundary,
        "implementation_identity": _implementation_identity(),
        "generation": (
            None
            if result is None
            else {
                "failure": result.failure,
                "stop_reason": result.stop_reason,
                "generated_token_ids": list(result.generated_token_ids),
            }
        ),
    }
    del device
    gc.collect()
    return lane


def _run_lane_from_paths(
    name: str,
    deployment_path: Path,
    capability_path: Path,
    ir_path: Path,
    snapshot: Path,
    prompt: list[int],
    max_new_tokens: int,
    layer: int,
    stop_boundary: int,
    trace_output_boundary: int | None,
    trace_input_sources: frozenset[int],
) -> dict[str, Any]:
    """Load process-local registries and execute one independent lane."""

    load_engines()
    graph = KernelGraph.read(ir_path)
    return _run_lane(
        name,
        deployment_path,
        capability_path,
        graph,
        snapshot,
        prompt,
        max_new_tokens,
        layer,
        stop_boundary,
        trace_output_boundary,
        trace_input_sources,
    )


def _record_groups(
    lane: dict[str, Any], collection: str, slot_field: str
) -> dict[tuple[int, int], list[dict[str, Any]]]:
    records: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for record in lane.get(collection) or []:
        key = (int(record["source_kernel_id"]), int(record[slot_field]))
        records.setdefault(key, []).append(record)
    return records


def _terminal_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The final lowered operator's repeated dynamic invocations.

    HBM can lower one graph source to auxiliary operators before its logical
    output, so comparing every observation creates false differences.  A row
    loop, however, invokes the *same* final descriptor and PC repeatedly; using
    only its last row can hide a real mismatch.  Keep the terminal equal-
    descriptor run.  Older synthetic records without descriptor provenance
    retain the conservative last-record behaviour.
    """

    if not records:
        return []
    last = records[-1]
    descriptor = last.get("operator_descriptor_id")
    pc = last.get("pc")
    if descriptor is None or pc is None:
        return [last]
    start = len(records) - 1
    while start > 0:
        previous = records[start - 1]
        if (
            previous.get("operator_descriptor_id") != descriptor
            or previous.get("pc") != pc
        ):
            break
        start -= 1
    return records[start:]


def _compare_records(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    collection: str,
    slot_field: str,
    label: str,
) -> dict[str, Any]:
    left_records = _record_groups(left, collection, slot_field)
    right_records = _record_groups(right, collection, slot_field)
    keys = sorted(set(left_records) | set(right_records))
    comparable = 0
    first = None
    missing = []
    physical_intermediates = []
    transport_shape_differences = []
    for key in keys:
        left_group = left_records.get(key)
        right_group = right_records.get(key)
        if left_group is None or right_group is None:
            divergence = {
                "rom": None if left_group is None else left_group[-1],
                "hbm": None if right_group is None else right_group[-1],
            }
            missing.append(
                {"source_kernel_id": key[0], slot_field: key[1], **divergence}
            )
            if first is None:
                first = (key, divergence)
            continue
        left_terminal = _terminal_records(left_group)
        right_terminal = _terminal_records(right_group)
        if len(left_terminal) != len(right_terminal):
            physical_intermediates.append(
                {
                    "source_kernel_id": key[0],
                    slot_field: key[1],
                    "reason": "terminal_invocation_count",
                    "rom_count": len(left_terminal),
                    "hbm_count": len(right_terminal),
                    "rom": left_terminal[-1],
                    "hbm": right_terminal[-1],
                }
            )
            continue
        for occurrence, (left_record, right_record) in enumerate(
            zip(left_terminal, right_terminal, strict=True)
        ):
            if left_record.get("dtype") != right_record.get("dtype") or left_record.get(
                "elements"
            ) != right_record.get("elements"):
                physical_intermediates.append(
                    {
                        "source_kernel_id": key[0],
                        slot_field: key[1],
                        "occurrence": occurrence,
                        "reason": "physical_shape_or_dtype",
                        "rom": left_record,
                        "hbm": right_record,
                    }
                )
                continue
            comparable += 1
            if left_record.get("shape") != right_record.get("shape"):
                transport_shape_differences.append(
                    {
                        "source_kernel_id": key[0],
                        slot_field: key[1],
                        "occurrence": occurrence,
                        "rom_shape": left_record.get("shape"),
                        "hbm_shape": right_record.get("shape"),
                    }
                )
            if (
                left_record.get("payload_sha256") != right_record.get("payload_sha256")
                or left_record.get("unreadable") != right_record.get("unreadable")
            ) and first is None:
                first = (
                    key,
                    {
                        "occurrence": occurrence,
                        "rom": left_record,
                        "hbm": right_record,
                    },
                )
    return {
        f"last_{label}_keys": [[source, slot] for source, slot in keys],
        f"comparable_{label}_count": comparable,
        "missing_records": missing,
        "physical_intermediates_not_compared": physical_intermediates,
        "transport_shape_differences": transport_shape_differences,
        "all_comparable_payloads_equal": first is None,
        "first_divergent_source_kernel_id": None if first is None else first[0][0],
        f"first_divergent_{slot_field}": None if first is None else first[0][1],
        "first_divergence": None if first is None else first[1],
    }


def compare_operator_outputs(
    left: dict[str, Any], right: dict[str, Any]
) -> dict[str, Any]:
    return _compare_records(
        left,
        right,
        collection="operator_outputs",
        slot_field="output_slot",
        label="output",
    )


def compare_operator_inputs(
    left: dict[str, Any], right: dict[str, Any]
) -> dict[str, Any]:
    return _compare_records(
        left,
        right,
        collection="operator_inputs",
        slot_field="input_slot",
        label="input",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, default=DEFAULT_IR)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--workload", type=Path, default=DEFAULT_WORKLOAD)
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=1,
        help=(
            "number of transactions to permit; use 2 to reach the first "
            "decode transaction"
        ),
    )
    parser.add_argument("--layer", type=int, default=2)
    parser.add_argument("--stop-boundary", type=int, default=3)
    parser.add_argument(
        "--trace-output-boundary",
        type=int,
        help=(
            "record only operators that produce this logical boundary; for "
            "example 32 records work after boundary 31 and before boundary 32"
        ),
    )
    parser.add_argument(
        "--trace-input-source",
        action="append",
        type=int,
        dest="trace_input_sources",
        help="source kernel whose input slots should be hashed; default: 196",
    )
    parser.add_argument(
        "--serial",
        action="store_true",
        help="run ROM and HBM sequentially instead of in separate processes",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "results/abi3/deepseek_v4_layer02_operator_bisect.json",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1
    if not args.snapshot.is_dir():
        print(f"snapshot is not a directory: {args.snapshot}", file=sys.stderr)
        return 1
    if args.max_new_tokens < 1:
        print("--max-new-tokens must be positive", file=sys.stderr)
        return 1
    if args.trace_output_boundary is not None and not (
        1 <= args.trace_output_boundary <= args.stop_boundary
    ):
        print(
            "--trace-output-boundary must be positive and no greater than "
            "--stop-boundary",
            file=sys.stderr,
        )
        return 1

    workload = json.loads(args.workload.read_text())
    prompt = [int(value) for value in workload.get("token_ids", [])]
    if not prompt:
        print("workload prompt is empty", file=sys.stderr)
        return 1

    graph = KernelGraph.read(args.ir)
    boundaries_per_transaction = sum(
        _boundary_kind(kernel) is not None for kernel in graph.kernels
    )
    last_reachable_boundary = (
        boundaries_per_transaction * args.max_new_tokens - 1
    )
    if args.stop_boundary > last_reachable_boundary:
        print(
            f"--stop-boundary {args.stop_boundary} is not reachable with "
            f"--max-new-tokens {args.max_new_tokens}; the last reachable "
            f"boundary is {last_reachable_boundary}",
            file=sys.stderr,
        )
        return 1
    trace_input_sources = frozenset(args.trace_input_sources or (196,))
    job_args = {
        name: (
            name,
            *LANES[name],
            args.ir,
            args.snapshot,
            prompt,
            args.max_new_tokens,
            args.layer,
            args.stop_boundary,
            args.trace_output_boundary,
            trace_input_sources,
        )
        for name in ("rom", "hbm")
    }
    lanes_by_name = {}
    if args.serial:
        for name, lane_args in job_args.items():
            print(f"running {name} through layer {args.layer}", flush=True)
            lanes_by_name[name] = _run_lane_from_paths(*lane_args)
    else:
        print(
            f"running ROM and HBM through layer {args.layer} in parallel",
            flush=True,
        )
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=2, mp_context=context) as executor:
            futures = {
                executor.submit(_run_lane_from_paths, *lane_args): name
                for name, lane_args in job_args.items()
            }
            for future in as_completed(futures):
                name = futures[future]
                lanes_by_name[name] = future.result()
                lane = lanes_by_name[name]
                print(
                    f"  {name}: stopped={lane['stopped_at_requested_boundary']} "
                    f"outputs={lane['operator_output_count']} "
                    f"wall={lane['wall_seconds']:.1f}s",
                    flush=True,
                )
    lanes = [lanes_by_name[name] for name in ("rom", "hbm")]

    comparison = compare_operator_outputs(lanes[0], lanes[1])
    input_comparison = compare_operator_inputs(lanes[0], lanes[1])
    usable = all(lane["stopped_at_requested_boundary"] for lane in lanes)
    document = {
        "schema": SCHEMA,
        "status": (
            "unusable"
            if not usable
            else "match"
            if comparison["all_comparable_payloads_equal"]
            else "diverged"
        ),
        "evidence_class": "functional_diagnostic_early_stop",
        "graph_id": graph.graph_id,
        "layer": args.layer,
        "max_new_tokens": args.max_new_tokens,
        "boundaries_per_transaction": boundaries_per_transaction,
        "stop_boundary": args.stop_boundary,
        "trace_output_boundary": args.trace_output_boundary,
        "trace_input_sources": sorted(trace_input_sources),
        "lane_execution": "serial" if args.serial else "parallel_processes",
        "workload": {
            "path": str(args.workload.resolve().relative_to(REPO)),
            "workload_id": workload.get("workload_id"),
            "workload_digest": workload.get("digest"),
            "prompt_token_count": len(prompt),
            "file_sha256": _sha256(args.workload),
        },
        "source_sha256": {
            str(path.resolve().relative_to(REPO)): _sha256(path)
            for path in (
                Path(__file__).resolve(),
                REPO / "tools/bisect_deepseek_lane_activations.py",
                args.ir,
                args.workload,
                *RUNTIME_SOURCES,
            )
        },
        "lanes": lanes,
        "comparison": comparison,
        "input_comparison": input_comparison,
        "comparison_method": {
            "logical_source_key": ["source_kernel_id", "operand_slot"],
            "auxiliary_operator_policy": "compare_final_descriptor_and_pc",
            "dynamic_invocation_policy": "compare_every_terminal_invocation_in_order",
            "transport_shape_policy": "ignore_shape_only_when_dtype_and_element_count_match",
        },
        "claim_boundary": {
            "target_transaction_committed": False,
            "prior_transactions_may_commit": (
                args.stop_boundary >= boundaries_per_transaction
            ),
            "target_transaction_generated_token": False,
            "prior_tokens_may_be_generated": (
                args.stop_boundary >= boundaries_per_transaction
            ),
            "token_correctness": False,
            "external_reference_comparator": False,
            "rtl": False,
            "cycles_or_performance": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(document))
    print(
        f"status={document['status']} first source="
        f"{comparison['first_divergent_source_kernel_id']}"
    )
    print(f"wrote {args.output}")
    return 0 if usable else 2


if __name__ == "__main__":
    raise SystemExit(main())
