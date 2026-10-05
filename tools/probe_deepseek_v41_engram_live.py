#!/usr/bin/env python3
"""Does the V4.1 oracle's Engram contribute anything?

The Engram adds ``gate * value`` into the residual stream at the layers
``engram_layer_ids`` names, and ``gate`` is a sigmoid -- so a contribution of
EXACTLY zero means ``value`` is zero, which means the row lookup returned nothing.

That is what the harness did.  ``NgramHashState`` registers ``primes``,
``offsets``, ``multipliers`` and ``token_map`` as non-persistent buffers whose
CONTENT its ``__init__`` computes; the skeleton is built on ``meta``, so they
arrived with no storage and ``_materialise_buffers`` filled them with zeros like
every other buffer.  ``token_map[input_ids]`` was then 0 for every token, and
``rolling % primes`` was integer modulo by ZERO -- 0xFFFFFFFF on CUDA.  All 24
hash columns at every position came out 4294967295, the gather returned zeros, and
the Engram added nothing at all.

This is the regression guard for the restore.  It asserts two things a live Engram
must show and a dead one cannot: the hash tables hold non-zero data, and the
module's output differs from its input.  Run it after any change to the oracle's
buffer materialisation.
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

SCHEMA = "opentallas.abi3.deepseek_v41_engram_live.v1"
DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/"
    "snapshots/dba1be0a40aa45a94ad051997016db3960a90277"
)
#: ``cache`` is the look-back history the forward writes before it reads, so zeros
#: are correct for it.  The other four are data.
SCRATCH_BUFFERS = ("cache",)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--workload",
        type=Path,
        default=REPO / "build/workloads/deepseek-v4.1-flash-prefix/TA-DS41-CHAT-1-P10.json",
    )
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

    tables: dict[str, Any] = {}
    state = getattr(engine.model, "engram_hash", None)
    if state is not None:
        for name, buffer in state._buffers.items():
            if buffer is None:
                continue
            entry: dict[str, Any] = {
                "shape": list(buffer.shape),
                "device": str(buffer.device),
                "scratch": name in SCRATCH_BUFFERS,
            }
            if buffer.device.type != "meta":
                array = buffer.detach().cpu().numpy()
                entry["nonzero"] = int((array != 0).sum())
                entry["size"] = int(array.size)
            tables[name] = entry
    dead_tables = sorted(
        name
        for name, entry in tables.items()
        if not entry["scratch"] and entry.get("size") and entry.get("nonzero") == 0
    )

    seen: dict[str, dict[str, Any]] = {}
    handles = []

    def watch(label: str):
        def hook(_module, inputs, output):  # noqa: ANN001
            tensor = output[0] if isinstance(output, tuple) else output
            if not (hasattr(tensor, "detach") and inputs and hasattr(inputs[0], "detach")):
                return
            after = np.asarray(tensor.detach().float().cpu(), dtype=np.float64)
            before = np.asarray(inputs[0].detach().float().cpu(), dtype=np.float64)
            after = after.reshape(-1, after.shape[-1])
            before = before.reshape(-1, before.shape[-1])
            difference = np.abs(after - before)
            seen[label] = {
                "rows": int(before.shape[0]),
                "rows_that_moved": int((difference.max(axis=1) > 0).sum()),
                "max_abs_contribution": float(difference.max()),
                "mean_abs_contribution": float(difference.mean()),
                "input_peak": float(np.abs(before).max()),
            }

        return hook

    hashes: dict[str, Any] = {}

    def watch_ids(label: str):
        def hook(_module, inputs, _output):  # noqa: ANN001
            if not (inputs and hasattr(inputs[0], "detach")):
                return
            ids = np.asarray(inputs[0].detach().cpu(), dtype=np.int64).reshape(-1)
            hashes[label] = {
                "count": int(ids.size),
                "min": int(ids.min()),
                "max": int(ids.max()),
                "sentinel_0xffffffff": int((ids == 0xFFFFFFFF).sum()),
                "distinct": int(np.unique(ids).size),
            }

        return hook

    for index, block in enumerate(engine.model.layers):
        engram = getattr(block, "engram", None)
        if engram is None:
            continue
        handles.append(engram.register_forward_hook(watch(f"L{index:02d}")))
        if hasattr(engram, "embed"):
            handles.append(engram.embed.register_forward_hook(watch_ids(f"L{index:02d}")))

    workload = json.loads(args.workload.read_text())
    ids = [int(t) for t in (workload.get("token_ids") or workload["prompt_token_ids"])]
    with torch.inference_mode():
        engine.forward(torch.tensor([ids], dtype=torch.long, device=args.device), 0)
    for handle in handles:
        handle.remove()

    inert = sorted(label for label, entry in seen.items() if entry["rows_that_moved"] == 0)
    sentinels = sorted(
        label for label, entry in hashes.items() if entry["sentinel_0xffffffff"]
    )
    live = not dead_tables and not inert and not sentinels

    report = {
        "schema": SCHEMA,
        "question": "does the oracle's Engram contribute anything to the residual?",
        "answer": (
            "yes at every engram layer" if live
            else "NO -- " + ", ".join(
                part for part in (
                    f"zeroed hash tables {dead_tables}" if dead_tables else "",
                    f"inert engram layers {inert}" if inert else "",
                    f"sentinel hash ids at {sentinels}" if sentinels else "",
                ) if part
            )
        ),
        "snapshot": str(args.snapshot),
        "workload": str(args.workload),
        "prompt_token_count": len(ids),
        "hash_tables": tables,
        "hash_tables_entirely_zero": dead_tables,
        "hash_ids_seen": hashes,
        "engram_layers": seen,
        "inert_engram_layers": inert,
        "engram_is_live": live,
        "not_a_claim": [
            "a live Engram is not a correct one: this shows the contribution is "
            "non-zero and the ids are in range, not that either matches the vendor",
            "nothing here is an accelerator measurement",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    for label in sorted(seen):
        entry = seen[label]
        h = hashes.get(label, {})
        print(
            f"  {label}: {entry['rows_that_moved']}/{entry['rows']} rows moved, "
            f"max contribution {entry['max_abs_contribution']:.6g} against a peak of "
            f"{entry['input_peak']:.6g}; hash ids {h.get('min')}..{h.get('max')} "
            f"({h.get('sentinel_0xffffffff')} sentinels)"
        )
    print(f"\nengram is live: {live}\n-> {args.output}")
    return 0 if live else 1


if __name__ == "__main__":
    raise SystemExit(main())
