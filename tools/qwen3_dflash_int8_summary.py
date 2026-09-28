#!/usr/bin/env python3
"""Summarize bounded Qwen DFlash INT8 acceptance against paired BF16 prompts."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def measure(rows):
    tokens = sum(r["tokens"] - 1 for r in rows)
    cycles = sum(r["cycles"] for r in rows)
    ref_cycles = sum((r["tokens"] - 1) / r["bf16_prefix_tau"] for r in rows)
    return {"post_prefill_tokens": tokens, "int8_verify_cycles": cycles,
            "bf16_verify_cycles_at_matched_output_length": int(round(ref_cycles)),
            "int8_tau": tokens / cycles, "bf16_prefix_tau": tokens / ref_cycles,
            "int8_over_bf16_tau": ref_cycles / cycles}


def summarize(raw, source_path, seed=42, reps=10000):
    rows = raw["rows"]
    if not rows or any(r["greedy_mismatches"] for r in rows):
        raise ValueError("empty or non-greedy INT8 acceptance record")
    if any(r["bf16_prefix_tau"] is None for r in rows):
        raise ValueError("BF16 reference lacks a matched output-length prefix")
    if any(sum(r["acceptance_lengths"]) != r["tokens"] - 1 or
           len(r["acceptance_lengths"]) != r["cycles"] for r in rows):
        raise ValueError("acceptance cycles do not account for every output token")
    by = defaultdict(list)
    for r in rows:
        by[r["workload"]].append(r)
    rng = np.random.default_rng(seed)
    boots = []
    names = sorted(by)
    for _ in range(reps):
        sample = []
        for w in names:
            items = by[w]
            sample.extend(items[int(i)] for i in rng.integers(0, len(items), len(items)))
        m = measure(sample)
        boots.append((m["int8_tau"], m["int8_over_bf16_tau"]))
    boots = np.array(boots)
    draft_w8 = raw.get("draft_weights") == "w8"
    tp2_target = bool(raw.get("tp2_target"))
    scope = ("Bounded greedy acceptance of a signed-INT8/FP8 " +
             ("TP-2" if tp2_target else "single-core") + " target with a " +
             ("per-row INT8" if draft_w8 else "released BF16") +
             " drafter. Not a routed RTL throughput or nine-workload production tau.")
    result = {"schema": "opentallas.qwen3-dflash-int8-acceptance-summary.v1",
              "summary_tool_sha256": sha(__file__),
              "source_record": str(source_path), "source_record_sha256": sha(source_path),
              "scope": scope,
              "measurement": measure(rows),
              "ci95_prompt_bootstrap_stratified_by_workload": {
                  "seed": seed, "replicates": reps,
                  "int8_tau": np.quantile(boots[:, 0], [0.025, 0.975]).tolist(),
                  "int8_over_bf16_tau": np.quantile(boots[:, 1], [0.025, 0.975]).tolist()},
              "sample": {"prompts": len(rows), "workloads": dict(sorted(Counter(r["workload"] for r in rows).items())),
                         "max_new_tokens": raw["max_new"], "block": raw["block"]},
              "limitations": [
                  "The paired BF16 reference is the prefix of a 2048-token BF16 run on the same prompts; target arithmetic can change the later greedy trajectory.",
                  "DFlash's released block-16 drafter runs at block 5 outside its training distribution.",
                  ("The INT8 drafter follows the released separate q/k/v and context K/V calls, with per-linear K-splits and BF16 output boundaries; its non-matrix operations are the released BF16 implementation. A matching TP-2 drafter program and RTL timing gate are pending."
                   if draft_w8 else "The released BF16 drafter is not the O4 INT8 drafter; this run isolates target arithmetic only."),
                  "The prompt subset excludes the longest agentic contexts and does not support replacing the nine-workload production tau."]}
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    Path(args.output).write_text(json.dumps(summarize(json.loads(Path(args.input).read_text()), args.input), indent=1) + "\n")


if __name__ == "__main__":
    main()
