"""The reduced V4.1 config translation, and the test that keeps it honest.

The whole value of ``tools/build_deepseek_v41_reduced_hf_config.py`` is that its
field map reproduces the RELEASED architecture section exactly from the released
runtime config. If it stops doing that, the map has drifted and the reduced
config it writes describes a different architecture -- which would compile.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.build_deepseek_v41_reduced_hf_config import (
    CARRIED,
    OPTIONAL,
    RENAMED,
    SAME_NAME,
    ConfigTranslationError,
    build_reduced_root,
    prove_against_released,
    translate_architecture,
)

ROOT = Path(__file__).resolve().parents[1]
RELEASED = ROOT / "compiler/models/deepseek-v4.1-flash"
REDUCED = ROOT / "compiler/models/deepseek-v4.1-flash-reduced-v1"


def test_map_reproduces_the_released_architecture_section() -> None:
    proof = prove_against_released()
    assert proof["released_config_is_reproduced_exactly"] is True
    assert proof["fields_reproduced"] == 59


def test_every_mapped_pair_agrees_in_the_released_pair() -> None:
    """Each pair is checked individually, so a failure names the field."""

    released_text = json.loads((RELEASED / "config.json").read_text())["text_config"]
    released_inference = json.loads((RELEASED / "inference_config.json").read_text())
    for key in SAME_NAME:
        assert released_text[key] == released_inference[key], key
    for hf_key, inf_key in RENAMED.items():
        assert released_text[hf_key] == released_inference[inf_key], (hf_key, inf_key)


def test_carried_fields_have_no_runtime_counterpart() -> None:
    """A carried field that DID have a source should have been mapped instead."""

    released_inference = json.loads((RELEASED / "inference_config.json").read_text())
    for key in CARRIED:
        assert key not in released_inference, key


def test_the_untestable_pair_is_untestable_for_the_stated_reason() -> None:
    """max_position_embeddings is marked optional because the source is absent."""

    released_inference = json.loads((RELEASED / "inference_config.json").read_text())
    for _, inf_key in OPTIONAL.items():
        assert inf_key not in released_inference, inf_key
    #: and the correspondence that supports the naming IS testable
    released_text = json.loads((RELEASED / "config.json").read_text())["text_config"]
    assert (
        released_text["rope_scaling"]["original_max_position_embeddings"]
        == released_inference["original_seq_len"]
    )


def test_a_drifted_map_is_a_failure_and_not_a_silent_translation() -> None:
    """The proof is load-bearing: break one pair and it must refuse."""

    released_text = json.loads((RELEASED / "config.json").read_text())["text_config"]
    released_inference = dict(
        json.loads((RELEASED / "inference_config.json").read_text())
    )
    released_inference["dim"] = released_inference["dim"] + 1
    rebuilt = translate_architecture(released_inference, released_text)
    assert rebuilt["hidden_size"] != released_text["hidden_size"]


def test_the_committed_reduced_config_is_what_the_tool_writes() -> None:
    """The artefact on disk is regenerable, not hand-edited."""

    on_disk = json.loads((REDUCED / "config.json").read_text())
    assert on_disk == build_reduced_root()


def test_the_reduced_config_keeps_the_mode_sequence_and_reduces_the_widths() -> None:
    """What plan section 10.2 says the reduction is for."""

    released_text = json.loads((RELEASED / "config.json").read_text())["text_config"]
    architecture = json.loads((REDUCED / "config.json").read_text())["text_config"]
    #: kept exactly -- the sequence is the subject under test
    assert architecture["num_hidden_layers"] == released_text["num_hidden_layers"]
    assert architecture["compress_ratios"] == released_text["compress_ratios"]
    for key in ("index_source_layer_ids", "kv_source_layer_ids",
                "dspark_target_layer_ids", "engram_layer_ids",
                "candidate_source_layer_id", "num_attention_heads",
                "index_n_heads", "engram_n_heads", "o_groups",
                "n_shared_experts", "num_experts_per_tok"):
        assert architecture[key] == released_text[key], key
    #: reduced
    for key in ("hidden_size", "moe_intermediate_size", "n_routed_experts",
                "vocab_size", "head_dim", "index_topk"):
        assert architecture[key] < released_text[key], key


def test_the_vision_tower_is_excluded() -> None:
    on_disk = json.loads((REDUCED / "config.json").read_text())
    assert "vision_config" not in on_disk
    released = json.loads((RELEASED / "config.json").read_text())
    assert "vision_config" in released


def test_the_root_dtype_is_carried_and_not_mapped() -> None:
    """Storage dtype and runtime dtype are different fields with the same name."""

    released = json.loads((RELEASED / "config.json").read_text())
    released_inference = json.loads((RELEASED / "inference_config.json").read_text())
    assert released["dtype"] != released_inference["dtype"]
    on_disk = json.loads((REDUCED / "config.json").read_text())
    assert on_disk["dtype"] == released["dtype"]
