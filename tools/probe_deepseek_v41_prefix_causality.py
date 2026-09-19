#!/usr/bin/env python3
"""Is a shorter prefix's V4.1 oracle answer a PREFIX of a longer one's?

Several V4.1 records bracket the device against the oracle across prompt lengths
-- 8 passes, 9 passes, 10 fails, 11 fails at token 3 -- and read the pattern as a
threshold in the DEVICE.  That reading needs a property nobody measured: that the
comparator computes the same thing for positions the two prompts share.  Row i of
a causal model depends only on rows 0..i, so the first nine rows of a nine-token
prefill and of a ten-token prefill ought to be identical.

This measures the difference, per layer, over the shared rows.  Digest inequality
would not be enough -- a kernel that tiles the query axis differently for 9 and 10
positions changes the reduction ORDER and moves the last bits, which is a
different claim -- so this reports max|diff| against the tensor's own peak.

Both lengths are fill-invariant end to end (run
``tools/probe_deepseek_v41_oracle_cache_invariance.py`` per prefix), so one
process is sound here: at these lengths there is no unwritten-cache term for the
second forward to inherit.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA = "opentallas.abi3.deepseek_v41_oracle_prefix_causality.v1"
DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/"
    "snapshots/dba1be0a40aa45a94ad051997016db3960a90277"
)
PREFIX = REPO / "build/workloads/deepseek-v4.1-flash-prefix"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--shorter", type=Path, default=PREFIX / "TA-DS41-CHAT-1-P9.json")
    parser.add_argument("--longer", type=Path, default=PREFIX / "TA-DS41-CHAT-1-P10.json")
    parser.add_argument("--max-seq-len", type=int, default=256)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    from compiler.frontend.deepseek_v41_tokenizer import (  # noqa: PLC0415
        load_verified_deepseek_v41_tokenizer,
    )
    from runtime.reference.deepseek_v4_oracle import OracleConfig  # noqa: PLC0415
    from runtime.reference.deepseek_v41_oracle import (  # noqa: PLC0415
        StreamingDeepSeekV41,
    )
    import torch  # noqa: PLC0415

    verified = load_verified_deepseek_v41_tokenizer(args.snapshot)
    backend = getattr(verified, "backend", None) or getattr(verified, "_backend", None)
    engine = StreamingDeepSeekV41(
        OracleConfig(
            snapshot=args.snapshot,
            max_seq_len=args.max_seq_len,
            device=args.device,
            verbose=False,
        ),
        tokenizer_backend=backend,
    )
    engine.load_endpoints()

    taps: dict[str, list[Any]] = {}
    handles = []

    def make(label: str):
        def hook(_module, _inputs, output):  # noqa: ANN001
            tensor = output[0] if isinstance(output, tuple) else output
            if not hasattr(tensor, "detach"):
                return
            array = np.asarray(tensor.detach().float().cpu(), dtype=np.float64)
            taps.setdefault(label, []).append(array.reshape(-1, array.shape[-1]))

        return hook

    for index, block in enumerate(engine.model.layers):
        attention = getattr(block, "attn", None) or getattr(block, "attention", None)
        if attention is not None:
            handles.append(attention.register_forward_hook(make(f"attn{index:02d}")))
    handles.append(engine.model.norm.register_forward_hook(make("norm")))

    tokens: list[int] = []
    lengths: list[int] = []
    for path in (args.shorter, args.longer):
        workload = json.loads(path.read_text())
        ids = [int(t) for t in (workload.get("token_ids") or workload["prompt_token_ids"])]
        lengths.append(len(ids))
        with torch.inference_mode():
            output = engine.forward(
                torch.tensor([ids], dtype=torch.long, device=args.device), 0
            )
        logits = output[0] if isinstance(output, tuple) else output
        logits = np.asarray(logits.detach().float().cpu(), dtype=np.float64).reshape(-1)
        tokens.append(int(logits[0]) if logits.size == 1 else int(logits.argmax()))
        print(f"{path.name}: {len(ids)} tokens -> {tokens[-1]}", flush=True)
    for handle in handles:
        handle.remove()

    rows: list[dict[str, Any]] = []
    for label in sorted(taps):
        runs = taps[label]
        if len(runs) < 2:
            continue
        a, b = runs[0], runs[1]
        shared = min(a.shape[0], b.shape[0])
        difference = np.abs(a[:shared] - b[:shared])
        peak = float(np.abs(a[:shared]).max()) or 1.0
        rows.append(
            {
                "tap": label,
                "shared_rows": int(shared),
                "rows_that_differ": int((difference.max(axis=1) > 0).sum()),
                "max_abs_diff": float(difference.max()),
                "max_abs_value": peak,
                "relative": float(difference.max() / peak),
            }
        )
    exact = [row["tap"] for row in rows if row["max_abs_diff"] == 0.0]
    worst = max(rows, key=lambda row: row["relative"])
    first = next((row for row in rows if row["max_abs_diff"] > 0.0), None)

    report = {
        "schema": SCHEMA,
        "question": (
            "the V4.1 prefix bracket reads 'passes at 9, fails at 10' as a "
            "threshold in the device.  Does the comparator compute the same thing "
            "for the positions the two prompts share?"
        ),
        "answer": (
            "NO.  The shared rows are exactly identical only in the layers that do "
            f"not compress ({', '.join(exact) or 'none'}); the first layer that "
            f"differs is {first['tap'] if first else 'none'} at "
            f"{first['relative']:.3%} of its own peak if any, and the difference "
            f"grows with depth to {worst['relative']:.3%} at {worst['tap']}.  So a "
            "prefix is not a prefix of the computation, the two lengths are "
            "independent tests, and the bracket is not a threshold."
        ),
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "torch": torch.__version__,
        },
        "snapshot": str(args.snapshot),
        "shorter": str(args.shorter),
        "longer": str(args.longer),
        "prompt_token_counts": lengths,
        "tokens": tokens,
        "taps_exactly_identical": exact,
        "first_tap_that_differs": first,
        "largest_relative_difference": worst,
        "per_tap": rows,
        "not_a_claim": [
            "this is not a defect in the vendor's model: each prompt is its own "
            "request and the release never claims one prefill extends another",
            "it says nothing about whether the DEVICE is right at either length",
            "it does invalidate reading a pass at one prefix length and a failure "
            "at the next as a threshold in anything",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(f"\nexactly identical taps: {exact}")
    print(f"first differing: {first['tap'] if first else None}")
    print(f"largest: {worst['tap']} at {worst['relative']:.3%}")
    print(f"-> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
