"""QK-CORES-9 (COORD 10-27): the no-LEF QC generator path takes pin direction from the plan pin table; it must equal the
RTL top port direction (btab profile1713 kit)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("gq", Path(__file__).with_name("gen_core_kit_qc.py"))
gq = importlib.util.module_from_spec(spec); spec.loader.exec_module(gq)

TOP = """module other (input wire x); endmodule
module qfd_dv_s8x_btab #(parameter integer MIF = 0, parameter W = (4)) (
    input  wire            ck,   // clock
    input  wire [23:0]     bs_addr,
    output reg  [255:0]    bs_q, extra,
    /* comment, with comma */
    input  wire [W-1:0]    pw,
    output reg             fault
);
endmodule
"""


def pins(**over):
    rows = [dict(name="ck", dir="in"), dict(name="bs_addr[0]", dir="in"), dict(name="bs_addr[23]", dir="in"),
            dict(name="bs_q[255]", dir="out"), dict(name="extra[3]", dir="out"), dict(name="pw[2]", dir="in"),
            dict(name="fault", dir="out")]
    for r in rows:
        r.update(over.get(r["name"], {}))
    return rows


def test_ports_parsed():
    p = gq.rtl_port_dirs(TOP, "qfd_dv_s8x_btab")
    assert p["ck"] == ("INPUT", (0, 0)) and p["bs_addr"] == ("INPUT", (23, 0))
    assert p["bs_q"] == ("OUTPUT", (255, 0)) and p["extra"] == ("OUTPUT", (255, 0))
    assert p["pw"] == ("INPUT", None) and p["fault"] == ("OUTPUT", (0, 0)) and "x" not in p


def test_consistent_table_passes():
    assert gq.plan_dir_errors(pins(), gq.rtl_port_dirs(TOP, "qfd_dv_s8x_btab")) == []


def test_flipped_dir_fails():
    e = gq.plan_dir_errors(pins(**{"bs_q[255]": dict(dir="in")}), gq.rtl_port_dirs(TOP, "qfd_dv_s8x_btab"))
    assert len(e) == 1 and "plan dir in != RTL output" in e[0]
    e = gq.plan_dir_errors(pins(**{"ck": dict(dir="out")}), gq.rtl_port_dirs(TOP, "qfd_dv_s8x_btab"))
    assert len(e) == 1 and "ck" in e[0]


def test_unknown_port_and_range_fail():
    p = gq.rtl_port_dirs(TOP, "qfd_dv_s8x_btab")
    assert "no RTL port" in gq.plan_dir_errors([dict(name="bs_qq[0]", dir="out")], p)[0]
    assert "outside RTL range" in gq.plan_dir_errors([dict(name="bs_addr[24]", dir="in")], p)[0]
    assert "scalar plan pin" in gq.plan_dir_errors([dict(name="bs_addr", dir="in")], p)[0]
    assert "plan dir None" in gq.plan_dir_errors([dict(name="fault")], p)[0]
