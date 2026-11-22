"""ahub_strap_ofs (KV-AHUB-RH1 11-21): AP_OFS / FR_OFS -> strap_ofs_ap / strap_ofs_fr ID-strap pins on the ck7 AHUB."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ahub_clock7 as C7  # noqa: E402
import ahub_strap_ofs as A  # noqa: E402

REPO = HERE.parents[4]
DW = (REPO / "rtl/hdc/nearhbm/qkd_ahub_static_dw.sv").read_text()
WRAP = ("module qkd_ahub (\n    input wire [15:0] hs_cal_r,\n    input wire [6:0] ck\n);\n"
        "    qkd_ahub_static_dw_ck7 #(.AP_OFS(64'hffddffdcffdfffdf), .FR_OFS(-7), .Z_IN_STRIDE(4)) u_leaf (\n"
        "        .ck(ck[0])\n    );\nendmodule\n")


def _kit_dw():
    return DW + "\n" + C7.apply(C7.module(DW, "qkd_ahub_static_dw"), C7.DW_SUBS) + "\n"


def test_rtl_appends_strap_modules_and_keeps_source():
    dw = _kit_dw()
    w, d, p = A.rtl(WRAP, dw)
    assert d.startswith(dw)                                   # canonical + ck7 text byte-identical
    assert "module qkd_ahub_static_io_st #(" in d and "module qkd_ahub_static_dw_ck7_st #(" in d
    io = A.module(d, "qkd_ahub_static_io_st")
    assert "parameter [63:0] AP_OFS" not in io and "input  wire [31:0]   strap_ofs_ap" in io
    assert "always @(posedge ck) begin ofs" not in io          # no strap capture register (KV-KITS-8)
    assert p == {"AP_OFS": "64'hffddffdcffdfffdf", "FR_OFS": -7, "Z_IN_STRIDE": 4}
    assert "qkd_ahub_static_dw_ck7_st #(.Z_IN_STRIDE(4)) u_leaf (" in w
    assert "input wire [31:0] strap_ofs_ap," in w and "input wire [7:0] strap_ofs_fr," in w


def test_encode_decode():
    assert A.encode("64'hffe3ffe2ffe1ffe1", -7) == (0xE3E2E1E1, 0xF9)
    assert A.decode(0xE3E2E1E1, 0xF9) == (0xFFE3FFE2FFE1FFE1, -7)
    with pytest.raises(ValueError):
        A.encode("64'hff00ffe2ffe1ffe1", -7)
    with pytest.raises(ValueError):
        A.encode("64'hffe3ffe2ffe1ffe1", 200)


def test_strap_pins_on_grid_and_count():
    pins = A.strap_pins("N", 420.024, 1.248, 604.8, 440.64)
    assert len(pins) == 40 and pins[0]["y"] == 440.64
    with pytest.raises(ValueError):
        A.strap_pins("N", 420.0, 1.248, 604.8, 440.64)
