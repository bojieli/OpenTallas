`timescale 1ns/1ps
// S81-SAFE-FIX/CTRL 10-19: one pseudo-channel of dsfd_ctrl_rg2, SAFE redesign of ot_s81ph_ctrl_pc (that module is
// unchanged: the closed S81-PH dsfd_ctrl_pc view binds it).  Same ports, same stream-side behaviour (rq pin register,
// credits rk, response rv/r_data/r_tag/r_beat, wd, status chain, sticky overflow), same PHY K/KR protocol.
// What changed (owner safe-design checklist 10-19; c1/c2 routes missed TT -6.38 in->reg on k_rdy, FF -6.55):
//  (1) PINS: k_rdy is captured in a FLOP AT THE PHY FACE (krq, plus kept copies krq_c per data group).  Nothing
//      combinational follows a PHY-face input any more: kr_v / kr_tag / kr_beat / kr_data land in plain pin flops every
//      cycle (no input-gated enable; the valid flop kr_q qualifies them).
//      Consequence for the PHY valid/ready (unchanged contract: a request transfers on an edge where k_v && k_rdy):
//      the controller learns whether a presented word was taken one cycle later, so a word is presented for ONE cycle
//      (k_v = 1), then k_v = 0 for one decision cycle (pend): taken (krq) -> the next word loads; not taken -> the SAME
//      word is presented again.  No word is ever presented twice after it was taken, no order change: issue rate is at
//      most one request per 2 ckh cycles per PC (priced: the S81 request mix is read-heavy with len 1-4 beats and the
//      response bus carries 1 beat a cycle; the measured bench latency is recorded in the receipt).
//  (3) FANOUT: the hold register's load enable is built per 32-bit group from KEPT copies of the issue state
//      (kv_c, pv_c, krq_c: one set per group, each driving <= 32 data enables + the group's FIFO read select copy).
//      The request FIFO (ot_s81ph_afifo_g) reads each group through its own kept one-hot select, and the response FIFO
//      the same way; the response output register loads every cycle (rv qualifies it: no 277-load enable on `empty`).
// Latency: request rq pin -> k_v = 1 cks + FIFO crossing (2 ckh sync) + 1 ckh (unchanged); a PHY refusal costs 2 ckh
// per retry instead of 1; response kr -> rd = 1 ckh pin reg + 1 ckh write + 2 cks sync + 1 cks out reg (unchanged).
`default_nettype none
module ot_s81ph_ctrl_pcr_ref #(
    parameter integer DQ = 8,
    parameter integer DR = 8,
    parameter integer AW = 30,
    parameter integer TW = 17
) (
    input  wire          cks,
    input  wire          ckh,
    input  wire          rst,
    input  wire [1:0]    ci,
    output reg  [1:0]    co,
    input  wire [340:0]  rq,          // {wdata 256, wstrb 32, tag 17, len 4, addr 30, we, v}
    output wire          rk,
    output reg           rv,
    output reg  [255:0]  r_data,
    output reg  [TW-1:0] r_tag,
    output reg  [3:0]    r_beat,
    output wire          wd,
    output wire          s_ovf,
    output reg           k_v,
    input  wire          k_rdy,
    output wire [AW-1:0] k_addr,
    output wire [3:0]    k_len,
    output wire [TW-1:0] k_tag,
    output wire          k_we,
    output wire [255:0]  k_wdata,
    output wire [31:0]   k_wstrb,
    input  wire          k_wr_done,
    input  wire          kr_v,
    output wire          kr_rdy,
    input  wire [TW-1:0] kr_tag,
    input  wire [3:0]    kr_beat,
    input  wire [255:0]  kr_data
);
    localparam integer QW = 340, RW = 256 + TW + 4, G = 32;
    localparam integer NGQ = (QW + G - 1) / G, NGR = (RW + G - 1) / G;
    wire srst_n, hrst_n;
    ot_s81ph_sync u_srs (.clk(cks), .rst_n(rst), .d(1'b1), .q(srst_n));
    ot_s81ph_sync u_hrs (.clk(ckh), .rst_n(rst), .d(1'b1), .q(hrst_n));
    wire h_live;
    ot_s81ph_sync u_hl (.clk(cks), .rst_n(srst_n), .d(hrst_n), .q(h_live));
    always @(posedge cks or negedge srst_n)
        if (!srst_n) co <= 2'b00; else co <= {ci[1] | s_ovf, ci[0] & h_live};
    // ---- stream side: request pin register -> request FIFO (unchanged)
    reg         rq_v_q;
    reg [339:0] rq_d_q;
    always @(posedge cks or negedge srst_n)
        if (!srst_n) rq_v_q <= 1'b0; else rq_v_q <= rq[0];
    always @(posedge cks) rq_d_q <= rq[340:1];
    wire          q_v;
    wire [QW-1:0] q_d;
    wire          q_rdy_unused;
    wire          h_pop;
    wire [NGQ-1:0] h_pop_g;
    ot_s81ph_afifo_g #(.W(QW), .DEPTH(DQ), .AF(1), .G(G)) u_q (
        .wclk(cks), .wrst_n(srst_n), .w_v(rq_v_q), .w_d(rq_d_q), .w_rdy(q_rdy_unused), .w_credit(rk), .w_ovf(s_ovf),
        .rclk(ckh), .rrst_n(hrst_n), .r_v(q_v), .r_pop(h_pop), .r_pop_g(h_pop_g), .r_d(q_d));
    // ---- HBM side: registered k_rdy, present-then-decide issue (master state)
    reg pend;                 // the previous cycle presented a word (k_v was 1)
    reg krq;                  // k_rdy at the PHY face, registered: the word presented last cycle was taken
    wire ld = !k_v && !(pend && !krq);          // hold register free: idle, or the last presentation was taken
    assign h_pop = ld;                          // the FIFO ignores a pop while empty
    always @(posedge ckh or negedge hrst_n)
        if (!hrst_n) begin k_v <= 1'b0; pend <= 1'b0; krq <= 1'b0; end
        else begin
            pend <= k_v;
            krq  <= k_rdy;
`ifdef S81CTRL_REFERENCE_UNUSED_KRDY
            k_v  <= k_v ? 1'b0 : ld ? q_v : 1'b0;          // mutant: a refused word is never presented again
`else
            k_v  <= k_v ? 1'b0 : ld ? q_v : 1'b1;          // refused (pend && !krq): present the same word again
`endif
        end
    // ---- hold register, per 32-bit group with kept copies of the issue state (each copy: <= 32 data enables)
    reg [QW-1:0] h;
    genvar gq;
    generate for (gq = 0; gq < NGQ; gq = gq + 1) begin : g_h
        localparam integer LO = gq * G;
        localparam integer WG = (gq == NGQ - 1) ? QW - LO : G;
        (* keep *) reg kv_c, pv_c, krq_c;
        always @(posedge ckh or negedge hrst_n)
            if (!hrst_n) begin kv_c <= 1'b0; pv_c <= 1'b0; krq_c <= 1'b0; end
            else begin
                pv_c  <= kv_c;
                krq_c <= k_rdy;
`ifdef S81CTRL_REFERENCE_UNUSED_KRDY
                kv_c  <= kv_c ? 1'b0 : (!kv_c && !(pv_c && !krq_c)) ? q_v : 1'b0;
`else
                kv_c  <= kv_c ? 1'b0 : (!kv_c && !(pv_c && !krq_c)) ? q_v : 1'b1;
`endif
            end
        wire ld_g = !kv_c && !(pv_c && !krq_c);
        assign h_pop_g[gq] = ld_g;
        always @(posedge ckh) if (ld_g) h[LO +: WG] <= q_d[LO +: WG];
    end endgenerate
`ifdef S81PH_MUT_PACK
    assign {k_wdata, k_wstrb, k_tag, k_len, k_addr, k_we} = h ^ {{(QW-36){1'b0}}, 1'b1, 35'd0};   // mutant: tag bit 0 flipped
`else
    assign {k_wdata, k_wstrb, k_tag, k_len, k_addr, k_we} = h;
`endif
    // ---- HBM side: response pin registers (plain flops, no input-gated enable) -> landing FIFO
    // kr_v lands in a plain pin flop (kr_vq); the ready this controller showed the PHY in that cycle (l_rdy, a register)
    // is captured beside it (kr_rq): the transfer was kr_v && kr_rdy at that edge, so the FIFO write valid is
    // kr_vq && kr_rq one cycle later -- no gate between the kr_v pin and its flop (native capture, cts_native_probe).
    reg           kr_vq, kr_rq;
    reg [RW-1:0]  krd_q;
    wire          l_rdy;
    assign kr_rdy = l_rdy;                       // registered (ot_s81ph_afifo_g.w_rdy)
    always @(posedge ckh or negedge hrst_n)
        if (!hrst_n) begin kr_vq <= 1'b0; kr_rq <= 1'b0; end else begin kr_vq <= kr_v; kr_rq <= l_rdy; end
    wire          kr_q = kr_vq && kr_rq;
    always @(posedge ckh) krd_q <= {kr_data, kr_tag, kr_beat};
    wire          l_v;
    wire [RW-1:0] l_d;
    wire          l_ovf, l_cr;
    ot_s81ph_afifo_g #(.W(RW), .DEPTH(DR), .AF(2), .G(G)) u_r (
        .wclk(ckh), .wrst_n(hrst_n), .w_v(kr_q), .w_d(krd_q), .w_rdy(l_rdy), .w_credit(l_cr), .w_ovf(l_ovf),
        .rclk(cks), .rrst_n(srst_n), .r_v(l_v), .r_pop(1'b1), .r_pop_g({NGR{1'b1}}), .r_d(l_d));
    // response output register: data loads every cycle (rv qualifies it; no enable fan-out on the FIFO's empty flop)
    always @(posedge cks or negedge srst_n)
        if (!srst_n) rv <= 1'b0; else rv <= l_v;
    always @(posedge cks)
`ifdef S81PH_MUT_BEAT
        {r_data, r_tag, r_beat} <= {l_d[RW-1:4], l_d[2:0], l_d[3]};
`else
        {r_data, r_tag, r_beat} <= l_d;
`endif
    // ---- write done: HBM pin register -> pulse crossing (unchanged)
    reg wd_q;
    always @(posedge ckh or negedge hrst_n) if (!hrst_n) wd_q <= 1'b0; else wd_q <= k_wr_done;
    ot_s81ph_pulse_x #(.CW(4)) u_wd (.sclk(ckh), .srst_n(hrst_n), .s_p(wd_q), .dclk(cks), .drst_n(srst_n), .d_p(wd));
endmodule
`default_nettype wire
