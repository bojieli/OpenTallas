#!/usr/bin/env python3
"""Capture vendor-reference DeepSeek layer boundaries for one prefill.

The accelerator lane bisector records the residual entering every layer and
the residual entering the final hyper-connection head.  A ROM/HBM agreement
only proves backend correlation, so this companion records the same boundaries
from the pinned vendor model.  It is an external comparator: reference values
are hashed and reported, never supplied to an accelerator execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import canonical_json  # noqa: E402
from runtime.abi3.constants import ReductionOrder  # noqa: E402
from runtime.reference.deepseek_v4_oracle import (  # noqa: E402
    DEFAULT_SNAPSHOT,
    OracleConfig,
    StreamingDeepSeekV4,
)
from runtime.sim.engines.vector import (  # noqa: E402
    binary32_rsqrt_rne,
    deepseek_rms_norm_binary32,
)
from runtime.sim.backend import _numpy_reduce_sum  # noqa: E402

DEFAULT_WORKLOAD = (
    REPO / "build/workloads/deepseek-v4-flash-0731-prefix/TA-DS-CHAT-1-P32.json"
)
DEFAULT_OUTPUT = REPO / "results/abi3/deepseek_v4_reference_boundaries_p32.json"
DEFAULT_ACCELERATOR_BOUNDARIES = (
    REPO / "results/abi3/deepseek_v4_lane_activation_bisect.json"
)
SCHEMA = "opentallas.deepseek_v4_reference_boundaries.v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload(tensor: Any, torch: Any) -> dict[str, Any]:
    contiguous = tensor.detach().contiguous()
    codes = _bf16_codes(contiguous, torch)
    values = contiguous.float()
    return {
        "dtype": "BF16",
        "shape": list(contiguous.shape),
        "elements": int(contiguous.numel()),
        "payload_sha256": hashlib.sha256(codes.tobytes()).hexdigest(),
        "minimum": float(values.min().item()),
        "maximum": float(values.max().item()),
        "mean": float(values.mean().item()),
    }


def _bf16_codes(tensor: Any, torch: Any) -> Any:
    return tensor.detach().contiguous().view(torch.uint16).cpu().numpy()


def _widen_bf16(codes: Any) -> Any:
    import numpy as np

    return (np.asarray(codes, dtype=np.uint16).astype(np.uint32) << 16).view(np.float32)


def compare_accelerator_boundaries(
    reference_boundaries: list[dict[str, Any]],
    accelerator: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare raw-code hashes without treating rank-only transport as data."""

    comparisons = []
    for lane in accelerator.get("lanes") or []:
        observed = lane.get("boundaries") or []
        count = min(len(reference_boundaries), len(observed))
        differences = [
            index
            for index in range(count)
            if reference_boundaries[index].get("payload_sha256")
            != observed[index].get("payload_sha256")
        ]
        if len(reference_boundaries) != len(observed):
            differences.extend(
                range(count, max(len(reference_boundaries), len(observed)))
            )
        first = differences[0] if differences else None
        comparisons.append(
            {
                "lane": lane.get("lane"),
                "boundaries_compared": count,
                "boundary_counts_equal": len(reference_boundaries) == len(observed),
                "exact_boundary_count": count
                - sum(index < count for index in differences),
                "first_divergent_boundary": first,
                "first_divergence": (
                    None
                    if first is None
                    else {
                        "reference": (
                            reference_boundaries[first]
                            if first < len(reference_boundaries)
                            else None
                        ),
                        "accelerator": (
                            observed[first] if first < len(observed) else None
                        ),
                    }
                ),
            }
        )
    return comparisons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--workload", type=Path, default=DEFAULT_WORKLOAD)
    parser.add_argument("--max-seq-len", type=int, default=128)
    parser.add_argument(
        "--accelerator-boundaries",
        type=Path,
        default=DEFAULT_ACCELERATOR_BOUNDARIES,
        help="optional ROM/HBM boundary artifact to compare by raw-code hash",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1
    if not args.snapshot.is_dir():
        print(f"snapshot is not a directory: {args.snapshot}", file=sys.stderr)
        return 1

    workload = json.loads(args.workload.read_text())
    prompt = [int(value) for value in workload.get("token_ids", [])]
    if not prompt:
        print("workload prompt is empty", file=sys.stderr)
        return 1
    if args.max_seq_len < len(prompt) + 1:
        print(
            f"--max-seq-len {args.max_seq_len} cannot hold the "
            f"{len(prompt)}-token prompt and one generated token",
            file=sys.stderr,
        )
        return 1

    started = time.perf_counter()
    engine = StreamingDeepSeekV4(
        OracleConfig(
            snapshot=args.snapshot,
            max_seq_len=args.max_seq_len,
            host_cache_dense=False,
            pin_host_cache=False,
            head_on_device=False,
        )
    )
    endpoints = engine.load_endpoints()
    boundaries: list[dict[str, Any]] = []
    layer0_stages: list[dict[str, Any]] = []
    layer0_attention_norm_audit: dict[str, Any] = {}
    handles = []

    def stage(name: str, kernel_id: str, tensor: Any) -> None:
        layer0_stages.append(
            {
                "stage": name,
                "kernel_id": kernel_id,
                **_payload(tensor, engine.torch),
            }
        )

    def layer_input(layer: int):
        def hook(_module: Any, inputs: tuple[Any, ...]) -> None:
            boundaries.append(
                {
                    "boundary": len(boundaries),
                    "boundary_kind": "layer_input",
                    "layer": layer,
                    **_payload(inputs[0], engine.torch),
                }
            )

        return hook

    for layer, module in enumerate(engine.model.layers):
        handles.append(module.register_forward_pre_hook(layer_input(layer)))

    # Record the coarse Block.forward joins in layer zero.  These correspond
    # to logical graph outputs and let the operator tracer narrow a boundary
    # mismatch without retaining or exporting the vendor activation itself.
    layer0 = engine.model.layers[0]
    hc_pre = layer0.hc_pre
    hc_post = layer0.hc_post
    hc_pre_calls = 0
    hc_post_calls = 0

    def traced_hc_pre(*hook_args: Any, **hook_kwargs: Any) -> Any:
        nonlocal hc_pre_calls
        result = hc_pre(*hook_args, **hook_kwargs)
        if hc_pre_calls == 0:
            stage(
                "attention_hc_pre_branch",
                "main.layer00.hc_attn_pre.branch_reduce",
                result[0],
            )
        else:
            stage(
                "ffn_hc_pre_branch",
                "main.layer00.hc_ffn_pre.branch_reduce",
                result[0],
            )
        hc_pre_calls += 1
        return result

    def traced_hc_post(*hook_args: Any, **hook_kwargs: Any) -> Any:
        nonlocal hc_post_calls
        result = hc_post(*hook_args, **hook_kwargs)
        if hc_post_calls == 0:
            stage(
                "attention_hc_post",
                "main.layer00.hc_attn_post",
                result,
            )
        else:
            stage(
                "ffn_hc_post",
                "main.layer00.hc_ffn_post",
                result,
            )
        hc_post_calls += 1
        return result

    layer0.hc_pre = traced_hc_pre
    layer0.hc_post = traced_hc_post

    def stage_hook(name: str, kernel_id: str):
        def hook(_module: Any, _inputs: tuple[Any, ...], output: Any) -> None:
            stage(name, kernel_id, output)

        return hook

    handles.extend(
        (
            layer0.attn_norm.register_forward_hook(
                stage_hook("attention_norm", "main.layer00.attn_norm")
            ),
            layer0.attn.register_forward_hook(
                stage_hook("attention_output", "main.layer00.output_b.contract")
            ),
            layer0.ffn_norm.register_forward_hook(
                stage_hook("ffn_norm", "main.layer00.ffn_norm")
            ),
            layer0.ffn.register_forward_hook(
                stage_hook("ffn_output", "main.layer00.expert_reduce")
            ),
        )
    )

    def audit_attention_norm(module: Any, inputs: tuple[Any, ...], output: Any) -> None:
        import numpy as np

        input_codes = _bf16_codes(inputs[0], engine.torch)
        weight_codes = _bf16_codes(
            module.weight.to(engine.torch.bfloat16), engine.torch
        )
        vendor_codes = _bf16_codes(output, engine.torch)
        contract_codes, saturations = deepseek_rms_norm_binary32(
            input_codes,
            weight_codes,
            epsilon_bits=0x358637BD,
        )
        contract_codes = contract_codes.reshape(vendor_codes.shape)
        differing = vendor_codes != contract_codes
        vendor_values = _widen_bf16(vendor_codes)
        contract_values = _widen_bf16(contract_codes)
        delta = np.abs(vendor_values - contract_values)
        device_values = inputs[0].float()
        vendor_means = device_values.square().mean(-1)
        vendor_arguments = vendor_means + module.eps
        vendor_inverse = engine.torch.rsqrt(vendor_arguments)
        vendor_mean_codes = (
            vendor_means.detach().contiguous().view(engine.torch.uint32).cpu().numpy()
        )
        vendor_argument_codes = (
            vendor_arguments.detach()
            .contiguous()
            .view(engine.torch.uint32)
            .cpu()
            .numpy()
        )
        vendor_inverse_codes = (
            vendor_inverse.detach().contiguous().view(engine.torch.uint32).cpu().numpy()
        )
        input_values = _widen_bf16(input_codes)
        squares = np.multiply(input_values, input_values, dtype=np.float32)
        contract_totals = _numpy_reduce_sum(
            squares,
            int(ReductionOrder.PAIRWISE_TREE),
        )
        contract_means = np.divide(
            contract_totals, np.float32(input_values.shape[-1]), dtype=np.float32
        )
        epsilon = np.asarray([0x358637BD], dtype=np.uint32).view(np.float32)[0]
        contract_arguments = np.add(contract_means, epsilon, dtype=np.float32)
        contract_argument_codes = contract_arguments.view(np.uint32)
        contract_inverse_codes = np.asarray(
            [binary32_rsqrt_rne(int(code)) for code in contract_argument_codes],
            dtype=np.uint32,
        )
        contract_mean_codes = contract_means.view(np.uint32)
        output_differences = []
        for coordinate in np.argwhere(differing)[:16]:
            index = tuple(int(value) for value in coordinate)
            output_differences.append(
                {
                    "index": list(index),
                    "vendor_code": int(vendor_codes[index]),
                    "frozen_contract_code": int(contract_codes[index]),
                    "absolute_difference": float(delta[index]),
                }
            )
        layer0_attention_norm_audit.update(
            {
                "kernel_id": "main.layer00.attn_norm",
                "input_payload_sha256": hashlib.sha256(
                    input_codes.tobytes()
                ).hexdigest(),
                "weight_payload_sha256": hashlib.sha256(
                    weight_codes.tobytes()
                ).hexdigest(),
                "vendor_output_payload_sha256": hashlib.sha256(
                    vendor_codes.tobytes()
                ).hexdigest(),
                "frozen_contract_output_payload_sha256": hashlib.sha256(
                    contract_codes.tobytes()
                ).hexdigest(),
                "elements": int(vendor_codes.size),
                "differing_elements": int(np.count_nonzero(differing)),
                "differing_rows": int(
                    np.count_nonzero(differing.reshape(-1, differing.shape[-1]).any(1))
                ),
                "maximum_absolute_difference": float(delta.max()),
                "mean_absolute_difference": float(delta.mean()),
                "frozen_contract_saturations": saturations,
                "output_differences": output_differences,
                "mean_square_code_differences": int(
                    np.count_nonzero(
                        vendor_mean_codes.reshape(-1) != contract_mean_codes
                    )
                ),
                "variance_argument_code_differences": int(
                    np.count_nonzero(
                        vendor_argument_codes.reshape(-1) != contract_argument_codes
                    )
                ),
                "inverse_rms_code_differences": int(
                    np.count_nonzero(
                        vendor_inverse_codes.reshape(-1) != contract_inverse_codes
                    )
                ),
                "intermediate_differences": [
                    {
                        "row": row,
                        "vendor_mean_square_code": int(
                            vendor_mean_codes.reshape(-1)[row]
                        ),
                        "frozen_contract_mean_square_code": int(
                            contract_mean_codes[row]
                        ),
                        "vendor_variance_argument_code": int(
                            vendor_argument_codes.reshape(-1)[row]
                        ),
                        "frozen_contract_variance_argument_code": int(
                            contract_argument_codes[row]
                        ),
                        "vendor_inverse_rms_code": int(
                            vendor_inverse_codes.reshape(-1)[row]
                        ),
                        "frozen_contract_inverse_rms_code": int(
                            contract_inverse_codes[row]
                        ),
                    }
                    for row in range(contract_mean_codes.size)
                    if (
                        int(vendor_mean_codes.reshape(-1)[row])
                        != int(contract_mean_codes[row])
                        or int(vendor_inverse_codes.reshape(-1)[row])
                        != int(contract_inverse_codes[row])
                    )
                ],
            }
        )

    handles.append(layer0.attn_norm.register_forward_hook(audit_attention_norm))

    def head_input(_module: Any, _inputs: tuple[Any, ...], output: Any) -> None:
        boundaries.append(
            {
                "boundary": len(boundaries),
                "boundary_kind": "head_input",
                "layer": None,
                **_payload(output, engine.torch),
            }
        )

    handles.append(engine.model.layers[-1].register_forward_hook(head_input))
    try:
        outcome = engine.greedy_generate(
            prompt,
            max_new_tokens=1,
            eos_token_id=1,
        )
    finally:
        layer0.hc_pre = hc_pre
        layer0.hc_post = hc_post
        for handle in handles:
            handle.remove()

    document = {
        "schema": SCHEMA,
        "status": "captured" if len(boundaries) == 44 else "unusable",
        "evidence_class": "external_reference_comparator",
        "not_a_claim": [
            "accelerator_execution",
            "artifact_only_execution",
            "rtl",
            "cycles_or_performance",
        ],
        "workload": {
            "path": str(args.workload.resolve().relative_to(REPO)),
            "workload_id": workload.get("workload_id"),
            "workload_digest": workload.get("digest"),
            "prompt_token_count": len(prompt),
            "file_sha256": _sha256(args.workload),
        },
        "snapshot": str(args.snapshot),
        "max_seq_len": args.max_seq_len,
        "expert_numeric_path": engine.expert_dtype,
        "vendor_source_sha256": engine.vendor_digests,
        "source_sha256": {
            str(Path(__file__).resolve().relative_to(REPO)): _sha256(
                Path(__file__).resolve()
            ),
            "runtime/reference/deepseek_v4_oracle.py": _sha256(
                REPO / "runtime/reference/deepseek_v4_oracle.py"
            ),
            "runtime/reference/tensor_accelerator_rmsnorm.py": _sha256(
                REPO / "runtime/reference/tensor_accelerator_rmsnorm.py"
            ),
            "runtime/sim/backend.py": _sha256(REPO / "runtime/sim/backend.py"),
            "runtime/sim/engines/vector.py": _sha256(
                REPO / "runtime/sim/engines/vector.py"
            ),
        },
        "endpoints": endpoints,
        "generated_token_ids": outcome["generated_token_ids"],
        "stop_reason": outcome["stop_reason"],
        "boundary_count": len(boundaries),
        "boundaries": boundaries,
        "layer0_stage_count": len(layer0_stages),
        "layer0_stages": layer0_stages,
        "layer0_attention_norm_audit": layer0_attention_norm_audit,
        "wall_seconds": round(time.perf_counter() - started, 6),
    }
    if args.accelerator_boundaries.is_file():
        accelerator = json.loads(args.accelerator_boundaries.read_text())
        document["accelerator_comparison"] = {
            "artifact": str(args.accelerator_boundaries.resolve().relative_to(REPO)),
            "artifact_sha256": _sha256(args.accelerator_boundaries),
            "artifact_status": accelerator.get("status"),
            "workload_digest_matches": (
                (accelerator.get("workload") or {}).get("workload_digest")
                == workload.get("digest")
            ),
            "lanes": compare_accelerator_boundaries(boundaries, accelerator),
        }
    else:
        document["accelerator_comparison"] = None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(document))
    print(
        f"status={document['status']} token={document['generated_token_ids']} "
        f"boundaries={len(boundaries)} wall={document['wall_seconds']:.1f}s"
    )
    print(f"wrote {args.output}")
    return 0 if document["status"] == "captured" else 2


if __name__ == "__main__":
    raise SystemExit(main())
