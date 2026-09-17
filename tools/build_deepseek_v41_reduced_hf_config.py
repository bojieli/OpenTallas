#!/usr/bin/env python3
"""Write the reduced V4.1 model's HuggingFace-shaped ``config.json``.

WHY THIS EXISTS. ``compiler/frontends/v3/deepseek_v41.py`` exports from the
HuggingFace config's architecture section -- ``released_architecture_config``
resolves ``text_config`` and ``validate_architecture_pins`` confronts every
width it sizes by. The reduced regression model carries only
``inference_config.json``, DeepSeek's own runtime form, so the front end cannot
see it at all. This translates one into the other.

THE MAPPING IS AUTHORED AND THEN TESTED, not inferred. Three classes of field:

* the same name in both forms;
* a different name. The first eight of these are the committed cross-check in
  ``compiler/frontend/deepseek_v4_graph.py``'s ``expected_values``, which the
  V4 front end already refuses to proceed past when the two forms disagree; the
  rest follow the same ``_id``/``_ids``/plural convention;
* HuggingFace-framework fields with no runtime counterpart at all, carried from
  the released config unchanged because they do not vary with width.

DO NOT DERIVE THIS MAP BY VALUE-MATCHING THE RELEASED PAIR. Both released files
are committed, and matching them by value looks like free evidence -- 31 names
agree and 17 more match by value -- but at least one of those is FALSE:
``num_key_value_heads`` and ``beta_slow`` are paired only because both equal 1,
where ``beta_slow`` is a YaRN parameter that belongs inside ``rope_scaling``. A
spurious pair here is worse than a refusal, because it produces a reduced model
that compiles and computes a different architecture.

THE TEST IS THAT THE MAP REPRODUCES THE RELEASED text_config EXACTLY from the
released inference config -- all 59 fields, byte for byte in value. Only then is
it applied to the reduced one. ``tests/test_deepseek_v41_reduced_hf_config.py``
runs that check, so the map cannot drift without a failure.

ONE PAIR CANNOT BE TESTED THAT WAY and is marked. The released inference config
carries no ``max_seq_len`` at all, so ``max_position_embeddings`` has no source
in the released pair. The reduced one does carry it, recorded by
``results/abi3/deepseek_v41_reduced_model.json`` as DERIVED -- "the workload's
prompt length plus its cap, rounded up to the largest compress ratio" -- and the
naming correspondence is supported by a pair that IS tested,
``original_seq_len`` against ``rope_scaling.original_max_position_embeddings``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
RELEASED = ROOT / "compiler/models/deepseek-v4.1-flash"
REDUCED = ROOT / "compiler/models/deepseek-v4.1-flash-reduced-v1"
REDUCTION_RECORD = ROOT / "results/abi3/deepseek_v41_reduced_model.json"


class ConfigTranslationError(RuntimeError):
    """Raised when the map does not reproduce the released architecture."""


#: The same name in both forms.
SAME_NAME = (
    "candidate_block_size", "candidate_topk_blocks", "compress_ratios",
    "compress_rope_theta", "dspark_block_size", "dspark_markov_rank",
    "dspark_n_routed_experts", "dspark_noise_token_id",
    "dspark_target_layer_ids", "engram_compressed_vocab_size",
    "engram_head_dim", "engram_layer_ids", "engram_max_ngram_size",
    "engram_n_heads", "engram_num_embeddings", "engram_vocab_size", "hc_eps",
    "hc_mult", "hc_sinkhorn_iters", "head_dim", "index_head_dim",
    "index_n_heads", "index_topk", "n_routed_experts", "n_shared_experts",
    "o_groups", "o_lora_rank", "q_lora_rank", "rope_theta", "swiglu_limit",
    "vocab_size",
)

#: huggingface_name <- inference_name. The first eight are
#: compiler/frontend/deepseek_v4_graph.py's own committed cross-check.
RENAMED: Mapping[str, str] = {
    "hidden_size": "dim",
    "moe_intermediate_size": "moe_inter_dim",
    "num_experts_per_tok": "n_activated_experts",
    "num_attention_heads": "n_heads",
    "num_hidden_layers": "n_layers",
    "routed_scaling_factor": "route_scale",
    "scoring_func": "score_func",
    "sliding_window": "window_size",
    "candidate_source_layer_id": "candidate_source_layer",
    "dspark_num_experts_per_tok": "dspark_n_activated_experts",
    "engram_pad_token_id": "engram_pad_id",
    "index_source_layer_ids": "index_source_layers",
    "kv_source_layer_ids": "kv_source_layers",
    "num_nextn_predict_layers": "n_mtp_layers",
    "qk_rope_head_dim": "rope_head_dim",
    "rms_norm_eps": "norm_eps",
}

#: Untestable against the released pair, because the released inference config
#: carries no source for it. Falls back to the released value when absent, which
#: is what keeps the released-pair test meaningful.
OPTIONAL: Mapping[str, str] = {"max_position_embeddings": "max_seq_len"}

#: The vision tower's own section, hf_name <- inference_name. Verified against
#: the released pair exactly like the architecture map, all ten fields.
VISION: Mapping[str, str] = {
    "num_hidden_layers": "vision_n_layers",
    "hidden_size": "vision_dim",
    "num_attention_heads": "vision_n_heads",
    "intermediate_size": "vision_inter_dim",
    "patch_size": "vision_patch_size",
    "rope_theta": "vision_rope_theta",
    "downsample_ratio": "vision_downsample_ratio",
    "max_image_tokens": "vision_max_n_token",
    "min_pixels": "vision_min_pixels",
    "max_wh_ratio": "vision_max_wh_ratio",
}

#: No runtime counterpart in either form; carried unchanged.
CARRIED = (
    "attention_bias", "attention_dropout", "hidden_act", "initializer_range",
    "model_type", "norm_topk_prob", "num_key_value_heads",
    "tie_word_embeddings", "topk_method", "use_cache",
)


def translate_architecture(
    inference: Mapping[str, Any], released_text: Mapping[str, Any]
) -> dict[str, Any]:
    """One inference config as a HuggingFace architecture section."""

    out: dict[str, Any] = {}
    for key in SAME_NAME:
        out[key] = inference[key]
    for hf_key, inf_key in RENAMED.items():
        out[hf_key] = inference[inf_key]
    for key in CARRIED:
        out[key] = released_text[key]
    for hf_key, inf_key in OPTIONAL.items():
        out[hf_key] = (
            inference[inf_key] if inf_key in inference else released_text[hf_key]
        )
    #: YaRN's parameters live flattened in the runtime form.
    scaling = dict(released_text["rope_scaling"])
    scaling["factor"] = inference["rope_factor"]
    scaling["beta_fast"] = inference["beta_fast"]
    scaling["beta_slow"] = inference["beta_slow"]
    scaling["original_max_position_embeddings"] = inference["original_seq_len"]
    out["rope_scaling"] = scaling
    return out


def translate_vision(
    inference: Mapping[str, Any], released_vision: Mapping[str, Any]
) -> dict[str, Any]:
    """One inference config's vision fields as a HuggingFace vision section."""

    out = {"model_type": released_vision["model_type"]}
    for hf_key, inf_key in VISION.items():
        out[hf_key] = inference[inf_key]
    return out


def prove_against_released() -> dict[str, Any]:
    """Reproduce the released architecture section from the released runtime one."""

    released_root = json.loads((RELEASED / "config.json").read_text())
    released_text = released_root["text_config"]
    released_inference = json.loads(
        (RELEASED / "inference_config.json").read_text()
    )
    rebuilt = translate_architecture(released_inference, released_text)
    missing = sorted(set(released_text) - set(rebuilt))
    extra = sorted(set(rebuilt) - set(released_text))
    differing = sorted(
        key for key in set(released_text) & set(rebuilt)
        if released_text[key] != rebuilt[key]
    )
    if missing or extra or differing:
        raise ConfigTranslationError(
            "the map does not reproduce the released architecture section: "
            f"missing={missing} extra={extra} differing={differing}"
        )
    released_vision = released_root["vision_config"]
    rebuilt_vision = translate_vision(released_inference, released_vision)
    vision_differs = sorted(
        key for key in set(released_vision) | set(rebuilt_vision)
        if released_vision.get(key) != rebuilt_vision.get(key)
    )
    if vision_differs:
        raise ConfigTranslationError(
            "the map does not reproduce the released vision section: "
            f"differing={vision_differs}"
        )
    return {
        "fields_reproduced": len(released_text),
        "vision_fields_reproduced": len(released_vision),
        "released_config_is_reproduced_exactly": True,
    }


def build_reduced_root() -> dict[str, Any]:
    """The reduced model's config.json, every field justified."""

    released_root = json.loads((RELEASED / "config.json").read_text())
    released_text = released_root["text_config"]
    reduced_inference = json.loads(
        (REDUCED / "inference_config.json").read_text()
    )
    reduction = json.loads(REDUCTION_RECORD.read_text())["reduction"]

    quantization = dict(released_root["quantization_config"])
    #: The reduction's own record: "config.json
    #: quantization_config.weight_block_size; the release's own act_quant
    #: asserts N % block_size == 0, so it is the floor and the granularity of
    #: every reduced width".
    block = int(reduction["quantization_block"])
    quantization["weight_block_size"] = [block, block]
    quantization["expert_dtype"] = reduced_inference["expert_dtype"]

    root = {
        "architectures": released_root["architectures"],
        "bos_token_id": released_root["bos_token_id"],
        #: root dtype is the checkpoint's storage dtype and is NOT the runtime
        #: form's dtype: the release states bfloat16 here and fp8 there, so this
        #: is carried rather than mapped.
        "dtype": released_root["dtype"],
        "eos_token_id": released_root["eos_token_id"],
        #: kept_exactly in the reduction record, and never on a text token's
        #: decode path.
        "image_token_id": reduced_inference["image_token_id"],
        "model_type": released_root["model_type"],
        "pad_token_id": released_root["pad_token_id"],
        "quantization_config": quantization,
        "text_config": translate_architecture(reduced_inference, released_text),
        "transformers_version": released_root["transformers_version"],
    }
    #: NO vision_config, and that is now sayable. The reduction excludes the
    #: tower -- reduced_vision_n_layers 0 against the release's 32, the workload
    #: being text only -- and the adapter reads the section's presence in the
    #: CONFIG as ``vision_enabled``, so a config without one derives neither the
    #: tower's tensors nor the bias_vl that rides with it.
    #:
    #: This file first wrote a zero-layer tower instead, because
    #: build_official_tensor_specs refuses a RECORD that pins no vision section
    #: -- such a record cannot say whether the release has a tower. But a
    #: zero-layer tower still sets vision_enabled, so 53 vision and
    #: vision-language tensors were derived that the checkpoint does not hold.
    #: A release record can now pin a section ABSENT, which answers "can this
    #: record speak about the tower" yes and "does the release have one" no,
    #: and validate_official_config refuses a config that carries a section
    #: pinned absent -- so absence is asserted rather than merely unmentioned.
    return root


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=REDUCED / "config.json")
    ap.add_argument("--print-only", action="store_true")
    args = ap.parse_args()

    proof = prove_against_released()
    print(f"map reproduces the released config exactly: "
          f"{proof['fields_reproduced']} architecture fields and "
          f"{proof['vision_fields_reproduced']} vision fields")

    root = build_reduced_root()
    text = json.dumps(root, indent=2, sort_keys=True) + "\n"
    if args.print_only:
        print(text)
        return 0
    args.output.write_text(text)
    print(f"wrote {args.output} ({len(text)} bytes)")
    architecture = root["text_config"]
    for key in ("hidden_size", "num_hidden_layers", "num_attention_heads",
                "num_key_value_heads", "head_dim", "moe_intermediate_size",
                "n_routed_experts", "vocab_size", "index_topk",
                "max_position_embeddings"):
        print(f"  {key:<26} {json.dumps(architecture[key])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
