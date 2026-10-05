#!/usr/bin/env python3
"""Run and retain the complete Qwen3 artifact/reference release differential."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import os
from pathlib import Path
import sys
from typing import Any

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.ir.model import canonical_json_bytes  # noqa: E402
from compiler.frontend.checkpoint import (  # noqa: E402
    load_checkpoint_lock,
    verify_checkpoint_lock,
)
from compiler.qwen3.reference import (  # noqa: E402
    OfficialQwen3Reference,
    compare_logits,
)
from compiler.qwen3.runtime import Qwen3ServiceEngine  # noqa: E402


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Compare compiled Qwen3-8B artifacts with pinned official source"
    )
    result.add_argument("--deployment", required=True, type=Path)
    result.add_argument("--snapshot", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    result.add_argument("--device", default="cuda")
    result.add_argument(
        "--attention-backend", choices=("sdpa", "eager"), default="sdpa"
    )
    result.add_argument(
        "--long-context-tokens",
        default=8000,
        type=int,
        help="required exact release differential length (must be 8000)",
    )
    result.add_argument(
        "--generated-tokens",
        default=32,
        type=int,
        help="greedy output tokens to compare across cached decode steps (32..256)",
    )
    return result


def _write_new(path: Path, value: Any) -> None:
    """Write one durable report without replacing prior release evidence."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_json_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())


def _span(
    service: Qwen3ServiceEngine,
    reference: OfficialQwen3Reference,
    token_ids: list[int],
    *,
    capture_layers: bool,
) -> dict[str, Any]:
    service_result = service.run_span(token_ids, capture_layer_hashes=capture_layers)
    reference_result = reference.run_span(
        token_ids, capture_layer_hashes=capture_layers
    )
    service_layers = service_result.report["layer_boundaries"]
    reference_layers = reference_result.report["layer_boundaries"]
    layers_match = (
        (
            len(service_layers) == 36
            and len(reference_layers) == 36
            and service_layers == reference_layers
        )
        if capture_layers
        else None
    )
    differential = compare_logits(
        service_result.logits, reference_result.logits, atol=0.0
    )
    return {
        "all_layer_boundaries_match": layers_match,
        "counter_reconciliation_exact": (
            service_result.report["counter_reconciliation"]["exact"] is True
            and service_result.report["counter_reconciliation"]["expected"]
            == service_result.report["counters"]
        ),
        "final_context_tokens": service_result.report["final_context_tokens"],
        "input_token_count": len(token_ids),
        "input_token_sha256": hashlib.sha256(
            canonical_json_bytes(token_ids)
        ).hexdigest(),
        "logits_differential": differential,
        "layer_boundary_count_compared": len(service_layers) if capture_layers else 0,
        "layer_boundaries": (
            service_layers
            if layers_match is True
            else {"reference": reference_layers, "service": service_layers}
            if capture_layers
            else []
        ),
        "reference_argmax_token_id": reference_result.report["logits"][
            "argmax_token_id"
        ],
        "reference_report_id": reference_result.report["report_id"],
        "service_argmax_token_id": service_result.report["logits"]["argmax_token_id"],
        "service_counters": service_result.report["counters"],
        "service_report_id": service_result.report["report_id"],
    }


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.long_context_tokens != 8000:
        parser().error("--long-context-tokens must equal 8000 for a release gate")
    if not 32 <= arguments.generated_tokens <= 256:
        parser().error("--generated-tokens must be in 32..256 for a release gate")
    if arguments.output.exists():
        parser().error(f"--output already exists: {arguments.output}")
    service = Qwen3ServiceEngine(
        arguments.deployment,
        device=arguments.device,
        attention_backend=arguments.attention_backend,
    )
    reference = OfficialQwen3Reference(
        arguments.snapshot,
        device=arguments.device,
        attention_backend=arguments.attention_backend,
    )
    checkpoint_lock = load_checkpoint_lock(
        Path(arguments.deployment).resolve() / "checkpoint.lock.json"
    )
    verify_checkpoint_lock(arguments.snapshot, checkpoint_lock)
    spans: list[dict[str, Any]] = []
    generated_token_ids: list[int] = []
    prompt = [151644, 872, 198, 9707, 151645, 198, 151644, 77091, 198]
    spans.append(_span(service, reference, prompt, capture_layers=True))
    generated_token_ids.append(spans[-1]["service_argmax_token_id"])
    while len(generated_token_ids) < arguments.generated_tokens:
        if generated_token_ids[-1] in {151643, 151645}:
            break
        spans.append(
            _span(
                service,
                reference,
                [generated_token_ids[-1]],
                capture_layers=True,
            )
        )
        generated_token_ids.append(spans[-1]["service_argmax_token_id"])
    service.reset()
    reference.reset()
    chunked_prompt = [151644, 872, 198, 9707, 151645, 198, 151644, 77091, 198]
    chunked_prefill = [
        _span(service, reference, chunked_prompt[:3], capture_layers=True),
        _span(service, reference, chunked_prompt[3:], capture_layers=True),
    ]
    service.reset()
    reference.reset()
    long_context = _span(
        service,
        reference,
        [151643] * arguments.long_context_tokens,
        capture_layers=True,
    )
    checks = spans + chunked_prefill + [long_context]
    passed = all(
        item["all_layer_boundaries_match"] is True
        and item["counter_reconciliation_exact"] is True
        and item["logits_differential"]["passed"]
        and item["service_argmax_token_id"] == item["reference_argmax_token_id"]
        for item in checks
    )
    body = {
        "attention_backend": arguments.attention_backend,
        "build_id": service.manifest["build_id"],
        "checkpoint_lock_id": service.manifest["model"]["checkpoint_lock_id"],
        "chunked_prefill": chunked_prefill,
        "context_target_tokens": 8000,
        "cuda_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "device_name": torch.cuda.get_device_name(0)
        if arguments.device.startswith("cuda")
        else "cpu",
        "generated_token_ids": generated_token_ids,
        "long_context": long_context,
        "passed": passed,
        "release_runner_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
        "schema": "opentallas.qwen3.release_gate.v1",
        "snapshot_reverified_against_lock": True,
        "spans": spans,
        "torch_version": torch.__version__,
        "transformers_version": importlib.metadata.version("transformers"),
    }
    report = {
        **body,
        "report_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }
    _write_new(arguments.output, report)
    print(report["report_id"])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
