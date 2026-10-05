"""Catch die-level per-stack tag truncation hidden by permissive full lint."""
from tools.rtl_chip_v41x_packed_die_boundary import CHIP, tag_width_check


def test_actual_die_tag_widths(tmp_path):
    result = tag_width_check((CHIP / "ot_chip_v41x_die.sv").read_text(), tmp_path)
    assert result["returncode"] == 0, result


def test_original_truncation_is_rejected(tmp_path):
    source = (CHIP / "ot_chip_v41x_die.sv").read_text()
    source = source.replace("wire [4*16-1:0] w_tag, w_s_tag;", "wire [15:0] w_tag, w_s_tag;")
    source = source.replace("wire [4*16-1:0] p_tag,p_stag;", "wire [15:0] p_tag,p_stag;")
    result = tag_width_check(source, tmp_path)
    assert result["returncode"] != 0
    assert any("expected 4 x 16 tag bits" in line for line in result["diagnostics"])
