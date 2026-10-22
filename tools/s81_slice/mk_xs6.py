#!/usr/bin/env python3
"""STW-S81c-COLLA-FRAME (10-21): generate rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs6.sv + ot_s81sl_xgr3.sv from xs5 / xs4 / xgr."""
import re, sys
R = sys.argv[1] + "/rtl/dsrom_sys/s81_dv/slice/"
xs4 = open(R + "ot_s81sl_xs4.sv").read(); xs5 = open(R + "ot_s81sl_xs5.sv").read(); xgr = open(R + "ot_s81sl_xgr.sv").read()

def cut(txt, start):
    i = txt.index(start); j = txt.index("endmodule", i) + len("endmodule"); return txt[i:j]

# ---------------- calendar reader: fetch compares precomputed (registered next-state compares)
cal = cut(xs4, "module ot_s81sl_xs4_cal (").replace("module ot_s81sl_xs4_cal (", "module ot_s81sl_xs6_cal (")
old_f = """    wire fetch, fetch_r;
    ot_s81sl_xs4_fetch u_fetch   (.priming(priming), .due5(due5), .fi(fetch_index), .nrows(nrows), .fetch(fetch));
    ot_s81sl_xs4_fetch u_fetch_r (.priming(priming), .due5(due5), .fi(fetch_index), .nrows(nrows), .fetch(fetch_r));"""
new_f = """    // XGR3 (PD-AUDIT C7: u_cal_reader due -> fetch_index 672 ps / 18 levels): the fetch term's state compares
    // (fetch_index < nrows, fetch_index < 4) are REGISTERED next-state compares (fl_n / fl_4, written with fetch_index /
    // nrows below), so due5 -> fetch is one AND-OR; same edges, same values (fl_* == the compares on every edge).
    (* keep = "true" *) reg [1:0] fl_n, fl_4;   // copy 0 -> u_fetch (index / valid side), copy 1 -> u_fetch_r (ROM address)
    wire fetch, fetch_r;
    ot_s81sl_xs6_fetch u_fetch   (.priming(priming), .due5(due5), .lt_n(fl_n[0]), .lt_4(fl_4[0]), .fetch(fetch));
    ot_s81sl_xs6_fetch u_fetch_r (.priming(priming), .due5(due5), .lt_n(fl_n[1]), .lt_4(fl_4[1]), .fetch(fetch_r));"""
assert cal.count(old_f) == 1; cal = cal.replace(old_f, new_f)
old_i = """    always @(posedge ck or negedge rg[2]) begin
        if (!rg[2]) begin nrows <= 13'd0; fetch_index <= 13'd0; end
        else begin
            if (pok[4]) nrows <= len_p;
            if (pok[3]) fetch_index <= 13'd0;
            if (fetch) fetch_index <= fetch_index + 13'd1;
        end
    end"""
new_i = """    // next-state candidates (independent of due5): nrows_nx, index held / cleared (fi_h) or incremented (fi_i)
    wire [12:0] nrows_nx = pok[4] ? len_p : nrows;
    wire [12:0] fi_h = pok[3] ? 13'd0 : fetch_index;
    wire [12:0] fi_i = fetch_index + 13'd1;
    wire c_hn = fi_h < nrows_nx, c_in = fi_i < nrows_nx, c_h4 = fi_h < 13'd4, c_i4 = fi_i < 13'd4;
    always @(posedge ck or negedge rg[2]) begin
        if (!rg[2]) begin nrows <= 13'd0; fetch_index <= 13'd0; fl_n <= 2'b00; fl_4 <= 2'b11; end
        else begin
            nrows <= nrows_nx;
            fetch_index <= fetch ? fi_i : fi_h;
            fl_n[0] <= fetch ? c_in : c_hn;  fl_4[0] <= fetch ? c_i4 : c_h4;
            fl_n[1] <= fetch ? c_in : c_hn;  fl_4[1] <= fetch ? c_i4 : c_h4;
        end
    end"""
assert cal.count(old_i) == 1; cal = cal.replace(old_i, new_i)
fetch_mod = """// XGR3 calendar fetch term from registered compares (one instance per consumer group)
(* keep_hierarchy = 1 *) module ot_s81sl_xs6_fetch (input wire priming, input wire due5, input wire lt_n, input wire lt_4,
                                                    output wire fetch);
    assign fetch = (priming && lt_n && lt_4) || (due5 && lt_n);
endmodule
// XGR3 kept one-hot source decodes (PD-AUDIT / native census: xgr s_q0 / s_q1 decodes drove 42-43 loads)
(* keep_hierarchy = 1 *) module ot_s81sl_xs6_dq0 (input wire [1:0] s, output wire [2:0] y);
`ifdef OT_S81SL_XS_MUT_BANK
    assign y = 3'b001 << (s == 2'd2 ? 2'd0 : s + 2'd1);
`else
    assign y = 3'b001 << s;
`endif
endmodule
(* keep_hierarchy = 1 *) module ot_s81sl_xs6_dq1 (input wire [1:0] s, output wire [2:0] y);
    assign y = 3'b001 << s;
endmodule
"""
# ---------------- streamer xs6 = xs5 with per-bank kept qs copies + kept decodes per line pair, xs6 calendar
i = xs5.index("module ot_s81sl_xs5 ("); body = xs5[i:]
body = body.replace("module ot_s81sl_xs5 (", "module ot_s81sl_xs6 (").replace("OT_S81SL_XS5_ROM", "OT_S81SL_XS6_ROM")
assert body.count("ot_s81sl_xs4_cal u_cal_reader") == 1
body = body.replace("ot_s81sl_xs4_cal u_cal_reader", "ot_s81sl_xs6_cal u_cal_reader")
old_pb = """        wire [2:0] s_q0 [0:1], s_q1 [0:1];
        assign s_q0[0] = soh_q0(qs_r[1:0]); assign s_q0[1] = soh_q0(qs_r[3:2]);
        assign s_q1[0] = soh(qs_r[5:4]);    assign s_q1[1] = soh(qs_r[7:6]);"""
new_pb = """        // XGR3: per-bank kept copy of the compact q codes + kept decode instances per line pair (gj 2p / 2p+1) and one
        // for the exp lines (was ONE decode per bank feeding 4 x 8-AND lines + 2 exp ANDs = 42-43 mapped loads)
        (* keep = "true" *) reg [7:0] qs_b;
        integer k2b;
        always @(posedge clk) for (k2b = 0; k2b < 4; k2b = k2b + 1) qs_b[2 * k2b +: 2] <= qs[k2b];
        wire [2:0] s_q0 [0:1], s_q1 [0:1];   // exp-line decodes (le*)
        ot_s81sl_xs6_dq0 u_de0 (.s(qs_b[1:0]), .y(s_q0[0])); ot_s81sl_xs6_dq1 u_de1 (.s(qs_b[5:4]), .y(s_q1[0]));
        assign s_q0[1] = 3'd0; assign s_q1[1] = 3'd0;
        wire [2:0] d_q0 [0:3], d_q1 [0:3];   // line-pair decodes: pair p covers gj 2p, 2p+1 (q half gj / 4 = p / 2)
        for (gp = 0; gp < 4; gp = gp + 1) begin : g_dp
            ot_s81sl_xs6_dq0 u_dq0 (.s(qs_b[2 * (gp / 2) +: 2]), .y(d_q0[gp]));
            ot_s81sl_xs6_dq1 u_dq1 (.s(qs_b[4 + 2 * (gp / 2) +: 2]), .y(d_q1[gp]));
        end"""
assert body.count(old_pb) == 1; body = body.replace(old_pb, new_pb)
old_ln = """            ot_s81sl_xs5_ln u_lq0 (.s(s_q0[gj / 4][ga]), .m({4'd0, qms_r[16 * ga + 4 * (gj / 4) +: 4]}), .y(lq0[gj]));
            ot_s81sl_xs5_ln u_lq1 (.s(s_q1[gj / 4][ga]), .m({4'd0, qms_r[16 * ga + 4 * (2 + gj / 4) +: 4]}), .y(lq1[gj]));"""
new_ln = """            ot_s81sl_xs5_ln u_lq0 (.s(d_q0[gj / 2][ga]), .m({4'd0, qms_r[16 * ga + 4 * (gj / 4) +: 4]}), .y(lq0[gj]));
            ot_s81sl_xs5_ln u_lq1 (.s(d_q1[gj / 2][ga]), .m({4'd0, qms_r[16 * ga + 4 * (2 + gj / 4) +: 4]}), .y(lq1[gj]));"""
assert body.count(old_ln) == 1; body = body.replace(old_ln, new_ln)
# the central qs_r had no other consumer than g_pb: drop it (each bank now registers its own copy on the same edge)
assert body.count("qs_r") == 3, body.count("qs_r")
body = body.replace("packed: qs_r[2 L +: 2] (q lookup L 0..3)", "packed: qs_b[2 L +: 2] per bank in g_pb (q lookup L 0..3)")
body = body.replace("    (* keep = \"true\" *) reg [7:0] qs_r;\n", "")
body = body.replace("            qs_r[2 * k2 +: 2] <= qs[k2];\n", "")
assert "qs_r" not in body
body = body.replace("    genvar gs, gc, gm, gj, ga, gb;", "    genvar gs, gc, gm, gj, ga, gb, gp;")
assert "gb, gp;" in body
hdr = """`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// STW-S81c-COLLA-FRAME (10-21 / 10-22): ot_s81sl_xs6 = ot_s81sl_xs5 (S81-ELEM2-XGRING, 0397b9edc) with two value-preserving
// structural fixes, GENERATED by mk_xs6.py from xs5 / xs4 (same ports, same edges, same function; tools/s81_slice/xs6_equiv.sh):
//  1 native census (xgr2 / xgr FAIL max 43, 6 drivers u_c.u_s.g_pb[a].s_q0 / s_q1 [0][a]): the per-bank one-hot q decode fed
//    4 x 8-AND kept lines + 2 exp ANDs -> each bank registers its own kept copy of the compact q codes (qs_b, same E2 edge,
//    replaces the single central qs_r) and decodes per line pair in kept ot_s81sl_xs6_dq0 / dq1 instances (<= 16 loads).
//  2 PD-AUDIT C7 (u_cal_reader due -> fetch_index 672 ps, 18 levels): ot_s81sl_xs6_cal = ot_s81sl_xs4_cal with the fetch
//    term's state compares (fetch_index < nrows / < 4) registered as next-state compares (fl_n / fl_4); due5 -> fetch is
//    one AND-OR.  No edge added (calendar rows, faults and ROM address timing unchanged).
// Helper modules (xs4_rst / _ctl / _pdec / _bdec / _due / _rng / _bad, xs5_ln) come from ot_s81sl_xs4.sv / ot_s81sl_xs5.sv.
// ---------------------------------------------------------------------------------------------------------------------
`ifdef SYNTHESIS
`define OT_S81SL_XS6_ROM(n) ot_rom_4096x72_m8
`else
`define OT_S81SL_XS6_ROM(n) ot_rom_4096x72_m8 #(.INSTANCE(n))
`endif
"""
body = re.sub(r"`undef OT_S81SL_XS5_ROM\s*$", "", body.rstrip()) + "\n`undef OT_S81SL_XS6_ROM\n"
assert "`undef OT_S81SL_XS5_ROM" not in body
# xs5 file starts with the ROM define; body must not use XS5 macros anymore
assert "OT_S81SL_XS5_ROM" not in body
open(R + "ot_s81sl_xs6.sv", "w").write(hdr + fetch_mod + "// native copy of ot_s81sl_xs4_cal + XGR3 fetch precompute\n" + cal + "\n\n" + body)

# ---------------- tops: ot_s81sl_xgr3 (FB) / ot_s81sl_xgr3m (MAIN) = xgr / xgr2 with the xs6 streamer
g1 = cut(xgr, "module ot_s81sl_xgr (").replace("module ot_s81sl_xgr (", "module ot_s81sl_xgr3 (")
assert g1.count("ot_s81sl_xs5 u_s") == 1; g1 = g1.replace("ot_s81sl_xs5 u_s", "ot_s81sl_xs6 u_s")
g2 = cut(xgr, "module ot_s81sl_xgr2 (").replace("module ot_s81sl_xgr2 (", "module ot_s81sl_xgr3m (")
assert g2.count("ot_s81sl_xgr u_c") == 1; g2 = g2.replace("ot_s81sl_xgr u_c", "ot_s81sl_xgr3 u_c")
open(R + "ot_s81sl_xgr3.sv", "w").write("""`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// STW-S81c-COLLA-FRAME (10-22): u_xg successor masters of ot_s81sl_xgr / ot_s81sl_xgr2 (0397b9edc; native census FAIL max 43)
// with the ot_s81sl_xs6 streamer (kept per-bank q decodes, registered calendar fetch compares).  SAME PORTS, SAME EDGES as
// xgr / xgr2 (die binding = master swap of u_xg; MU.S81.CAL deltas of xgr (+1/stop, FB) / xgr2 (+2/stop, MAIN) unchanged).
//   ot_s81sl_xgr3  (FB kit s81sl_xgr3_b)  = ot_s81sl_xgr with u_s ot_s81sl_xs6
//   ot_s81sl_xgr3m (MAIN kit s81sl_xgr3)  = ot_s81sl_xgr2 with u_c ot_s81sl_xgr3
// GENERATED by mk_xs6.py (scratch stw-s81c-colla/frame/gen) from ot_s81sl_xgr.sv.
// ---------------------------------------------------------------------------------------------------------------------
""" + g1 + "\n\n" + g2 + "\n")
print("OK")
