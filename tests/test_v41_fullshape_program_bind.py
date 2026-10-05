"""Fail-closed admission for the shipped layer-0 program and sparse images."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_fullshape_program_bind as B  # noqa: E402
import hdc_replay_v41 as R  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402


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
    # 12532 (the CROM word after pre0; the rank-sliced sink freed 48 words) + 199999 * 32
    assert record["rope_token_patch"]["absolute_first_word"] == 6_412_500
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


def test_production_rope_has_blocking_prefetch_tagged_reads_and_su_drain():
    record = B.bind(B.DEFAULT_LAYOUT, B.DEFAULT_SHARD, rope_mode="hbm_cache")
    assert record["instruction_count"] == 113
    assert record["rope_token_patch"] is None
    assert record["rope_patch_sha256"] is None
    rope = record["rope_hbm_table"]
    assert rope["storage"] == "hbm_read_only_table"
    assert rope["physical_region_base_sector"] is None
    assert rope["full_table_image_sha256"] is None
    assert (rope["prefetch_pc"], rope["su_read_pcs"], rope["release_pc"]) == (18, [19, 23, 35], 36)
    instructions = record["instruction_trace"]
    assert instructions[18]["fields"]["ctl"] == 5
    assert instructions[18]["fields"]["ctl_lane"] == 0
    assert instructions[18]["fields"]["ctl_slot"] == 0
    assert instructions[36]["fields"]["ctl"] == 6
    assert instructions[36]["fields"]["wait"] & 2  # SU is drained before release
    for pc in rope["su_read_pcs"]:
        f = instructions[pc]["fields"]
        assert f["b_base"] == f["d_base"] == 2 << 28
        assert f["b_d"] == f["d_d"] == 2  # DYN.ROPE = absolute position * 32
    assert "full-position table image" in " ".join(record["blockers"])


def test_unknown_rope_mode_fails_closed():
    with pytest.raises(ValueError, match="unknown RoPE mode"):
        B.bind(B.DEFAULT_LAYOUT, B.DEFAULT_SHARD, rope_mode="unverified")


def test_yarn_rope_reads_use_distinct_cache_kind_tag():
    lay = R.ShapeLayout(R.SHIPPED, tp_exact=True, rope_storage="hbm_cache")
    builder = R.ShapeBuilder(lay)
    builder.rope("Q", lay.vm.map["Q"], 1, 512, "rope_yarn", I.DYN["ROPE"], False, "probe")
    fields = builder.prog[-1][0]
    assert fields["b_base"] == fields["d_base"] == 3 << 28
    assert fields["b_d"] == fields["d_d"] == I.DYN["ROPE"]
    assert fields["b_half"] == fields["c_pair"] == 1
