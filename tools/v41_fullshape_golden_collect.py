#!/usr/bin/env python3
"""Validate and pin full-shape V4.1 golden shards; never infer an RTL verdict.

The campaign may run a context in consecutive layer ranges so it can resume at
a layer boundary. This collector checks every saved array, the boundaries, the
terminal logits, and the exact released-checkpoint snapshot used to produce it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

import numpy as np

from v41_fullshape_shard_compare import validate_golden_chain

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = (Path.home() / ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash"
                    / "snapshots/dba1be0a40aa45a94ad051997016db3960a90277")
DEFAULT_OUTPUT = ROOT / "results/rtl/hdc_v41x_fullshape_golden.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def snapshot_pin(snapshot: Path) -> dict:
    index = snapshot / "model.safetensors.index.json"
    weight_map = json.loads(index.read_text())["weight_map"]
    files = {}
    for name in sorted(set(weight_map.values())):
        path = snapshot / name
        if not path.is_symlink():
            raise ValueError(f"{path}: expected content-addressed Hugging Face blob symlink")
        blob = path.readlink().name
        if re.fullmatch(r"[0-9a-f]{64}", blob) is None or not path.is_file():
            raise ValueError(f"{path}: invalid or missing content-addressed blob")
        files[name] = {"sha256_blob_id": blob, "bytes": path.stat().st_size}
    return {"revision": snapshot.name, "index_sha256": sha256(index),
            "shard_count": len(files), "shards": files,
            "verification": "snapshot's content-addressed blob IDs and existence; full shard rehash not run"}


def collect(scratch: Path, contexts: list[int], snapshot: Path, source_root: Path = ROOT,
            annotate_shards: bool = False) -> dict:
    checkpoint = snapshot_pin(snapshot)
    source_files = ["tools/rtl_v41_fullshape_layer_campaign.py", "tools/v41_fullshape_golden_collect.py",
                    "tools/v41_fullshape_shard_compare.py", "tools/hdc_golden_v41.py", "tools/hdc_golden.py",
                    "compiler/models/deepseek-v4.1-flash/inference_config.json"]
    out = {"schema": "opentallas.rtl.hdc_v41x_fullshape_golden.v1", "status": "golden_only",
           "claim_boundary": "Released-checkpoint golden decode on deterministic synthetic, format-consistent "
                             "KV/index state. No full-shape RTL layer, token cycle, or place-and-route verdict.",
           "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source_root,
                                                     text=True).strip(),
           "source_sha256": {name: sha256(source_root / name) for name in source_files},
           "checkpoint": checkpoint, "contexts": {}}
    for context in contexts:
        rows = validate_golden_chain(scratch, context, list(range(40)), source_root)["layers"]
        summaries = sorted(scratch.glob(f"golden_ctx{context}_*.json"))
        if not summaries:
            raise ValueError(f"context {context}: no campaign summary")
        summary_rows = {}
        history = head = None
        state_segments = []
        for path in summaries:
            summary = json.loads(path.read_text())
            if summary["context"] != context or summary["arith"] != "chunk8":
                raise ValueError(f"{path}: context or arithmetic mismatch")
            if history is None:
                history = summary["history"]
            elif summary["history"] != history:
                raise ValueError(f"{path}: token history mismatch")
            state_segments.append({"layers": [s["layer"] for s in summary["layers"]],
                                   "description": summary["state"]})
            for layer in summary["layers"]:
                index = layer["layer"]
                if index in summary_rows:
                    raise ValueError(f"{path}: duplicate layer {index}")
                summary_rows[index] = layer
            if "head" in summary:
                if head is not None:
                    raise ValueError(f"{path}: duplicate terminal head")
                head = summary["head"]
        if set(summary_rows) != set(range(40)) or head is None:
            raise ValueError(f"context {context}: incomplete 40-layer golden token or missing head")
        with np.load(scratch / f"ctx{context}_head.npz", allow_pickle=False) as npz:
            logits = np.ascontiguousarray(np.asarray(npz["logits"], dtype=np.float32))
        if hashlib.sha256(logits.tobytes()).hexdigest() != head["logits_sha256"]:
            raise ValueError(f"context {context}: terminal logits digest mismatch")
        if int(np.argmax(logits)) != head["next_token"]:
            raise ValueError(f"context {context}: terminal argmax mismatch")
        previous_context = None
        for row in rows:
            original = summary_rows[row["layer"]]
            if (row["input_sha256"], row["output_sha256"]) != (
                    original["input_sha256"], original["output_sha256"]):
                raise ValueError(f"context {context} layer {row['layer']}: summary/shard mismatch")
            if previous_context is not None:
                incoming = original.get("ctx_in", {})
                if incoming.get("sel") != previous_context.get("sel"):
                    raise ValueError(f"context {context} layer {row['layer']}: index selection carry mismatch")
                candidate = previous_context.get("cand_file")
                if candidate is not None:
                    with np.load(scratch / candidate, allow_pickle=False) as npz:
                        cand = np.ascontiguousarray(np.asarray(npz["cand"], dtype=np.float32))
                    if hashlib.sha256(cand.tobytes()).hexdigest() != incoming.get("cand_sha256"):
                        raise ValueError(f"context {context} layer {row['layer']}: candidate carry mismatch")
                elif incoming.get("cand_sha256") is not None:
                    raise ValueError(f"context {context} layer {row['layer']}: unexpected candidate input")
            previous_context = original.get("ctx_out", {})
            if annotate_shards:
                path = scratch / f"ctx{context}_L{row['layer']:02d}.json"
                shard = json.loads(path.read_text())
                pins = {"token_history": history,
                        "checkpoint_index_sha256": checkpoint["index_sha256"],
                        "checkpoint_revision": checkpoint["revision"]}
                for key, value in pins.items():
                    if key in shard and shard[key] != value:
                        raise ValueError(f"{path}: existing {key} pin disagrees")
                shard.update(pins)
                path.write_text(json.dumps(shard, indent=1) + "\n")
        out["contexts"][str(context)] = {
            "position": context - 1, "token_history": history,
            "initial_state_segments": state_segments,
            "layer_count": len(rows), "layers": [{"layer": r["layer"], "input_sha256": r["input_sha256"],
                                                   "output_sha256": r["output_sha256"],
                                                   "arrays": r["arrays"]} for r in rows],
            "next_token": head["next_token"], "logits_sha256": head["logits_sha256"],
            "terminal_margin": head["margin"], "scratch_schema": "ctx{context}_L{layer:02d}.json/.npz",
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--contexts", default="200000,1048576")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--annotate-shards", action="store_true",
                        help="add token-history and checkpoint pins to each validated shard JSON")
    args = parser.parse_args()
    record = collect(args.scratch, [int(x) for x in args.contexts.split(",")], args.snapshot,
                     annotate_shards=args.annotate_shards)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": record["status"], "contexts": list(record["contexts"]),
                      "next_tokens": {k: v["next_token"] for k, v in record["contexts"].items()}}))


if __name__ == "__main__":
    main()
