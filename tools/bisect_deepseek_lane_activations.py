#!/usr/bin/env python3
"""Locate the first residual boundary where the DeepSeek ABI3 lanes diverge.

The governed token captures show that the ROM wafer and the 32-node HBM cluster
already differ before the vocabulary projection.  A token identifies no layer,
and reading the arena after a transaction is unsound because activation slots
are reused.  This tool therefore samples in flight through ``Device.on_issue``.

For each requested transaction it retains a digest of the residual entering
every layer's attention hyper-connection, followed by the residual entering the
final hyper-connection head.  Those are synchronization-safe graph boundaries:
any backend-added collective for the preceding layer has completed before the
next layer consumes its residual.  The tool compares raw storage codes, shape
and dtype.  It never supplies an activation from one lane to the other.

This is a diagnostic artifact, not a token-correctness pass.  A clean execution
that finds a difference exits successfully and records ``status: diverged``;
execution failure or an unusable trace exits non-zero.
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
from runtime.abi3.constants import DType  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.driver import GenerationDriver  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402

SCHEMA = "opentallas.deepseek_v4_lane_activation_bisect.v1"
DEFAULT_IR = REPO / "build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json"
DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/"
    "models--deepseek-ai--DeepSeek-V4-Flash-0731/snapshots/"
    "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
)
LANES = {
    "rom": (
        REPO / "build/abi3/deepseek-v4-flash-rom-tokens",
        REPO / "configs/hardware/abi3_capability/rom_deepseek_v4.json",
    ),
    "hbm": (
        REPO / "build/abi3/deepseek-v4-flash-hbm-tokens",
        REPO / "configs/hardware/abi3_capability/hbm_sram_cluster_32.json",
    ),
}
RUNTIME_SOURCES = (
    REPO / "compiler/backends/numeric_contracts.py",
    REPO / "compiler/backends/rom/common/program.py",
    REPO / "compiler/backends/hbm_sram/lower.py",
    REPO / "compiler/backends/hbm_sram/plan.py",
    REPO / "runtime/reference/quantization.py",
    REPO / "runtime/sim/backend.py",
    REPO / "runtime/sim/device.py",
    REPO / "runtime/sim/engines/deepseek_vector.py",
    REPO / "runtime/sim/engines/reduction.py",
    REPO / "runtime/sim/engines/tensor.py",
    REPO / "runtime/sim/engines/vector.py",
)


def _implementation_identity() -> dict[str, Any]:
    try:
        from runtime.sim.backend import get_backend

        return dict(get_backend().implementation_identity())
    except Exception as exc:
        return {"unavailable": f"{type(exc).__name__}: {exc}"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _boundary_kind(kernel: Any) -> str | None:
    if kernel.kind == "HYPER_CONNECT_PRE" and kernel.kernel_id.endswith(
        ".hc_attn_pre"
    ):
        return "layer_input"
    if kernel.kernel_id == "main.hc_head":
        return "head_input"
    return None


def _run_lane(
    name: str,
    deployment_path: Path,
    capability_path: Path,
    graph: KernelGraph,
    snapshot: Path,
    prompt: list[int],
    max_new_tokens: int,
) -> dict[str, Any]:
    deployment = Deployment.read(deployment_path)
    capability = Capability.from_dict(json.loads(capability_path.read_text()))
    boundaries: list[dict[str, Any]] = []
    transaction = 0

    def hook(pc: int, instruction: Any, family: Any, ctx: Any) -> None:
        nonlocal transaction
        try:
            operator = ctx.operator(instruction.descriptor_id)
        except Exception:
            return
        source = int(operator.payload.get("source_kernel_id", -1))
        if not 0 <= source < len(graph.kernels):
            return
        kernel = graph.kernels[source]
        kind = _boundary_kind(kernel)
        if kind is None:
            return
        view = ctx.input_view(operator, 0)
        raw = np.ascontiguousarray(np.asarray(ctx.read(view)))
        boundaries.append(
            {
                "boundary": len(boundaries),
                "transaction": transaction,
                "phase": "prefill" if transaction == 0 else "decode",
                "boundary_kind": kind,
                "source_kernel_id": source,
                "kernel_id": kernel.kernel_id,
                "pc": pc,
                "dtype": DType(int(view.dtype)).name,
                "shape": list(raw.shape),
                "elements": int(raw.size),
                "payload_sha256": hashlib.sha256(raw.tobytes()).hexdigest(),
            }
        )
        if kind == "head_input":
            transaction += 1

    device = Device(
        deployment,
        capability,
        root=snapshot,
        verify=False,
        on_issue=hook,
    )
    result = GenerationDriver(device).generate(
        prompt, max_new_tokens=max_new_tokens
    )
    lane = {
        "lane": name,
        "deployment": str(deployment_path.relative_to(REPO)),
        "deployment_digest": deployment.deployment_digest.hex(),
        "deployment_json_sha256": _sha256(deployment_path / "deployment.json"),
        "capability": str(capability_path.relative_to(REPO)),
        "capability_digest": capability.digest,
        "node_count": device.node_count,
        "generated_token_ids": list(result.generated_token_ids),
        "requested_token_count": max_new_tokens,
        "failure": result.failure,
        "wall_seconds": round(result.wall_seconds, 6),
        "implementation_identity": _implementation_identity(),
        "boundary_count": len(boundaries),
        "boundaries": boundaries,
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
) -> dict[str, Any]:
    """Load process-local registries and execute one independent lane."""

    load_engines()
    return _run_lane(
        name,
        deployment_path,
        capability_path,
        KernelGraph.read(ir_path),
        snapshot,
        prompt,
        max_new_tokens,
    )


def compare_boundaries(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_rows = left.get("boundaries") or []
    right_rows = right.get("boundaries") or []
    compared = min(len(left_rows), len(right_rows))
    first = None
    fields = (
        "transaction",
        "phase",
        "boundary_kind",
        "dtype",
        "shape",
        "elements",
        "payload_sha256",
    )
    for index in range(compared):
        if any(
            left_rows[index].get(field) != right_rows[index].get(field)
            for field in fields
        ):
            first = index
            break
    if first is None and len(left_rows) != len(right_rows):
        first = compared
    return {
        "boundaries_compared": compared,
        "boundary_counts_equal": len(left_rows) == len(right_rows),
        "all_boundaries_equal": first is None,
        "first_divergent_boundary": first,
        "first_divergence": (
            None
            if first is None
            else {
                "rom": left_rows[first] if first < len(left_rows) else None,
                "hbm": right_rows[first] if first < len(right_rows) else None,
            }
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, default=DEFAULT_IR)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    prompt_source = parser.add_mutually_exclusive_group()
    prompt_source.add_argument(
        "--prompt",
        help="comma-separated token ids; defaults to the official BOS token 0",
    )
    prompt_source.add_argument(
        "--workload",
        type=Path,
        help="pinned workload JSON whose token_ids supply the prompt",
    )
    parser.add_argument("--max-new-tokens", type=int, default=1)
    parser.add_argument(
        "--serial",
        action="store_true",
        help="run ROM and HBM sequentially instead of in separate processes",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "results/abi3/deepseek_v4_lane_activation_bisect.json",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1
    if not args.snapshot.is_dir():
        print(f"snapshot is not a directory: {args.snapshot}", file=sys.stderr)
        return 1
    workload = None
    if args.workload is not None:
        workload = json.loads(args.workload.read_text())
        prompt = [int(value) for value in workload.get("token_ids", [])]
    else:
        raw_prompt = args.prompt if args.prompt is not None else "0"
        prompt = [int(value) for value in raw_prompt.split(",") if value.strip()]
    if not prompt:
        print("prompt is empty", file=sys.stderr)
        return 1
    if args.max_new_tokens < 1:
        print("--max-new-tokens must be positive", file=sys.stderr)
        return 1

    graph = KernelGraph.read(args.ir)
    job_args = {
        name: (
            name,
            *LANES[name],
            args.ir,
            args.snapshot,
            prompt,
            args.max_new_tokens,
        )
        for name in ("rom", "hbm")
    }
    lanes_by_name = {}
    if args.serial:
        for name, lane_args in job_args.items():
            print(
                f"running {name} lane on {len(prompt)} prompt token(s)",
                flush=True,
            )
            lanes_by_name[name] = _run_lane_from_paths(*lane_args)
    else:
        print(
            f"running ROM and HBM on {len(prompt)} prompt token(s) in parallel",
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
                    f"  {name}: token={lane['generated_token_ids']} "
                    f"boundaries={lane['boundary_count']} "
                    f"wall={lane['wall_seconds']:.1f}s "
                    f"failure={lane['failure']}",
                    flush=True,
                )
    lanes = [lanes_by_name[name] for name in ("rom", "hbm")]

    comparison = compare_boundaries(lanes[0], lanes[1])
    usable = (
        all(lane["failure"] is None for lane in lanes)
        and all(lane["boundary_count"] > 0 for lane in lanes)
        and comparison["boundary_counts_equal"]
    )
    document = {
        "schema": SCHEMA,
        "status": (
            "unusable"
            if not usable
            else "match"
            if comparison["all_boundaries_equal"]
            else "diverged"
        ),
        "evidence_class": "functional_diagnostic",
        "prompt_token_ids": prompt,
        "prompt_token_count": len(prompt),
        "max_new_tokens": args.max_new_tokens,
        "lane_execution": "serial" if args.serial else "parallel_processes",
        "workload": (
            None
            if workload is None
            else {
                "path": str(args.workload.resolve().relative_to(REPO)),
                "workload_id": workload.get("workload_id"),
                "workload_digest": workload.get("digest"),
                "file_sha256": _sha256(args.workload),
            }
        ),
        "graph_id": graph.graph_id,
        "source_sha256": {
            str(path.resolve().relative_to(REPO)): _sha256(path)
            for path in (
                Path(__file__).resolve(),
                args.ir,
                *RUNTIME_SOURCES,
                *((args.workload,) if args.workload is not None else ()),
            )
        },
        "lanes": lanes,
        "comparison": comparison,
        "claim_boundary": {
            "functional_transactions_requested": args.max_new_tokens,
            "prefill_transactions_requested": 1,
            "decode_transactions_requested": args.max_new_tokens - 1,
            "external_reference_comparator": False,
            "token_correctness": False,
            "rtl": False,
            "cycles_or_performance": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(document))
    print(
        f"status={document['status']} first boundary="
        f"{comparison['first_divergent_boundary']}"
    )
    print(f"wrote {args.output}")
    return 0 if usable else 2


if __name__ == "__main__":
    raise SystemExit(main())
