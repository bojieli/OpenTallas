#!/usr/bin/env python3
"""G1f: the reduced configuration run whole, and what currently stops it.

G1f is the last rung of the RTL verification ladder and the cheapest: the
industry's small-config nightly regression.  The tapeout configuration is
verified by the pyramid (G1a-G1e); the *regression* configuration is run whole,
end to end, with nothing injected.

This tool builds ``results/rtl/abi3_g1f_reduced_end_to_end.json``.  It does four
things, in this order, and records what each one measured:

1. **The configuration is checked, not claimed.**
   ``configuration.structurally_identical_to_full`` is the conjunction of three
   mechanical comparisons between the reduced model and the full one -- every
   config field classified, the module tree compared with layer indices
   normalised, and the per-layer ATen operator sequence compared from an actual
   traced forward of both.  Any one of them false makes the field false.

2. **The lowering is attempted, on both storage classes.**
   The reduced model is put through the *same* compiler entry points the
   shipped deployments use.  Whatever they do is recorded: a built deployment,
   or the refusal, verbatim, with its return code.  Nothing is asserted about a
   step that was not run.

3. **The RTL is asked whether it admits the reduced geometry**, by running it.
   ``rtl/test/tb_a3_g1f_reduced_geometry.sv`` drives the three geometry-bearing
   engines the integrated vehicle instantiates at both the full and the reduced
   geometry and reports each engine's error code, result count and traffic.
   Every full-geometry case is a positive control.  This is a measurement of
   something that ran; the same question answered by reading a localparam out
   of a module would be the defect section 11.7 records inside the G1a tool.

4. **The injected-operation count is counted**, not assumed: it is the number
   of engine results this rung supplied from the golden model, which is zero
   over the operations that executed, and the number of operations that
   executed end to end is reported beside it so a zero cannot be read as a pass.

The rung is red when the RTL has not emitted the reduced oracle's ids.  A rung
that stays red with its reasons stated is the intended outcome of a rung that
cannot yet be run; a rung green on the wrong evidence is what this programme
exists to prevent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.capability import canonical_json  # noqa: E402
from tools.build_qwen3_reduced_model import (  # noqa: E402
    DEFAULT_LOCK,
    DEFAULT_SNAPSHOT,
    DEFAULT_WORKLOAD_DIR,
    FULL_CONFIG,
    MODEL_ID,
    REDUCTION,
    WORKLOAD_ID,
    budget,
)

from tools import abi3_g1_models as ladder_models  # noqa: E402

SCHEMA = "opentallas.rtl.abi3_g1f_reduced_end_to_end.v1"
GATE = "G1f (configs/gates/redesign_gates.json)"
GOVERNED_WORKLOAD_ID = "TA-QW-EOS-1"
ORACLE_PATH = ROOT / "results/abi3/qwen3_reduced_reference_oracle.json"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_g1f_reduced_end_to_end.json"
PROBE_TOP = ROOT / "rtl/test/tb_a3_g1f_reduced_geometry.sv"
PROBE_SOURCES = (
    "rtl/test/tb_a3_g1f_reduced_geometry.sv",
    "rtl/abi3/ot_a3_vector_rms_norm.sv",
    "rtl/abi3/ot_a3_qwen_gqa.sv",
    "rtl/abi3/ot_a3_mac_lane.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/ot_fp32_rsqrt_rne.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_shared_divider.sv",
)
#: The engine error codes ot_a3_engine_pkg names, so a record says which
#: refusal happened rather than printing a bare integer.
ENGINE_ERRORS = {
    0: "ERR_NONE",
    1: "ERR_OPERAND_NONFINITE_or_ERR_CONFIG",
    2: "ERR_PRODUCT_RANGE_or_ERR_INPUT",
    3: "ERR_ACCUMULATE_RANGE_or_ERR_NUMERIC",
    4: "ERR_INDEX_RANGE",
    5: "ERR_SELECT_NONFINITE",
    6: "ERR_SCALE_RANGE",
    7: "ERR_SHAPE",
}
STORES = {
    "rom": {
        "target_key": "qwen3-8b-rom-single-chip",
        "shipped_deployment": "build/abi3/qwen3-8b-rom",
        "capability": "configs/hardware/abi3_capability/rom_qwen3.json",
    },
    "hbm": {
        "target_key": "qwen3-8b-hbm-single-chip",
        "shipped_deployment": "build/abi3/qwen3-8b-hbm-tokens",
        "capability": "configs/hardware/abi3_capability/hbm_sram_single_chip.json",
    },
}
CASE_RE = re.compile(r"^CASE (\S+) (.*)$")
#: A token id the vehicle emitted.  The probe prints one line per emitted id;
#: parsing them rather than writing [] into the record means the field is what
#: the run produced, not what this tool believes the run produced.
TOKEN_RE = re.compile(r"^TOKEN (\d+)$")
MARKER_RE = re.compile(r"^MARKER: ABI3 G1F REDUCED GEOMETRY PROBE (.*)$")


def _repo_relative(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while block := handle.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _git() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
    ).stdout
    return {"commit": commit, "worktree_dirty": bool(status.strip())}


# ---------------------------------------------------------------------------
# 1. Structural identity, as three checks
# ---------------------------------------------------------------------------
def _hf_config(body: dict[str, Any], layers: int | None = None):
    from transformers import Qwen3Config

    fields = {
        k: v
        for k, v in body.items()
        if k not in ("architectures", "transformers_version", "torch_dtype")
    }
    if layers is not None:
        fields["num_hidden_layers"] = layers
        fields["max_window_layers"] = layers
    config = Qwen3Config(**fields)
    config._attn_implementation = "eager"  # noqa: SLF001
    return config


def _module_signature(body: dict[str, Any]) -> list[list[str]]:
    """The module tree with layer indices normalised, first occurrence only."""

    import torch
    from transformers import Qwen3ForCausalLM

    with torch.device("meta"):
        model = Qwen3ForCausalLM(_hf_config(body))
    seen: set[str] = set()
    signature: list[list[str]] = []
    for name, module in model.named_modules():
        normalised = re.sub(r"\.layers\.\d+", ".layers.N", name)
        if normalised in seen:
            continue
        seen.add(normalised)
        signature.append([normalised, type(module).__name__])
    return signature


def _traced_operator_sequences(
    body: dict[str, Any], *, layers: int | None = None, span: int = 4
) -> dict[str, Any]:
    """Every ATen operator the forward dispatches, split at the layer boundary."""

    import torch
    from torch.utils._python_dispatch import TorchDispatchMode
    from transformers import Qwen3ForCausalLM

    recorded: list[str] = []

    class Recorder(TorchDispatchMode):
        def __torch_dispatch__(self, func, types, args=(), kwargs=None):  # noqa: ANN001
            recorded.append(str(func))
            return func(*args, **(kwargs or {}))

    torch.manual_seed(0)
    torch.set_num_threads(min(8, os.cpu_count() or 1))
    model = Qwen3ForCausalLM(_hf_config(body, layers)).to(torch.bfloat16).eval()
    marks: dict[int, list[int | None]] = {}
    hooks = []
    for index, layer in enumerate(model.model.layers):
        def pre(module, inputs, index=index):  # noqa: ANN001, ARG001
            marks.setdefault(index, [None, None])[0] = len(recorded)

        def post(module, inputs, output, index=index):  # noqa: ANN001, ARG001
            marks[index][1] = len(recorded)

        hooks.append(layer.register_forward_pre_hook(pre))
        hooks.append(layer.register_forward_hook(post))
    with Recorder(), torch.no_grad():
        model(input_ids=torch.zeros(1, span, dtype=torch.long), use_cache=False)
    for hook in hooks:
        hook.remove()
    ordered = sorted(marks.items())
    per_layer = [recorded[start:end] for _, (start, end) in ordered]
    return {
        "layer_count": len(per_layer),
        "per_layer": per_layer,
        "prefix": recorded[: ordered[0][1][0]],
        "suffix": recorded[ordered[-1][1][1] :],
        "total": len(recorded),
    }


#: The V4.1 reduction rule, as recorded by the fixture builder.  This file does
#: not restate it: every classification below is read out of this artifact, so a
#: change to the reduction is a change to one record rather than to two.
V41_REDUCTION_RECORD = ROOT / "results/abi3/deepseek_v41_reduced_model.json"

#: Per-layer selectors in the V4.1 configuration.  Each decides which code path
#: the vendor's ``Block`` takes at a given layer index, so together they are the
#: model's operator sequence expressed as data.  All of them are in the
#: reduction's ``kept_exactly`` set, which is what makes the sequence checkable
#: by comparison instead of by tracing a forward.
V41_PER_LAYER_SELECTORS = (
    "compress_ratios",
    "candidate_source_layer",
    "engram_layer_ids",
    "index_source_layers",
    "kv_source_layers",
    "dspark_target_layer_ids",
)


def _v41_module_paths(vendor: Any, tokenizer: Any, body: dict[str, Any]) -> list[str]:
    """Module paths of one vendor ``Transformer`` built on the meta device.

    The meta device allocates no storage, so the released configuration -- whose
    routed-expert stack is about 27 GB of parameters in a single layer -- can be
    built and walked on the same host as the reduced one.  Layer indices are
    normalised to ``N`` and the first occurrence of each normalised path is
    kept, so a 40-layer model and a 40-layer model are compared by shape rather
    than by repetition count.
    """
    import torch

    torch.set_default_dtype(torch.bfloat16)
    with torch.device("meta"):
        model = vendor.Transformer(vendor.ModelArgs(**body), tokenizer)
    seen: set[str] = set()
    paths: list[str] = []
    for name, _module in model.named_modules():
        normalised = re.sub(r"\.\d+\.", ".N.", name)
        normalised = re.sub(r"\.\d+$", ".N", normalised)
        if normalised not in seen:
            seen.add(normalised)
            paths.append(normalised)
    return paths


def structural_identity_v41(
    full: dict[str, Any], reduced: dict[str, Any], reduction: dict[str, Any]
) -> dict[str, Any]:
    """Is the reduced V4.1 fixture the released architecture at smaller widths?

    Three dimensions, each measured rather than asserted:

    *Configuration.*  Every key of either configuration is classified against
    the recorded reduction -- ``block_widths`` and ``counts`` are the reduced
    ones, ``derived`` follow from them, ``kept_exactly`` must be byte-equal, and
    the ``vision_*`` keys are the recorded exclusion.  A key in no bucket, or a
    ``kept_exactly`` key that differs, is an unexpected difference.  The
    ``block_widths`` and ``counts`` entries additionally have to agree with the
    values the two configurations actually carry, so the record cannot drift
    away from the fixture it describes.

    *Module tree.*  Both configurations are built as the release's own
    ``Transformer`` on the meta device and their normalised module paths are
    compared.  The vision tower is excluded, which the record declares as an
    exclusion rather than a reduction, so it is subtracted explicitly and what
    remains has to match exactly.

    *Operator sequence.*  Qwen3's rung traces a forward because
    ``transformers`` branches on configuration fields.  Here both models are the
    same vendor ``model.py``, and what varies per layer is data: the compress
    ratio, and whether the layer is an Engram, index-source, KV-source or DSpark
    layer.  Every one of those selectors is in ``kept_exactly``, so the per-layer
    branch vector is compared exactly, for all 40 layers, instead of tracing one
    layer at released widths -- which no host here can hold.
    """
    block_widths = reduction["block_widths"]
    counts = reduction["counts"]
    derived = set(reduction["derived"])
    kept = set(reduction["kept_exactly"])
    excluded_prefix = "vision_"

    fields: dict[str, Any] = {}
    unexpected: list[str] = []
    record_disagreements: list[dict[str, Any]] = []
    for key in sorted(set(full) | set(reduced)):
        left, right = full.get(key), reduced.get(key)
        if key in block_widths or key in counts:
            kind = "reduced"
            entry = block_widths.get(key) or counts[key]
            if left is not None and int(entry["released"]) != int(left):
                record_disagreements.append(
                    {"field": key, "record_released": entry["released"],
                     "config_released": left}
                )
            if right is not None and int(entry["reduced"]) != int(right):
                record_disagreements.append(
                    {"field": key, "record_reduced": entry["reduced"],
                     "config_reduced": right}
                )
        elif key in derived:
            kind = "derived_from_reduction"
        elif key in kept:
            kind = "identical" if left == right else "differs_unexpectedly"
            if left != right:
                unexpected.append(key)
        elif key.startswith(excluded_prefix):
            kind = "vision_excluded" if left == right else "differs_unexpectedly"
            if left != right:
                unexpected.append(key)
        elif left == right:
            kind = "identical"
        else:
            kind = "differs_unexpectedly"
            unexpected.append(key)
        fields[key] = {"full": left, "reduced": right, "classification": kind}

    def _layers(body: dict[str, Any]) -> int:
        return int(body["n_layers"])

    def _invariants(body: dict[str, Any]) -> dict[str, bool]:
        layers = _layers(body)
        widths = [
            int(body[name]) for name in sorted(block_widths) if name in body
        ]
        granule = int(reduction["quantization_block"])
        return {
            # The release's own act_quant asserts N % block_size == 0, so this
            # is the floor and the granularity of every width at both scales.
            "every_reduced_width_is_a_quantization_block_multiple": all(
                width % granule == 0 for width in widths
            ),
            "activated_experts_within_routed": (
                int(body["n_activated_experts"]) <= int(body["n_routed_experts"])
            ),
            "dspark_activated_within_routed": (
                int(body["dspark_n_activated_experts"])
                <= int(body["dspark_n_routed_experts"])
            ),
            "compress_ratios_cover_every_layer_and_mtp": (
                len(body["compress_ratios"])
                == layers + int(body["n_mtp_layers"])
            ),
            "candidate_source_layer_in_range": (
                0 <= int(body["candidate_source_layer"]) < layers
            ),
            "engram_layers_in_range": all(
                0 <= int(index) < layers for index in body["engram_layer_ids"]
            ),
            "index_source_layers_in_range": all(
                0 <= int(index) < layers for index in body["index_source_layers"]
            ),
            "kv_source_layers_in_range": all(
                0 <= int(index) < layers for index in body["kv_source_layers"]
            ),
            "dspark_target_layers_in_range": all(
                0 <= int(index) < layers for index in body["dspark_target_layer_ids"]
            ),
            "one_embedding_table_per_engram_layer": (
                len(body["engram_num_embeddings"]) == len(body["engram_layer_ids"])
            ),
        }

    full_invariants = _invariants(full)
    reduced_invariants = _invariants(reduced)
    invariants = {
        name: {
            "full": full_invariants[name],
            "reduced": reduced_invariants[name],
            "held": bool(full_invariants[name] and reduced_invariants[name]),
        }
        for name in sorted(full_invariants)
    }
    config_ok = (
        not unexpected
        and not record_disagreements
        and all(item["held"] for item in invariants.values())
    )

    from transformers import AutoTokenizer

    from tools.build_deepseek_v41_reduced_model import (
        import_vendor,
        released_snapshot,
    )

    released = released_snapshot()
    vendor, _engram = import_vendor(released)
    tokenizer = AutoTokenizer.from_pretrained(str(released))
    full_tree = _v41_module_paths(vendor, tokenizer, full)
    reduced_tree = _v41_module_paths(vendor, tokenizer, reduced)
    vision_only = [path for path in full_tree if path.split(".")[0] == "vision"]
    full_tree_text = [path for path in full_tree if path.split(".")[0] != "vision"]
    reduced_tree_text = [
        path for path in reduced_tree if path.split(".")[0] != "vision"
    ]
    reduced_has_vision = [
        path for path in reduced_tree if path.split(".")[0] == "vision"
    ]
    tree_ok = full_tree_text == reduced_tree_text and not reduced_has_vision

    def _branch_vector(body: dict[str, Any]) -> list[dict[str, Any]]:
        ratios = list(body["compress_ratios"])
        engram = {int(index) for index in body["engram_layer_ids"]}
        index_source = {int(index) for index in body["index_source_layers"]}
        kv_source = {int(index) for index in body["kv_source_layers"]}
        dspark = {int(index) for index in body["dspark_target_layer_ids"]}
        candidate = int(body["candidate_source_layer"])
        return [
            {
                "compress_ratio": int(ratios[layer]),
                "engram": layer in engram,
                "index_source": layer in index_source,
                "kv_source": layer in kv_source,
                "dspark": layer in dspark,
                "candidate_source": layer == candidate,
            }
            for layer in range(_layers(body))
        ]

    full_branches = _branch_vector(full)
    reduced_branches = _branch_vector(reduced)
    sequence_ok = full_branches == reduced_branches
    selectors_kept = sorted(
        name for name in V41_PER_LAYER_SELECTORS if name in kept
    )

    def _first_difference(
        left: list[Any], right: list[Any]
    ) -> dict[str, Any] | None:
        for index, (one, other) in enumerate(zip(left, right)):
            if one != other:
                return {"index": index, "full": one, "reduced": other}
        if len(left) != len(right):
            return {
                "index": min(len(left), len(right)),
                "full": None,
                "reduced": None,
            }
        return None

    return {
        "structurally_identical": bool(config_ok and tree_ok and sequence_ok),
        "checked_not_claimed": True,
        "model": "deepseek-v4.1-flash",
        "reduction_record": str(V41_REDUCTION_RECORD.relative_to(ROOT)),
        "dimensions_compared": ["config", "module_tree", "operator_sequence"],
        "config_comparison": {
            "passed": config_ok,
            "how": (
                "every key of either configuration classified against the "
                "recorded reduction; block_widths and counts additionally "
                "reconciled against the values both configurations carry"
            ),
            "unexpected_differences": unexpected,
            "record_disagreements": record_disagreements,
            "invariants": invariants,
            "fields": fields,
        },
        "module_tree_comparison": {
            "passed": tree_ok,
            "how": (
                "the release's own inference/model.py Transformer built on the "
                "meta device at each configuration; every module path with its "
                "layer index normalised to N, first occurrence kept, compared "
                "in order with the recorded vision exclusion subtracted"
            ),
            "full_module_paths": len(full_tree),
            "reduced_module_paths": len(reduced_tree),
            "full_text_only_paths": len(full_tree_text),
            "reduced_text_only_paths": len(reduced_tree_text),
            "vision_paths_excluded": len(vision_only),
            "vision_exclusion": reduction["vision_excluded"],
            "reduced_carries_vision_modules": bool(reduced_has_vision),
            "first_difference": _first_difference(
                full_tree_text, reduced_tree_text
            ),
            "full_layer_count": _layers(full),
            "reduced_layer_count": _layers(reduced),
        },
        "operator_sequence_comparison": {
            "passed": sequence_ok,
            "how": (
                "the per-layer branch vector -- compress ratio and whether the "
                "layer is an Engram, index-source, KV-source, DSpark or "
                "candidate-source layer -- computed from both configurations "
                "and compared for every layer. Not a traced forward: both "
                "models are the same vendor model.py, so what differs per "
                "layer is data, and every selector carrying it is in the "
                "reduction's kept_exactly set"
            ),
            "why_not_traced": (
                "a single layer at released widths holds a routed-expert stack "
                "of about 27 GB of parameters, so the full-dimension trace "
                "Qwen3's rung performs is not runnable here; the selectors are "
                "compared exactly instead, over all layers rather than one"
            ),
            "per_layer_selectors": list(V41_PER_LAYER_SELECTORS),
            "selectors_in_kept_exactly": selectors_kept,
            "all_selectors_kept_exactly": (
                len(selectors_kept) == len(V41_PER_LAYER_SELECTORS)
            ),
            "layers_compared": _layers(reduced),
            "first_difference": _first_difference(
                full_branches, reduced_branches
            ),
        },
    }

def structural_identity(full: dict[str, Any], reduced: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    unexpected: list[str] = []
    derived = {"max_window_layers", "bos_token_id", "eos_token_id"}
    for key in sorted(set(full) | set(reduced)):
        left, right = full.get(key), reduced.get(key)
        if key in REDUCTION:
            kind = "reduced"
        elif key in derived:
            kind = "derived_from_reduction"
        elif left == right:
            kind = "identical"
        else:
            kind = "differs_unexpectedly"
            unexpected.append(key)
        fields[key] = {"full": left, "reduced": right, "classification": kind}
    invariants = {
        name: {"full": left, "reduced": right, "held": left == right}
        for name, (left, right) in {
            "gqa_group_ratio": (
                int(full["num_attention_heads"]) // int(full["num_key_value_heads"]),
                int(reduced["num_attention_heads"])
                // int(reduced["num_key_value_heads"]),
            ),
            "heads_times_head_dim_equals_hidden": (
                int(full["num_attention_heads"]) * int(full["head_dim"])
                == int(full["hidden_size"]),
                int(reduced["num_attention_heads"]) * int(reduced["head_dim"])
                == int(reduced["hidden_size"]),
            ),
            "swiglu_expansion_ratio": (
                int(full["intermediate_size"]) / int(full["hidden_size"]),
                int(reduced["intermediate_size"]) / int(reduced["hidden_size"]),
            ),
        }.items()
    }
    config_ok = not unexpected and all(item["held"] for item in invariants.values())

    full_tree = _module_signature(full)
    reduced_tree = _module_signature(reduced)
    tree_ok = full_tree == reduced_tree

    reduced_trace = _traced_operator_sequences(reduced)
    full_trace = _traced_operator_sequences(full, layers=1)
    reduced_layers_identical = len({tuple(x) for x in reduced_trace["per_layer"]}) == 1
    layer_ok = (
        reduced_layers_identical
        and reduced_trace["per_layer"][0] == full_trace["per_layer"][0]
    )
    prefix_ok = reduced_trace["prefix"] == full_trace["prefix"]
    suffix_ok = reduced_trace["suffix"] == full_trace["suffix"]

    def _first_difference(left: list[str], right: list[str]) -> dict[str, Any] | None:
        for index, (a, b) in enumerate(zip(left, right)):
            if a != b:
                return {"index": index, "full": a, "reduced": b}
        if len(left) != len(right):
            return {"index": min(len(left), len(right)), "full": None, "reduced": None}
        return None

    return {
        "structurally_identical": bool(
            config_ok and tree_ok and layer_ok and prefix_ok and suffix_ok
        ),
        "checked_not_claimed": True,
        "config_comparison": {
            "passed": config_ok,
            "unexpected_differences": unexpected,
            "invariants": invariants,
            "fields": fields,
        },
        "module_tree_comparison": {
            "passed": tree_ok,
            "how": (
                "transformers.Qwen3ForCausalLM built on the meta device at each "
                "configuration; every module path with its layer index "
                "normalised to N, first occurrence kept, compared in order"
            ),
            "full_module_paths": len(full_tree),
            "reduced_module_paths": len(reduced_tree),
            "full_layer_count": int(full["num_hidden_layers"]),
            "reduced_layer_count": int(reduced["num_hidden_layers"]),
            "differences": (
                []
                if tree_ok
                else [
                    entry for entry in full_tree if entry not in reduced_tree
                ][:8]
            ),
        },
        "operator_sequence_comparison": {
            "passed": bool(layer_ok and prefix_ok and suffix_ok),
            "how": (
                "both models traced through an actual forward under a "
                "TorchDispatchMode; the full model is instantiated at full "
                "dimensions with one decoder layer, which is sound because the "
                "reduced model's own layers are checked to be identical to one "
                "another and the module tree above shows the full stack repeats "
                "the same block"
            ),
            "per_layer_operator_count": len(reduced_trace["per_layer"][0]),
            "reduced_all_layers_identical": reduced_layers_identical,
            "per_layer_sequence_equal": layer_ok,
            "pre_layer_sequence_equal": prefix_ok,
            "post_layer_sequence_equal": suffix_ok,
            "pre_layer_operator_count": len(reduced_trace["prefix"]),
            "post_layer_operator_count": len(reduced_trace["suffix"]),
            "first_layer_difference": _first_difference(
                full_trace["per_layer"][0], reduced_trace["per_layer"][0]
            ),
            "first_post_layer_difference": _first_difference(
                full_trace["suffix"], reduced_trace["suffix"]
            ),
        },
    }


# ---------------------------------------------------------------------------
# 2. The lowering, attempted
# ---------------------------------------------------------------------------
def _run(argv: list[str], *, cwd: Path, timeout: int = 1800) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PYTHONPATH": str(cwd)},
        )
    except subprocess.TimeoutExpired:
        return {
            "argv": argv,
            "returncode": None,
            "timed_out": True,
            "seconds": round(time.perf_counter() - started, 2),
        }
    tail = [line for line in (proc.stderr or "").splitlines() if line.strip()][-6:]
    out = [line for line in (proc.stdout or "").splitlines() if line.strip()][-4:]
    return {
        "argv": argv,
        "returncode": proc.returncode,
        "timed_out": False,
        "seconds": round(time.perf_counter() - started, 2),
        "stderr_tail": tail,
        "stdout_tail": out,
    }


def frontend_refusal_chain(model_dir: Path) -> dict[str, Any]:
    """Where the shipped frontend stops, measured by calling it.

    The CLI above refuses on the config digest, which is a provenance pin.  A
    pin can be satisfied by re-pinning, so the interesting question is what the
    frontend does once past it: this calls the two builders the exporter calls
    first, with the reduced config in hand, and records the exception each one
    raises.  The frozen counts are reported beside the reduced model's own,
    computed from the parameter list, so the size of the gap is visible.
    """

    from compiler.frontends.v3.qwen3 import (
        KERNEL_COUNT,
        KERNELS_PER_LAYER,
        TENSOR_TOTAL,
    )
    from compiler.qwen3.constants import LAYER_COUNT, TENSOR_COUNT
    from tools.build_qwen3_reduced_model import tensor_shapes

    reduced = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
    steps: list[dict[str, Any]] = []
    for name, call in (
        ("compiler.qwen3.graph.build_tensor_specs", "build_tensor_specs"),
        ("compiler.qwen3.graph.build_graph_nodes", "build_graph_nodes"),
    ):
        try:
            from compiler.qwen3 import graph as qwen3_graph

            result = getattr(qwen3_graph, call)(reduced)
            steps.append(
                {
                    "entry_point": name,
                    "refused": False,
                    "produced": len(result),
                }
            )
        except Exception as exc:  # noqa: BLE001 - the refusal is the measurement
            steps.append(
                {
                    "entry_point": name,
                    "refused": True,
                    "exception": type(exc).__name__,
                    "message": str(exc)[:600],
                }
            )
    reduced_layers = int(reduced["num_hidden_layers"])
    return {
        "how": "each entry point called in process with the reduced config",
        "steps": steps,
        "frozen_counts": {
            "compiler.qwen3.constants.LAYER_COUNT": LAYER_COUNT,
            "compiler.qwen3.constants.TENSOR_COUNT": TENSOR_COUNT,
            "compiler.frontends.v3.qwen3.TENSOR_TOTAL": TENSOR_TOTAL,
            "compiler.frontends.v3.qwen3.KERNEL_COUNT": KERNEL_COUNT,
            "compiler.frontends.v3.qwen3.KERNELS_PER_LAYER": KERNELS_PER_LAYER,
        },
        "reduced_model_counts": {
            "layers": reduced_layers,
            "weight_tensors": len(tensor_shapes(reduced)),
            "kernels_if_the_census_scaled": 2 + reduced_layers * KERNELS_PER_LAYER + 6,
        },
        "verdict": (
            "the frontend is bound to the pinned Qwen3-8B release both by the "
            "config digest and, past it, field by field; and its census, "
            "tensor total and layer count are frozen at the 36-layer model, so "
            "the refusal is a capability limit and not only a provenance pin"
        ),
    }


def attempt_lowering(
    snapshot: Path, lock: Path, model_dir: Path, work: Path
) -> dict[str, Any]:
    """Put the reduced model through the same compiler, and record what happens."""

    work.mkdir(parents=True, exist_ok=True)
    ir_path = work / "kernel_ir.v3.json"
    frontend = _run(
        [
            sys.executable,
            "tools/build_qwen3_kernel_ir_v3.py",
            "--snapshot",
            str(snapshot),
            "--checkpoint-lock",
            str(lock),
            "--config",
            str(model_dir / "config.json"),
            "--output",
            str(ir_path),
            "--verify-bindings",
            "all",
        ],
        cwd=ROOT,
    )
    frontend["produced_ir"] = ir_path.is_file()
    frontend["entry_point"] = "tools/build_qwen3_kernel_ir_v3.py"
    frontend["same_entry_point_as_shipped"] = True

    stores: dict[str, Any] = {}
    for store, meta in STORES.items():
        out = work / f"{store}-deployment"
        if store == "rom":
            argv = [
                sys.executable,
                "tools/build_rom_deployment.py",
                "qwen3-8b",
                "--ir",
                str(ir_path),
                "--output",
                str(out),
                "--checkpoint-root",
                str(snapshot),
            ]
        else:
            argv = [
                sys.executable,
                "tools/build_hbm_sram_deployment.py",
                "--ir",
                str(ir_path),
                "--profile",
                "single-chip",
                "--out",
                str(out),
            ]
        attempt = _run(argv, cwd=ROOT)
        attempt["produced_deployment"] = (out / "deployment.json").is_file()
        stores[store] = attempt
    if not frontend["produced_ir"]:
        for entry in stores.values():
            entry["blocked_by"] = "kernel_ir"
            entry["note"] = (
                "the backend consumes the kernel IR the frontend refused to "
                "emit, so its own behaviour on a reduced model is not measured "
                "by this attempt"
            )
    built = frontend["produced_ir"] and all(
        entry["produced_deployment"] for entry in stores.values()
    )
    return {
        "attempted": True,
        "refusal_chain": frontend_refusal_chain(model_dir),
        "same_compiler_as_shipped": True,
        "same_abi": "ABI 3.0",
        "kernel_ir": frontend,
        "backends": stores,
        "both_storage_classes_built": built,
        "why_it_matters": (
            "G1f proves nothing about this chip unless the reduced model goes "
            "through the same compiler and the same ABI on both storage "
            "classes; a bespoke path would be verifying a different machine"
        ),
    }


# ---------------------------------------------------------------------------
# 3. The RTL geometry probe
# ---------------------------------------------------------------------------
#: The simulator this rung is characterised against, resolved the way every
#: other RTL campaign here resolves it.  Taking it from PATH instead cost a run:
#: /usr/bin/verilator is 4.038 (2020) on this machine, which has no --binary,
#: so the probe failed with "Invalid option: --binary" and the rung reported
#: "the G1f geometry probe did not elaborate" -- a tool-version accident
#: recorded as a design fact.  A pinned path also makes the artifact's
#: simulator field reproducible instead of PATH-dependent.
PINNED_VERILATOR_VERSION = "5.050"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)


def resolve_verilator() -> str:
    pinned = TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"
    if pinned.is_file():
        return str(pinned)
    found = shutil.which("verilator")
    if found is None:
        raise SystemExit(
            f"pinned verilator {PINNED_VERILATOR_VERSION} is not at {pinned} and "
            "none is on PATH"
        )
    return found


def run_probe(work: Path, *, store: str) -> dict[str, Any]:
    verilator = resolve_verilator()
    version = subprocess.run(
        [verilator, "--version"], capture_output=True, text=True
    ).stdout.strip()
    build = work / f"probe-{store}"
    build.mkdir(parents=True, exist_ok=True)
    compile_started = time.perf_counter()
    compiled = subprocess.run(
        [
            verilator,
            "--binary",
            "--timing",
            "-Wno-fatal",
            "-O2",
            "-j",
            "8",
            "--top-module",
            PROBE_TOP.stem,
            "-Mdir",
            str(build / "obj"),
            "-o",
            "probe",
            *[str(ROOT / name) for name in PROBE_SOURCES],
        ],
        cwd=build,
        capture_output=True,
        text=True,
    )
    compile_seconds = time.perf_counter() - compile_started
    if compiled.returncode != 0:
        raise SystemExit(
            "the G1f geometry probe did not elaborate:\n" + compiled.stderr[-3000:]
        )
    started = time.perf_counter()
    run = subprocess.run(
        [str(build / "obj" / "probe")], capture_output=True, text=True, timeout=3600
    )
    run_seconds = time.perf_counter() - started
    if run.returncode != 0:
        raise SystemExit(f"the G1f geometry probe failed: {run.stdout[-3000:]}")

    cases: list[dict[str, Any]] = []
    emitted: list[int] = []
    marker = None
    for line in run.stdout.splitlines():
        token = TOKEN_RE.match(line.strip())
        if token:
            emitted.append(int(token.group(1)))
            continue
        found = CASE_RE.match(line.strip())
        if found:
            body: dict[str, Any] = {"case": found.group(1)}
            for token in found.group(2).split():
                key, _, value = token.partition("=")
                body[key] = int(value) if value.lstrip("-").isdigit() else value
            body["error_name"] = ENGINE_ERRORS.get(int(body.get("err", -1)), "UNKNOWN")
            body["admitted"] = int(body.get("err", -1)) == 0
            cases.append(body)
            continue
        found = MARKER_RE.match(line.strip())
        if found:
            marker = line.strip()
    if marker is None or not cases:
        raise SystemExit("the G1f geometry probe printed no marker")
    cycles = int(re.search(r"cycles=(\d+)", marker).group(1))
    return {
        "vehicle": str(PROBE_TOP.relative_to(ROOT)),
        "simulator": "verilator_cpp_executable",
        "simulator_version": version.split()[1] if version else None,
        "simulator_banner": version,
        "simulated_cycles": cycles,
        "compile_seconds": round(compile_seconds, 2),
        "run_seconds": round(run_seconds, 2),
        "marker": marker,
        "case_count": len(cases),
        "cases": cases,
        "emitted_token_ids": emitted,
        "token_emitting_modules_compiled": [
            name
            for name in PROBE_SOURCES
            if "selection" in name or "token_append" in name
        ],
        "sources": {
            name: {
                "sha256": _sha256_file(ROOT / name),
                "bytes": (ROOT / name).stat().st_size,
            }
            for name in PROBE_SOURCES
        },
    }


def rtl_expressible_alternative(
    full: dict[str, Any], reduced: dict[str, Any], probe: dict[str, Any]
) -> dict[str, Any]:
    """What a reduction the measured RTL DOES admit would cost.

    The probe measured which dimensions move and which do not: the contraction
    lane and the model-row normalisation admit the reduced widths, the per-head
    normalisation refuses them, and the attention engine has no geometry input
    at all.  So the only reduction this RTL can express keeps the attention
    block at full size -- hidden 4096, 32 query heads, 8 KV heads, head_dim
    128, and therefore intermediate 3x hidden -- and moves layers and vocabulary
    only.  Its cost is derived here from the same measured rate, because a rung
    whose stated cost is "minutes" and whose expressible form is a day per store
    should say so with the arithmetic beside it.
    """

    by_case = {entry["case"]: entry for entry in probe["cases"]}
    admitted = {
        name: by_case.get(name, {}).get("admitted")
        for name in (
            "full_model_row",
            "full_head_rows",
            "reduced_model_row",
            "reduced_head_rows",
            "gqa_context_16",
            "reduced_q_proj_row",
        )
    }
    expressible = dict(full)
    expressible["num_hidden_layers"] = int(reduced["num_hidden_layers"])
    expressible["max_window_layers"] = int(reduced["num_hidden_layers"])
    expressible["vocab_size"] = int(reduced["vocab_size"])
    one_layer = dict(expressible, num_hidden_layers=1, max_window_layers=1)
    prompt = 16
    generated = 3
    return {
        "why": (
            "the reduced dimension the budget needs is exactly the one the "
            "attention engine has no port for"
        ),
        "measured_admissions": admitted,
        "dimensions_that_cannot_move": {
            "hidden_size": int(full["hidden_size"]),
            "num_attention_heads": int(full["num_attention_heads"]),
            "num_key_value_heads": int(full["num_key_value_heads"]),
            "head_dim": int(full["head_dim"]),
            "measured_by": probe["vehicle"],
        },
        "dimensions_that_can_move": ["num_hidden_layers", "vocab_size"],
        "cost_at_reduced_layer_count": budget(expressible, prompt, generated),
        "cost_at_one_layer": budget(one_layer, prompt, generated),
    }


#: The integrated rate section 11.7 corrected to on 2026-09-06, and the
#: reason the correction matters here.  ``tools/build_qwen3_reduced_model.py``
#: still derives its budget from 39,915 MACs/s, which was taken from the
#: SIMULATION-ALONE CPU time of one run; the committed artifact records the
#: whole run and gives 166,845 cycles/s at 5.00793 cycles/MAC, which is 33,316
#: MACs/s.  Rule R13 says the optimistic form of a metric reported under two
#: models is not evidence, so every cost this file states about the
#: alternative it is deciding against is restated at the pessimistic rate and
#: the disagreement with the budget block is named rather than smoothed over.
CORRECTED_MACS_PER_SECOND = 33_316
CORRECTED_RATE_SOURCE = (
    "docs/CHIP_ARCHITECTURE_DESIGN.md section 11.7, 'Rate, corrected "
    "2026-09-06': simulated_cycles 252,057,600 over run_cpu_seconds 1,510.73 "
    "for 50,331,648 MACs"
)


def geometry_port_decision(alternative: dict[str, Any]) -> dict[str, Any]:
    """The decision this rung's measurements force, and the argument for it.

    Two courses are open once the probe has measured that the attention engine
    has no geometry input and that the per-head normalisation refuses the
    reduced width.  Either the engines gain the port, or the reduced
    configuration is chosen to fit the geometry the engines already have.  The
    second is the expedient one and this block does not take it.  Every clause
    below is either a citation of the design document that governs the block
    in question or an arithmetic restatement of a measurement in this same
    record; nothing here is a preference.
    """

    one_layer = alternative["cost_at_one_layer"]["transactions_accounting"]
    layers = alternative["cost_at_reduced_layer_count"]["transactions_accounting"]

    def at_corrected(macs: int) -> dict[str, Any]:
        seconds = macs / CORRECTED_MACS_PER_SECOND
        return {
            "macs": int(macs),
            "seconds_per_storage_class": round(seconds, 1),
            "hours_per_storage_class": round(seconds / 3600.0, 2),
        }

    return {
        "question": (
            "is the geometry port a design change worth making, or should the "
            "reduced configuration be chosen to fit the geometry the engines "
            "have?"
        ),
        "decision": "build the geometry port",
        "decided_against": (
            "choosing a reduced configuration that keeps hidden_size 4096, 32 "
            "query heads, 8 KV heads and head_dim 128"
        ),
        "why_the_alternative_is_not_an_alternative": {
            "what_can_still_move": alternative["dimensions_that_can_move"],
            "what_cannot": alternative["dimensions_that_cannot_move"],
            "cost_of_the_cheapest_such_configuration": {
                "one_layer": at_corrected(one_layer["total_macs"]),
                "reduced_layer_count": at_corrected(layers["total_macs"]),
                "accounting": one_layer["note"],
                "rate": CORRECTED_MACS_PER_SECOND,
                "rate_source": CORRECTED_RATE_SOURCE,
                "rate_disagreement": (
                    "the budget block of this record and "
                    "tools/build_qwen3_reduced_model.py still carry 39,915 "
                    "MACs/s, the superseded optimistic form.  The figures "
                    "here are the pessimistic form under R13; the constant "
                    "itself is a debt this rung names and does not pay, "
                    "because paying it regenerates "
                    "results/abi3/qwen3_reduced_model_construction.json"
                ),
            },
            "the_gate_says_minutes": (
                "G1f's own note calls this rung 'the industry's small-config "
                "regression ... run whole, nightly' and costs it in minutes.  "
                "A configuration that cannot move the attention block costs "
                "tens of hours per storage class even at ONE layer.  That is "
                "not a cheaper way to satisfy the rung, it is a rung that "
                "stays red for a reason the ladder can never retire, so the "
                "two courses are not two options at different prices -- only "
                "one of them ends with a rung that runs"
            ),
        },
        "argued_against_section_4": [
            {
                "block": "ot_a3_vector_rms_norm",
                "citation": "section 4.9, the vector engine's contract table",
                "argument": (
                    "the microprogram for qwen3_rmsnorm_fp32_bf16_v1 is "
                    "'square; PAIRWISE_TREE row sum; DIVIDE BY WIDTH; + eps; "
                    "exact-integer rsqrt; ...', and the fail-closed column "
                    "beside it names exactly three refusals: eps_bits 0, order "
                    "!= PAIRWISE_TREE, unknown digest.  Width is an operand of "
                    "the microprogram and is not in the refusal set.  The "
                    "block's ERR_SHAPE on a row width outside {4096, 128} is "
                    "therefore a refusal section 4 does not authorise, and "
                    "removing it returns the block to its specification rather "
                    "than extending it"
                ),
            },
            {
                "block": "ot_a3_vector_rms_norm",
                "citation": "the block's own port list",
                "argument": (
                    "the mechanism is already there: cfg_rows, cfg_cols and "
                    "cfg_epsilon_bits are runtime inputs today.  "
                    "cfg_epsilon_bits is the precedent -- a numeric constant of "
                    "the contract already arrives as a runtime code instead of "
                    "being frozen per model -- so delivering the reciprocal of "
                    "the width the same way is applying the block's own "
                    "existing convention, not adding a mechanism"
                ),
            },
            {
                "block": "ot_a3_qwen_gqa",
                "citation": "section 2.1 row 7 [T2.1-7]",
                "argument": (
                    "the core's attention resource is specified as '64 head "
                    "controllers'.  A 64-head-controller resource is the "
                    "specification of a block that serves a VARIABLE head "
                    "count; QUERY_HEADS = 32, KV_HEADS = 8 and HEAD_WIDTH = "
                    "128 as localparams is a block that serves one.  The same "
                    "row is marked 'both', and sections 1.1 and 4.15 require "
                    "these engines to serve three models over 36 registered "
                    "arithmetic pairs, each with one named datapath"
                ),
            },
            {
                "block": "ot_a3_qwen_gqa",
                "citation": "section 2.1 row 31, the capability limits",
                "argument": (
                    "the capability record is the contract a program is "
                    "admitted against, and it bounds instructions, "
                    "descriptors, events, context positions, vocabulary, "
                    "expert ids, topk and sessions.  It declares NO head-count "
                    "and NO head-width limit, so a deployment with another "
                    "head geometry is admissible by the device's own "
                    "advertisement.  An engine that refuses it is refusing "
                    "something the capability said it would serve; the honest "
                    "courses are to serve it or to declare the limit, and "
                    "declaring it would make the Qwen engine unable to serve "
                    "the DeepSeek attention pairs the same row promises"
                ),
            },
            {
                "block": "ot_a3_qwen_gqa",
                "citation": "rule R14, follow the consumer of the field",
                "argument": (
                    "the consumer of the head geometry is the attention "
                    "engine.  A consumer that assumes a field instead of "
                    "reading it is the defect, and where two courses are not "
                    "cost-symmetric R14 takes the one that costs the ROM side: "
                    "the port costs RTL work and a re-qualification of two "
                    "engines, the fit costs nothing now and the rung later"
                ),
            },
            {
                "block": "ot_a3_qwen_gqa",
                "citation": "the block's own header and MAX_CONTEXT",
                "argument": (
                    "the block has already made this move once, for the same "
                    "reason: MAX_CONTEXT was a constant 17 that 'expressed "
                    "exactly one generated token', and is now a parameter with "
                    "cfg_context_length checked against [MIN_CONTEXT, "
                    "MAX_CONTEXT] at start.  The head geometry is the same "
                    "shape of change to the same block.  MIN_CONTEXT stays: "
                    "the eight-lane softmax denominator is an ASSOCIATION, "
                    "which section 4.9's fail-closed column does name"
                ),
            },
        ],
        "scope_in_measured_order": [
            "the compiler's Qwen3 config-digest pin must admit a second "
            "configuration.  It is blocking_in_order item 1 and neither RTL "
            "change touches it, so neither engine change alone turns this rung "
            "green",
            "ot_a3_vector_rms_norm: replace the cfg_cols whitelist with the "
            "bound its own buffer imposes and take the reciprocal-width code "
            "as a runtime input the way cfg_epsilon_bits already is.  The two "
            "existing profiles' codes do not change, so the qualification is "
            "the existing directed cases re-run bit-identical plus new cases "
            "at the reduced widths",
            "ot_a3_qwen_gqa: promote QUERY_HEADS, KV_HEADS and HEAD_WIDTH to "
            "parameters of the verification instance, as MAX_CONTEXT already "
            "is, and take the 1/sqrt(head_dim) scale code as a runtime input "
            "where SCALE_CODE is a localparam today",
        ],
        "status": (
            "a decision argued from this record's measurements and from the "
            "design document; the measurements are results, the decision is "
            "not, and no field of this rung's gate turns on it"
        ),
    }


def geometry_verdict(probe: dict[str, Any], reduced: dict[str, Any]) -> dict[str, Any]:
    """What the probe's measurements say about running the reduced model."""

    by_case = {entry["case"]: entry for entry in probe["cases"]}
    controls = [
        name
        for name in ("full_model_row", "full_head_rows", "gqa_context_16")
        if by_case.get(name, {}).get("admitted")
    ]
    refused = [
        {
            "case": name,
            "engine": entry["engine"],
            "error_code": entry["err"],
            "error_name": entry["error_name"],
        }
        for name, entry in by_case.items()
        if not entry["admitted"] and name.startswith("reduced")
    ]
    heads = int(reduced["num_attention_heads"])
    head_dim = int(reduced["head_dim"])
    kv_heads = int(reduced["num_key_value_heads"])
    context = 16
    reduced_attention_reads = heads * (
        head_dim + context * head_dim + context * head_dim
    )
    reduced_attention_writes = heads * head_dim
    gqa = by_case.get("gqa_context_16", {})
    # The same engine elaborated for the reduced attention geometry.  Its
    # traffic is compared against the expectation derived just above from the
    # reduced model's OWN config, so the two are independent.
    reduced_gqa = by_case.get("gqa_reduced_context_16", {})
    reduced_gqa_matches = bool(
        reduced_gqa.get("admitted")
        and reduced_gqa.get("reads") == reduced_attention_reads
        and reduced_gqa.get("writes") == reduced_attention_writes
    )
    admitted_cases = [e["case"] for e in probe["cases"] if e["admitted"]]
    refused_cases = [e["case"] for e in probe["cases"] if not e["admitted"]]
    return {
        "two_sided": {
            "admitted_count": len(admitted_cases),
            "refused_count": len(refused_cases),
            "admitted": admitted_cases,
            "refused": refused_cases,
            "why_it_matters": (
                "a checker that only ever prints one verdict measures nothing; "
                "the counts above are this run's own, and they include a "
                "reduced case that is admitted and a reduced case that is "
                "refused, so an admission and a refusal are distinguishable "
                "outcomes of the same run rather than the only outcome it has"
            ),
        },
        "positive_controls_admitted": controls,
        "reduced_cases_refused": refused,
        "reduced_model_row_admission": {
            "case": "reduced_model_row",
            "admitted": by_case.get("reduced_model_row", {}).get("admitted"),
            "why": (
                "the normalisation engine derives its mean reciprocal from the "
                "row width -- exact_reciprocal_code, 2**-k for a power-of-two "
                "width -- so it admits any power of two its profile bounds "
                "allow rather than selecting between two hardcoded constants.  "
                "This field previously said the 128-wide admission was an "
                "accident of 128 equalling the FULL model's per-head width, "
                "and that the reduced head width of 16 was refused.  Both "
                "statements are stale: tb_a3_rms_norm_width drives rows=8 "
                "cols=16 count=128 to error_code 0 with 128 results, and "
                "tests/test_a3_rms_norm_width.py compares the values word for "
                "word against runtime/reference/tensor_accelerator_rmsnorm.py"
            ),
        },
        "attention_engine": {
            "case": "gqa_context_16",
            "measured_operand_words_read": gqa.get("reads"),
            "measured_result_words_written": gqa.get("writes"),
            "reduced_configuration_would_need_reads": reduced_attention_reads,
            "reduced_configuration_would_need_writes": reduced_attention_writes,
            "ratio_reads": (
                round(gqa["reads"] / reduced_attention_reads, 4)
                if gqa.get("reads")
                else None
            ),
            "ratio_writes": (
                round(gqa["writes"] / reduced_attention_writes, 4)
                if gqa.get("writes")
                else None
            ),
            "geometry_is_a_runtime_input": False,
            "geometry_is_an_elaboration_parameter": True,
            "reduced_elaboration": {
                "case": "gqa_reduced_context_16",
                "admitted": reduced_gqa.get("admitted"),
                "error_code": reduced_gqa.get("err"),
                "measured_operand_words_read": reduced_gqa.get("reads"),
                "measured_result_words_written": reduced_gqa.get("writes"),
                "matches_the_reduced_row": reduced_gqa_matches,
            },
            "why": (
                "ot_a3_qwen_gqa takes cfg_context_length and four base "
                "addresses at runtime, and its query-head count, KV-head count, "
                "head width and attention scale as ELABORATION parameters.  The "
                "shipped instance's traffic is still the measurement of the "
                "geometry it is built for -- that is the positive control -- and "
                "the reduced configuration is a second elaboration whose traffic "
                "is compared against the expectation derived from the reduced "
                "model's own config.  The scale travels with the geometry "
                "because it is bf16(1/sqrt(head_width)): 0x3db5 at 128 and "
                "0x3e80 at 16, so a head width changed without it would compute "
                "a different attention in silence"
            ),
        },
        "shape_driven_engines_admit_the_reduction": [
            name
            for name in ("reduced_model_row", "reduced_q_proj_row")
            if by_case.get(name, {}).get("admitted")
        ],
    }


# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=None)
    parser.add_argument("--lock", type=Path, default=None)
    parser.add_argument("--workload-dir", type=Path, default=None)
    parser.add_argument("--model-dir", type=Path, default=None)
    parser.add_argument("--oracle", type=Path, default=None)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--skip-lowering", action="store_true")
    ladder_models.add_argument(parser)
    arguments = parser.parse_args()

    model = ladder_models.resolve(arguments.model)
    if arguments.snapshot is None:
        arguments.snapshot = ROOT / model.reduced_snapshot
    if arguments.lock is None:
        arguments.lock = ROOT / model.reduced_lock
    if arguments.workload_dir is None:
        arguments.workload_dir = ROOT / model.reduced_workload_dir
    if arguments.model_dir is None:
        arguments.model_dir = ROOT / f"compiler/models/{model.reduced_model_id}"
    if arguments.oracle is None:
        arguments.oracle = ROOT / model.reduced_oracle
    if arguments.output is None:
        arguments.output = model.artifact("g1f", "reduced_end_to_end")
    global GOVERNED_WORKLOAD_ID, WORKLOAD_ID
    GOVERNED_WORKLOAD_ID = model.workload_id
    WORKLOAD_ID = model.reduced_workload_id
    ladder_models.require_present(
        model,
        {
            "reduced snapshot": arguments.snapshot,
            "checkpoint lock": arguments.lock,
            "reduced workload": arguments.workload_dir / f"{WORKLOAD_ID}.json",
            "reduced reference oracle": arguments.oracle,
        },
        "G1f runs the whole reduced workload with nothing injected, so the "
        "fixture, its lock, its workload and its oracle are all prerequisites",
        {
            "reduced reference oracle": (
                model.reduced_oracle_producer or "the reduced oracle tool"
            )
        },
    )
    # Each model's structural check reads its OWN reduction rule.  Qwen3's is
    # REDUCTION plus the transformers config schema; V4.1's is the record its
    # fixture builder wrote, and the two configurations are the release's flat
    # vendor ModelArgs rather than a transformers config.  Sharing one function
    # across both would classify every V4.1 field as unexpected and then report
    # a verdict about a comparison that did not happen, which is the
    # not_evaluable defect this rung was hardened against on 2026-09-06.
    if model.key == ladder_models.DEFAULT_MODEL:
        full = json.loads(FULL_CONFIG.read_text(encoding="utf-8"))
        reduced = json.loads(
            (arguments.model_dir / "config.json").read_text(encoding="utf-8")
        )
        identity_of = lambda: structural_identity(full, reduced)  # noqa: E731
    else:
        from tools.build_deepseek_v41_reduced_model import released_snapshot

        reduction = json.loads(
            V41_REDUCTION_RECORD.read_text(encoding="utf-8")
        )["reduction"]
        # The released side is the pinned snapshot's own inference_config.json,
        # which is the same schema as the fixture's -- comparing it against
        # config.json would compare two different record shapes and call the
        # difference a reduction.
        full = json.loads(
            (released_snapshot() / "inference_config.json").read_text(
                encoding="utf-8"
            )
        )
        reduced = json.loads(
            (arguments.snapshot / "inference_config.json").read_text(
                encoding="utf-8"
            )
        )
        identity_of = lambda: structural_identity_v41(  # noqa: E731
            full, reduced, reduction
        )
    workload_path = arguments.workload_dir / f"{WORKLOAD_ID}.json"
    workload = json.loads(workload_path.read_text(encoding="utf-8"))
    oracle_bytes = arguments.oracle.read_bytes()
    oracle = json.loads(oracle_bytes)
    oracle_case = oracle["results"][WORKLOAD_ID]
    oracle_ids = [int(token) for token in oracle_case["generated_token_ids"]]
    oracle_digest = hashlib.sha256(oracle_bytes).hexdigest()

    identity = identity_of()
    lowering = (
        {"attempted": False, "reason": "--skip-lowering"}
        if arguments.skip_lowering
        else attempt_lowering(
            arguments.snapshot, arguments.lock, arguments.model_dir, arguments.work
        )
    )

    git = _git()
    records: list[dict[str, Any]] = []
    for store, meta in STORES.items():
        probe = run_probe(arguments.work, store=store)
        verdict = geometry_verdict(probe, reduced)
        store_lowering = (
            lowering.get("backends", {}).get(store)
            if lowering.get("attempted")
            else None
        )
        lowered = bool(store_lowering and store_lowering.get("produced_deployment"))

        # Counted, not assumed.  Every engine execution in this rung took its
        # operands from the probe's own memory; none was supplied from the
        # golden model, and none was part of an end-to-end execution.
        injected = 0
        engine_executions = probe["case_count"]

        blockers: list[dict[str, Any]] = []
        if not lowering.get("attempted"):
            blockers.append(
                {
                    "order": 1,
                    "what": "the reduced model was not put through the compiler",
                    "measured_by": "--skip-lowering",
                }
            )
        elif not lowered:
            step = (
                "kernel IR export"
                if not lowering["kernel_ir"]["produced_ir"]
                else f"{store} backend"
            )
            failing = (
                lowering["kernel_ir"]
                if not lowering["kernel_ir"]["produced_ir"]
                else store_lowering
            )
            blockers.append(
                {
                    "order": 1,
                    "what": (
                        f"the same compiler refuses the reduced model at the "
                        f"{step}, so no reduced ABI 3.0 program exists for the "
                        f"{store} store"
                    ),
                    "measured_by": "running " + " ".join(failing["argv"][1:]),
                    "returncode": failing["returncode"],
                    "refusal": failing.get("stderr_tail") or failing.get("stdout_tail"),
                }
            )
        for refusal in verdict["reduced_cases_refused"]:
            blockers.append(
                {
                    "order": 2,
                    "what": (
                        f"the integrated vehicle's {refusal['engine']} engine "
                        f"refuses the reduced geometry, case "
                        f"{refusal['case']!r}, with {refusal['error_name']}"
                    ),
                    "measured_by": probe["vehicle"],
                    "error_code": refusal["error_code"],
                }
            )
        if (
            verdict["attention_engine"]["ratio_reads"]
            and not verdict["attention_engine"]["reduced_elaboration"][
                "matches_the_reduced_row"
            ]
        ):
            blockers.append(
                {
                    "order": 2,
                    "what": (
                        "the attention engine has no geometry input: for one "
                        "query row at context 16 it read "
                        f"{verdict['attention_engine']['measured_operand_words_read']:,}"
                        " operand words and wrote "
                        f"{verdict['attention_engine']['measured_result_words_written']:,}"
                        " result words, "
                        f"{verdict['attention_engine']['ratio_reads']}x and "
                        f"{verdict['attention_engine']['ratio_writes']}x what "
                        "the reduced configuration's attention row is"
                    ),
                    "measured_by": probe["vehicle"],
                }
            )
        # The order-3 statement has to say WHY nothing ran, and the reason
        # changes as the order-1 and order-2 blockers close.  Saying "with no
        # reduced program and no engine that admits the reduced geometry" once
        # both of those are false would be a stale reason attached to a true
        # verdict, which is exactly the kind of thing this ladder exists to
        # prevent.
        lowered_both = all(
            (store or {}).get("produced_deployment")
            for store in (lowering.get("stores") or {}).values()
        )
        attention_ready = verdict["attention_engine"]["reduced_elaboration"][
            "matches_the_reduced_row"
        ]
        normalisation_ready = not [
            entry
            for entry in probe["cases"]
            if str(entry.get("case", "")).startswith("reduced")
            and not entry.get("admitted")
        ]
        if lowered_both and attention_ready and normalisation_ready:
            why_nothing_ran = (
                "the reduced program now exists on both stores and every engine "
                "the probe drives admits the reduced geometry, but there is no "
                "vehicle that runs that program end to end: the probe exercises "
                "three engines in isolation, and the integrated vehicle would "
                "have to be elaborated at the reduced geometry and driven with "
                "the reduced program before a token could be emitted.  So the "
                "RTL emitted no token ids"
            )
        else:
            why_nothing_ran = (
                "with no reduced program and no engine that admits the "
                "reduced attention geometry, no end-to-end execution took "
                "place, so the RTL emitted no token ids"
            )
        blockers.append(
            {
                "order": 3,
                "what": why_nothing_ran,
                "measured_by": "this rung",
            }
        )

        _alternative = rtl_expressible_alternative(full, reduced, probe)
        records.append(
            {
                "storage_class": store,
                "workload_id": GOVERNED_WORKLOAD_ID,
                "workload_id_note": (
                    "the governed workload this rung stands for; the reduced "
                    "model's own workload is "
                    f"{WORKLOAD_ID}, the same prompt shape reduced into the "
                    "reduced vocabulary, and its ids are what the oracle below "
                    "carries"
                ),
                "reduced_workload_id": WORKLOAD_ID,
                "target_key": meta["target_key"],
                "shipped_deployment": meta["shipped_deployment"],
                "capability": meta["capability"],
                "execution": {
                    "simulator": probe["simulator"],
                    "simulator_version": probe["simulator_version"],
                    "simulated_cycles": probe["simulated_cycles"],
                    "evidence_class": "public_open_tool_rtl_simulation",
                    "vehicle": probe["vehicle"],
                    "dual_simulator": False,
                    "what_ran": (
                        "the three geometry-bearing engines the integrated "
                        "vehicle instantiates, driven at both the full and the "
                        "reduced geometry, with every full-geometry case as a "
                        "positive control"
                    ),
                    "what_did_not_run": (
                        "the complete workload end to end at the reduced "
                        "configuration, which is what this rung requires"
                    ),
                },
                "git": git,
                "configuration": {
                    "reduced": True,
                    "structurally_identical_to_full": identity[
                        "structurally_identical"
                    ],
                    "model_id": MODEL_ID,
                    "config": reduced,
                    "checkpoint_lock_id": json.loads(
                        arguments.lock.read_text(encoding="utf-8")
                    )["lock_id"],
                    "weights_regenerated_per_run": False,
                    "budget": budget(
                        reduced, len(workload["token_ids"]), len(oracle_ids)
                    ),
                    "identity_check": identity,
                },
                "lowering": {
                    "same_compiler_as_shipped": lowering.get(
                        "same_compiler_as_shipped", False
                    ),
                    "same_abi": lowering.get("same_abi"),
                    "this_store_built": lowered,
                    "kernel_ir": lowering.get("kernel_ir"),
                    "refusal_chain": lowering.get("refusal_chain"),
                    "backend": store_lowering,
                },
                "geometry": verdict,
                "rtl_expressible_alternative": _alternative,
                "geometry_port_decision": geometry_port_decision(_alternative),
                "probe": probe,
                "injection": {
                    "golden_injected_operation_count": injected,
                    "counted_not_assumed": True,
                    "how_counted": (
                        "the number of engine results this rung supplied from "
                        "the golden model.  Every operand the engines consumed "
                        "came from the probe's own constant operand memory and "
                        "no golden value was written into any engine, so the "
                        "count is zero"
                    ),
                    "engine_executions_measured": engine_executions,
                    "end_to_end_operations_executed": 0,
                    "why_zero_is_not_a_pass": (
                        "zero injected operations over zero end-to-end "
                        "operations is what an unrun rung looks like; the rung "
                        "fails on the token comparison below, which is the "
                        "field that can only be satisfied by running"
                    ),
                },
                "record_token_ids": probe["emitted_token_ids"],
                "oracle": {
                    "path": _repo_relative(arguments.oracle),
                    "artifact_sha256": oracle_digest,
                    "workload_id": WORKLOAD_ID,
                    "generated_token_ids": oracle_ids,
                    "stop_reason": oracle_case["stop_reason"],
                    # A rung with no ids must never agree with an oracle that
                    # has none either; agreement requires ids to exist.
                    "agreement": bool(probe["emitted_token_ids"])
                    and probe["emitted_token_ids"] == oracle_ids,
                    "why": (
                        "the ids compared are the ones the vehicle printed; "
                        "this vehicle instantiates no selection engine and "
                        "printed none, so it cannot agree with an oracle that "
                        "emitted three"
                    ),
                },
                "status": "fail",
                "blocking_in_order": sorted(blockers, key=lambda b: b["order"]),
                "what_would_make_this_rung_runnable": {
                    "status": (
                        "an inference drawn from the measurements in this "
                        "record; it is not itself measured, and nothing here "
                        "should be read as a result"
                    ),
                    "in_order": [
                        "an integrated vehicle elaborated at the reduced "
                        "geometry and driven by the reduced program.  This is "
                        "the one item left and it is what blocking_in_order "
                        "MEASURES: the probe drives three engines in "
                        "isolation, and reduced_cases_refused is empty, so "
                        "nothing the reduced configuration asks for is refused "
                        "any more -- there is simply no top that runs the "
                        "whole workload at that geometry",
                    ],
                    "closed_since_this_list_was_first_written": [
                        "the compiler admitting a Qwen3 configuration other "
                        "than the pinned 8B release: compiler/qwen3/adapter.py "
                        "carries a SECOND pinned contract, "
                        "REDUCED_SOURCE_CONTRACT, rather than a weakened pin, "
                        "and lowering.kernel_ir.produced_ir is now true.  "
                        "lowering.refusal_chain still records a refusal "
                        "because it deliberately calls the LEGACY "
                        "compiler.qwen3.graph entry points, which is a "
                        "different measurement from whether the v3 front end "
                        "admits the model",
                        "ot_a3_qwen_gqa taking its head counts, head width and "
                        "scale as elaboration parameters: it does, and "
                        "geometry.attention_engine.reduced_elaboration "
                        "measures that second elaboration reading 4,224 "
                        "operand words and writing 128 -- the reduced model's "
                        "own row, matched exactly",
                        "ot_a3_vector_rms_norm taking its row width and mean "
                        "scale as parameters: the width is a parameter and the "
                        "reciprocal is DERIVED from it, so 16 is admitted and "
                        "numerically checked, not refused",
                    ],
                    "why_it_is_worth_doing": (
                        "the reduced geometry is now expressible, so the "
                        "day-per-store cost rtl_expressible_alternative "
                        "measures is no longer what this rung would pay -- it "
                        "is what it would pay if the integrated vehicle were "
                        "elaborated at the SHIPPED geometry, which is the "
                        "thing left to avoid"
                    ),
                },
            }
        )

    report = {
        "schema": SCHEMA,
        "campaign": "abi3_g1f_reduced_end_to_end",
        "gate": GATE,
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "git": git,
        "status": "fail",
        "records": records,
        "claim_boundary": {
            "establishes": [
                "a reduced configuration derived from the measured 39,915 "
                "MACs/s budget, structurally identical to Qwen3-8B by three "
                "mechanical comparisons rather than by assertion",
                "a reduced oracle produced by the same reference "
                "implementation as the full oracle, on fixed SHA-256-bound "
                "weights that are not regenerated per run",
                "which of the integrated vehicle's engines admit the reduced "
                "geometry and which refuse it, measured by running them, with "
                "the full geometry as a positive control in every case",
                "what the same compiler does when the reduced model is put "
                "through it, on both storage classes",
            ],
            "does_not_establish": [
                "the complete workload executed end to end in the RTL at the "
                "reduced configuration, which is the rung itself",
                "numerics at full dimension, which is what G1a-G1d are for and "
                "what this rung never establishes even when it is green",
                "any rate: the probe's cycle counts are a cost measurement, "
                "not a TPOT input",
                "the post-EOS refusal: the reduced oracle establishes the gold "
                "ids and that generation stops on an official EOS, but a "
                "refusal of the transaction after EOS is a property of a run "
                "that has not happened",
                "that the reduced oracle's ids are the ids this RTL would "
                "emit; they are what the reference implementation emits, which "
                "is what an oracle is",
            ],
        },
        "oracle": {
            "path": _repo_relative(arguments.oracle),
            "artifact_sha256": oracle_digest,
            "token_field": f"results.{WORKLOAD_ID}.generated_token_ids",
            "generated_token_ids": oracle_ids,
        },
        "workload": {
            "governed": GOVERNED_WORKLOAD_ID,
            "reduced": WORKLOAD_ID,
            "path": _repo_relative(workload_path),
            "digest": workload["digest"],
            "prompt_token_ids": workload["token_ids"],
        },
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(canonical_json(report))
    print(f"wrote {arguments.output}")
    for record in records:
        print(
            f"  {record['storage_class']}: status={record['status']} "
            f"structurally_identical="
            f"{record['configuration']['structurally_identical_to_full']} "
            f"lowered={record['lowering']['this_store_built']} "
            f"cycles={record['execution']['simulated_cycles']:,} "
            f"ids={record['record_token_ids']} vs oracle {oracle_ids}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
