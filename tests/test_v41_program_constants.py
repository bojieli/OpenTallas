"""Every immediate of the production V4.1 L0 program comes from the checked constants manifest.

The manifest (results/rtl/v41_program_constants.json) is derived from the model's inference_config.json and
the golden's own source by tools/v41_program_constants.py; these tests fail if the manifest drifts from its
sources, or if any encoded program word (results/rtl/hdc_v41x_fullshape_l0_program.hex) carries an immediate
that differs from -- or is not sourced in -- the manifest.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa_v41 as I  # noqa: E402
import hdc_replay_v41 as R  # noqa: E402
import v41_program_constants as KC  # noqa: E402

PROGRAM = ROOT / "results/rtl/hdc_v41x_fullshape_l0_program.hex"
BINDS = [ROOT / "results/rtl/hdc_v41x_fullshape_program_bind_rope_hbm.json",
         ROOT / "results/rtl/hdc_v41x_fullshape_1m_program_bind_rope_hbm.json"]
CONFIG = json.loads((ROOT / "compiler/models/deepseek-v4.1-flash/inference_config.json").read_text())
IMMS = ("imm1", "imm2", "imm3")
# The fixes of 2026-09-30 (field, PCs, manifest constant): the task's defect list, pinned independently of
# the emitter's own annotations.
EXPECTED = [("imm1", [30], "attn_scale"), ("imm2", [25, 74], "hc_eps"), ("imm2", [26, 75], "hc_post_scale"),
            ("imm3", [56, 70, 80, 85, 90, 95, 98], "swiglu_limit"), ("imm2", [64], "router_den_eps"),
            ("imm1", [65], "route_scale"), ("imm2", [0, 5, 12, 16, 46, 51], "norm_eps"),
            ("imm1", [0, 46], "count_hc_dim"), ("imm1", [5, 51], "count_dim"), ("imm1", [12], "count_q_rank"),
            ("imm1", [16], "count_head_dim")]


def words():
    return [I.decode(int(x, 16), full_shape=True) for x in PROGRAM.read_text().split()]


def consts():
    return KC.load("deepseek-v4.1-flash")


def test_manifest_is_derived_from_its_sources():
    old = json.loads(KC.OUT.read_text())
    new = KC.build()
    skip = {"tool_sha256"} | ({"release_config_crosscheck"} if new["release_config_crosscheck"] is None else set())
    assert {k: v for k, v in old.items() if k not in skip} == {k: v for k, v in new.items() if k not in skip}


def test_manifest_values_follow_the_config_and_golden():
    c = consts()
    f32 = lambda x: f"0x{int(np.float32(x).view(np.uint32)):08x}"  # noqa: E731
    assert c["norm_eps"]["f32_bits"] == f32(CONFIG["norm_eps"]) == "0x1e3ce508"
    assert c["hc_eps"]["f32_bits"] == f32(CONFIG["hc_eps"])
    assert c["swiglu_limit"]["value"] == CONFIG["swiglu_limit"] == 10.0
    assert c["route_scale"]["value"] == CONFIG["route_scale"] == 1.5
    assert c["attn_scale"]["f32_bits"] == f32(CONFIG["head_dim"] ** -0.5) == "0x3d3504f3"
    assert c["hc_post_scale"]["value"] == 2.0 and c["router_den_eps"]["f32_bits"] == f32(1e-20)
    man = json.loads(KC.OUT.read_text())["models"]["deepseek-v4.1-flash"]
    assert man["config_sha256"] == KC.sha(ROOT / man["config"])


def test_every_program_immediate_matches_its_manifest_source():
    c, w = consts(), words()
    for bind in BINDS:
        tr = json.loads(bind.read_text())["instruction_trace"]
        assert len(tr) == len(w) == 113
        for pc, (row, d) in enumerate(zip(tr, w)):
            src = row.get("imm_sources", {})
            for field in IMMS:
                if field in src:
                    assert d[field] == KC.bits(c, src[field]), (bind.name, pc, field, src[field], hex(d[field]))
                else:          # an immediate with no manifest source must not be encoded at all
                    assert d[field] == 0, (bind.name, pc, row["tag"], field, hex(d[field]))


@pytest.mark.parametrize("field,pcs,name", EXPECTED)
def test_fixed_immediates(field, pcs, name):
    c, w = consts(), words()
    for pc in pcs:
        assert w[pc][field] == KC.bits(c, name), (pc, field, name, hex(w[pc][field]))


def test_emitter_has_no_immediate_literals():
    src = (ROOT / "tools/hdc_replay_v41.py").read_text()
    assert not re.search(r"imm[123]=(0|f32\()", src)


def test_sinkhorn_unit_parameters_match_the_manifest():
    man = json.loads(KC.OUT.read_text())["models"]["deepseek-v4.1-flash"]["unit_parameters"]
    for f in ("rtl/hdc/v41/ot_hdc_sinkhorn_seq.sv", "rtl/hdc/v41/ot_hdc_sinkhorn_mc.sv"):
        t = (ROOT / f).read_text()
        assert int(re.search(r"ITERS\s*=\s*(\d+)", t).group(1)) == man["sinkhorn_iters"]["value"]
        assert "32'h" + man["sinkhorn_eps"]["f32_bits"][2:].upper() in t


def test_shipped_shape_matches_the_config():
    s = R.SHIPPED
    assert (s["dim"], s["hc"], s["heads"], s["hd"], s["rd"], s["q_rank"], s["o_groups"], s["o_rank"], s["n_exp"],
            s["k_exp"], s["moe_ff"], s["window"], s["topk"], s["vocab"], s["ih"], s["ihd"]) == (
        CONFIG["dim"], CONFIG["hc_mult"], CONFIG["n_heads"], CONFIG["head_dim"], CONFIG["rope_head_dim"],
        CONFIG["q_lora_rank"], CONFIG["o_groups"], CONFIG["o_lora_rank"], CONFIG["n_routed_experts"],
        CONFIG["n_activated_experts"], CONFIG["moe_inter_dim"], CONFIG["window_size"], CONFIG["index_topk"],
        CONFIG["vocab_size"], CONFIG["index_n_heads"], CONFIG["index_head_dim"])


def test_attention_sink_is_sliced_by_the_rank_heads():
    import rtl_v41_fullshape_layer_campaign as LC
    s = dict(R.SHIPPED, ratio=R.RATIO)
    for rank in range(4):
        rows = {n: r for n, _, r, _ in LC.die_slices(0, rank, s, [], False)}
        assert rows["attn_sink"] == (16 * rank, 16 * rank + 16)
    lay = json.loads((ROOT / "results/rtl/hdc_v41x_fullshape_token_selected_rom_layout.json").read_text())
    assert lay["constants"]["attn_sink"]["word_count"] == 16


def test_core_dyn_table_matches_the_emitter():
    import v41_fullshape_isa as X
    for pos in (0, 1, 126, 127, 128, 199999, 1048575):
        X.full_dyn(pos)            # raises on any disagreement


def test_isa_record_passes_both_contexts():
    rec = json.loads((ROOT / "results/rtl/w17_l0_fullshape_isa.json").read_text())
    assert rec["status"] == "pass"
    for ctx in ("1048576", "200000"):
        c = rec["contexts"][ctx]
        assert c["verdict"] == "pass" and not c["defects"] and not c["unwritten_reads"]
        assert all(r["bit_exact"] for r in c["regions"]) and len(c["regions"]) == 9
    assert rec["program_sha256"] == KC.sha(PROGRAM)
