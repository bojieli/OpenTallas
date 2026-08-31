#!/usr/bin/env python3
"""Locate the first residual boundary where the DeepSeek ABI3 lanes diverge.

The governed token captures show that the ROM wafer and the 32-node HBM cluster
already differ before the vocabulary projection.  A token identifies no layer,
and reading the arena after a transaction is unsound because activation slots
are reused.  This tool therefore samples in flight through ``Device.on_issue``.

For one prefill transaction it retains a digest of the residual entering each
layer's attention hyper-connection, followed by the residual entering the final
hyper-connection head.  Those are synchronization-safe graph boundaries: any
backend-added collective for the preceding layer has completed before the next
layer consumes its residual.  The tool compares raw storage codes, shape and
dtype.  It never supplies an activation from one lane to the other.

This is a diagnostic artifact, not a token-correctness pass.  A clean execution
that finds a difference exits successfully and records ``status: diverged``;
execution failure or an unusable trace exits non-zero.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

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
    REPO / "runtime/sim/backend.py",
    REPO / "runtime/sim/device.py",
    REPO / "runtime/sim/engines/tensor.py",
)


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
) -> dict[str, Any]:
    deployment = Deployment.read(deployment_path)
    capability = Capability.from_dict(json.loads(capability_path.read_text()))
    boundaries: list[dict[str, Any]] = []

    def hook(pc: int, instruction: Any, family: Any, ctx: Any) -> None:
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

    device = Device(
        deployment,
        capability,
        root=snapshot,
        verify=False,
        on_issue=hook,
    )
    result = GenerationDriver(device).generate(prompt, max_new_tokens=1)
    lane = {
        "lane": name,
        "deployment": str(deployment_path.relative_to(REPO)),
        "deployment_digest": deployment.deployment_digest.hex(),
        "deployment_json_sha256": _sha256(deployment_path / "deployment.json"),
        "capability": str(capability_path.relative_to(REPO)),
        "capability_digest": capability.digest,
        "node_count": device.node_count,
        "generated_token_ids": list(result.generated_token_ids),
        "failure": result.failure,
        "wall_seconds": round(result.wall_seconds, 6),
        "boundary_count": len(boundaries),
        "boundaries": boundaries,
    }
    del device
    gc.collect()
    return lane


def compare_boundaries(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_rows = left.get("boundaries") or []
    right_rows = right.get("boundaries") or []
    compared = min(len(left_rows), len(right_rows))
    first = None
    fields = ("boundary_kind", "dtype", "shape", "elements", "payload_sha256")
    for index in range(compared):
        if any(left_rows[index].get(field) != right_rows[index].get(field) for field in fields):
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
    parser.add_argument(
        "--prompt",
        default="0",
        help="comma-separated token ids; default is the official BOS token 0",
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
    prompt = [int(value) for value in args.prompt.split(",") if value.strip()]
    if not prompt:
        print("prompt is empty", file=sys.stderr)
        return 1

    load_engines()
    graph = KernelGraph.read(args.ir)
    lanes = []
    for name in ("rom", "hbm"):
        deployment, capability = LANES[name]
        print(f"running {name} lane on {len(prompt)} prompt token(s)", flush=True)
        lane = _run_lane(
            name, deployment, capability, graph, args.snapshot, prompt
        )
        lanes.append(lane)
        print(
            f"  token={lane['generated_token_ids']} "
            f"boundaries={lane['boundary_count']} "
            f"wall={lane['wall_seconds']:.1f}s failure={lane['failure']}",
            flush=True,
        )

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
        "graph_id": graph.graph_id,
        "source_sha256": {
            str(path.resolve().relative_to(REPO)): _sha256(path)
            for path in (Path(__file__).resolve(), args.ir, *RUNTIME_SOURCES)
        },
        "lanes": lanes,
        "comparison": comparison,
        "claim_boundary": {
            "one_prefill_transaction": True,
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
