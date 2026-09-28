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
    assert record["instruction_count"] == len(record["instruction_trace"]) == 111
    assert [row["pc"] for row in record["instruction_trace"]] == list(range(111))
    assert all(isinstance(row["fields"]["unit"], int) and
               isinstance(row["reads"], list) and isinstance(row["writes"], list)
               for row in record["instruction_trace"])
    assert record["source_experts"] == [110, 112, 141, 144, 357, 361]
    assert all(x["backed"] for x in record["qe_address_trace"])
    assert any("FP4 QE" in x for x in record["blockers"])
    assert any("RoPE" in x and "production" in x for x in record["blockers"])
    assert record["rope_token_patch"]["absolute_first_word"] == 6_412_548
    assert record["resource_trace"]["qe_direct_expanded_bytes"] > record["resource_trace"]["rom_capacity_bytes"]
    assert record["resource_trace"]["packed_die_bytes"] < record["resource_trace"]["rom_capacity_bytes"]
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
    assert set(pairs) == {("exp.w1", 64_640 + 110 * 6400),
                          ("exp.w3", 2_522_240 + 110 * 6400)}


def test_missing_selected_expert_fails_before_isa_emit(tmp_path):
    layout = json.loads(B.DEFAULT_QE.read_text())
    del layout["matrices"]["exp141.w2"]
    path = tmp_path / "qe.json"
    path.write_text(json.dumps(layout))
    with pytest.raises(ValueError, match="exp141.w2"):
        B.bind(B.DEFAULT_LAYOUT, B.DEFAULT_SHARD, path)


def test_expert_stride_must_match_placed_id(tmp_path):
    layout = json.loads(B.DEFAULT_QE.read_text())
    layout["matrices"]["exp110.w1"]["expert_stride_words"] = 1
    path = tmp_path / "qe.json"
    path.write_text(json.dumps(layout))
    with pytest.raises(ValueError, match="expert family w1"):
        B.bind(B.DEFAULT_LAYOUT, B.DEFAULT_SHARD, path)


def test_w2_may_have_a_different_expert_stride(tmp_path):
    record = B.bind(B.DEFAULT_LAYOUT, B.DEFAULT_SHARD)
    assert record["status"] == "blocked"  # physical FP4 port remains unimplemented
    assert {x["start_word"] for x in record["qe_address_trace"]
            if x["matrix"] == "exp.w2" and x["expert_id"] == 110} == {4_979_840 + 110 * 5760}
