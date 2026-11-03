#!/usr/bin/env python3
"""DIE-QC-66/CORES-NK 11-03: opt-in ICG_IDLE_RT on qfd_tile_nk_a0c (default 0 = unchanged elaboration).

Place-stage probe of NK NKP=7 (3_place.odb, estimate_parasitics -placement, TT): u_me.idle -> g_icg.g_root.en_g -264.6 ps
and u_me.idle -> g_icg.dr[*] -152.9 ps.  idle (graph home 408,666) and en_g (home 159,658) are ~250 um apart by plan,
and the enable cone (act -> en -> en_q) sits on that wire.  ICG_IDLE_RT = 1 (ICG = 1, ICG_EREG = 1 only) re-times
me_idle once at the tile root on the ungated ck (idle_r, async-set by rst_e like en_q / dr) and recomputes act / dr / en
from idle_r inside g_root, so the long wire is a pure flop -> flop hop (idle -> idle_r) and the enable cone is local.

Cycles: !idle_r asserts one edge after !me_idle.  me_idle falls only on the engine-accept edge of a go, while go_h
(ICG_GOH) is still set and dr has just been reloaded to ICG_DRAIN by it, so the one-edge gap is covered by dr: no
gated edge is lost, no visible / declared cycle.  When the engine drains, the enable stays on one edge longer (power
only).  The new chain branch keeps every existing genblk name / autonumber for ICG_IDLE_RT = 0.
usage: idle_rt_patch.py RTLDIR   (patches RTLDIR/qfd_tile_nk_a0c.sv; exact anchors, fail-closed)"""
import sys
from pathlib import Path


def rep(t, a, b):
    assert t.count(a) == 1, (a[:80], t.count(a))
    return t.replace(a, b)


P_OLD = "    parameter integer NKP = 0\n`ifndef SYNTHESIS\n"
P_NEW = ("    parameter integer NKP = 0,\n"
         "    // ICG_IDLE_RT (DIE-QC-66 11-03, opt-in, default 0 = unchanged; ICG = 1 + ICG_EREG = 1 only): me_idle re-timed\n"
         "    // at the tile root on the ungated ck (idle_r) before the enable cone; absorbed by the dr drain (see g_erx)\n"
         "    parameter integer ICG_IDLE_RT = 0\n"
         "`ifndef SYNTHESIS\n")
ER_OLD = "            end else begin : g_er\n"
ER_NEW = "            end else if (ICG_IDLE_RT == 0) begin : g_er\n"
END_OLD = ("                assign en_g = en_q | ((ICG_IREG != 0) ? 1'b0 : (((mut == 12) ? 1'b0 : go_f) | ((mut == 4) ? 1'b0 : nv_act)));\n"
           "            end\n"
           "`ifdef SYNTHESIS\n"
           "            ICGx8DC_ASAP7_75t_R u_icg")
ERX = ("                assign en_g = en_q | ((ICG_IREG != 0) ? 1'b0 : (((mut == 12) ? 1'b0 : go_f) | ((mut == 4) ? 1'b0 : nv_act)));\n"
       "            end else begin : g_erx\n"
       "                // ICG_IDLE_RT: me_idle (u_me.idle, far side of the tile) re-timed here on the ungated ck; act / dr / en\n"
       "                // as above but from idle_r (the outer act / dr / en are then unused).  !idle_r lags !me_idle by one\n"
       "                // edge: a reload by the lagged term alone loads ICG_DRAIN - 1, so dr_x / en_x match dr / en on every\n"
       "                // edge (the busy start lies inside the go_h / dr window of its go).  Bench: tb_a0_nkp MUT4 idle_r\n"
       "                // stuck idle, MUT5 dr_x stuck 0, MUT6 (+ICG_MUT=16) lagged reload = ICG_DRAIN must FAIL.\n"
       "                reg idle_r;\n"
       "                always @(posedge ck or negedge rst_e) if (!rst_e) idle_r <= 1'b1; else idle_r <= me_idle;\n"
       "                wire act_o = ((mut == 5) ? 1'b0 : !rst_e) | go_act | ((mut == 4) ? 1'b0 : nv_act);   // terms not lagged\n"
       "                wire busy_r = (mut == 2) ? 1'b0 : !idle_r;                                              // lagged !me_idle\n"
       "                wire act_x = act_o | busy_r;\n"
       "                reg [7:0] dr_x;\n"
       "                always @(posedge ck or negedge rst_e)\n"
       "                    if (!rst_e) dr_x <= (mut == 5) ? 8'd0 : 8'(ICG_DRAIN);\n"
       "                    else if (act_o) dr_x <= 8'(ICG_DRAIN);\n"
       "                    else if (busy_r) dr_x <= 8'(ICG_DRAIN - ((mut == 16) ? 0 : 1));   // = original reload one edge earlier\n"
       "                    else if (dr_x != 8'd0) dr_x <= dr_x - 8'd1;\n"
       "                wire en_x = act_x | ((mut == 3) ? 1'b0 : (dr_x != 8'd0)) | (mut == 9);\n"
       "                reg en_q;\n"
       "                always @(posedge ck or negedge rst_e) if (!rst_e) en_q <= 1'b1; else en_q <= en_x;\n"
       "                assign en_g = en_q | ((ICG_IREG != 0) ? 1'b0 : (((mut == 12) ? 1'b0 : go_f) | ((mut == 4) ? 1'b0 : nv_act)));\n"
       "            end\n"
       "`ifdef SYNTHESIS\n"
       "            ICGx8DC_ASAP7_75t_R u_icg")
CHK_OLD = "        if (ICG == 1) begin : g_root   // DIE-QC-16: one tile-root gate\n"


def main():
    p = Path(sys.argv[1]) / "qfd_tile_nk_a0c.sv"
    t = o = p.read_text()
    assert "ICG_IDLE_RT" not in t, "already patched"
    t = rep(t, P_OLD, P_NEW)
    t = rep(t, ER_OLD, ER_NEW)
    t = rep(t, END_OLD, ERX)
    assert t.count(CHK_OLD) == 1
    t = t.rstrip("\n")
    assert t.endswith("endmodule"), "qfd_tile_nk_a0c.sv does not end with endmodule"
    t = (t[: -len("endmodule")]
         + "    generate if (ICG_IDLE_RT != 0) begin : g_irt_chk\n"
         + "        initial if (ICG != 1 || ICG_EREG == 0 || ICG_DRAIN < 2) $fatal(1, \"ICG_IDLE_RT needs ICG = 1, ICG_EREG = 1, ICG_DRAIN >= 2\");\n"
         + "    end endgenerate\nendmodule\n")
    assert t != o
    p.write_text(t)
    print("patched", p)


if __name__ == "__main__":
    main()
