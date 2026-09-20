#!/usr/bin/env python3
"""The device's selected compressed positions against the VENDOR Indexer's own.

A top-k is the one discrete step in layer 2's attention, and
results/abi3/deepseek_v41_divergence_enters_layer2_attention.json shows a 44.8x jump
across exactly that sublayer that is absent at prompt position 0. If the two sides
select DIFFERENT positions then the mechanism is settled: a one-ulp score difference
swaps a selection and the attention output differs by far more than the scores did,
which no amount of arithmetic tightening downstream can repair.

The vendor's Indexer.forward returns precisely this quantity --
``index_score.topk(topk, dim=-1, sorted=False).indices.sort(dim=-1).values`` with
out-of-range entries replaced by -1 -- so the comparison is between two integer sets
and needs no tolerance at all. That is the whole appeal of this instrument: every
earlier V4.1 comparison had to argue about how close two floats should be.

Reported per layer that owns its keys: the sizes, the symmetric difference, and the
first query row whose selection differs.
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

SCHEMA = "opentallas.abi3.deepseek_v41_index_selection_agreement.v1"
DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/"
    "snapshots/dba1be0a40aa45a94ad051997016db3960a90277"
)


def _compare(device_rows: np.ndarray, oracle_rows: np.ndarray) -> dict[str, Any]:
    rows = min(device_rows.shape[0], oracle_rows.shape[0])
    per_row = []
    first_difference = None
    for index in range(rows):
        left = {int(v) for v in device_rows[index] if int(v) >= 0}
        right = {int(v) for v in oracle_rows[index] if int(v) >= 0}
        only_device = sorted(left - right)
        only_oracle = sorted(right - left)
        entry = {
            "row": index,
            "device_selected": len(left),
            "oracle_selected": len(right),
            "in_both": len(left & right),
            "only_device": only_device[:16],
            "only_oracle": only_oracle[:16],
            "symmetric_difference": len(only_device) + len(only_oracle),
        }
        per_row.append(entry)
        if entry["symmetric_difference"] and first_difference is None:
            first_difference = entry
    return {
        "rows_compared": rows,
        "rows_that_differ": sum(1 for r in per_row if r["symmetric_difference"]),
        "first_row_that_differs": first_difference,
        "per_row": per_row,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--workload",
        type=Path,
        default=REPO / "build/workloads/deepseek-v4.1-flash-prefix/TA-DS41-CHAT-1-P10.json",
    )
    parser.add_argument("--device-selections", type=Path, required=True)
    parser.add_argument("--max-seq-len", type=int, default=256)
    parser.add_argument("--torch-device", default="cuda")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    device_side = json.loads(args.device_selections.read_text())

    #: ASSEMBLE A STREAMED SELECT FROM ITS ISSUES.  ``selections`` holds the FIRST
    #: issue of each descriptor, which for a streamed select is query row zero --
    #: and row zero legitimately selects nothing, because a compressed group has to
    #: have completed before a position can attend to it.  Comparing that one row
    #: against the oracle's ten reported "9 query rows missing, device selected
    #: NOTHING" for a device that selects correctly on the other nine.
    #:
    #: ``per_issue_rows`` holds every issue with the query row it computed, derived
    #: from its output view (results/abi3/
    #: deepseek_v41_select_row_is_on_its_output_view.json). Where those rows are
    #: present this stacks them into the [span, slots] array the oracle emits. The
    #: same row is issued once per node and every copy agrees, which is asserted
    #: rather than assumed.
    per_issue = device_side.get("per_issue_rows") or {}
    assembled: dict[int, np.ndarray] = {}
    for descriptor, issues in per_issue.items():
        by_row: dict[int, list[list[int]]] = {}
        for issue in issues:
            row_index = issue.get("query_row")
            if row_index is None or len(issue["rows"]) != 1:
                by_row = {}
                break
            existing = by_row.setdefault(int(row_index), issue["rows"][0])
            if existing != issue["rows"][0]:
                raise SystemExit(
                    f"descriptor {descriptor} issued query row {row_index} twice "
                    "with different selections; the per-node copies must agree "
                    "for this assembly to mean anything"
                )
        if by_row and sorted(by_row) == list(range(len(by_row))):
            assembled[int(descriptor)] = np.asarray(
                [by_row[i] for i in range(len(by_row))], dtype=np.int64
            )

    device_selections = []
    for entry in device_side["selections"]:
        descriptor = int(entry.get("operator", -1))
        if descriptor in assembled:
            device_selections.append(assembled[descriptor])
        else:
            device_selections.append(np.asarray(entry["rows"], dtype=np.int64))
    if not device_selections:
        raise SystemExit("the device selection file holds nothing")
    if assembled:
        print(
            "assembled from per-issue rows: "
            + ", ".join(
                f"descriptor {d} -> {tuple(a.shape)}"
                for d, a in sorted(assembled.items())
            )
        )

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
            device=args.torch_device,
            verbose=False,
        ),
        tokenizer_backend=backend,
    )
    engine.load_endpoints()

    captured: dict[int, np.ndarray] = {}
    handles = []

    def hook(layer_index: int):
        def inner(_module, _inputs, output):  # noqa: ANN001
            if layer_index in captured or not hasattr(output, "detach"):
                return None
            rows = np.asarray(output.detach().cpu(), dtype=np.int64)
            captured[layer_index] = rows.reshape(-1, rows.shape[-1])
            return None

        return inner

    #: Only a layer that owns its keys runs a selection of its own; the others read
    #: the source layer's, which is why the device emits far fewer INDEX_TOPK
    #: operators than there are layers.
    owners: list[int] = []
    for index, layer in enumerate(engine.model.layers):
        indexer = getattr(getattr(layer, "attn", None), "indexer", None)
        if indexer is None:
            continue
        if getattr(indexer, "owns_k", False):
            owners.append(index)
        handles.append(indexer.register_forward_hook(hook(index)))

    workload = json.loads(args.workload.read_text())
    prompt = [int(t) for t in workload["token_ids"]]
    with torch.inference_mode():
        engine.forward(
            torch.tensor([prompt], dtype=torch.long, device=args.torch_device), 0
        )
    for handle in handles:
        handle.remove()

    ordered = sorted(captured)
    comparisons = []
    for position, device_rows in enumerate(device_selections):
        if position >= len(ordered):
            break
        layer_index = ordered[position]
        comparisons.append(
            {
                "device_selection_order": position,
                "oracle_layer": layer_index,
                "oracle_layer_owns_its_keys": layer_index in owners,
                "device_dims": list(device_rows.shape),
                "oracle_dims": list(captured[layer_index].shape),
                **_compare(device_rows, captured[layer_index]),
            }
        )

    differ = [c for c in comparisons if c["rows_that_differ"]]
    #: A SHAPE mismatch matters more than a set mismatch and hides it: rows are
    #: compared pairwise up to the shorter side, so a device selection with one
    #: query row against an oracle's ten reports "0 differing" over one row while
    #: nine rows were never looked at.
    shape_mismatches = [
        {
            "device_selection_order": c["device_selection_order"],
            "oracle_layer": c["oracle_layer"],
            "device_dims": c["device_dims"],
            "oracle_dims": c["oracle_dims"],
            "device_rows_missing": max(0, c["oracle_dims"][0] - c["device_dims"][0]),
            "device_selected_nothing": all(
                r["device_selected"] == 0 for r in c["per_row"]
            ),
        }
        for c in comparisons
        if c["device_dims"][0] != c["oracle_dims"][0]
        or all(r["device_selected"] == 0 for r in c["per_row"])
    ]
    report = {
        "schema": SCHEMA,
        "question": (
            "layer 2's attention is where the V4.1 device departs from the "
            "comparator, and a top-k is the only discrete step in it. Do the two "
            "sides SELECT the same compressed positions?"
        ),
        "answer": (
            (
                "THE SHAPES DO NOT EVEN MATCH at "
                + ", ".join(
                    f"oracle layer {m['oracle_layer']} "
                    f"(device {m['device_dims']} against oracle {m['oracle_dims']}"
                    + (", device selected NOTHING" if m["device_selected_nothing"] else "")
                    + ")"
                    for m in shape_mismatches
                )
            )
            if shape_mismatches
            else ("the selections differ" if differ else
                  "every compared selection is identical")
        ),
        "shape_mismatches": shape_mismatches,
        "prompt_token_count": len(prompt),
        "device_selections": str(args.device_selections),
        "oracle_layers_with_an_indexer": ordered,
        "oracle_layers_that_own_their_keys": owners,
        "comparisons": comparisons,
        "not_a_claim": [
            "this is runtime.sim, not RTL",
            "identical selections would NOT mean the block agrees: it would rule the "
            "top-k out as the amplifier and send the bisection to the arithmetic",
            "the device emits one INDEX_TOPK per key-owning layer, so the pairing is "
            "by order and holds only while both sides agree on which layers own keys",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    for m in shape_mismatches:
        print(f"  SHAPE MISMATCH oracle layer {m['oracle_layer']}: device "
              f"{m['device_dims']} against oracle {m['oracle_dims']}, "
              f"{m['device_rows_missing']} query rows missing"
              + (", device selected NOTHING" if m["device_selected_nothing"] else ""))
    print(f"oracle layers with an indexer: {ordered}")
    print(f"oracle layers that own their keys: {owners}")
    for c in comparisons:
        print(f"  device selection {c['device_selection_order']} vs oracle layer "
              f"{c['oracle_layer']}: rows {c['rows_compared']}, differing "
              f"{c['rows_that_differ']}, device dims {c['device_dims']}, oracle dims "
              f"{c['oracle_dims']}")
        first = c["first_row_that_differs"]
        if first:
            print(f"      first differing row {first['row']}: in both "
                  f"{first['in_both']}, only device {first['only_device'][:8]}, "
                  f"only oracle {first['only_oracle'][:8]}")
    print(f"-> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
