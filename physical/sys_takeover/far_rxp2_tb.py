#!/usr/bin/env python3
"""sys-takeover 2026-10-10: the committed far-bus gate (rtl/test/emb_hbm/tb_emb_far_bus.sv) for RXP 2: the bus has one pin
register on emb_o / kv_o, so they are compared against the golden core's outputs one lclk later; every class / order /
data / credit-count check is unchanged.   far_rxp2_tb.py OUTDIR -> OUTDIR/tb_emb_far_bus_rxp2.sv"""
import pathlib
import sys

t = pathlib.Path("rtl/test/emb_hbm/tb_emb_far_bus.sv").read_text()
a = '  if({hub_o,emb_o,kv_o,fault} !== {ghub,gemb,gkv,gfault}) $fatal(1,"FAIL far native-output equivalence");'
assert t.count(a) == 1
t = t.replace(a, '  if({hub_o,emb_o,kv_o,fault} !== {ghub,gemb_d,gkv_d,gfault}) '
                 '$fatal(1,"FAIL far native-output equivalence (golden emb / kv one pin register later)");')
b = " integer txe=0,"
assert t.count(b) == 1
t = t.replace(b, " reg [524:0] gemb_d=0, gkv_d=0;\n always @(posedge lclk) begin gemb_d <= gemb; gkv_d <= gkv; end\n" + b)
(pathlib.Path(sys.argv[1]) / "tb_emb_far_bus_rxp2.sv").write_text(t)
