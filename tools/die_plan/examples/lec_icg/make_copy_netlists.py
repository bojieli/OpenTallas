#!/usr/bin/env python3
"""Derive the clock-gate COPY fixtures from netlist_ok.v (lane S81-CORE-LAT-R7, 2026-10-26) exactly as the core_infra
hook edits a netlist (ot_ci_tree_gate_copy): a new ICGx1 \\u_gb.u_icg_c1 of the same master, ENA/SE on the SAME nets as
\\u_gb.u_icg, CLK through one tree buffer (BUFx4 u_ckb_c1) from clk, own GCLK gb_c1; the rb[0..3] members move from gb.
  netlist_COPY.v          : must be EQUIVALENT (same registered enable eb_q)
  netlist_MUT_COPY_EN.v   : copy ENA on u_ga's enable net -> must be NOT EQUIVALENT
  netlist_MUT_COPY_SE.v   : copy SE tied high (always transparent) -> must be NOT EQUIVALENT
    python3 tools/die_plan/examples/lec_icg/make_copy_netlists.py"""
from pathlib import Path

D = Path(__file__).resolve().parent


def make(ena, se, extra_wires=""):
    s = (D / "netlist_ok.v").read_text()
    n = 0
    for b in range(4):
        old = "  DFFHQNx1_ASAP7_75t_R \\rb[%d]$_DFFE_PP_  (\n    .CLK(gb)," % b
        assert old in s, old
        s = s.replace(old, old.replace(".CLK(gb)", ".CLK(gb_c1)")); n += 1
    anchor = "  assign \\u_ga.gclk  = ga;"
    assert anchor in s
    s = s.replace(anchor, "  BUFx4_ASAP7_75t_R u_ckb_c1 (\n    .A(clk),\n    .Y(ck_c1)\n  );\n"
                  "  ICGx1_ASAP7_75t_R \\u_gb.u_icg_c1  (\n    .CLK(ck_c1),\n    .ENA(%s),\n    .GCLK(gb_c1),\n    .SE(%s)\n  );\n"
                  % (ena, se) + anchor)
    w = "  wire gb;\n"
    assert w in s
    s = s.replace(w, w + "  wire gb_c1;\n  wire ck_c1;\n" + extra_wires, 1)
    assert n == 4
    return s


def main():
    (D / "netlist_COPY.v").write_text(make("eb_q", "_064_"))
    (D / "netlist_MUT_COPY_EN.v").write_text(make("\\u_ga.en ", "_064_"))
    (D / "netlist_MUT_COPY_SE.v").write_text(make("eb_q", "1'b1"))


if __name__ == "__main__":
    main()
