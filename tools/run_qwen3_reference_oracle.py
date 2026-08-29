#!/usr/bin/env python3
"""Independent Qwen3-8B greedy-decode oracle.

This is an *external comparator*, not part of the accelerator path.  It runs the
pinned checkpoint through the vendor modelling code to produce the token IDs a
faithful implementation should produce for each pinned workload, so that the
accelerator's own output can be checked against something it did not compute.

It is never used to produce accelerator tokens, never supplies an activation,
and its results are labelled as an external reference in every report.  ADR-003
section 18 permits exactly this use and forbids the other one.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import canonical_json  # noqa: E402

DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/"
    "b968826d9c46dd6066d109eabc6255188de91218"
)



def _chunked_greedy(model, input_ids, *, max_new_tokens, chunk, eos_ids):
    """Greedy decode with a chunked prefill.

    Feeding an 8,000-token prompt in one pass materialises an activation
    working set this GPU does not have spare beside its other tenants.  Chunking
    carries the KV cache forward instead, which bounds the working set to one
    chunk while producing exactly the same result: attention still attends over
    the full accumulated cache.
    """
    import torch

    device = model.device
    ids = input_ids.to(device)
    past = None
    with torch.inference_mode():
        for start in range(0, ids.shape[1], chunk):
            piece = ids[:, start : start + chunk]
            out = model(input_ids=piece, past_key_values=past, use_cache=True)
            past = out.past_key_values
            if start % (chunk * 8) == 0:
                print(
                    f"  prefill {min(start + chunk, ids.shape[1])}/{ids.shape[1]}",
                    flush=True,
                )
        generated: list[int] = []
        logits = out.logits[:, -1, :]
        for _ in range(max_new_tokens):
            token = int(torch.argmax(logits[0]).item())
            generated.append(token)
            if token in eos_ids:
                break
            step = torch.tensor([[token]], dtype=torch.long, device=device)
            out = model(input_ids=step, past_key_values=past, use_cache=True)
            past = out.past_key_values
            logits = out.logits[:, -1, :]
    return generated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--workloads", type=Path, default=REPO / "build" / "workloads" / "qwen3-8b"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "results" / "abi3" / "qwen3_reference_oracle.json",
    )
    parser.add_argument("--only", action="append", default=None)
    parser.add_argument("--gpu-gib", type=int, default=9)
    parser.add_argument(
        "--cpu-only",
        action="store_true",
        help=(
            "Run entirely on CPU. Slower, but immune to the GPU memory "
            "fluctuation caused by other tenants on this machine, which is what "
            "matters for a long-prefill oracle that must not be evicted."
        ),
    )
    parser.add_argument("--cpu-gib", type=int, default=80)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--prefill-chunk",
        type=int,
        default=0,
        help=(
            "Feed the prompt in chunks of this many tokens, carrying the KV "
            "cache between chunks. Zero uses one pass. Chunking bounds the "
            "activation working set, which is what makes an 8,000-token "
            "prefill fit beside other tenants on this GPU."
        ),
    )
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    index = json.loads((args.workloads / "index.json").read_text())
    tokenizer = AutoTokenizer.from_pretrained(
        str(args.snapshot), local_files_only=True, trust_remote_code=False
    )

    print(
        "loading Qwen3-8B in bfloat16 "
        + ("on CPU ..." if args.cpu_only else "with GPU/CPU sharding ..."),
        flush=True,
    )
    started = time.perf_counter()
    placement = (
        {"device_map": {"": "cpu"}}
        if args.cpu_only
        else {
            "device_map": "auto",
            "max_memory": {0: f"{args.gpu_gib}GiB", "cpu": f"{args.cpu_gib}GiB"},
        }
    )
    model = AutoModelForCausalLM.from_pretrained(
        str(args.snapshot),
        dtype=torch.bfloat16,
        **placement,
        local_files_only=True,
        trust_remote_code=False,
        attn_implementation="sdpa",
    )
    model.eval()
    print(f"loaded in {time.perf_counter() - started:.1f}s", flush=True)

    report = {
        "schema": "opentallas.abi3.reference_oracle.v1",
        "evidence_class": "external_reference_comparator",
        "not_a_claim": [
            "accelerator_execution",
            "artifact_only_execution",
            "timing_or_performance",
        ],
        "model_id": "qwen3-8b",
        "snapshot": str(args.snapshot),
        "tokenizer_sha256": index["tokenizer_sha256"],
        "torch_version": torch.__version__,
        "dtype": "bfloat16",
        "selection": "greedy_lowest_token_id_argmax",
        "device_map": "cpu bfloat16" if args.cpu_only else "auto (gpu+cpu bfloat16)",
        "results": {},
    }

    for wid, entry in sorted(index["workloads"].items()):
        if args.only and wid not in args.only:
            continue
        body = json.loads((args.workloads / entry["path"]).read_text())
        ids = body["token_ids"]
        print(
            f"\n=== {wid} ({entry['kind']}, {len(ids)} prompt tokens, "
            f"max_new={entry['max_new_tokens']}) ===",
            flush=True,
        )
        input_ids = torch.tensor([ids], dtype=torch.long)
        step_started = time.perf_counter()
        eos_set = {151645, 151643}
        if tokenizer.eos_token_id is not None:
            eos_set.add(int(tokenizer.eos_token_id))
        if args.prefill_chunk:
            generated = _chunked_greedy(
                model,
                input_ids,
                max_new_tokens=entry["max_new_tokens"],
                chunk=args.prefill_chunk,
                eos_ids=eos_set,
            )
        else:
            with torch.inference_mode():
                out = model.generate(
                    input_ids=input_ids.to(model.device),
                    max_new_tokens=entry["max_new_tokens"],
                    do_sample=False,
                    num_beams=1,
                    temperature=None,
                    top_p=None,
                    top_k=None,
                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                    return_dict_in_generate=True,
                    output_scores=False,
                )
            generated = out.sequences[0][len(ids) :].tolist()
        elapsed = time.perf_counter() - step_started
        text = tokenizer.decode(generated, skip_special_tokens=False)
        visible = tokenizer.decode(generated, skip_special_tokens=True)
        eos_ids = set(
            [tokenizer.eos_token_id] if tokenizer.eos_token_id is not None else []
        )
        eos_ids |= {151645, 151643}
        stop = "eos" if generated and generated[-1] in eos_ids else "max_new_tokens"
        report["results"][wid] = {
            "kind": entry["kind"],
            "workload_digest": entry["digest"],
            "prompt_token_count": len(ids),
            "generated_token_ids": generated,
            "generated_token_count": len(generated),
            "stop_reason": stop,
            "raw_decoded_text": text,
            "visible_decoded_text": visible,
            "wall_seconds": round(elapsed, 3),
        }
        print(f"generated {len(generated)} tokens in {elapsed:.1f}s, stop={stop}")
        print(f"first 24 ids: {generated[:24]}")
        print(f"text: {visible[:400]!r}", flush=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_json(report))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(report))
    print(f"\nwrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
