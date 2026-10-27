#!/usr/bin/env python3
"""HEAD-CORE-R11 2026-10-26 (COORD RULING HEAD-CORE-R10 KEEP FAIL): no kept SPLIT9 round-carry copy on a chain-head adder.

ot_dsrom_head_elem's two product chains start from the constant cs[l][0] = 32'd0, so g_ch[l].g_s[0].u_a adds +0 to a
product.  Its four (* keep *) round-carry copies g_cy_copy.cyq[0..3] are dead by construction (zero bypass; and 0 under
OT_S81HD_FADD_ZERO_ARITH): synthesis keeps them load-free, P&R removes them, and lec.py's kept-register check fails closed
on the 8 missing declared bits.  Source fix: ot_v41_fadd parameter CY_COPY (default 1 = unchanged); CY_COPY 0 uses the
registered round carry rnd9[24] itself -- the SAME value on the SAME edge as every copy (u_c8 registers r8, cyq <= r8[24]),
so it is bit-identical for any operands -- and the chain head instantiates CY_COPY(s != 0).

apply_fadd / apply_head_elem patch the text of either the closed f11f3cc47 files (hd_elemA_rebuild.py kits) or main's;
each anchor must occur exactly once (fail closed), so a drifted source is never patched silently.
"""
import sys

FADD_PARAM_OLD = "    parameter integer SPLIT9 = 0,\n"
FADD_PARAM_NEW = FADD_PARAM_OLD + (
    "    // CY_COPY (default 1; HEAD-CORE-R11 2026-10-26): with SPLIT9, the round carry leaves u_c8 as four KEPT copies.\n"
    "    // 0 = no kept copies: cyk is the registered round carry rnd9[24] itself (same value, same edge as every copy, so\n"
    "    // bit-identical for any operands).  For an adder whose operand the instantiating generate ties to a constant (the\n"
    "    // chain head of ot_dsrom_head_elem: a = +0), where the copies are dead kept flops by construction.\n"
    "    parameter integer CY_COPY = 1,\n")
FADD_GEN_OLD = "    if (SPLIT9) begin : g_cy_copy\n"
FADD_GEN_NEW = "    if (SPLIT9 && CY_COPY) begin : g_cy_copy\n"
ELEM_OLD = ("            ot_v41_fadd #(.CUT(CUT), .SPLIT9(SPLIT9)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(cv[l][s]), "
            ".a(cs[l][s]), .b(p[8*l + s]),\n")
ELEM_NEW = ("            // s = 0 adds the constant cs[l][0] = +0: no kept round-carry copies (CY_COPY 0, HEAD-CORE-R11)\n"
            "            ot_v41_fadd #(.CUT(CUT), .SPLIT9(SPLIT9), .CY_COPY(s != 0)) u_a (.clk(clk), .rst_n(rst_n), "
            ".valid_in(cv[l][s]), .a(cs[l][s]), .b(p[8*l + s]),\n")
ELEM_HEAD_OLD = "        assign cs[l][0] = 32'd0;\n"


def _sub(text, old, new, what):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"cy_copy_const: {what} anchor found {n} times (need exactly 1)")
    return text.replace(old, new, 1)


def apply_fadd(text):
    text = _sub(text, FADD_PARAM_OLD, FADD_PARAM_NEW, "ot_v41_fadd SPLIT9 parameter")
    return _sub(text, FADD_GEN_OLD, FADD_GEN_NEW, "ot_v41_fadd g_cy_copy generate")


def apply_head_elem(text):
    if text.count(ELEM_HEAD_OLD) != 1:     # the constant the CY_COPY(s != 0) choice relies on
        raise SystemExit("cy_copy_const: chain head constant cs[l][0] = 32'd0 not found exactly once")
    return _sub(text, ELEM_OLD, ELEM_NEW, "ot_dsrom_head_elem chain adder")


if __name__ == "__main__":     # cy_copy_const.py FADD.sv HEAD_ELEM.sv  (in place)
    fa, he = sys.argv[1:3]
    fa_new, he_new = apply_fadd(open(fa).read()), apply_head_elem(open(he).read())
    open(fa, "w").write(fa_new)
    open(he, "w").write(he_new)
    print("cy_copy_const: patched", fa, he)
