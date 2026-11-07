#!/usr/bin/env python3
"""S81-BKSEL-RF7 vG: apply the vG RTL delta to a copy of the vD kit rtl dir (gate), or the reference delay form (gold)."""
import sys, pathlib
mode, d = sys.argv[1], pathlib.Path(sys.argv[2])
def sub(fn, old, new, n=1):
    p = d / fn; t = p.read_text()
    assert t.count(old) == n, (fn, old[:60], t.count(old))
    p.write_text(t.replace(old, new))

BANK_OLD = """`ifdef OT_HB_PINCOPY
            // one bank pin per kept capture flop (KITS-SPARE-2/HB 10-25): the bank's copy registers are fed in parallel
            .clk(clk), .rst_n(rst_n), .clr({17{nc}}), .i_v(i_v), .i_en(i_en), .i_dg(nd), .gsel({16{ng}}),
`else"""

if mode == "gate":
    # ---- per-row + per-bank input stages in front of every bank
    sub("ot_s81ph_hq_parts.sv", """    genvar b, l;
    generate for (b = 0; b < 8; b = b + 1) begin : g_bank
        wire [127:0] nd;""", """    genvar b, l;
`ifdef OT_BKQ_BSTG
    // S81-BKSEL-RF7 vG 11-07 (OT_BKQ_BSTG, PIN CYCLES +2 on t_s): every hist_bank input is two edges later, as one block, so
    // the bank sees the old input sequence shifted by two edges and gsum / gbin come two edges later.  Stage 1 = one kept
    // copy per bank row (g_row: i_v, rst_n, i_en, i_dg) or per bank (c1, g1: clr, gsel); stage 2 = one flop per bank pin,
    // placed at the pin (bank_regs.tcl), fanout <= 8.  vE TT -70: reg -> shared 8-bank net -> bank pin, slew 777, 127 ps
    // macro setup.  Now the far-row wire is flop to flop and the last hop is one flop at the pin.  busy stays on the
    // undelayed inputs (sx_v shadow), so the slice control does not move; the tile delays the other t_s bits to match.
    wire [1:0] row_v, row_rn; wire [2*16-1:0] row_en; wire [2*128-1:0] row_dg;
    generate for (b = 0; b < 2; b = b + 1) begin : g_row
        (* keep = "true" *) reg v, rn;
        (* keep = "true" *) reg [15:0] en;
        (* keep = "true" *) reg [127:0] dg;
        always @(posedge clk) begin v <= i_v; rn <= rst_n; en <= i_en; dg <= i_dg; end
        assign row_v[b] = v; assign row_rn[b] = rn; assign row_en[16*b +: 16] = en; assign row_dg[128*b +: 128] = dg;
    end endgenerate
`endif
    generate for (b = 0; b < 8; b = b + 1) begin : g_bank
        wire [127:0] nd;""")
    sub("ot_s81ph_hq_parts.sv", """        wire       nc = (MUT == 2 && b == 3) ? 1'b0 : clr[b];
""", """        wire       nc = (MUT == 2 && b == 3) ? 1'b0 : clr[b];
`ifdef OT_BKQ_BSTG
        (* keep = "true" *) reg c1; (* keep = "true" *) reg [3:0] g1;
        (* keep = "true" *) reg s_v, s_rn;
        (* keep = "true" *) reg [15:0] s_en;
        (* keep = "true" *) reg [127:0] s_dg;
        (* keep = "true" *) reg [2:0] s_clr;      // 17 clr pins: 6 + 6 + 5
        (* keep = "true" *) reg [7:0] s_g;        // 64 gsel pins: 2 copies, 8 pins per flop
        wire [127:0] row_nd;
        for (l = 0; l < 16; l = l + 1) begin : g_rd
            assign row_nd[8*l +: 8] = row_dg[128*(b / 4) + 8*l +: 8] ^ (8'((MUT == 1) ? (b ^ 1) : b) << 5);
        end
        always @(posedge clk) begin
`ifdef OT_BKQ_BSTG_MUT_DG
            s_dg <= (b == 5) ? (row_nd ^ 128'd1) : row_nd;   // proof mutant: bank 5 i_dg[0] inverted
`else
            s_dg <= row_nd;
`endif
`ifdef OT_BKQ_BSTG_MUT_RN
            s_rn <= (b == 2) ? rst_n : row_rn[b / 4];      // proof mutant: bank 2 reset one edge early
`else
            s_rn <= row_rn[b / 4];
`endif
            s_v <= row_v[b / 4]; s_en <= row_en[16*(b / 4) +: 16];
            c1 <= nc; g1 <= ng;
`ifdef OT_BKQ_BSTG_MUT_G
            s_clr <= {3{c1}}; s_g <= {g1, (b == 6) ? ng : g1};  // proof mutant: bank 6 low gsel copy one edge early
`else
            s_clr <= {3{c1}}; s_g <= {2{g1}};
`endif
        end
`endif
""")
    sub("ot_s81ph_hq_parts.sv", BANK_OLD, """`ifdef OT_BKQ_BSTG
            .clk(clk), .rst_n(s_rn), .clr({{5{s_clr[2]}}, {6{s_clr[1]}}, {6{s_clr[0]}}}), .i_v(s_v), .i_en(s_en), .i_dg(s_dg),
            .gsel({{8{s_g[7:4]}}, {8{s_g[3:0]}}}),
`elsif OT_HB_PINCOPY
            // one bank pin per kept capture flop (KITS-SPARE-2/HB 10-25): the bank's copy registers are fed in parallel
            .clk(clk), .rst_n(rst_n), .clr({17{nc}}), .i_v(i_v), .i_en(i_en), .i_dg(nd), .gsel({16{ng}}),
`else""")
    # ---- t_s control bits: two more stages
    sub("ot_s81ph_hq_tile.sv", """`ifdef OT_BKQ_GBREG2
    assign t_s = {sq2, sq1[831:0]};
`else""", """`ifdef OT_BKQ_BSTG
    // S81-BKSEL-RF7 vG: the banks are two edges later, so the control bits take two more stages (PIN CYCLES +2 on t_s).
    reg [864:832] sq3, sq4;
`ifdef OT_BKQ_BSTG_MUT_CTL
    always @(posedge ck[0]) begin sq3 <= sq2; sq4 <= sq2; end  // proof mutant: control one edge short
`else
    always @(posedge ck[0]) begin sq3 <= sq2; sq4 <= sq3; end
`endif
    assign t_s = {sq4, sq1[831:0]};
`elsif OT_BKQ_GBREG2
    assign t_s = {sq2, sq1[831:0]};
`else""")
    # ---- fanout <= 8: replicas with keep
    sub("ot_s81ph_hq_tile.sv", """    wire [2:0] b1c;
""", """`ifdef OT_BKQ_FO8
    localparam integer NB1 = 6, GB1 = 7;     // S81-BKSEL-RF7: 6 kept copies, <= 7 groups (14 loads over 2 outputs: fanout <= 8)
`else
    localparam integer NB1 = 3, GB1 = 13;
`endif
    wire [NB1-1:0] b1c;
""")
    sub("ot_s81ph_hq_tile.sv", "for (c = 0; c < 3; c = c + 1) begin : g_b1c", "for (c = 0; c < NB1; c = c + 1) begin : g_b1c")
    sub("ot_s81ph_hq_tile.sv", "begin oh0 <= ~b1c[g / 13]; oh1 <= b1c[g / 13]; end", "begin oh0 <= ~b1c[g / GB1]; oh1 <= b1c[g / GB1]; end")
    # position copies: a fifth copy for lanes 14, 15
    sub("ot_s81ph_hq_tile.sv", """    wire [4*20-1:0] curc;
    generate for (fs = 0; fs < 4; fs = fs + 1) begin : g_cur""", """`ifdef OT_BKQ_FO8
    localparam integer NCUR = 5;
`else
    localparam integer NCUR = 4;
`endif
    wire [NCUR*20-1:0] curc;
    generate for (fs = 0; fs < NCUR; fs = fs + 1) begin : g_cur""")
    sub("ot_s81ph_hq_tile.sv", "b_idx[20*l +: 20] <= curc[20*(l/4) +: 20] + l[19:0];", "b_idx[20*l +: 20] <= curc[20*((NCUR == 5 && l >= 14) ? 4 : l/4) +: 20] + l[19:0];")
    # threshold copies per 2 lanes
    sub("ot_s81ph_hq_tile.sv", """    (* keep = "true" *) reg [4*16-1:0] cq_T;
""", """`ifdef OT_BKQ_FO8
    (* keep = "true" *) reg [8*16-1:0] cq_T;    // S81-BKSEL-RF7: one copy per 2 lanes (fanout <= 8)
`else
    (* keep = "true" *) reg [4*16-1:0] cq_T;
`endif
""")
    sub("ot_s81ph_hq_tile.sv", "cq_T <= {4{cq0[15:0]}};", """cq_T <= {
`ifdef OT_BKQ_FO8
        8
`else
        4
`endif
        {cq0[15:0]}};""")
    sub("ot_s81ph_hq_slice.sv", "    input  wire [4*16-1:0]       c_Tc,       // kept copies of c_T, one per 4-lane group\n", """`ifdef OT_BKQ_FO8
    input  wire [8*16-1:0]       c_Tc,       // kept copies of c_T, one per 2 lanes
`else
    input  wire [4*16-1:0]       c_Tc,       // kept copies of c_T, one per 4-lane group
`endif
""")
    sub("ot_s81ph_hq_slice.sv", "            wire [15:0] cT  = c_Tc[16*(gl / 4) +: 16];\n", """`ifdef OT_BKQ_FO8
            wire [15:0] cT  = c_Tc[16*(gl / 2) +: 16];
`else
            wire [15:0] cT  = c_Tc[16*(gl / 4) +: 16];
`endif
""")
    sub("ot_s81ph_hq_slice.sv", "    wire [4*16-1:0] tswc;\n", """`ifdef OT_BKQ_FO8
    localparam integer NTS = 8, GTS = 2;
`else
    localparam integer NTS = 4, GTS = 4;
`endif
    wire [NTS*16-1:0] tswc;
""")
    sub("ot_s81ph_hq_slice.sv", "generate for (gg = 0; gg < 4; gg = gg + 1) begin : g_tsw", "generate for (gg = 0; gg < NTS; gg = gg + 1) begin : g_tsw")
    sub("ot_s81ph_hq_slice.sv", "wire [15:0] t  = tswc[16*(gl / 4) +: 16];", "wire [15:0] t  = tswc[16*(gl / GTS) +: 16];")
elif mode == "gold":
    # Reference: vD with a plain two-edge delay on ALL inputs of each bank and on the t_s control bits; nothing else.
    sub("ot_s81ph_hq_parts.sv", BANK_OLD, """`ifdef OT_HB_PINCOPY
            .clk(clk), .rst_n(d2_rn), .clr(d2_clr), .i_v(d2_v), .i_en(d2_en), .i_dg(d2_dg), .gsel(d2_g),
`else""")
    sub("ot_s81ph_hq_parts.sv", """        wire       nc = (MUT == 2 && b == 3) ? 1'b0 : clr[b];
""", """        wire       nc = (MUT == 2 && b == 3) ? 1'b0 : clr[b];
        reg d1_rn, d2_rn, d1_v, d2_v; reg [16:0] d1_clr, d2_clr; reg [15:0] d1_en, d2_en; reg [127:0] d1_dg, d2_dg; reg [63:0] d1_g, d2_g;
        always @(posedge clk) begin
            d1_rn <= rst_n; d2_rn <= d1_rn; d1_v <= i_v; d2_v <= d1_v; d1_clr <= {17{nc}}; d2_clr <= d1_clr;
            d1_en <= i_en; d2_en <= d1_en; d1_dg <= nd; d2_dg <= d1_dg; d1_g <= {16{ng}}; d2_g <= d1_g;
        end
""")
    # enable-held, reset-free copies: all copies share D and enable; they agree from the first read on (not provable from a free power-up state), so the reference has the same 6 copies
    sub("ot_s81ph_hq_tile.sv", "    wire [2:0] b1c;\n", "    localparam integer NB1 = 6, GB1 = 7;\n    wire [NB1-1:0] b1c;\n")
    sub("ot_s81ph_hq_tile.sv", "for (c = 0; c < 3; c = c + 1) begin : g_b1c", "for (c = 0; c < NB1; c = c + 1) begin : g_b1c")
    sub("ot_s81ph_hq_tile.sv", "begin oh0 <= ~b1c[g / 13]; oh1 <= b1c[g / 13]; end", "begin oh0 <= ~b1c[g / GB1]; oh1 <= b1c[g / GB1]; end")
    sub("ot_s81ph_hq_tile.sv", """`ifdef OT_BKQ_GBREG2
    assign t_s = {sq2, sq1[831:0]};
`else""", """`ifdef OT_BKQ_GBREG2
    reg [864:832] sq3, sq4;
    always @(posedge ck[0]) begin sq3 <= sq2; sq4 <= sq3; end
    assign t_s = {sq4, sq1[831:0]};
`else""")
else:
    raise SystemExit("mode")
print("patched", mode, d)
