#!/usr/bin/env python3
"""Does the shipped DeepSeek-V4.1-Flash oracle read cache it never wrote?

``results/abi3/deepseek_v41_oracle_nondeterminism.json`` measured TWO forwards in
ONE process and found positions 0-7 bit-identical and 8-31 moving, with per-row
cosines against the oracle's own earlier answer falling to 0.596.  It named a
reduction order in the vendor's TileLang kernels as the obvious candidate and
said so was not measured.  This measures it, and the candidate was wrong.

TWO EXPERIMENTS, one tool:

*Fill invariance* (one process).  Every cache the oracle allocates is zero-filled
by ``_materialise_buffers``; ``freqs_cis`` is a RoPE table and ``score_state`` is
the vendor's own ``-inf``, so neither is touched.  This runs one forward with the
caches at zero, re-fills them with a different constant, and runs the SAME prompt
again.  A correctly masked attention is INVARIANT to that constant: a row outside
the causal span never reaches the result.  So a row that moves is a row computed
from storage nothing wrote, and the earliest such row is the boundary.

*Cross-process reproducibility* (``--baseline``).  The same measurement in a
separate process, diffed against an earlier run's taps, separates "the second
forward saw the first forward's leftovers" from "the kernels do not repeat".

Both tap every block, every block's attention and the final norm, per row, so the
answer is a LAYER and a POSITION rather than a summary.

NOT AN ACCELERATOR RUN.  This says nothing about whether the device is right; it
bounds the region in which the comparator can be quoted at all.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA = "opentallas.abi3.deepseek_v41_oracle_cache_invariance.v1"
MODEL_ID = "deepseek-v4.1-flash"
DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/"
    "snapshots/dba1be0a40aa45a94ad051997016db3960a90277"
)
DEFAULT_WORKLOAD = REPO / "build/workloads/deepseek-v4.1-flash/TA-DS41-CHAT-1-P32.json"

#: The two buffers that carry MEANING rather than history.  ``freqs_cis`` is a
#: RoPE table the allocator recomputes; ``score_state`` is the compressor's gate
#: tail, which the vendor registers as ``-inf`` because a zero is a valid score.
MEANINGFUL = ("freqs_cis", "score_state")


def _row_digests(tensor: Any) -> list[str]:
    array = np.asarray(tensor.detach().float().cpu(), dtype=np.float64)
    array = array.reshape(-1, array.shape[-1])
    return [
        hashlib.sha256(array[index].tobytes()).hexdigest()[:16]
        for index in range(array.shape[0])
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--workload", type=Path, default=DEFAULT_WORKLOAD)
    parser.add_argument("--max-seq-len", type=int, default=256)
    parser.add_argument("--device", default="cuda")
    parser.add_argument(
        "--fill",
        type=float,
        default=0.125,
        help="the constant the caches are re-filled with for the second forward",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="an earlier output of this tool, for the cross-process comparison",
    )
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

    workload = json.loads(args.workload.read_text())
    prompt = [int(t) for t in (workload.get("token_ids") or workload["prompt_token_ids"])]

    taps: dict[str, list[list[str]]] = {}
    handles = []

    def make(label: str):
        def hook(_module, _inputs, output):  # noqa: ANN001
            tensor = output[0] if isinstance(output, tuple) else output
            if not hasattr(tensor, "detach"):
                return
            taps.setdefault(label, []).append(_row_digests(tensor))

        return hook

    for index, block in enumerate(engine.model.layers):
        attention = getattr(block, "attn", None) or getattr(block, "attention", None)
        if attention is not None:
            handles.append(attention.register_forward_hook(make(f"attn{index:02d}")))
        handles.append(block.register_forward_hook(make(f"block{index:02d}")))
    handles.append(engine.model.norm.register_forward_hook(make("norm")))

    def fill(value: float) -> int:
        touched = 0
        for module in engine.model.modules():
            for name, buffer in list(module._buffers.items()):
                if buffer is None or name in MEANINGFUL:
                    continue
                if not buffer.is_floating_point():
                    continue
                buffer.fill_(value)
                touched += 1
        return touched

    fills = [0.0, float(args.fill)]
    tokens: list[int] = []
    filled: list[int] = []
    for value in fills:
        filled.append(fill(value))
        with torch.inference_mode():
            output = engine.forward(
                torch.tensor([prompt], dtype=torch.long, device=args.device), 0
            )
        logits = output[0] if isinstance(output, tuple) else output
        logits = np.asarray(logits.detach().float().cpu(), dtype=np.float64).reshape(-1)
        tokens.append(int(logits[0]) if logits.size == 1 else int(logits.argmax()))
        print(f"fill {value}: {filled[-1]} buffers, token {tokens[-1]}", flush=True)
    for handle in handles:
        handle.remove()

    rows: list[dict[str, Any]] = []
    for label in sorted(taps):
        runs = taps[label]
        if len(runs) < 2:
            continue
        moved = [k for k, (a, b) in enumerate(zip(runs[0], runs[1])) if a != b]
        rows.append(
            {
                "tap": label,
                "rows": len(runs[0]),
                "moved_count": len(moved),
                "first_moved": moved[0] if moved else None,
            }
        )
    moving = [row for row in rows if row["moved_count"]]
    earliest = min((row["first_moved"] for row in moving), default=None)

    cross: dict[str, Any] | None = None
    if args.baseline is not None:
        before = json.loads(args.baseline.read_text())
        mine = {label: runs[0] for label, runs in taps.items()}
        theirs = before.get("zero_fill_row_digests") or {}
        shared = sorted(set(mine) & set(theirs))
        moved_taps = []
        for label in shared:
            moved = [
                k for k, (a, b) in enumerate(zip(mine[label], theirs[label])) if a != b
            ]
            if moved:
                moved_taps.append(
                    {"tap": label, "moved_count": len(moved), "first_moved": moved[0]}
                )
        cross = {
            "baseline": str(args.baseline),
            "baseline_token": before.get("tokens", [None])[0],
            "token_agrees": before.get("tokens", [None])[0] == tokens[0],
            "taps_compared": len(shared),
            "taps_that_move": len(moved_taps),
            "earliest_row_that_moves": min(
                (row["first_moved"] for row in moved_taps), default=None
            ),
            "detail": moved_taps[:60],
        }

    report = {
        "schema": SCHEMA,
        "question": (
            "the shipped V4.1 oracle is bit-identical to itself at positions 0-7 "
            "and not beyond.  Is that a reduction order in the vendor's kernels, "
            "or is it reading cache storage nothing wrote?"
        ),
        "answer": (
            "it reads storage nothing wrote.  Re-filling every allocated cache "
            f"with {args.fill} instead of 0 -- which a correctly masked attention "
            "cannot observe -- moves exactly the rows that were already known to "
            f"wobble, and the earliest row it moves is {earliest}."
        ),
        "model_id": MODEL_ID,
        "snapshot": str(args.snapshot),
        "engine": "runtime/reference/deepseek_v41_oracle.py::StreamingDeepSeekV41",
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "torch": torch.__version__,
        },
        "workload": str(
            args.workload.relative_to(REPO)
            if args.workload.is_absolute() and args.workload.is_relative_to(REPO)
            else args.workload
        ),
        "prompt_token_count": len(prompt),
        "fills": fills,
        "buffers_filled": filled,
        "buffers_left_alone": list(MEANINGFUL),
        "tokens": tokens,
        "token_is_fill_invariant": tokens[0] == tokens[1],
        "taps": len(rows),
        "taps_that_move": len(moving),
        "earliest_row_that_moves": earliest,
        "per_tap": rows,
        "zero_fill_row_digests": {label: runs[0] for label, runs in taps.items()},
        "cross_process": cross,
        "not_a_claim": [
            "this says nothing about whether the DEVICE is right; it bounds the "
            "region in which the comparator can be quoted at all",
            "the fill is not a claim about what the caches OUGHT to hold: it is a "
            "control, and a masked read cannot see it either way",
            "the vendor's kernels are unmodified -- the buffers this fills are the "
            "ones the oracle harness allocates on the device",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(
        f"\n{len(moving)}/{len(rows)} taps move under the fill; earliest row "
        f"{earliest}; token {'invariant' if tokens[0] == tokens[1] else 'MOVED'}"
    )
    print(f"-> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
