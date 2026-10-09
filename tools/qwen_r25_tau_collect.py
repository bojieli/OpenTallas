#!/usr/bin/env python3
"""Validate full six-class shard coverage before composing the pre-registered tau.

Reads harvested snapshots only; it never changes a live run or publishes a model
rate. Legacy per-prompt ratios cannot establish exact pooled accepted/step counts.
"""
import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

KEY = "tau_bf16_S7_B4"
EXPECTED_PINS = {
    "target": "Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218",
    "draft": "deepseek-ai/dspark_qwen3_8b_block7@03326e5043815da1f81b109078b2889737c26017",
    "deepspec": "deepseek-ai/DeepSpec@005e03b81cec38b7da6399833d609ee89a2587f2",
    "tool_sha256": "37b8d3e1e9f06aa9798ce4332f84fb1daebbfbe786842b7c2eed4670a0068372",
    "compute_dtype": "float32", "max_new_tokens": 512, "device": "cpu",
    "prompts_sha256": "d95ec25641b4629d47c40c95ad9895673f97bbee7f4d45474bb3d8542a558ffd",
}
COUNTS = {"chat": 12, "reasoning": 24, "coding": 24,
          "agentic": 72, "assistant_fc": 48, "creative": 3}
SHARDS = {**{f"ag{i}": ("agentic", 12*i, 12) for i in range(6)},
          **{f"as{i}": ("assistant_fc", 12*i, 12) for i in range(4)},
          **{f"re{i}": ("reasoning", 12*i, 12) for i in range(2)},
          **{f"co{i}": ("coding", 12*i, 12) for i in range(2)},
          "ch0": ("chat", 0, 12), "cr0": ("creative", 0, 3)}
PIN_FIELDS = ("target", "draft", "deepspec", "tool_sha256", "compute_dtype",
              "max_new_tokens", "device")


def collect(directory):
    samples, pins, files, errors, missing = {}, None, [], [], []
    for shard, (cls, first, count) in SHARDS.items():
        path = Path(directory) / (shard + ".json")
        if not path.exists():
            missing.append(shard)
            continue
        data = path.read_bytes()
        files.append({"path": str(path), "sha256": hashlib.sha256(data).hexdigest()})
        try:
            record = json.loads(data)
            if record["schema"] != "opentallas.qwen-rom-dspark-tau.v1":
                raise ValueError("unexpected schema")
            these_pins = {k: record[k] for k in PIN_FIELDS}
            these_pins["prompts_sha256"] = record["prompts_jsonl"]["sha256"]
            these_pins["class_map"] = record["prompts_jsonl"]["class_map"]
            if any(these_pins[k] != v for k, v in EXPECTED_PINS.items()):
                raise ValueError("source differs from registered campaign")
            if pins is None:
                pins = these_pins
            if these_pins != pins:
                raise ValueError("source or execution pins differ across shards")
            for sample in record["samples"]:
                idx = sample["prompt_index"]
                if sample["class"] != cls or type(idx) is not int or not first <= idx < first+count:
                    raise ValueError("sample outside registered shard interval")
                identity = (cls, idx)
                if identity in samples:
                    raise ValueError("duplicate sample identity")
                tau = sample[KEY]
                if type(tau) not in (int, float) or not math.isfinite(tau) or not 1 <= tau <= 4:
                    raise ValueError("invalid primary tau")
                if sample["fast_path_equals_reference_at_first_step"] is not True:
                    raise ValueError("released drafter first-step reference disagrees")
                samples[identity] = sample
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{shard}: {exc}")
    classes = {}
    for cls, count in COUNTS.items():
        rows = [v for (c, _), v in samples.items() if c == cls]
        complete = {i for (c, i) in samples if c == cls} == set(range(count))
        median = statistics.median(r[KEY] for r in rows) if rows else None
        classes[cls] = {"samples": len(rows), "expected": count, "complete": complete,
                        "median": median, "pooled_tau": None,
                        "pooled_reason": "legacy run does not record accepted-token and replay-step counts"}
    complete = not errors and all(c["complete"] for c in classes.values())
    medians = [c["median"] for c in classes.values()]
    return {"schema": "opentallas.qwen-r25-tau-blend.v1",
            "status": "COMPLETE_CHARACTERIZATION" if complete else "INCOMPLETE",
            "primary_key": KEY, "source_pins": pins, "files": files,
            "errors": errors, "missing_shards": missing, "classes": classes,
            "blend_owner6": statistics.harmonic_mean(medians) if complete else None,
            "envelope": [min(medians), max(medians)] if complete else None,
            "deployment_qualified": False,
            "limitations": ["FP32-upcast released BF16 target, not the r25 INT8 target",
                            "drafter reference comparison covers the first step of each prompt only",
                            "quality and RTL accept/rollback gates remain separate"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("output exists; use a new snapshot path to preserve earlier evidence")
    result = collect(args.directory)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "blend_owner6", "errors", "missing_shards")}))


if __name__ == "__main__":
    main()
