"""YOSYS-CONCAT 10-26: rtl_lint rejects the cast forms the flow's yosys read_verilog -sv mis-elaborates silently.
Positive / negative cases are taken from the frontend probe set (read_verilog -sv vs read_slang, orfs:asap7lock)."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rtl_lint

BAD = {   # silently mis-elaborated by read_verilog -sv (probe DIFF)
    'qc_lec4': "{3'b010,5'd0,({1'(s/(H*2)),1'((s/2)%H),1'(s%2)}^3'(M!=0?1:0))}",
    'xor_cast': "{3'b010, (2'(x4) ^ w)}",
    'add_cast': "{x4[2:0], (2'(x4) + w)}",
    'cast_mid': "{3'b010, (2'(x4) & w), 3'b101}",
    'nested': "{3'b011, {3'b010, (2'(x4) ^ w)}}",
    'repl': "{2{(2'(x4) ^ w)}}",
    'tern_branch': "{3'b010, (c ? 2'(x4) : w)}",
    'tern_cc': "{3'b010, (c ? {1'(x4),1'(x4)} : w)}",
    'type_cast': "{3'b010, (t2_t'(x4) ^ w)}",
    'param_size': "{3'b010, (P2'(x4) ^ w)}",
    'red_or': "|2'(x4)",
    'red_xor_space': "^ 2'(x4)",
    'and_not': "w & ~2'(x4)",
}
GOOD = {  # elaborated correctly (probe EQ)
    'bare_cast': "{3'b010, 2'(x4)}",
    'bare_cc_of_casts': "{3'b010, {1'(x4),1'(x4)}}",
    'named_wire': "{3'b010, lo}",
    'const_cast': "{3'b010, (w ^ 2'(P2!=0?1:0))}",
    'literal_cast': "{3'b010, (w ^ 3'(0))}",
    'compare': "{3'b010, (2'(x4) == w)}",
    'logical': "{3'b010, (1'(x4) && c)}",
    'tern_cond': "{3'b010, (1'(x4) ? w : x2)}",
    'index': "{3'b010, x4[2'(x4)]}",
    'call_arg': "{3'b010, f(2'(x4)) ^ w}",
    'no_concat': "2'(x4) ^ w",
    'binary_or': "x2 | 2'(x4)",
    'binary_sub': "x2 - 2'(x4)",
    'paren_red': "|(2'(x4))",
    'assign_pattern': "'{2'(x4) ^ w, 2'd0}",
    'bare_outer_cast': "{3'b010, 2'(x2 + (2'(x4) >> s))}",
    'signed_cast': "{3'b010, ({signed'(x4[0:0]),x4[1]} ^ w)}",
}


def mod(expr):
    return ("module m #(parameter integer P2=2)(input wire [3:0] x4, input wire [1:0] x2, w, lo, input wire c, s,\n"
            " output wire [9:0] y);\n localparam integer H=1, M=0;\n typedef logic [1:0] t2_t;\n"
            " function automatic [1:0] f(input [1:0] v); f = v; endfunction\n"
            f" // a comment {{3'b010, (2'(x4) ^ w)}} is ignored\n assign y = {expr};\nendmodule\n")


def test_bad_forms_are_rejected():
    for name, expr in BAD.items():
        hits = rtl_lint.yosys_cast_hits(mod(expr))
        assert hits and all(h[0] == 7 for h in hits), (name, hits)
    assert rtl_lint.yosys_cast_hits(mod(BAD['red_or']))[0][1] == 'YC2'
    assert rtl_lint.yosys_cast_hits(mod(BAD['xor_cast']))[0][1] == 'YC1'


def test_good_forms_pass():
    for name, expr in GOOD.items():
        assert rtl_lint.yosys_cast_hits(mod(expr)) == [], (name, rtl_lint.yosys_cast_hits(mod(expr)))


def test_fixed_qc_lec4_form_passes():
    text = ("module m #(parameter integer HEADS=1, MUT_TAG=0)(input wire clk, output reg [10:0] word_tag);\n"
            " integer selected;\n"
            " wire signed [31:0] tag_q2=selected/(HEADS*2),tag_q1=(selected/2)%HEADS,tag_q0=selected%2;\n"
            " wire [2:0] word_tag_lo={tag_q2[0],tag_q1[0],tag_q0[0]}^((MUT_TAG!=0)?3'd1:3'd0);\n"
            " always @(posedge clk) word_tag<={3'b010,5'd0,word_tag_lo};\nendmodule\n")
    assert rtl_lint.yosys_cast_hits(text) == []


def test_kit_lint_fails_on_cast_form_without_yosys_error(tmp_path):
    (tmp_path / 'config.mk').write_text('export DESIGN_NAME = m\nexport VERILOG_FILES = /work/rtl/m.sv\n')
    (tmp_path / 'rtl').mkdir()
    (tmp_path / 'rtl' / 'm.sv').write_text(mod(BAD['qc_lec4']))
    fake = tmp_path / 'fake_yosys'
    fake.write_text('#!/bin/sh\nexit 0\n')
    fake.chmod(0o755)
    assert rtl_lint.run(tmp_path, str(fake)) == 1
    rec = json.loads((tmp_path / 'rtl_lint.json').read_text())
    assert rec['verdict'] == 'FAIL' and rec['yosys_cast'] == 1 and 'YC1' in rec['errors'][0], rec
    (tmp_path / 'rtl' / 'm.sv').write_text(mod(GOOD['named_wire']))
    assert rtl_lint.run(tmp_path, str(fake)) == 0
    assert json.loads((tmp_path / 'rtl_lint.json').read_text())['yosys_cast'] == 0
