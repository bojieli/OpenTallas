`timescale 1ns/1ps
// Five speculative positions consume ONE synchronous INT8 matrix word and
// one scale response per cycle. Each position keeps its own activation stream,
// K-split accumulators and scaled FP32 result. The caller issues one common
// matrix descriptor and waits for all five idle bits before the next matrix.
// This is the weight-broadcast MAC array; draft/accept/commit scheduling sits
// outside it, and the fifth lane is not a fifth ROM read.
module ot_hdc_qwen_m5_verify_array #(
    parameter integer W = 16, G = 4, IL = 8, AW = 24, NW = 16
) (
    input  wire clk, rst_n, go,
    output wire ready, idle, fault,
    input  wire [NW-1:0] i_nout, i_tiles, i_k,
    input  wire [AW-1:0] i_wbase, i_ts, i_ks, i_js,
    input  wire [AW-1:0] i_xks, i_xjs, i_xcs,
    input  wire [AW-1:0] i_ots, i_ojs,
    input  wire [3:0] i_split,
    input  wire i_round, i_amax,
    input  wire [5*AW-1:0] i_xbase, i_obase,
    output wire wrom_re,
    output wire [AW-1:0] wrom_addr,
    input  wire [G*W*8-1:0] wrom_q,
    output wire scale_re,
    output wire [G*AW-1:0] scale_addr,
    input  wire [G*W*16-1:0] scale_q,
    output wire [5*G-1:0] x_re,
    output wire [5*G*AW-1:0] x_addr,
    input  wire [5*G*32-1:0] x_q,
    output wire [4:0] ov,
    output wire [5*G-1:0] o_we,
    output wire [5*G*AW-1:0] o_addr,
    output wire [5*G*W-1:0] o_mask,
    output wire [5*G*W*32-1:0] o_data,
    output wire [5*NW-1:0] am_idx,
    output wire [5*32-1:0] am_val,
    output wire [4:0] am_any
);
    wire [4:0] ready_s, idle_s, fault_s, wr_s, sr_s;
    wire [5*AW-1:0] wa_s;
    wire [5*G*AW-1:0] sa_s;
    assign ready = &ready_s;
    assign idle = &idle_s;
    assign wrom_re = wr_s[0];
    assign wrom_addr = wa_s[0 +: AW];
    assign scale_re = sr_s[0];
    assign scale_addr = sa_s[0 +: G*AW];
    // An address disagreement is a protocol fault: no speculative position
    // may pull a different weight from the single physical ROM port.
    wire mismatch = (|((wr_s ^ {5{wr_s[0]}}))) || (|((sr_s ^ {5{sr_s[0]}}))) ||
                    (wr_s[1] && wa_s[AW +: 4*AW] != {4{wa_s[0 +: AW]}}) ||
                    (sr_s[1] && sa_s[G*AW +: 4*G*AW] != {4{sa_s[0 +: G*AW]}});
    assign fault = (|fault_s) || mismatch;
    genvar s;
    generate for (s = 0; s < 5; s = s + 1) begin : g_slot
        ot_hdc_matvec #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW), .INT8_WEIGHT(1)) u_me (
            .clk(clk), .rst_n(rst_n), .go(go), .ready(ready_s[s]), .idle(idle_s[s]),
            .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(1'b0),
            .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js),
            .i_xbase(i_xbase[s*AW +: AW]), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs),
            .i_jsh(3'd0), .i_split(i_split), .i_wcs({AW{1'b0}}), .i_round(i_round),
            .i_obase(i_obase[s*AW +: AW]), .i_ots(i_ots), .i_ojs(i_ojs),
            .i_mmode(1'b0), .i_oen(1'b1), .i_amax(i_amax), .i_rmax(1'b0), .i_mbase({AW{1'b0}}),
            .wrom_re(wr_s[s]), .wrom_addr(wa_s[s*AW +: AW]), .wrom_q(wrom_q),
            .scale_re(sr_s[s]), .scale_addr(sa_s[s*G*AW +: G*AW]), .scale_q(scale_q),
            .kv_re(), .kv_addr(), .kv_q({(G*W*32){1'b0}}),
            .x_re(x_re[s*G +: G]), .x_addr(x_addr[s*G*AW +: G*AW]), .x_q(x_q[s*G*32 +: G*32]),
            .ov(ov[s]), .o_we(o_we[s*G +: G]), .o_addr(o_addr[s*G*AW +: G*AW]),
            .o_mask(o_mask[s*G*W +: G*W]), .o_data(o_data[s*G*W*32 +: G*W*32]),
            .am_idx(am_idx[s*NW +: NW]), .am_val(am_val[s*32 +: 32]), .am_any(am_any[s]),
            .mx_we(), .mx_addr(), .mx_mask(), .mx_data(), .progress(), .fault(fault_s[s])
        );
    end endgenerate
endmodule
