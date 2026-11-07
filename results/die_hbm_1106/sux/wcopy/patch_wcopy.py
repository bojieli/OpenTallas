#!/usr/bin/env python3
"""patch_wcopy.py KIT N (HBM-FORM-SPLIT-14-SUX 11-06, wa_pin -> w_mask_in class): kit RTL gets per-column write copies.
N=1: the existing WCOPY=1 form (commit n+2).
N=2: as 1, plus a one-hot registered word-select per column (ws_q): the 256 w_mask_in pins are driven by flops with no
decode between register and SRAM pin; same n+2 commit, same mask function.
Patches the data store and pinned bank text, then flips the core default WCOPY to N."""
import re
import sys
from pathlib import Path

kit, n = Path(sys.argv[1]), int(sys.argv[2])
p = kit / "rtl" / "ot_hbm_su_static_data_store.sv"
t = p.read_text()


def sub(a, b):
    global t
    assert t.count(a) == 1, a
    t = t.replace(a, b)


sub(" parameter integer WCOPY=0\n)(",
    " // WCOPY 2 (HBM-FORM-SPLIT-14-SUX): as 1, plus one-hot word-select copy ws_q: w_mask_in is register-driven, no decode.\n"
    " // MUT_WCOPY: bench mutants only (1 = wrong word select, 2 = column 3 write-data copy one edge late).\n"
    " parameter integer WCOPY=0,MUT_WCOPY=0\n)(")
sub("wire wv_c;wire[RB-1:0]wa_c;wire[31:0]wd_c;",
    "wire wv_c;wire[RB-1:3]wah_c;wire[2:0]wal_c;wire[7:0]ws_c;wire[31:0]wd_c;")
sub("(* keep *) reg wv_q;(* keep *) reg[RB-1:0]wa_q;(* keep *) reg[31:0]wd_q;",
    "(* keep *) reg wv_q;(* keep *) reg[RB-1:3]wa_q;(* keep *) reg[31:0]wd_q;")
sub("always @(posedge clk)begin wv_q<=write_v;wa_q<=write_addr;wd_q<=write_data;end\n"
    "   assign wv_c=wv_q;assign wa_c=wa_q;assign wd_c=wd_q;",
    "always @(posedge clk)begin wv_q<=write_v;wa_q<=write_addr[RB-1:3];end\n"
    "   if(MUT_WCOPY==2&&r==3)begin:g_mut_wd reg[31:0]wd_m;always @(posedge clk)begin wd_m<=write_data;wd_q<=wd_m;end end\n"
    "   else begin:g_wd always @(posedge clk)wd_q<=write_data;end\n"
    "   if(WCOPY==2)begin:g_ws\n"
    "    (* keep *) reg[7:0]ws_q;\n"
    "    always @(posedge clk)ws_q<=8'd1<<(write_addr[2:0]^(MUT_WCOPY==1?3'd1:3'd0));\n"
    "    assign ws_c=ws_q;assign wal_c=3'd0;\n"
    "   end else begin:g_wl\n"
    "    (* keep *) reg[2:0]wal_q;\n"
    "    always @(posedge clk)wal_q<=write_addr[2:0]^(MUT_WCOPY==1?3'd1:3'd0);\n"
    "    assign wal_c=wal_q;assign ws_c=8'd0;\n"
    "   end\n"
    "   assign wv_c=wv_q;assign wah_c=wa_q;assign wd_c=wd_q;")
sub("assign wv_c=write_v;assign wa_c=write_addr;assign wd_c=write_data;",
    "assign wv_c=write_v;assign wah_c=write_addr[RB-1:3];assign wal_c=write_addr[2:0];assign ws_c=8'd0;assign wd_c=write_data;")
sub("wire[255:0]mask={224'd0,32'hffffffff} << {wa_c[2:0],5'd0};",
    "wire[255:0]mask;\n"
    "  if(WCOPY==2)begin:g_mws for(genvar k=0;k<8;k=k+1)begin:g_w assign mask[k*32+:32]={32{ws_c[k]}};end end\n"
    "  else begin:g_mdec assign mask={224'd0,32'hffffffff} << {wal_c,5'd0};end")
sub(".w_addr_in({1'b0,wa_c[8:3]})", ".w_addr_in({1'b0,wah_c[8:3]})")
p.write_text(t)

b = kit / "rtl" / "ot_hbm_su_static_pinned_bank.sv"
s = b.read_text()
a = " parameter integer WCOPY=0,\n"
assert s.count(a) == 1
s = s.replace(a, " parameter integer WCOPY=0,MUT_WCOPY=0,\n")
a = ".WCOPY(WCOPY))u_data("
assert s.count(a) == 1
s = s.replace(a, ".WCOPY(WCOPY),.MUT_WCOPY(MUT_WCOPY))u_data(")
b.write_text(s)

for c in (kit / "rtl").glob("ot_hbm_su_pg_lane_*_x_core.sv"):
    s = c.read_text()
    s2, k = re.subn(r"parameter integer WCOPY = 0", f"parameter integer WCOPY = {n}", s)
    assert k == 1, c
    c.write_text(s2)
    print("core", c.name, "WCOPY", n)
