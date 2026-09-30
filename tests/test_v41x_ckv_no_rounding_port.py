"""Gate: the selected-CKV path never uses the DMA's FP8 element port.

ot_chip_v41x_ckv_selected_dma's q_fp8/q port rounds E2M1 x E4M3 to E4M3, which is NOT the golden value
(qdq_fp4_e4m3 keeps the exact product, at most 8 significant bits, exactly in BF16).  The attention path forwards
the raw E2M1 nibbles and E4M3 scales (fmt = 1 group words) and ot_hdc_v41x_attn_deq dequantises them exactly.
This test fails if any selected-CKV module reads the rounding port or stops forwarding raw codes."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _src(p):
    return re.sub(r"//.*", "", (ROOT / p).read_text())


def test_fetches_never_read_the_rounding_port():
    s = _src("rtl/chip/ot_chip_v41x_ckv_sel_fetch.sv")
    assert ".re(1'b0)" in s and ".q(q_unused)" in s and ".q_fp8(q8_unused)" in s
    assert s.count("q8_unused") == 2 and s.count("q_unused;") == 1   # declared + connected, never read
    w = _src("rtl/chip/ot_chip_v41x_ckv_pc_fetch.sv")
    assert "ot_chip_v41x_ckv_selected_dma" not in w and "ot_chip_v41x_ckv_fp4_decode" not in w


def test_merger_forwards_raw_codes_as_fmt1():
    m = _src("rtl/chip/ot_chip_v41x_ckv_stream_merge.sv")
    assert "{1'b1, 120'b0, c_rows[l*2304 + 2048 + 16*g +: 16]" in m and "c_rows[l*2304 + 128*g +: 128]}" in m
    assert "q_fp8" not in m and "fp4_decode" not in m
    for p in ("rtl/chip/ot_chip_v41x_ckv_sel_collect.sv", "rtl/chip/ot_chip_v41x_ckv_sel_ids.sv",
              "rtl/test/tb_chip_v41x_ckv_sel_attn.sv"):
        assert "q_fp8" not in _src(p), p


def test_engine_dequantises_fmt1_exactly():
    t = _src("rtl/hdc/v41x/ot_hdc_v41x_attn.sv")
    assert "if (gw[264]) elem = {pad, 1'b1, 4'd0, gw[4*x +: 4], gw[128 + 8*(x/16) +: 8]};" in t
