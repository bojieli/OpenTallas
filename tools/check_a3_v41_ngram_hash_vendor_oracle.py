#!/usr/bin/env python3
"""Cross-check `ngram_row_ids` against the pinned vendor Engram module itself.

The reference in `runtime/reference/engram.py` is written from the semantics of
the pinned `inference/engram.py` (SRC-DSV41-FLASH-MODEL).  This tool closes the
loop by EXECUTING that pinned source: it verifies the file's SHA-256 against the
digest `docs/SOURCES.md` records, constructs `NgramHashState` with the released
layout injected (its `__init__` needs the vendor tokenizer, which is not
reproduced here), calls the vendor's own `forward`, and compares every row id
against the reference for every layer, order, head and position, including DEAD
spans and sequence-start blocking.

The vendor source is not vendored into this repository, so this record is
produced on demand and is not a campaign step.  Pass the pinned file's path:

    tools/check_a3_v41_ngram_hash_vendor_oracle.py --vendor-source <path>
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.reference.engram import ngram_row_ids  # noqa: E402
from tools.build_a3_v41_ngram_hash_vectors import (  # noqa: E402
    PINNED_CONFIG,
    PINNED_ENGRAM_SOURCE_SHA256,
    released_layout,
)

DEFAULT_OUTPUT = ROOT / "results/rtl/a3_v41_ngram_hash_vendor_oracle.json"


def load_vendor(path: Path) -> tuple[Any, str]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != PINNED_ENGRAM_SOURCE_SHA256:
        raise SystemExit(
            f"{path} has SHA-256 {digest}, not the pinned "
            f"{PINNED_ENGRAM_SOURCE_SHA256}"
        )
    spec = importlib.util.spec_from_file_location("pinned_engram", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, digest


def main() -> int:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("--vendor-source", type=Path, required=True)
    argument_parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    argument_parser.add_argument("--sequences", type=int, default=3)
    argument_parser.add_argument("--length", type=int, default=40)
    argument_parser.add_argument("--pad-id", type=int, default=7)
    args = argument_parser.parse_args()

    import numpy as np
    import torch

    vendor, digest = load_vendor(args.vendor_source)
    layout = released_layout()
    heads = PINNED_CONFIG["engram_n_heads"]
    max_ngram = PINNED_CONFIG["engram_max_ngram_size"]
    vocab = PINNED_CONFIG["engram_compressed_vocab_size"]

    primes = tuple(tuple(tuple(row) for row in layer["primes"]) for layer in layout["layers"])
    offsets = [layer["offsets"] for layer in layout["layers"]]
    multipliers = torch.tensor([layer["multipliers"] for layer in layout["layers"]])

    #: `NgramHashState.__init__` builds the compressed token map from the vendor
    #: tokenizer; only `forward` is under test here, so the buffers it reads are
    #: injected directly with the released layout.
    state = object.__new__(vendor.NgramHashState)
    torch.nn.Module.__init__(state)

    class Layout:
        pass

    holder = Layout()
    holder.max_ngram_size = max_ngram
    state.layout = holder
    state.pad_id = args.pad_id
    state.register_buffer("primes", torch.tensor(primes), persistent=False)
    state.register_buffer("offsets", torch.tensor(np.array(offsets)), persistent=False)
    state.register_buffer("multipliers", multipliers, persistent=False)
    state.register_buffer(
        "token_map", torch.arange(vocab, dtype=torch.int64), persistent=False
    )
    state.register_buffer(
        "cache",
        torch.empty(args.sequences, args.length, dtype=torch.int64),
        persistent=False,
    )

    rng = random.Random(20260913)
    sequences = [
        [rng.randrange(vocab) for _ in range(args.length)] for _ in range(args.sequences)
    ]
    dead = {(0, 5), (0, 6), (1, 17), (2, 0), (2, args.length - 1)}
    mask = torch.ones(args.sequences, args.length, dtype=torch.bool)
    for batch, position in dead:
        mask[batch, position] = False

    vendor_rows = state.forward(torch.tensor(sequences), 0, mask)

    compared = 0
    mismatches: list[dict[str, int]] = []
    for layer_index, layer in enumerate(layout["layers"]):
        for order in range(2, max_ngram + 1):
            for head in range(heads):
                column = (order - 2) * heads + head
                for batch, sequence in enumerate(sequences):
                    records = ngram_row_ids(
                        sequence,
                        order=order,
                        head=head,
                        multipliers=layer["multipliers"],
                        primes=layer["primes"],
                        offsets=layer["offsets"],
                        pad_id=args.pad_id,
                        compressed_vocab_size=vocab,
                        dead_positions=[
                            position for item, position in dead if item == batch
                        ],
                        n_heads=heads,
                        order_min=2,
                        table_rows=layer["table_rows"],
                    )
                    for position, record in enumerate(records):
                        compared += 1
                        wanted = int(vendor_rows[batch, position, layer_index, column])
                        if wanted != int(record["row_id"]):
                            mismatches.append(
                                {
                                    "layer": layer["layer_id"],
                                    "order": order,
                                    "head": head,
                                    "batch": batch,
                                    "position": position,
                                    "vendor": wanted,
                                    "reference": int(record["row_id"]),
                                }
                            )

    record = {
        "schema": "opentallas.rtl.a3_v41_ngram_hash_vendor_oracle.v1",
        "status": "pass" if not mismatches else "fail",
        "records_compared": compared,
        "mismatches": len(mismatches),
        "mismatch_detail": mismatches[:16],
        "reference": {
            "module": "runtime/reference/engram.py",
            "function": "ngram_row_ids",
            "sha256": hashlib.sha256(
                (ROOT / "runtime/reference/engram.py").read_bytes()
            ).hexdigest(),
        },
        "vendor_source": {
            "source": "SRC-DSV41-FLASH-MODEL inference/engram.py",
            "revision": "dba1be0a40aa45a94ad051997016db3960a90277",
            "sha256": digest,
            "executed_entry_point": "NgramHashState.forward",
            "not_executed": [
                "build_compressed_token_map (needs the vendor tokenizer)",
                "NgramHashState.__init__",
                "ParallelEngramEmbedding (the row read)",
            ],
        },
        "layout": {
            "released_primes_sum_equals_engram_num_embeddings": True,
            "layers": [
                {
                    "layer_id": layer["layer_id"],
                    "table_rows": layer["table_rows"],
                    "multipliers": layer["multipliers"],
                }
                for layer in layout["layers"]
            ],
        },
        "stimulus": {
            "sequences": args.sequences,
            "length": args.length,
            "pad_id": args.pad_id,
            "dead_positions": sorted(f"{batch}:{position}" for batch, position in dead),
            "orders": list(range(2, max_ngram + 1)),
            "heads": list(range(heads)),
        },
        "tools": {"torch": torch.__version__, "numpy": np.__version__},
        "claim_boundary": {
            "establishes_the_compressed_token_map": False,
            "establishes_the_released_pad_id": False,
            "executes_rtl": False,
            "runs_inside_the_rtl_campaign": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(
        f"vendor oracle cross-check status={record['status']} "
        f"records={compared} mismatches={len(mismatches)}"
    )
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
