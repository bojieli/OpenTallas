"""Fail-closed admission for the shipped layer-0 program and sparse images."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_fullshape_program_bind as B  # noqa: E402


def test_current_layout_is_not_misreported_as_executable():
    record = B.bind(B.DEFAULT_LAYOUT, B.DEFAULT_SHARD)
    assert record["status"] == "blocked"
    assert record["matrix_count"] == 29
    assert record["source_experts"] == [110, 112, 141, 144, 357, 361]
    assert any("wq_a" in x and "image ends" in x for x in record["blockers"])
    assert any("RoPE plain" in x for x in record["blockers"])
    assert len(record["me_wo_a_trace"]) == 2
    assert [x["image_start_word"] for x in record["me_wo_a_trace"]] == [7680, 73216]
    assert [x["x_first"] for x in record["me_wo_a_trace"]] == [74272, 78368]
    assert all(x["x_first"] == x["required_x_first"] and
               x["output_first"] == x["required_output_first"] and
               x["image_start_word"] == x["expected_image_start_word"] and
               x["xjs"] == 0 for x in record["me_wo_a_trace"])
    # Gate and up have different QE base regions and disjoint VM outputs.
    pairs = [(x["matrix"], x["start_word"]) for x in record["qe_address_trace"]
             if x["expert_id"] == 110 and x["matrix"] in ("exp.w1", "exp.w3")]
    assert set(pairs) == {("exp.w1", 174080), ("exp.w3", 727040)}


def test_missing_selected_expert_fails_before_isa_emit(tmp_path):
    layout = json.loads(B.DEFAULT_LAYOUT.read_text())
    del layout["matrices"]["exp141.w2"]
    path = tmp_path / "layout.json"
    path.write_text(json.dumps(layout))
    with pytest.raises(ValueError, match="exp141.w2"):
        B.bind(path, B.DEFAULT_SHARD)


def test_expert_stride_must_match_placed_id(tmp_path):
    layout = json.loads(B.DEFAULT_LAYOUT.read_text())
    layout["matrices"]["exp110.w1"]["expert_stride_words"] = 1
    path = tmp_path / "layout.json"
    path.write_text(json.dumps(layout))
    with pytest.raises(ValueError, match="expert family w1"):
        B.bind(path, B.DEFAULT_SHARD)


def test_w2_may_have_a_different_expert_stride(tmp_path):
    layout = json.loads(B.DEFAULT_LAYOUT.read_text())
    for expert in layout["selected_expert_ids"]:
        item = layout["matrices"][f"exp{expert}.w2"]
        item["expert_stride_words"] = 5760
        item["base_word"] = item["expert_id_base"] + expert * 5760
        item["geometry"]["base_word"] = item["base_word"]
        item["geometry"]["end_word_exclusive"] = item["base_word"] + item["word_count"]
    path = tmp_path / "layout.json"
    path.write_text(json.dumps(layout))
    record = B.bind(path, B.DEFAULT_SHARD)
    assert record["status"] == "blocked"  # old 64-bank layout still cannot feed QE
    assert {x["start_word"] for x in record["qe_address_trace"]
            if x["matrix"] == "exp.w2" and x["expert_id"] == 110} == {1121600 + 110 * 5760}
