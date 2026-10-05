#!/usr/bin/env python3
"""Bisect a Qwen3-8B accelerator run against per-layer reference activations.

A token-level difference says only that something is wrong; it does not say
where. This tool finds the first kernel whose output diverges from the vendor
model's own hidden states, which turns an open-ended numerics hunt into a
bounded one.

Two things make it trustworthy.

It samples **in flight**, through the device's ``on_issue`` hook, at the moment
the producing engine writes. Reading an activation after a transaction does not
work: arena slots are reused, and ``sequence.embedding`` shares a slot with all
thirty-six layer residuals, so a post-hoc read returns whichever tensor last
occupied it. That mistake produced a convincing false positive before this tool
existed.

And the reference is used only to *check*. The accelerator computes every
activation itself from compiled artifacts; nothing here is fed back into it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.backends.hbm_sram.capability import PROFILES  # noqa: E402
from compiler.backends.hbm_sram.lower import lower_to_abi3  # noqa: E402
from compiler.backends.hbm_sram.plan import build_plan  # noqa: E402
from compiler.ir.v3.kernel_ir import KernelGraph  # noqa: E402
from runtime.abi3.capability import canonical_json  # noqa: E402
from runtime.abi3.constants import NO_ID, DType  # noqa: E402
from runtime.abi3.descriptors import ExtendedDescriptorType as T  # noqa: E402
from runtime.driver import GenerationDriver  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402

DEFAULT_SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots"
    / "b968826d9c46dd6066d109eabc6255188de91218"
)


def widen(codes: np.ndarray) -> np.ndarray:
    return (codes.astype(np.uint32) << np.uint32(16)).view(np.float32)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, default=REPO / "build/ir-v3/qwen3-8b/kernel_ir.v3.json")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--layers", type=int, default=36)
    parser.add_argument(
        "--output", type=Path, default=REPO / "results/abi3/qwen3_activation_bisect.json"
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1

    load_engines()
    capability = PROFILES["single-chip"]
    capability = capability() if callable(capability) else capability
    graph = KernelGraph.read(args.ir)
    plan = build_plan(graph, capability)
    deployment = lower_to_abi3(graph, capability, plan=plan)

    # One operator serves every layer: the layer loop reuses the body, so the
    # operator's source_kernel_id points at layer zero's kernel. Which layer is
    # executing comes from the loop's induction value, which the engine context
    # carries.
    target_operator: int | None = None
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_type != T.OPERATOR:
            continue
        kernel_index = descriptor.payload["source_kernel_id"]
        if kernel_index == NO_ID or kernel_index >= len(graph.kernels):
            continue
        kernel = graph.kernels[kernel_index]
        if kernel.kind == "ADD" and kernel.outputs and kernel.outputs[0].endswith(
            ".residual"
        ):
            target_operator = descriptor.descriptor_id
            break
    if target_operator is None:
        print("could not find the per-layer residual operator", file=sys.stderr)
        return 1
    print(f"capturing operator {target_operator} (per-layer residual)")

    captured: dict[int, np.ndarray] = {}

    def hook(pc: int, instruction: Any, family: Any, ctx: Any) -> None:
        if instruction.descriptor_id != target_operator:
            return
        operator = ctx.table.get(target_operator, T.OPERATOR)
        view = ctx.view(operator.payload["output_view_0"])
        layer = max(ctx.loops.values()) if ctx.loops else len(captured)
        captured[len(captured)] = np.array(ctx.views.read_array(view))

    prompt = [785, 6722, 315, 9625, 374]  # "The capital of France is"
    device = Device(
        deployment, capability, root=args.snapshot, verify=False, on_issue=hook
    )
    driver = GenerationDriver(device)
    result = driver.generate(prompt, max_new_tokens=1)
    print(f"accelerator token {result.generated_token_ids} failure={result.failure}")
    print(f"captured {len(captured)} layer residuals", flush=True)

    print("loading the reference ...", flush=True)
    import torch
    from transformers import AutoModelForCausalLM

    model = AutoModelForCausalLM.from_pretrained(
        str(args.snapshot), dtype=torch.bfloat16, device_map={"": "cpu"},
        local_files_only=True,
    )
    model.eval()
    with torch.inference_mode():
        out = model(
            input_ids=torch.tensor([prompt], dtype=torch.long),
            output_hidden_states=True,
        )
    reference_token = int(torch.argmax(out.logits[0, -1]).item())
    hidden = [h[0].float().numpy() for h in out.hidden_states]

    report: dict[str, Any] = {
        "schema": "opentallas.abi3.activation_bisect.v1",
        "evidence_class": "external_reference_comparator",
        "prompt_token_ids": prompt,
        "accelerator_token_ids": list(result.generated_token_ids),
        "reference_token_id": reference_token,
        "token_agreement": list(result.generated_token_ids)[:1] == [reference_token],
        "layers": [],
        "first_divergent_layer": None,
    }
    for layer in sorted(captured):
        if layer + 1 >= len(hidden):
            break
        # The device captures the rows the loop body wrote; the reference has
        # one row per prompt token. Compare the trailing rows they have in
        # common, since a shape mismatch here produces meaningless deltas -- an
        # earlier version compared one device row against five reference rows
        # flattened and reported a divergence at every layer.
        rows = hidden[layer + 1].shape[0]
        width = hidden[layer + 1].shape[1]
        device_rows = captured[layer].reshape(-1).size // width
        take = min(rows, device_rows)
        got = widen(captured[layer].reshape(-1))[-take * width :]
        want = hidden[layer + 1][-take:].reshape(-1)
        delta = np.abs(got - want)
        entry = {
            "layer": layer,
            "elements": int(got.size),
            "max_abs": float(delta.max()),
            "mean_abs": float(delta.mean()),
            "differing": int((delta > 0).sum()),
            "reference_scale": float(np.abs(want).max()),
        }
        report["layers"].append(entry)
        if report["first_divergent_layer"] is None and entry["max_abs"] > 0.5:
            report["first_divergent_layer"] = layer
        print(
            f"layer {layer:2d}: max|d|={entry['max_abs']:.4g} "
            f"mean|d|={entry['mean_abs']:.4g} "
            f"ref_scale={entry['reference_scale']:.4g} "
            f"differing={entry['differing']}/{entry['elements']}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(report))
    print(f"\nfirst divergent layer: {report['first_divergent_layer']}")
    print(f"token agreement: {report['token_agreement']}")
    print(f"wrote {args.output}")
    return 0 if report["token_agreement"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
