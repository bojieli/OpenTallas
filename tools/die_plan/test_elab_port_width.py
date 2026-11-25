"""ELAB-PORT-WIDTH (COORD 11-24): every cell's connected widths vs its master's declared widths (report only)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import elab_port_width as EPW  # noqa: E402

STUBS = r"""
`define OT_T_W 8
module ot_hdc_v41x_kreg #(
    parameter integer W = 1,
    parameter integer R = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
endmodule
module ot_pl_land_chunk_r #(
    parameter integer W = 514, D = 4, K = 2, CHUNK_BITS = 24,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [D*W-1:0] bank,
    input wire [D*(AW+1)-1:0] epo,
    input wire [D*((W+CHUNK_BITS-1)/CHUNK_BITS)-1:0] vld,
    output wire [W-1:0] o
);
endmodule
module old_style (a, b, c);
    parameter N = 4;
    localparam M = N * 2;
    input [M-1:0] a;
    input b;
`ifdef OT_WIDE
    output [`OT_T_W*2-1:0] c;
`else
    output [`OT_T_W-1:0] c;
`endif
endmodule
module typed_leaf (input my_pkg::t_req r, input wire [3:0] x, input wire word_v);
endmodule
"""


def bits(n, start=2):
    return list(range(start, start + n))


def b32(v):
    return format(v & 0xFFFFFFFF, "032b")


def netlist():
    """slang-style: kreg blackbox imported at the FIRST instance's ABI (W=576) -> the W=1 cell connected 576 bits"""
    bb = {"blackbox": "00000000000000000000000000000001"}
    return {"modules": {
        "top": {"attributes": {"top": "00000000000000000000000000000001"}, "ports": {}, "cells": {
            "u_a": {"type": "mid", "parameters": {}, "connections": {}},
            "u_b": {"type": "mid", "parameters": {}, "connections": {}},
        }},
        "mid": {"ports": {"x": {"direction": "input", "bits": bits(3)}}, "cells": {
            "u_k576": {"type": "ot_hdc_v41x_kreg", "parameters": {"W": b32(576)},
                       "connections": {"clk": [2], "rst_n": [3], "d": bits(576), "q": bits(576, 700)}},
            "u_k1": {"type": "ot_hdc_v41x_kreg", "parameters": {"W": b32(1)},
                     "connections": {"clk": [2], "rst_n": [3], "d": bits(576), "q": bits(576, 700)}},
            "u_ch": {"type": "ot_pl_land_chunk_r", "parameters": {"W": b32(100), "D": b32(4)},
                     "connections": {"ck": [2], "rsi": [3], "bank": bits(400), "epo": bits(12), "vld": bits(20),
                                     "o": bits(100)}},
            "u_old": {"type": "old_style", "parameters": {"N": b32(3)},
                      "connections": {"a": bits(6), "b": [2], "c": bits(8)}},
            "u_ty": {"type": "typed_leaf", "parameters": {}, "connections": {"r": bits(9), "x": bits(4)}},
            "u_body": {"type": "body_m", "parameters": {}, "connections": {"i": bits(5)}},
            "$and$x.sv:1$1": {"type": "$and", "parameters": {}, "connections": {"A": [2], "B": [3], "Y": [4]}},
        }},
        "body_m": {"ports": {"i": {"direction": "input", "bits": bits(4)}}, "cells": {}},
        "ot_hdc_v41x_kreg": {"attributes": bb, "ports": {"d": {"direction": "input", "bits": bits(576)},
                                                          "q": {"direction": "output", "bits": bits(576)}},
                             "cells": {}},
        "ot_pl_land_chunk_r": {"attributes": bb, "ports": {}, "cells": {}},
        "old_style": {"attributes": bb, "ports": {}, "cells": {}},
        "typed_leaf": {"attributes": bb, "ports": {}, "cells": {}},
    }}


def test_sv_eval():
    env = {"W": 100, "D": 4, "CHUNK_BITS": 24}
    assert EPW.sv_eval("D*((W+CHUNK_BITS-1)/CHUNK_BITS)-1", env) == 19
    assert EPW.sv_eval("(D <= 2) ? 1 : $clog2(D)", env) == 2
    assert EPW.sv_eval("8'hff + 'd1 + 4'b1_0 + 2**3 + (1 << 4) - 7 % 4", {}) == 255 + 1 + 2 + 8 + 16 - 3
    assert EPW.sv_eval("W > 8 && D == 4 ? W : 0", env) == 100
    try:
        EPW.sv_eval("UNKNOWN + 1", env)
        assert False
    except EPW.Unresolved:
        pass


def test_kreg_first_instance_abi_is_reported():
    rep = EPW.check(netlist(), EPW.declarations(STUBS), top="top")
    k = rep["ot_hdc_v41x_kreg"]
    assert (k["cells"], k["bad_cells"], k["inst"], k["bad_inst"]) == (2, 1, 4, 2)
    assert k["source"] == "declaration" and k["ports"]["d"]["sample"] == [1, 576]
    assert k["examples"][0]["cell"] == "u_k1" and k["examples"][0]["params"]["W"] == 1
    out = EPW.lines(rep)
    assert any(ln.startswith("WARN ELAB-PORT-WIDTH ot_hdc_v41x_kreg cells=1/2 inst=2/4") for ln in out)


def test_correct_widths_are_clean():
    rep = EPW.check(netlist(), EPW.declarations(STUBS), top="top")
    # integer division (vld 4*((100+23)/24) = 20), $clog2 AW, comma parameter lists, non-ANSI + `ifdef/`define
    assert rep["ot_pl_land_chunk_r"]["bad_cells"] == 0 and not rep["ot_pl_land_chunk_r"]["unresolved"]
    assert rep["old_style"]["bad_cells"] == 0 and not rep["old_style"]["unresolved"]
    rep2 = EPW.check(netlist(), EPW.declarations(STUBS, ["OT_WIDE"]), top="top")
    assert rep2["old_style"]["bad_cells"] == 1 and rep2["old_style"]["ports"]["c"]["sample"] == [16, 8]


def test_body_module_and_typed_port():
    rep = EPW.check(netlist(), EPW.declarations(STUBS), top="top")
    assert rep["body_m"]["source"] == "body" and rep["body_m"]["ports"]["i"]["sample"] == [4, 5]
    assert "$and" not in rep
    ty = rep["typed_leaf"]
    assert ty["bad_cells"] == 0 and "r" in ty["unresolved"] and "x" not in ty["unresolved"]


def test_listed_variant_uses_restored_parameters():
    """bind_slang_abi.restore: listed leaf variants carry hdlname + parameter_default_values; widths then agree"""
    y = netlist()
    y["modules"]["ot_hdc_v41x_kreg$1"] = {"attributes": {"blackbox": "1", "hdlname": "ot_hdc_v41x_kreg"},
                                          "parameter_default_values": {"W": b32(1)}, "ports": {}, "cells": {}}
    y["modules"]["mid"]["cells"]["u_k1"] = {"type": "ot_hdc_v41x_kreg$1", "parameters": {"W": b32(1)},
                                            "connections": {"clk": [2], "rst_n": [3], "d": [5], "q": [6]}}
    rep = EPW.check(y, EPW.declarations(STUBS), top="top", listed=["ot_hdc_v41x_kreg"])
    k = rep["ot_hdc_v41x_kreg"]
    assert k["bad_cells"] == 0 and k["listed"] and k["cells"] == 2


def test_bind_report_writes_json_and_never_raises(tmp_path):
    (tmp_path / "asbuilt_lib_stubs.sv").write_text(STUBS)
    out = EPW.bind_report(netlist(), {"top": "top", "defines": []}, tmp_path)
    assert any("WARN ELAB-PORT-WIDTH ot_hdc_v41x_kreg" in ln for ln in out)
    assert out[-1].startswith("LIST ELAB-PORT-WIDTH checked")
    js = json.loads((tmp_path / "elab_port_width.json").read_text())
    assert js["masters"]["ot_hdc_v41x_kreg"]["bad_cells"] == 1
    bad = EPW.bind_report({"modules": None}, {"top": "top"}, tmp_path)
    assert bad and bad[0].startswith("LIST ELAB-PORT-WIDTH not run")


def test_cli(tmp_path, capsys):
    (tmp_path / "asbuilt.json").write_text(json.dumps(netlist()))
    (tmp_path / "asbuilt_lib_stubs.sv").write_text(STUBS)
    assert EPW.main(["--out", str(tmp_path), "--json", str(tmp_path / "r.json")]) == 0
    o = capsys.readouterr().out
    assert "WARN ELAB-PORT-WIDTH ot_hdc_v41x_kreg cells=1/2 inst=2/4" in o
    assert json.loads((tmp_path / "r.json").read_text())["masters"]["body_m"]["bad_cells"] == 1


def test_cli_reads_defines_and_top_from_the_elab_script(tmp_path, capsys):
    (tmp_path / "asbuilt.json").write_text(json.dumps(netlist()))
    (tmp_path / "asbuilt_lib_stubs.sv").write_text(STUBS)
    (tmp_path / "asbuilt.ys").write_text("read_slang -DOT_WIDE -DX=3 --top top a.sv\nhierarchy -top top\n")
    assert EPW.main(["--out", str(tmp_path), "--json", str(tmp_path / "r.json")]) == 0
    js = json.loads((tmp_path / "r.json").read_text())
    assert js["masters"]["old_style"]["bad_cells"] == 1      # OT_WIDE from the script -> c declared 16, connected 8
    assert js["masters"]["ot_hdc_v41x_kreg"]["inst"] == 4


def test_word_prefix_is_not_a_net_type_and_open_ports_are_not_hits():
    d = EPW.declarations(STUBS)["typed_leaf"]["ports"]
    assert "word_v" in d and "d_v" not in d                   # 'wor' of word_v is not the wor net type
    y = netlist()
    y["modules"]["mid"]["cells"]["u_ty"]["connections"].update(word_v=[], x=bits(4))
    rep = EPW.check(y, EPW.declarations(STUBS), top="top")
    assert rep["typed_leaf"]["bad_cells"] == 0 and rep["typed_leaf"]["open_ports"] == 1


def test_plain_blackbox_defaults_do_not_override_derived_parameters():
    """native yosys: a plain blackbox module lists RTL defaults (PW = FW+51 at FW=546); the cell overrides only FW"""
    stub = "module face #(parameter integer FW=546, parameter integer PW=FW+51)(input wire [PW-1:0] phy_rx);\nendmodule\n"
    y = {"modules": {"top": {"cells": {"u": {"type": "face", "parameters": {"FW": b32(514)},
                                             "connections": {"phy_rx": bits(565)}}}},
                     "face": {"attributes": {"blackbox": "1"}, "parameter_default_values": {"FW": b32(546), "PW": b32(597)},
                              "ports": {}, "cells": {}}}}
    rep = EPW.check(y, EPW.declarations(stub), top="top")
    assert rep["face"]["bad_cells"] == 0
