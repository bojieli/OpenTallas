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
import math
import os
import platform
import sys
import time
import traceback
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
    import_vendor,
)

sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

import deepseek_v4_prefill_tiling as tiling  # noqa: E402
from opentallas.schema import ModelProfile  # noqa: E402
from opentallas.workload import kv_traffic, rho_one, weight_traffic  # noqa: E402

SCHEMA = "opentallas.abi3.reference_oracle.v1"
MODEL_ID = "deepseek-v4-flash-0731"
EOS_TOKEN_ID = 1

#: Recorded in ``adaptations`` whenever a rung actually used the tiled prefill,
#: in the same shape as the adaptations the engine itself declares.
PREFILL_TILING_ADAPTATION = {
    "id": "prefill_sequence_tiling",
    "vendor_symbol": (
        "model.Indexer.forward / model.Block.hc_pre / model.Block.hc_post / "
        "model.Attention.forward / model.Compressor.forward / model.MoE.forward"
    ),
    "reason": (
        "the vendor prefills a prompt in one call and three of its "
        "intermediates are quadratic in prompt length: Indexer.index_score is "
        "[b, s, 64, s/4] (1.28 TB of bfloat16 at s=200000, per sparse layer), "
        "hc_post's outer product is [b, s, 4, 4, 4096] float32 (52.5 GB) and "
        "hc_pre's float32 cast is [b, s, 16384] (13.1 GB). No single GPU runs "
        "that; the 32k, 128k and 200k rungs had already failed on it with CUDA "
        "out-of-memory, and would fail on an otherwise empty 95 GiB device too"
    ),
    "change": (
        "the same expressions are evaluated over slices of the query axis and "
        "written into one preallocated output, instead of over the whole "
        "sequence at once; tile lengths come from byte budgets, not from the "
        "context. Nothing is skipped, reordered across a reduction, or "
        "recomputed at a different width: every reduction the vendor performs "
        "(over heads, over the compressor's pooling window, over K in each "
        "GEMM) is still performed in one piece"
    ),
    "fidelity": (
        "each tiled intermediate is a per-query quantity, so a query slice of "
        "it holds the values the untiled tensor would have held; this is "
        "checked end to end rather than argued, by re-running the two rungs "
        "that already executed untiled and requiring identical token ids - see "
        "prefill_tiling_verification"
    ),
}


#: What the engine's own caches cost per entry: the main KV cache is bfloat16
#: [head_dim=512] and the indexer's is bfloat16 [index_head_dim=128].  What the
#: *profile* charges per entry is read from the profile, never restated here -
#: it has already been wrong once (583/68, corrected to 1024/256 against these
#: measurements), and a hardcoded copy would have gone on being wrong silently.
ENGINE_MAIN_ENTRY_BYTES = 512 * 2
ENGINE_INDEX_ENTRY_BYTES = 128 * 2

#: Maps the kind recorded per layer to the profile group label it belongs to.
KIND_TO_LABEL = {"window": "window", "csa": "csa", "hca": "hca-128"}


def _profile_entry_widths(profile) -> dict[str, dict[str, float]]:  # noqa: ANN001
    """The bytes the profile charges per entry, per attention group."""
    widths: dict[str, dict[str, float]] = {}
    for group in profile.attention_groups:
        label = group.label or group.kind
        widths[label] = {
            "entry_bytes": float(group.entry_bytes),
            "index_entry_bytes": float(group.index_entry_bytes),
        }
    return widths


def _normalised_bytes(per_layer, widths) -> float:  # noqa: ANN001
    """The engine's own entry counts, priced at the profile's entry widths.

    This separates "did the engine read the right *entries*" from "does the
    profile charge the right number of bytes for one". Both matter and they
    fail differently: the first is a structural error in the traffic model, the
    second is a constant.
    """
    total = 0.0
    for entry in per_layer.values():
        label = KIND_TO_LABEL.get(entry["kind"], entry["kind"])
        width = widths.get(label)
        if width is None:
            continue
        total += entry["main_pairs"] * width["entry_bytes"]
        total += entry["index_pairs"] * width["index_entry_bytes"]
    return total


def _round_up(value: int, multiple: int) -> int:
    return ((value + multiple - 1) // multiple) * multiple


def _predicted_decode(profile, context_tokens: int) -> dict[str, float]:  # noqa: ANN001
    """The profile's own decode-step KV prediction, in entries and in bytes.

    Read off ``kv_traffic``'s breakdown rather than restated here, so a change
    to the profile cannot silently pass the comparison.
    """
    traffic = kv_traffic(profile, context_tokens)
    main_entries = 0.0
    index_entries = 0.0
    for detail in traffic.breakdown:
        layers = float(detail["layers"])
        if "entries_read_per_layer" in detail:
            main_entries += layers * float(detail["entries_read_per_layer"])
        if "main_entries_read_per_layer" in detail:
            main_entries += layers * float(detail["main_entries_read_per_layer"])
        if "index_entries_scanned_per_layer" in detail:
            index_entries += layers * float(detail["index_entries_scanned_per_layer"])
    return {
        "context_tokens": context_tokens,
        "main_entries": main_entries,
        "index_entries": index_entries,
        "read_bytes": traffic.read_bytes,
        "storage_bytes_per_user": traffic.storage_bytes_per_user,
        "bytes_per_layer_position": (
            traffic.read_bytes / (profile.num_layers * context_tokens)
        ),
        "weight_to_kv_read_ratio": rho_one(profile, context_tokens),
        "breakdown": [dict(detail) for detail in traffic.breakdown],
    }


def _compare_kv(profile, phases, prompt_tokens: int) -> dict[str, object]:  # noqa: ANN001
    """Join the measured counters to the analytical model, rung by rung.

    Two checks, following ``tools/validate_model_against_execution.py``: the
    (layer, position) pair count, and the bytes one layer reads for one context
    position.  The first is where a *sparse* model differs from that tool's
    causal triangle -- DeepSeek-V4-Flash is not supposed to visit the triangle,
    and the profile's compressed/sparse groups say how much of it it should
    visit instead.  The second is where the storage format shows up.
    """
    if not phases:
        return {}
    prefill = phases[0]
    decode = [phase for phase in phases[1:] if phase.main_pairs]
    widths = _profile_entry_widths(profile)
    steps = []
    for index, phase in enumerate(decode, start=1):
        context = prompt_tokens + index
        predicted = _predicted_decode(profile, context)
        measured_bytes = phase.main_bytes + phase.index_bytes
        normalised = _normalised_bytes(phase.per_layer, widths)
        steps.append(
            {
                "step": index,
                "context_tokens": context,
                "measured": {
                    "main_context_positions": phase.main_pairs,
                    "index_context_positions": phase.index_pairs,
                    "main_kv_bytes_read": phase.main_bytes,
                    "index_kv_bytes_read": phase.index_bytes,
                    "total_kv_bytes_read": measured_bytes,
                    "bytes_per_layer_position": (
                        measured_bytes / (profile.num_layers * context)
                    ),
                    "engine_main_entry_bytes": ENGINE_MAIN_ENTRY_BYTES,
                    "engine_index_entry_bytes": ENGINE_INDEX_ENTRY_BYTES,
                },
                "predicted": {
                    "main_context_positions": predicted["main_entries"],
                    "index_context_positions": predicted["index_entries"],
                    "read_bytes": predicted["read_bytes"],
                    "bytes_per_layer_position": predicted["bytes_per_layer_position"],
                    "profile_entry_widths": widths,
                    "weight_to_kv_read_ratio": predicted["weight_to_kv_read_ratio"],
                    "bytes_priced_at_profile_widths": normalised,
                },
                "ratios": {
                    "main_position_ratio": (
                        phase.main_pairs / predicted["main_entries"]
                        if predicted["main_entries"]
                        else None
                    ),
                    "index_position_ratio": (
                        phase.index_pairs / predicted["index_entries"]
                        if predicted["index_entries"]
                        else None
                    ),
                    "raw_byte_ratio": (
                        measured_bytes / predicted["read_bytes"]
                        if predicted["read_bytes"]
                        else None
                    ),
                    "format_normalised_byte_ratio": (
                        normalised / predicted["read_bytes"]
                        if predicted["read_bytes"]
                        else None
                    ),
                },
                "sparsity": {
                    "selected_compressed_positions_per_query": (
                        phase.selected_per_query
                    ),
                    "candidate_compressed_positions_per_query": (
                        phase.candidates_per_query
                    ),
                    "full_context_positions": context,
                    "fraction_of_context_read_per_layer": {
                        str(layer): (
                            entry["main_pairs"] + entry["index_pairs"]
                        )
                        / context
                        for layer, entry in sorted(phase.per_layer.items())
                    },
                },
                "per_layer": {
                    str(layer): entry
                    for layer, entry in sorted(phase.per_layer.items())
                },
            }
        )
    representative = steps[0] if steps else None
    return {
        "note": (
            "measured counts come from the sparse-attention kernel's own "
            "topk_idxs (a -1 entry is a masked slot nobody reads) and from the "
            "indexer's scan width; predicted counts come from "
            "src/opentallas/workload.py::kv_traffic on "
            "configs/models/deepseek-v4-flash-0731.json"
        ),
        "profile_entry_widths": widths,
        "profile_path_note": (
            "predicted values come from configs/models/deepseek-v4-flash-0731.json "
            "as it stood when this rung ran; the entry widths it charged are "
            "recorded above so the comparison can be re-derived"
        ),
        "format_note": (
            "the reference engine holds both caches in bfloat16 (1024 B main, "
            "256 B index per entry) while the profile charges the published "
            "serving recipe (583 B main, 68 B index). raw_byte_ratio therefore "
            "carries that format factor; format_normalised_byte_ratio applies "
            "the profile's own widths to the engine's own entry counts and is "
            "the number that tests the traffic model"
        ),
        "prefill": {
            "main_context_positions": prefill.main_pairs,
            "index_context_positions": prefill.index_pairs,
            "main_kv_bytes_read": prefill.main_bytes,
            "index_kv_bytes_read": prefill.index_bytes,
            "queries": prefill.queries,
            "causal_triangle_pairs_all_layers": (
                profile.num_layers * prompt_tokens * (prompt_tokens + 1) // 2
            ),
            "fraction_of_causal_triangle": (
                (prefill.main_pairs + prefill.index_pairs)
                / (profile.num_layers * prompt_tokens * (prompt_tokens + 1) / 2)
                if prompt_tokens
                else None
            ),
            "note": (
                "a dense causal model would visit the whole triangle; this "
                "model is sparse and the fraction is the measure of it"
            ),
        },
        "decode_steps": steps,
        "representative_decode_step": representative,
    }


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


def _run_equivalence(
    args, report, engine, build_engine, sequence_length_for,
    selected, bodies, tiling_config, flush, note,
):  # noqa: ANN001
    """Prefill each workload through both bodies and measure the distance.

    The tiled bodies are switched off by raising their own floor, so both
    passes run in one process, against one set of weights, on one engine: the
    only thing that changes between them is how many pieces the sequence is
    evaluated in.  A second prefill from ``start_pos = 0`` rewrites exactly the
    cache and compressor state the first one wrote, and the compressor state
    buffers are reset to their constructed values in between regardless.
    """
    import torch

    tiled_floor = tiling_config.floor
    findings = {}
    for workload_id, entry in selected:
        ids = bodies[workload_id]["token_ids"]
        length = sequence_length_for([workload_id])
        if length != engine.args.max_seq_len:
            engine, _ = build_engine(length)
        prompt = torch.tensor([ids], dtype=torch.long, device=engine.device)
        rows = {}
        # Three passes, not two.  The second untiled pass is the control: a
        # tiling difference only means something measured against how far this
        # model moves when nothing at all is changed.
        for mode, floor in (
            ("untiled", 1 << 30),
            ("untiled_repeat", 1 << 30),
            ("tiled", tiled_floor),
        ):
            tiling_config.floor = floor
            for layer in engine.model.layers:
                if layer.attn.compress_ratio:
                    engine._reset_compressor(layer.attn.compressor)
                    if layer.attn.indexer is not None:
                        engine._reset_compressor(layer.attn.indexer.compressor)
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
            started = time.perf_counter()
            with torch.inference_mode():
                _, logits, _ = engine.forward(prompt, 0)
            torch.cuda.synchronize()
            rows[mode] = {
                "logits": logits[0].float().cpu(),
                "seconds": time.perf_counter() - started,
                "peak_device_bytes": int(torch.cuda.max_memory_allocated()),
            }
            note(
                f"{workload_id} {mode}: prefill {rows[mode]['seconds']:.1f}s "
                f"peak {rows[mode]['peak_device_bytes'] / 2**30:.2f} GiB"
            )
        tiling_config.floor = tiled_floor
        a, b = rows["untiled"]["logits"], rows["tiled"]["logits"]
        control = rows["untiled_repeat"]["logits"]
        delta = (a - b).abs()
        control_delta = (a - control).abs()
        order_a = a.argsort(descending=True)
        order_b = b.argsort(descending=True)
        order_c = control.argsort(descending=True)
        top1_a, top2_a = int(order_a[0]), int(order_a[1])
        margin_a = float(a[top1_a] - a[top2_a])
        findings[workload_id] = {
            "control_untiled_vs_untiled": {
                "note": (
                    "the same body, the same weights, the same input, run "
                    "twice: anything non-zero here is the engine's own "
                    "run-to-run variation and is the floor under every other "
                    "number in this record"
                ),
                "bitwise_identical": bool(a.equal(control)),
                "max_abs_logit_difference": float(control_delta.max()),
                "mean_abs_logit_difference": float(control_delta.mean()),
                "greedy_token": int(order_c[0]),
                "greedy_token_agrees": top1_a == int(order_c[0]),
            },
            "prompt_token_count": len(ids),
            "sequence_tile": tiling_config.seq_tile,
            "tiles_over_sequence": math.ceil(len(ids) / tiling_config.seq_tile),
            "greedy_token_untiled": top1_a,
            "greedy_token_tiled": int(order_b[0]),
            "greedy_token_agrees": top1_a == int(order_b[0]),
            "top1_minus_top2_untiled": margin_a,
            "max_abs_logit_difference": float(delta.max()),
            "mean_abs_logit_difference": float(delta.mean()),
            "max_abs_logit_value": float(a.abs().max()),
            "relative_max_difference": float(delta.max() / a.abs().max()),
            "difference_over_greedy_margin": (
                float(delta.max() / margin_a) if margin_a else None
            ),
            "tiling_difference_over_control_difference": (
                float(delta.max() / control_delta.max())
                if float(control_delta.max()) > 0
                else None
            ),
            "untiled_prefill_seconds": round(rows["untiled"]["seconds"], 3),
            "untiled_repeat_prefill_seconds": round(
                rows["untiled_repeat"]["seconds"], 3
            ),
            "tiled_prefill_seconds": round(rows["tiled"]["seconds"], 3),
            "untiled_peak_device_bytes": rows["untiled"]["peak_device_bytes"],
            "tiled_peak_device_bytes": rows["tiled"]["peak_device_bytes"],
            "device_bytes_saved": (
                rows["untiled"]["peak_device_bytes"]
                - rows["tiled"]["peak_device_bytes"]
            ),
        }
        note(f"{workload_id} equivalence: {findings[workload_id]}")
    report["results"] = {}
    report["tiling_equivalence"] = {
        "note": (
            "one engine, one set of weights, one process; the only difference "
            "between the two passes is how many pieces the sequence is "
            "evaluated in"
        ),
        "workloads": findings,
    }
    flush()
    return 0


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
    parser.add_argument(
        "--tile-prefill",
        action="store_true",
        help=(
            "evaluate the quadratic prefill intermediates a query slice at a "
            "time; required above about 24k tokens on any single GPU"
        ),
    )
    parser.add_argument(
        "--tiling-floor",
        type=int,
        default=4096,
        help=(
            "prompts at or below this length run the vendor bodies untouched "
            "even with --tile-prefill; set below a completed rung's length to "
            "re-run that rung through the tiled path as an equivalence check"
        ),
    )
    parser.add_argument("--seq-tile", type=int, default=2048)
    parser.add_argument(
        "--index-tile",
        type=int,
        default=0,
        help=(
            "fix the indexer sub-tile at this many rows for every rung "
            "instead of deriving it from --index-score-budget-mib; a byte "
            "budget gives a different row count at every context, and a "
            "GEMM's result depends on its row count"
        ),
    )
    parser.add_argument("--expert-rows", type=int, default=1 << 15)
    parser.add_argument("--compressor-positions", type=int, default=1 << 14)
    parser.add_argument(
        "--host-residual",
        action="store_true",
        help=(
            "hold the hyper-connection residual ([1, s, 4, 4096] bfloat16, "
            "6.1 GiB at 200k) in pinned host memory; only hc_pre and hc_post "
            "read it and both are per-position, so it is staged one tile at a "
            "time"
        ),
    )
    parser.add_argument(
        "--index-score-budget-mib",
        type=int,
        default=1024,
        help="ceiling for the indexer's [tile, heads, context/4] score block",
    )
    parser.add_argument(
        "--hc-budget-mib",
        type=int,
        default=768,
        help="ceiling for hc_post's [tile, hc, hc, dim] float32 block",
    )
    parser.add_argument(
        "--measure-kv",
        action="store_true",
        help=(
            "count the (layer, position) pairs attention visited and the KV "
            "bytes they are, and compare against the analytical profile"
        ),
    )
    parser.add_argument(
        "--model-profile",
        type=Path,
        default=REPO / "configs" / "models" / "deepseek-v4-flash-0731.json",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help=(
            "merge into an existing report rather than starting a new one: "
            "results already present are preserved with their recorded "
            "digests, and only the workloads run now are replaced"
        ),
    )
    parser.add_argument(
        "--progress-log",
        type=Path,
        default=None,
        help="append a timestamped line per decode step and per rung here",
    )
    parser.add_argument(
        "--tiling-equivalence",
        action="store_true",
        help=(
            "instead of generating, prefill each selected workload twice in "
            "one process -- once through the vendor bodies and once through "
            "the tiled ones -- and report the distance between the two logit "
            "vectors and whether the greedy choice moves"
        ),
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not (args.force or args.append):
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1

    prior: dict[str, object] = {}
    if args.append:
        if not args.output.exists():
            print(f"--append needs an existing {args.output}", file=sys.stderr)
            return 1
        prior = json.loads(args.output.read_text())

    def note(message: str) -> None:
        stamped = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {message}"
        print(stamped, flush=True)
        if args.progress_log:
            args.progress_log.parent.mkdir(parents=True, exist_ok=True)
            with args.progress_log.open("a") as handle:
                handle.write(stamped + "\n")

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

    # The tiled bodies have to be on the vendor classes *before* the engine is
    # constructed: the engine stashes the Block and Expert forwards it finds and
    # wraps those with weight residency, so installing afterwards would either
    # bypass residency or wrap it twice.
    tiling_config = tiling.TilingConfig(
        seq_tile=args.seq_tile,
        index_score_bytes=args.index_score_budget_mib << 20,
        hc_bytes=args.hc_budget_mib << 20,
        floor=args.tiling_floor,
        host_residual=args.host_residual,
        index_tile_rows=args.index_tile,
        expert_rows=args.expert_rows,
        compressor_positions=args.compressor_positions,
    )
    vendor_model_mod = None
    if args.tile_prefill or args.measure_kv:
        vendor_model_mod, _, _, _ = import_vendor(args.snapshot)
    if args.tile_prefill:
        tiling.install(vendor_model_mod, tiling_config)
        note(
            f"prefill tiling installed (seq_tile={tiling_config.seq_tile}, "
            f"index_score<={args.index_score_budget_mib} MiB, "
            f"hc<={args.hc_budget_mib} MiB, floor={tiling_config.floor})"
        )
    if args.measure_kv:
        tiling.instrument_decode(vendor_model_mod)
        tiling.COUNTERS.enabled = True

    profile = None
    if args.measure_kv:
        profile = ModelProfile.load(args.model_profile)

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
        # The length the first engine was built at.  Under
        # --engine-per-workload every result carries its own "max_seq_len",
        # because the engine is rebuilt at each workload's own length.
        "initial_max_seq_len": max_seq_len,
        "engine_per_workload": bool(args.engine_per_workload),
        "mandatory_context_tokens": index.get("mandatory_context_tokens"),
        "context_ladder": index.get("context_ladder"),
        "adaptations": [dict(item) for item in ADAPTATIONS]
        + ([dict(PREFILL_TILING_ADAPTATION)] if args.tile_prefill else []),
        "head_split_verification": engine.head_split_evidence,
        "fp4_gemm_verification": engine.fp4_gemm_evidence,
        "expert_numeric_path": engine.expert_dtype,
        "prefill_tiling": (
            {
                "enabled": True,
                "sequence_tile": tiling_config.seq_tile,
                "index_score_budget_bytes": tiling_config.index_score_bytes,
                "hyper_connection_budget_bytes": tiling_config.hc_bytes,
                "compressor_positions_per_tile": tiling_config.compressor_positions,
                "expert_rows_per_tile": tiling_config.expert_rows,
                "untiled_floor_tokens": tiling_config.floor,
                "hyper_connection_residual_on_host": tiling_config.host_residual,
                "index_tile_rows_fixed": tiling_config.index_tile_rows,
                "rope_table_sharing": tiling.deduplicate_freqs_cis(
                    engine.model, engine.torch
                ),
            }
            if args.tile_prefill
            else {"enabled": False}
        ),
        "kv_measurement_enabled": bool(args.measure_kv),
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

    # With --engine-per-workload each engine keeps its own counters, so the
    # session totals have to be accumulated as engines are retired rather than
    # read off whichever one happens to be alive at the end.
    session = {"peak_device_bytes": 0, "bytes_read": 0, "host_cache_bytes": 0}

    def absorb(built) -> None:  # noqa: ANN001
        if built is None:
            return
        session["peak_device_bytes"] = max(
            session["peak_device_bytes"], int(built.peak_device_bytes)
        )
        session["bytes_read"] += int(built.store.stats.bytes_read)
        session["host_cache_bytes"] = max(
            session["host_cache_bytes"], int(built.store.stats.host_cache_bytes)
        )

    if prior:
        # Rungs that already ran keep their recorded result and digest; this
        # session only adds what it actually executed.  Their prior
        # not_executed entries are dropped for whatever runs now, and kept
        # otherwise, so the artifact never claims a rung both ran and did not.
        carried_results = dict(prior.get("results", {}))
        carried_not_executed = dict(prior.get("not_executed", {}))
        running = {workload_id for workload_id, _ in selected}
        report["results"] = {
            key: value
            for key, value in carried_results.items()
            if key not in running
        }
        report["not_executed"] = {
            key: value
            for key, value in carried_not_executed.items()
            if key not in running
        }
        report["superseded"] = {
            "prior_report_written_over": str(args.output),
            "prior_results_preserved": sorted(report["results"]),
            "prior_not_executed_preserved": sorted(report["not_executed"]),
            "rerun_in_this_session": sorted(running),
            "note": (
                "results carried over were produced by an earlier session of "
                "this same tool; their generated_token_ids and workload_digest "
                "are unchanged"
            ),
        }
        for key in (
            "prefill_tiling_verification",
            "untiled_prefill_arithmetic",
        ):
            if key in prior:
                report[key] = prior[key]

    def flush() -> None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_json(report))

    flush()

    if args.tiling_equivalence:
        return _run_equivalence(
            args, report, engine, build_engine, sequence_length_for,
            selected, bodies, tiling_config, flush, note,
        )

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
        note(f"starting {workload_id} ({len(ids)} prompt tokens)")

        if args.engine_per_workload:
            own_length = sequence_length_for([workload_id])
            if own_length != engine.args.max_seq_len:
                absorb(engine)
                engine = None
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
            if step == 0 or (step + 1) % 8 == 0 or new_tokens <= 16:
                free_bytes = int(engine.torch.cuda.mem_get_info()[0])
                note(
                    f"  {workload_id} step {step + 1}/{new_tokens} "
                    f"id={token_id} {seconds:.2f}s "
                    f"peak={engine.generation_peak_device_bytes / 2**30:.2f} GiB "
                    f"free={free_bytes / 2**30:.2f} GiB"
                )
            if args.measure_kv:
                tiling.COUNTERS.start_phase()

        if args.measure_kv:
            tiling.COUNTERS.phases.clear()
            tiling.COUNTERS.start_phase()

        rung_started = time.perf_counter()
        try:
            outcome = engine.greedy_generate(
                ids,
                max_new_tokens=new_tokens,
                eos_token_id=EOS_TOKEN_ID,
                progress=progress,
            )
        except (OracleError, RuntimeError, MemoryError) as exc:
            detail = f"{type(exc).__name__}: {exc}"
            # Which line asked for the memory matters as much as how much:
            # "it stopped here" is the answer the ladder exists to produce.
            frames = traceback.extract_tb(exc.__traceback__)
            report["not_executed"][workload_id] = {
                "kind": entry["kind"],
                "prompt_token_count": entry["prompt_token_count"],
                "reason": "execution_failed",
                "detail": detail[:2000],
                "failed_at": [
                    f"{frame.filename}:{frame.lineno} {frame.name}: {frame.line}"
                    for frame in frames[-6:]
                ],
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
            "rung_wall_seconds": round(time.perf_counter() - rung_started, 3),
            "prefill_tiled": bool(
                args.tile_prefill and len(ids) > tiling_config.floor
            ),
            "tile_geometry": (
                {
                    "sequence_tile": tiling_config.seq_tile,
                    "sequence_tiles": math.ceil(len(ids) / tiling_config.seq_tile),
                    "hyper_connection_tile": tiling_config.hc_tile(4, 4096),
                    "indexer_sub_tile": tiling_config.index_tile(64, len(ids) // 4),
                    "indexer_score_block_bytes": (
                        tiling_config.index_score_block_bytes(64, len(ids) // 4)
                    ),
                    "compressor_positions_per_tile": (
                        tiling_config.compressor_positions
                    ),
                    "expert_rows_per_tile": tiling_config.expert_rows,
                    "hyper_connection_residual_on_host": (
                        tiling_config.host_residual
                    ),
                }
                if (args.tile_prefill and len(ids) > tiling_config.floor)
                else None
            ),
            "host_footprint_after_rung": _host_footprint(),
            "device_free_bytes_after_rung": int(engine.torch.cuda.mem_get_info()[0]),
        }
        if args.measure_kv and profile is not None:
            report["results"][workload_id]["kv_measurement"] = _compare_kv(
                profile, tiling.COUNTERS.phases, len(ids)
            )
        if args.tile_prefill and len(ids) > tiling_config.floor:
            report["results"][workload_id]["untiled_prefill_arithmetic"] = (
                tiling.untiled_peak_bytes(len(ids))
            )
        report["results"][workload_id]["irreducible_resident_arithmetic"] = (
            tiling.projected_resident_bytes(len(ids))
        )
        note(
            f"{workload_id}: {len(generated)} tokens, "
            f"stop={outcome['stop_reason']}, "
            f"prefill {outcome['prefill_seconds']:.1f}s, "
            f"decode {outcome['decode_seconds_total']:.1f}s, "
            f"peak {outcome['peak_device_bytes'] / 2**30:.2f} GiB"
        )
        note(f"{workload_id} ids: {generated[:24]}")
        note(f"{workload_id} text: {visible[:400]!r}")
        if args.measure_kv:
            measurement = report["results"][workload_id].get("kv_measurement", {})
            step = measurement.get("representative_decode_step")
            if step:
                note(
                    f"{workload_id} KV: measured "
                    f"{step['measured']['total_kv_bytes_read']:,} B/step over "
                    f"{step['measured']['main_context_positions']:,} main + "
                    f"{step['measured']['index_context_positions']:,} index "
                    f"(layer, position) pairs; profile predicts "
                    f"{step['predicted']['read_bytes']:,.0f} B; "
                    f"position ratio "
                    f"{step['ratios']['main_position_ratio']:.4f}, "
                    f"format-normalised byte ratio "
                    f"{step['ratios']['format_normalised_byte_ratio']:.4f}"
                )
        flush()

    absorb(engine)
    report["total_wall_seconds"] = round(time.perf_counter() - started_all, 3)
    report["host_footprint"] = _host_footprint()
    report["peak_device_bytes"] = session["peak_device_bytes"]
    report["checkpoint_bytes_read"] = session["bytes_read"]
    report["host_weight_cache_bytes"] = session["host_cache_bytes"]
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
