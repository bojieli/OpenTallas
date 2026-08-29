#!/usr/bin/env python3
"""Bisect a Qwen3-8B accelerator run against per-layer reference activations.

The accelerator now executes end to end and produces legal tokens that differ
from the reference oracle. A token-level difference says only "something is
wrong"; it does not say where. This tool finds the first layer whose output
diverges, which turns an open-ended numerics hunt into a bounded one.

The reference is the vendor model's own hidden states for the same prompt. That
is an external comparator used to *check* the accelerator, never to supply it
with a value -- the accelerator computes every activation itself from compiled
artifacts, and this tool only reads them back out of device memory afterwards.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.backends.hbm_sram.capability import PROFILES  # noqa: E402
from compiler.backends.hbm_sram.lower import lower_to_abi3  # noqa: E402
from compiler.ir.v3.kernel_ir import KernelGraph  # noqa: E402
from runtime.abi3.capability import canonical_json  # noqa: E402
from runtime.abi3.descriptors import Phase, Symbol  # noqa: E402
from runtime.driver import GenerationDriver  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402

DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/"
    "b968826d9c46dd6066d109eabc6255188de91218"
)


def widen(codes: np.ndarray) -> np.ndarray:
    return (codes.astype(np.uint32) << np.uint32(16)).view(np.float32)


def read_activation(device: Device, lowering: Any, tensor_id: str) -> np.ndarray | None:
    """Read one named activation back out of device memory."""
    plan = lowering.plan
    key = plan.activation_keys.get(tensor_id)
    if key is None:
        return None
    slot_id = plan.arena_of_key.get(key)
    if slot_id is None:
        return None
    object_id = lowering._arena_object.get(slot_id)  # noqa: SLF001
    if object_id is None:
        return None
    slot = next((s for s in plan.arena_slots if s.slot_id == slot_id), None)
    if slot is None:
        return None
    obj = device.memory[object_id]
    payload = obj.read(0, min(slot.size_bytes, obj.size_bytes))
    return np.frombuffer(payload, dtype=np.uint16)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, default=REPO / "build/ir-v3/qwen3-8b/kernel_ir.v3.json")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--prompt-tokens", type=int, default=8)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=REPO / "results/abi3/qwen3_activation_bisect.json")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1

    load_engines()
    capability = PROFILES["single-chip"]
    capability = capability() if callable(capability) else capability
    graph = KernelGraph.read(args.ir)
    deployment = lower_to_abi3(graph, capability)

    # The lowering object is needed to map a tensor name to its arena object.
    from compiler.backends.hbm_sram import lower as lower_module

    lowering = getattr(lower_module, "_LAST_LOWERING", None)

    device = Device(deployment, capability, root=args.snapshot, verify=False)
    driver = GenerationDriver(device)

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        str(args.snapshot), local_files_only=True
    )
    prompt = tokenizer.encode("The capital of France is", add_special_tokens=False)
    prompt = (prompt * ((args.prompt_tokens // len(prompt)) + 1))[: args.prompt_tokens]
    print(f"prompt {len(prompt)} tokens: {prompt}", flush=True)

    result = driver.generate(prompt, max_new_tokens=1)
    print(f"accelerator: {result.generated_token_ids} stop={result.stop_reason} "
          f"failure={result.failure}", flush=True)

    print("loading the reference for per-layer hidden states ...", flush=True)
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
    reference_logits = out.logits[0, -1].float().numpy()
    reference_token = int(np.argmax(reference_logits))
    hidden = [h[0].float().numpy() for h in out.hidden_states]
    print(f"reference token: {reference_token} "
          f"({tokenizer.decode([reference_token])!r})", flush=True)

    report: dict[str, Any] = {
        "schema": "opentallas.abi3.activation_bisect.v1",
        "evidence_class": "external_reference_comparator",
        "prompt_token_ids": prompt,
        "accelerator_token_ids": list(result.generated_token_ids),
        "reference_token_id": reference_token,
        "token_agreement": list(result.generated_token_ids)[:1] == [reference_token],
        "layers": [],
    }

    if lowering is None:
        report["note"] = (
            "the lowering object was not retained, so per-layer activations "
            "could not be read back; token comparison only"
        )
    else:
        for layer in range(min(args.layers, len(hidden) - 1)):
            name = f"layer.{layer:02d}.residual.mlp"
            codes = read_activation(device, lowering, name)
            entry: dict[str, Any] = {"layer": layer, "tensor": name}
            if codes is None:
                entry["status"] = "not_readable"
            else:
                got = widen(codes)[: hidden[layer + 1].size]
                want = hidden[layer + 1].reshape(-1)[: got.size]
                delta = np.abs(got - want)
                entry.update(
                    status="compared",
                    elements=int(got.size),
                    max_abs=float(delta.max()),
                    mean_abs=float(delta.mean()),
                    differing=int((delta > 0).sum()),
                )
            report["layers"].append(entry)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(report))
    print(f"\naccelerator {result.generated_token_ids} vs reference [{reference_token}]:"
          f" {'MATCH' if report['token_agreement'] else 'DIVERGE'}")
    print(f"wrote {args.output}")
    return 0 if report["token_agreement"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
