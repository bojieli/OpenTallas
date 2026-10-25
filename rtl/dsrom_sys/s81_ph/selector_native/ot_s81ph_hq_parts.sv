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
    generate for (b = 0; b < 8; b = b + 1) begin : g_bank
        wire [127:0] nd;
        for (l = 0; l < 16; l = l + 1) begin : g_d
            assign nd[8*l +: 8] = i_dg[8*l +: 8] ^ (8'((MUT == 1) ? (b ^ 1) : b) << 5);
        end
        wire [3:0] ng = gsel_d[4*b +: 4] ^ (4'(b) << 1);
        wire       nc = (MUT == 2 && b == 3) ? 1'b0 : clr[b];
`ifdef OT_HARD_CHILDREN
        ot_s81ph_native_sel_hist_bank u_bank (
`else
        ot_s81ph_native_sel_hist_bank #(.W(16), .CB(11), .BANK(0), .NB(32), .HPIPE(1)) u_bank (
`endif
`ifdef OT_HB_PINCOPY
            // one bank pin per kept capture flop (KITS-SPARE-2/HB 10-25): the bank's copy registers are fed in parallel
            .clk(clk), .rst_n(rst_n), .clr({17{nc}}), .i_v(i_v), .i_en(i_en), .i_dg(nd), .gsel({16{ng}}),
`else
            .clk(clk), .rst_n(rst_n), .clr(nc), .i_v(i_v), .i_en(i_en), .i_dg(nd), .gsel(ng),
`endif
            .gsum(gsum[30*b +: 30]), .gbin(bk_out[176*b +: 176]), .busy(bb_unused[b]));
    end endgenerate
    reg [175:0] j;
    integer k;
    always @(*) begin j = 176'd0; for (k = 0; k < 8; k = k + 1) j = j | bk_out[176*k +: 176]; end
    assign gbin = j;
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
