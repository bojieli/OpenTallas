`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// S81-TOPK7 (2026-10-20) HIERARCHICAL QUARTER parts (opt-in OT_S81PH_SEL_HQ, used only by ot_s81ph_hq_slice.sv).
// Structural successor of the monolithic OMERGE/succ quarter whose mapped native census FAILED 741 drivers > 32 loads
// (results/arch/s81_topk5_1020/quarter_omerge_canonical, evidence 89ba149e4).  Every part is exact against the original
// unit and adds 0 edges:
//   ot_s81ph_hq_pack   the compaction/packing unit as NP independent bit PLANES of the lane payload; each plane is the
//                      unchanged ot_s81ph_native_sel_pack (FAN32 + ACC32) on PW/NP payload bits with its OWN select copy,
//                      so every lane control (frc/qfc/acl/cstage valid+shift) steers <= 8 payload bits, not 38.
//   ot_s81ph_hq_hist   one 256-bin histogram as 8 copies of the hardened 32-bin bank ot_s81ph_native_sel_hist_bank
//                      (TOPK5 R3 gate PASS max25; BANK 0 master + constant digit / group inversions, as
//                      ot_s81ph_native_sel_hist_banked) wired with ZERO added edges: inputs straight to the bank's own
//                      HPIPE capture, gsel = the command input (the bank's kept per-bin gsel copies register it on the
//                      edge the original r_cg / FAN32 copies did), gsum concatenated, gbin = OR of the 8 registered bank
//                      outputs (combinational, as gbin -> status register before).  busy is recomputed EXACTLY at the
//                      parent from the bank inputs (x_v | v1 | v2 shadow, the bank's own HPIPE recurrence); the bank's
//                      registered busy output is one edge late and is not used.
//   ot_sram_showahead_1r1w_h2  ot_sram_showahead_1r1w with the write-hit compare computed twice from two identical,
//                      distinct copies of {we, wa, ra} (each hit net drives <= 19 slice flags instead of 37).
// ---------------------------------------------------------------------------------------------------------------

module ot_s81ph_hq_pack #(
    parameter integer W  = 16,
    parameter integer PW = 37,
    parameter integer NP = 6
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [NP-1:0]   i_v,         // per-plane copies (identical values)
    input  wire [NP-1:0]   i_fl,
    input  wire [NP*W-1:0] i_sel,       // per-plane select copies (identical values): prefix
    input  wire [NP*W-1:0] i_selg,      // per-plane select copies (identical values): lane gating
    input  wire [NP*W-1:0] i_selh,      // per-plane select copies (identical values): prefix of lanes >= W/2
    input  wire [W*PW-1:0] i_p,
    output wire [NP-1:0]   o_v,         // per-plane o_v: identical, DISTINCT flops (select sources downstream)
    output wire [W-1:0]    o_lv,
    output wire [W*PW-1:0] o_line,
    output wire            o_bv,
    output wire            o_fl
);
    function automatic integer plo(input integer p);   // first payload bit of plane p (first PW%NP planes one wider)
        integer q, s; begin s = 0; for (q = 0; q < p; q = q + 1) s = s + PW / NP + ((q < PW % NP) ? 1 : 0); plo = s; end
    endfunction
    genvar p, l;
    generate for (p = 0; p < NP; p = p + 1) begin : g_pl
        localparam integer LO = plo(p);
        localparam integer PP = PW / NP + ((p < PW % NP) ? 1 : 0);
        wire [W*PP-1:0] ip, ol;
        wire [W-1:0] lv;
        wire bv, fl;
        for (l = 0; l < W; l = l + 1) begin : g_l
            assign ip[PP*l +: PP] = i_p[PW*l + LO +: PP];
            assign o_line[PW*l + LO +: PP] = ol[PP*l +: PP];
        end
        ot_s81ph_native_sel_pack #(.W(W), .PW(PP)) u_p (
            .clk(clk), .rst_n(rst_n), .i_v(i_v[p]), .i_fl(i_fl[p]), .i_sel(i_sel[W*p +: W]), .i_p(ip), .i_selg(i_selg[W*p +: W]), .i_selh(i_selh[W*p +: W]),
            .o_v(o_v[p]), .o_lv(lv), .o_line(ol), .o_bv(bv), .o_fl(fl));
        if (p == 0) begin : g_ctl
            assign o_lv = lv; assign o_bv = bv; assign o_fl = fl;
        end
    end endgenerate
endmodule

module ot_s81ph_hq_hist #(
    parameter integer HLAT = 0,        // S81-ARCH-RTL-2 11-12: 1 = lockup latches u_fl_* on row -> bank stage and g1 -> s_g
    parameter integer MUT = 0          // 1: every bank counts its neighbour's bins (witness); 2: bank 3 never clears (witness)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    clr,            // per-bank copies of the clear (identical values, distinct nets)
    input  wire          i_v,
    input  wire [15:0]   i_en,
    input  wire [127:0]  i_dg,
    input  wire [8*4-1:0] gsel_d,        // per-bank copies of the command input whose register is the original gsel
    output wire [239:0]  gsum,
    output wire [175:0]  gbin,
    output wire          busy
);
    // exact original busy: HPIPE 1 recurrence of ot_s81ph_native_sel_hist, shadowed from the bank inputs
    reg sx_v, sx_clr, s_v1, s_v2;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin sx_v <= 1'b0; sx_clr <= 1'b0; s_v1 <= 1'b0; s_v2 <= 1'b0; end
        else begin sx_v <= i_v; sx_clr <= clr[0]; s_v1 <= sx_v && !sx_clr; s_v2 <= s_v1 && !sx_clr; end
    assign busy = sx_v || s_v1 || s_v2;
    wire [8*176-1:0] bk_out;
    wire [7:0] bb_unused;
    genvar b, l;
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
        // HLAT: the row stage (v / en / dg) -> per-bank pin stage (s_v / s_en / s_dg) through one lockup latch
        // (vC4r: u_hf/u_hc g_row dg -> g_bank s_dg 377 endpoints to -66 ps, en -> s_en 44)
        wire v_l; wire [15:0] en_l; wire [127:0] dg_l;
        ot_s81ph_hlk #(.W(1 + 16 + 128), .EN(HLAT)) u_fl_row (.clk(clk), .d({v, en, dg}), .q({v_l, en_l, dg_l}));
        assign row_v[b] = v_l; assign row_rn[b] = rn; assign row_en[16*b +: 16] = en_l; assign row_dg[128*b +: 128] = dg_l;
    end endgenerate
`endif
    generate for (b = 0; b < 8; b = b + 1) begin : g_bank
        wire [127:0] nd;
        for (l = 0; l < 16; l = l + 1) begin : g_d
            assign nd[8*l +: 8] = i_dg[8*l +: 8] ^ (8'((MUT == 1) ? (b ^ 1) : b) << 5);
        end
        wire [3:0] ng = gsel_d[4*b +: 4] ^ (4'(b) << 1);
        wire       nc = (MUT == 2 && b == 3) ? 1'b0 : clr[b];
`ifdef OT_BKQ_BSTG
        (* keep = "true" *) reg c1; (* keep = "true" *) reg [3:0] g1;
        wire [3:0] g1_l;   // HLAT: g1 -> s_g (gsel pin stage) through one lockup latch (vC4r 79 endpoints)
        ot_s81ph_hlk #(.W(4), .EN(HLAT)) u_fl_g1 (.clk(clk), .d(g1), .q(g1_l));
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
            s_clr <= {3{c1}}; s_g <= {g1_l, (b == 6) ? ng : g1_l};  // proof mutant: bank 6 low gsel copy one edge early
`else
            s_clr <= {3{c1}}; s_g <= {2{g1_l}};
`endif
        end
`endif
`ifdef OT_HARD_CHILDREN
        ot_s81ph_native_sel_hist_bank u_bank (
`else
        ot_s81ph_native_sel_hist_bank  u_bank (
`endif
`ifdef OT_BKQ_BSTG
            .clk(clk), .rst_n(s_rn), .clr({{5{s_clr[2]}}, {6{s_clr[1]}}, {6{s_clr[0]}}}), .i_v(s_v), .i_en(s_en), .i_dg(s_dg),
            .gsel({{8{s_g[7:4]}}, {8{s_g[3:0]}}}),
`elsif OT_HB_PINCOPY
            // one bank pin per kept capture flop (KITS-SPARE-2/HB 10-25): the bank's copy registers are fed in parallel
            .clk(clk), .rst_n(rst_n), .clr({17{nc}}), .i_v(i_v), .i_en(i_en), .i_dg(nd), .gsel({16{ng}}),
`else
            .clk(clk), .rst_n(rst_n), .clr(nc), .i_v(i_v), .i_en(i_en), .i_dg(nd), .gsel(ng),
`endif
            .gsum(gsum[30*b +: 30]), .gbin(bk_out[176*b +: 176]), .busy(bb_unused[b]));
    end endgenerate
    reg [175:0] j;
    integer k;
`ifdef OT_BKQ_GBREG
    // S81-BKSEL-RF3 vC 11-06 (OT_BKQ_GBREG): the 8-bank OR moves BEHIND a per-bank register. bk_q is the first flop
    // after each bank (placed beside its bank pins), gbin = OR of the 8 bk_q. gbin is then one edge LATER than the
    // combinational form; the parent tile (ot_s81ph_hq_tile.sv, same define) drops its sq stage on the gbin bits, so
    // t_s = sq1 is cycle-exact with the old form (sq1 = OR(bk_out) two edges back in both). 0 added cycles.
    reg [8*176-1:0] bk_q;
    always @(posedge clk) bk_q <= bk_out;
`ifdef OT_BKQ_ORT
    // DIE-S81-78 bksel vI 11-07 (OT_BKQ_ORT, 0 cycles, COORD 20:0x): the 8-bank OR as a PLACED tree.  vH routed: 43 of the
    // 49 resolved worst TT slew pins were bk_q (at the bank pins, x ~381) -> BUFx3 -> one AND4/5 of the flat OR8 placed at
    // the middle of the 8 banks (x ~200): 170-190 um legs, slew 476-634 ps.  Same Boolean OR, same edge (bk_q -> gq);
    // the kept level nets force the tree so ort_place.tcl can put each level at the centroid of its drivers:
    // pair (banks 2p, 2p+1: adjacent sites, ~48 um legs) -> row (4 banks of one site row) -> final next to gq.
    (* keep = "true" *) wire [175:0] ort_p0, ort_p1, ort_p2, ort_p3, ort_r0, ort_r1;
    assign ort_p0 = bk_q[176*0 +: 176] | bk_q[176*1 +: 176];
    assign ort_p1 = bk_q[176*2 +: 176] | bk_q[176*3 +: 176];
    assign ort_p2 = bk_q[176*4 +: 176] | bk_q[176*5 +: 176];
    assign ort_p3 = bk_q[176*6 +: 176] | bk_q[176*7 +: 176];
    assign ort_r0 = ort_p0 | ort_p1;
    assign ort_r1 = ort_p2 | ort_p3;
    always @(*) j = ort_r0 | ort_r1;
`else
    always @(*) begin j = 176'd0; for (k = 0; k < 8; k = k + 1) j = j | bk_q[176*k +: 176]; end
`endif
`ifdef OT_BKQ_GBREG2
    // S81-BKSEL-RF5 vD 11-06 (OT_BKQ_GBREG2, PIN CYCLES +1 on t_s): the 8-bank OR result is registered again (gq, placed
    // at the bank centroid) before it crosses the core to the out-face flop (vCn: bk_q -> OR8 -> t_s_f 778 ps, TT -190).
    // The tile (same define) adds one stage on every other t_s bit, so ALL of t_s is exactly one cycle later than vC.
    reg [175:0] gq;
`ifdef OT_BKQ_GBREG2_MUT
    always @(posedge clk) gq <= j & ~176'd1;      // proof mutant: bit 0 of the registered OR stuck at 0
`else
    always @(posedge clk) gq <= j;
`endif
`endif
`else
    always @(*) begin j = 176'd0; for (k = 0; k < 8; k = k + 1) j = j | bk_out[176*k +: 176]; end
`endif
`ifdef OT_BKQ_GBREG2
    assign gbin = gq;
`else
    assign gbin = j;
`endif
endmodule

// Two-hit-copy showahead store (same contract as ot_sram_showahead_1r1w WREG 1).  Copy 0 drives the macros and slices
// [0, NS/2); copy 1 (identical inputs, distinct registers upstream) drives slices [NS/2, NS).
module ot_sram_showahead_1r1w_h2 #(
    parameter integer W=553, AW=3, NS=(W+15)/16, MUT=0
)(input wire clk, input wire rst_n,
  input wire [1:0] we, input wire [2*AW-1:0] wa, input wire [W-1:0] wd,
  input wire [2*AW-1:0] ra, output wire [W-1:0] q);
    localparam integer NB=(W+127)/128;
    reg [1:0] wv; reg [AW-1:0] waddr0, waddr1; reg [W-1:0] wdata, prevdata;
    always @(posedge clk or negedge rst_n) if (!rst_n) wv <= 2'b00; else wv <= we;
    always @(posedge clk) begin waddr0 <= wa[0 +: AW]; waddr1 <= wa[AW +: AW]; wdata <= wd; prevdata <= wdata; end
    wire [1:0] chit = {we[1] && wa[AW +: AW] == ra[AW +: AW], we[0] && wa[0 +: AW] == ra[0 +: AW]};
    wire [1:0] phit = {wv[1] && waddr1 == ra[AW +: AW], wv[0] && waddr0 == ra[0 +: AW]};
    wire [NB*128-1:0] padded={{(NB*128-W){1'b0}},wdata}, raw;
    genvar b,s;
    generate for(b=0;b<NB;b=b+1) begin:g_bank
`ifdef OT_SRAM_P192
        ot_sram_1r1w_32x128_m1_p192_rc u_m(.clk(clk),
`else
        ot_sram_1r1w_32x128_m1 u_m(.clk(clk),
`endif
            .r_ce_in(1'b1),.r_addr_in(5'(ra[0 +: AW])),
            .rd_out(raw[b*128+:128]),.w_ce_in(wv[0]),.w_addr_in(5'(waddr0)),
            .wd_in(padded[b*128+:128]),.w_mask_in({128{1'b1}}));
    end
    for(s=0;s<NS;s=s+1) begin:g_slice
        localparam integer LO=s*16, SW=(W-LO<16)?W-LO:16, H=(s < NS/2) ? 0 : 1;
        (* keep="true" *) reg cur_q, prev_q;
        always @(posedge clk or negedge rst_n)
            if(!rst_n) begin cur_q<=1'b0; prev_q<=1'b0; end
            else begin cur_q<=(MUT==1)?1'b0:chit[H]; prev_q<=(MUT==2)?1'b0:phit[H]; end
        assign q[LO+:SW]=cur_q ? wdata[LO+:SW] : prev_q ? prevdata[LO+:SW] : raw[LO+:SW];
    end endgenerate
endmodule
