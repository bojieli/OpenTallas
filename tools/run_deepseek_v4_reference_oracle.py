#!/usr/bin/env python3
"""Independent DeepSeek-V4-Flash-0731 greedy-decode oracle.

This is an *external comparator*, not part of the accelerator path.  It runs the
pinned checkpoint through the vendor modelling code to produce the token IDs a
faithful implementation should produce for each pinned workload, so that the
accelerator's own output can be checked against something it did not compute.

It is never used to produce accelerator tokens, never supplies an activation,
and its results are labelled as an external reference in every report.  ADR-003
section 18 permits exactly this use and forbids the other one.

Differences from ``run_qwen3_reference_oracle.py``, all forced by the model
-------------------------------------------------------------------------
*No Transformers path.*  There is no ``AutoModelForCausalLM`` for this
architecture, so the vendor's own ``inference/model.py`` and ``inference/
kernel.py`` are imported and driven directly by
``runtime.reference.deepseek_v4_oracle``, which materialises one block - and one
routed expert - at a time from the released shards.  The measured reasons and
the exact adaptations are recorded in the report under ``adaptations``.

*No chat template.*  ``tokenizer_config.json`` carries no ``chat_template``, so
prompts come from the pinned workload documents, which
``tools/build_deepseek_v4_workloads.py`` renders through the official
``encoding/encoding_dsv4.py`` wire format.

*Explicit greedy selection.*  The vendor's ``sample()`` defaults to Gumbel-max
(``probs.div_(torch.empty_like(probs).exponential_(1)).argmax(-1)``), which is
not reproducible.  This oracle selects by ``argmax`` over the float32 logits
with ties resolved to the lowest token id.  The vendor value is still computed
alongside - at ``temperature=0`` its own branch is also an argmax - and every
step's agreement or disagreement is recorded in ``vendor_sample_agreements`` /
``vendor_sample_disagreements``.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.frontend.deepseek_v4_tokenizer import (  # noqa: E402
    load_verified_deepseek_v4_tokenizer,
)
from runtime.abi3.capability import canonical_json  # noqa: E402
from runtime.reference.deepseek_v4_oracle import (  # noqa: E402
    ADAPTATIONS,
    DEFAULT_SNAPSHOT,
    OracleConfig,
    OracleError,
    StreamingDeepSeekV4,
)

SCHEMA = "opentallas.abi3.reference_oracle.v1"
MODEL_ID = "deepseek-v4-flash-0731"
EOS_TOKEN_ID = 1


def _round_up(value: int, multiple: int) -> int:
    return ((value + multiple - 1) // multiple) * multiple


def _host_memory() -> dict[str, int]:
    fields = {"MemTotal": 0, "MemAvailable": 0}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, _, rest = line.partition(":")
            if key in fields:
                fields[key] = int(rest.strip().split()[0]) * 1024
    except OSError:
        pass
    return {
        "host_total_bytes": fields["MemTotal"],
        "host_available_bytes": fields["MemAvailable"],
    }


def _host_footprint() -> dict[str, object]:
    """Separate the engine's own memory from mapped checkpoint pages.

    The shards are read through ``safetensors``' mmap, so every page the loader
    touches is charged to RSS even though it is clean, file-backed and evictable
    under pressure.  Peak RSS therefore approaches the size of the checkpoint
    and says nothing about what the engine actually needs; ``RssAnon`` is the
    number that does.
    """
    footprint: dict[str, object] = {
        "note": (
            "peak_rss_bytes counts clean file-backed pages of the mmapped "
            "checkpoint; anonymous_rss_bytes is the engine's own memory"
        )
    }
    try:
        import resource

        footprint["peak_rss_bytes"] = (
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        )
    except Exception:
        footprint["peak_rss_bytes"] = 0
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            key, _, rest = line.partition(":")
            if key in ("RssAnon", "RssFile", "VmRSS"):
                value = int(rest.strip().split()[0]) * 1024
                footprint[
                    {
                        "RssAnon": "anonymous_rss_bytes",
                        "RssFile": "file_backed_rss_bytes",
                        "VmRSS": "resident_bytes",
                    }[key]
                ] = value
    except OSError:
        pass
    return footprint


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--workloads",
        type=Path,
        default=REPO / "build" / "workloads" / "deepseek-v4-flash-0731",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "results" / "abi3" / "deepseek_v4_reference_oracle.json",
    )
    parser.add_argument("--only", action="append", default=None)
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=None,
        help="override the workload's own max_new_tokens (useful on the ladder)",
    )
    parser.add_argument(
        "--head-on-device",
        action="store_true",
        help=(
            "hold the 2.02 GiB float32 LM head in device memory; it stays on "
            "the host otherwise, because device memory here is shared with "
            "other tenants"
        ),
    )
    parser.add_argument(
        "--no-host-cache",
        action="store_true",
        help="do not retain block weights in host memory between steps",
    )
    parser.add_argument(
        "--engine-per-workload",
        action="store_true",
        help=(
            "rebuild the engine at each workload's own sequence length instead "
            "of sizing the KV caches once from the longest one; this is what "
            "the context ladder needs so a short rung is not charged for a "
            "long rung's caches"
        ),
    )
    parser.add_argument(
        "--time-budget-seconds",
        type=float,
        default=None,
        help="stop starting new workloads once this much wall time has elapsed",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1

    index_path = args.workloads / "index.json"
    if not index_path.exists():
        print(
            f"no workload index at {index_path}; run "
            f"tools/build_deepseek_v4_workloads.py first",
            file=sys.stderr,
        )
        return 1
    index = json.loads(index_path.read_text())

    selected = sorted(index["workloads"].items())
    if args.only:
        wanted = set(args.only)
        selected = [item for item in selected if item[0] in wanted]
        missing = wanted - {item[0] for item in selected}
        if missing:
            print(f"unknown workloads: {sorted(missing)}", file=sys.stderr)
            return 1
    if not selected:
        print("no workloads selected", file=sys.stderr)
        return 1

    bodies = {}
    for workload_id, entry in selected:
        bodies[workload_id] = json.loads(
            (args.workloads / entry["path"]).read_text()
        )

    if args.engine_per_workload:
        # Climb the ladder shortest first, so every rung that *can* run has
        # already been recorded by the time a longer one exhausts the device.
        selected.sort(key=lambda item: item[1]["prompt_token_count"])

    entries = dict(selected)

    def sequence_length_for(workload_ids: list[str]) -> int:
        longest = 0
        for workload_id in workload_ids:
            entry = entries[workload_id]
            new_tokens = args.max_new_tokens or entry["max_new_tokens"]
            longest = max(
                longest, len(bodies[workload_id]["token_ids"]) + new_tokens
            )
        return _round_up(longest, 128)

    # max_seq_len sizes the KV caches and the RoPE tables, so a run that mixes a
    # 1,000-token workload with a 200,000-token one would charge the small one
    # for the big one's caches.  --engine-per-workload rebuilds the engine at
    # each workload's own length, which is what the context ladder needs.
    if args.engine_per_workload:
        # Start at the first rung's own length rather than the tallest, which
        # may not be allocatable at all.
        max_seq_len = sequence_length_for([selected[0][0]])
    else:
        max_seq_len = sequence_length_for([wid for wid, _ in selected])

    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    import torch

    started_all = time.perf_counter()
    tokenizer = load_verified_deepseek_v4_tokenizer(args.snapshot)

    def build_engine(sequence_length: int):
        config = OracleConfig(
            snapshot=args.snapshot,
            max_seq_len=sequence_length,
            head_on_device=args.head_on_device,
            host_cache_dense=not args.no_host_cache,
        )
        print(
            f"building streaming engine (max_seq_len={sequence_length}) ...",
            flush=True,
        )
        built = StreamingDeepSeekV4(config)
        placement = built.load_endpoints()
        return built, placement

    engine, endpoints = build_engine(max_seq_len)
    setup_seconds = time.perf_counter() - started_all
    print(f"engine ready in {setup_seconds:.1f}s: {endpoints}", flush=True)

    report = {
        "schema": SCHEMA,
        "evidence_class": "external_reference_comparator",
        "not_a_claim": [
            "accelerator_execution",
            "artifact_only_execution",
            "timing_or_performance",
        ],
        "model_id": MODEL_ID,
        "snapshot": str(args.snapshot),
        "source": index.get("source", {}),
        "tokenizer_sha256": index["tokenizer_sha256"],
        "vendor_source_sha256": engine.vendor_digests,
        # Kept at the top level as well as inside "environment" so this report
        # has the same readable shape as the Qwen3 one.
        "torch_version": engine.torch.__version__,
        "dtype": "vendor mixed: FP8-E4M3 dense, MXFP4-E2M1 routed experts, "
        "bfloat16 activations, float32 norms/gating/hyper-connections/head",
        "selection": "greedy_lowest_token_id_argmax",
        "vendor_sample_note": (
            "model.sample() is not used for selection; its default path is "
            "Gumbel-max and is not reproducible. The vendor value is computed "
            "with temperature=0 and compared at every step."
        ),
        "device_map": (
            "single-GPU layer streaming from the released HF shards; "
            f"embed on {endpoints['embed_device']}, "
            f"lm_head on {endpoints['head_device']}"
        ),
        "max_seq_len": max_seq_len,
        "engine_per_workload": bool(args.engine_per_workload),
        "mandatory_context_tokens": index.get("mandatory_context_tokens"),
        "context_ladder": index.get("context_ladder"),
        "adaptations": [dict(item) for item in ADAPTATIONS],
        "head_split_verification": engine.head_split_evidence,
        "fp4_gemm_verification": engine.fp4_gemm_evidence,
        "expert_numeric_path": engine.expert_dtype,
        "environment": {
            **engine.environment(),
            **_host_memory(),
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "cpu_count": os.cpu_count(),
        },
        "setup_seconds": round(setup_seconds, 3),
        "results": {},
        "not_executed": {},
    }

    def flush() -> None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_json(report))

    flush()

    for workload_id, entry in selected:
        elapsed_all = time.perf_counter() - started_all
        if args.time_budget_seconds and elapsed_all > args.time_budget_seconds:
            report["not_executed"][workload_id] = {
                "kind": entry["kind"],
                "prompt_token_count": entry["prompt_token_count"],
                "reason": "time_budget_exhausted",
                "detail": (
                    f"{elapsed_all:.0f}s of a {args.time_budget_seconds:.0f}s "
                    "budget already spent before this workload started"
                ),
            }
            print(f"\n=== {workload_id}: skipped, time budget ===", flush=True)
            flush()
            continue

        body = bodies[workload_id]
        ids = body["token_ids"]
        new_tokens = args.max_new_tokens or entry["max_new_tokens"]
        print(
            f"\n=== {workload_id} ({entry['kind']}, {len(ids)} prompt tokens, "
            f"max_new={new_tokens}) ===",
            flush=True,
        )

        if args.engine_per_workload:
            own_length = sequence_length_for([workload_id])
            if own_length != engine.args.max_seq_len:
                del engine
                gc.collect()
                torch.cuda.empty_cache()
                try:
                    engine, endpoints = build_engine(own_length)
                except (OracleError, RuntimeError, MemoryError) as exc:
                    report["not_executed"][workload_id] = {
                        "kind": entry["kind"],
                        "prompt_token_count": entry["prompt_token_count"],
                        "reason": "engine_build_failed",
                        "detail": f"{type(exc).__name__}: {exc}"[:2000],
                        "requested_max_seq_len": own_length,
                    }
                    print(f"FAILED to build engine: {exc}"[:500], flush=True)
                    # The ladder is sorted ascending, so nothing above this
                    # rung can fit either; say so rather than leaving a gap.
                    position = [wid for wid, _ in selected].index(workload_id)
                    for taller_id, taller in selected[position + 1 :]:
                        report["not_executed"][taller_id] = {
                            "kind": taller["kind"],
                            "prompt_token_count": taller["prompt_token_count"],
                            "reason": "not_attempted",
                            "detail": (
                                f"a shorter rung ({workload_id}, "
                                f"{entry['prompt_token_count']} tokens) already "
                                "could not allocate its persistent state"
                            ),
                        }
                    flush()
                    break

        def progress(step: int, token_id: int, seconds: float) -> None:
            if step == 0 or (step + 1) % 16 == 0:
                print(
                    f"    step {step + 1}/{new_tokens} id={token_id} "
                    f"{seconds:.2f}s",
                    flush=True,
                )

        try:
            outcome = engine.greedy_generate(
                ids,
                max_new_tokens=new_tokens,
                eos_token_id=EOS_TOKEN_ID,
                progress=progress,
            )
        except (OracleError, RuntimeError, MemoryError) as exc:
            detail = f"{type(exc).__name__}: {exc}"
            report["not_executed"][workload_id] = {
                "kind": entry["kind"],
                "prompt_token_count": entry["prompt_token_count"],
                "reason": "execution_failed",
                "detail": detail[:2000],
                "device_free_bytes_at_failure": int(
                    engine.torch.cuda.mem_get_info()[0]
                ),
            }
            print(f"FAILED: {detail[:500]}", flush=True)
            engine.torch.cuda.empty_cache()
            flush()
            continue

        generated = outcome["generated_token_ids"]
        raw_text = tokenizer.decode(generated)
        visible = tokenizer.decode(generated, skip_special_tokens=True)

        report["results"][workload_id] = {
            "kind": entry["kind"],
            "workload_digest": entry["digest"],
            "prompt_token_count": len(ids),
            "generated_token_ids": generated,
            "generated_token_count": len(generated),
            "stop_reason": outcome["stop_reason"],
            "raw_decoded_text": raw_text,
            "visible_decoded_text": visible,
            "prefill_seconds": round(outcome["prefill_seconds"], 3),
            "decode_seconds_total": round(outcome["decode_seconds_total"], 3),
            "decode_seconds_per_token": (
                round(outcome["decode_seconds_per_token"], 4)
                if outcome["decode_seconds_per_token"] is not None
                else None
            ),
            "wall_seconds": round(
                outcome["prefill_seconds"] + outcome["decode_seconds_total"], 3
            ),
            "vendor_sample_agreements": outcome["vendor_sample_agreements"],
            "vendor_sample_disagreements": outcome["vendor_sample_disagreements"],
            "peak_device_bytes": int(outcome["peak_device_bytes"]),
            "max_seq_len": int(engine.args.max_seq_len),
            "expert_numeric_path": engine.expert_dtype,
            "checkpoint_bytes_read": int(engine.store.stats.bytes_read),
        }
        print(
            f"generated {len(generated)} tokens, stop={outcome['stop_reason']}, "
            f"prefill {outcome['prefill_seconds']:.1f}s, "
            f"decode {outcome['decode_seconds_total']:.1f}s"
        )
        print(f"first 24 ids: {generated[:24]}")
        print(f"text: {visible[:400]!r}", flush=True)
        flush()

    report["total_wall_seconds"] = round(time.perf_counter() - started_all, 3)
    report["host_footprint"] = _host_footprint()
    report["peak_device_bytes"] = int(engine.peak_device_bytes)
    report["checkpoint_bytes_read"] = int(engine.store.stats.bytes_read)
    report["host_weight_cache_bytes"] = int(engine.store.stats.host_cache_bytes)
    executed = report["results"]
    natural = [
        value["prompt_token_count"]
        for value in executed.values()
        if value["kind"] == "long_natural"
    ]
    report["largest_natural_context_executed"] = max(natural) if natural else 0
    flush()
    print(f"\nwrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
