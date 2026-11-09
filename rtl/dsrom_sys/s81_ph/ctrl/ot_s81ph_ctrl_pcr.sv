`timescale 1ns/1ps
// S81-SAFE-FIX/CTRL 10-19: one pseudo-channel of dsfd_ctrl_rg2, SAFE redesign of ot_s81ph_ctrl_pc (that module is
// unchanged: the closed S81-PH dsfd_ctrl_pc view binds it).  Same ports, same stream-side behaviour (rq pin register,
// credits rk, response rv/r_data/r_tag/r_beat, wd, status chain, sticky overflow), same PHY K/KR protocol.
// What changed (owner safe-design checklist 10-19; c1/c2 routes missed TT -6.38 in->reg on k_rdy, FF -6.55):
//  (1) PINS: k_rdy is captured in a FLOP AT THE PHY FACE (krq; since S81-TRANSPORT-FIX it is only a check).  Nothing
//      combinational follows a PHY-face input any more: kr_v / kr_tag / kr_beat / kr_data land in plain pin flops every
//      cycle (no input-gated enable; the valid flop kr_q qualifies them).
//      A word is presented for ONE cycle (k_v = 1), then k_v = 0 for one decision cycle.  Since S81-TRANSPORT-FIX (note
//      below) a presented word is taken by construction and the next word loads if a credit is held.  Issue rate is at
//      most one request per 2 ckh cycles per PC (priced: the S81 request mix is read-heavy with len 1-4 beats and the
//      response bus carries 1 beat a cycle; the measured bench latency is recorded in the receipt).
//  (3) FANOUT: the hold register's load enable is built per 32-bit group from KEPT copies of the issue state
//      (kv_c, cr_c: one set per group, each driving <= 32 data enables + the group's FIFO read select copy).
//      The request FIFO (ot_s81ph_afifo_g) reads each group through its own kept one-hot select, and the response FIFO
//      the same way; the response output register loads every cycle (rv qualifies it: no 277-load enable on `empty`).
// S81-TRANSPORT-FIX 11-08 (TRANSPORT-2 path 3a): the die binds pipeline stages on k_* / k_rdy (DN controller->PHY, UP
// PHY->controller, plan values 2/2 .. 15/12), so k_rdy at this edge says nothing about the word presented at this edge
// (present-then-decide lost or duplicated words whenever the PHY queue refused).  Issue is now END-TO-END CREDIT, safe
// at any depth: a word is presented only while requests presented minus requests completed (o) is below PQD, the PHY's
// queue depth; a read completes on its last response beat (length queue lq, reads are in order), a write on wr_done.
// Every word in the PHY queue is outstanding, so the queue holds at most PQD - 1 when a new word lands: q_rdy is 1 on
// every arrival, there is no refusal, no retry and no stale k_rdy decision.  Cost: a read keeps its credit until data
// returns (+ tCL + transport), so a PC's peak is PQD requests per loop.  k_rdy stays a pin (checked: it must read 1
// while nothing is outstanding; sticky k_bad joins the overflow fault).  MUT S81CTRL_MUT_CREDIT: limit PQD + 1.
// Latency: request rq pin -> k_v = 1 cks + FIFO crossing (2 ckh sync) + 1 ckh (unchanged); response kr -> rd = 1 ckh pin reg + 1 ckh write + 2 cks sync + 1 cks out reg (unchanged).
`default_nettype none
module ot_s81ph_ctrl_pcr #(
    parameter integer DQ = 8,
    parameter integer DR = 8,
    parameter integer PQD = 8,    // PHY request queue depth (ot_s81_hbm_pcc QD): the end-to-end credit limit
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
    `ifdef S81CTRL_NATIVE32
    localparam integer QW = 340, RW = 256 + TW + 4, G = 12;
`else
    localparam integer QW = 340, RW = 256 + TW + 4, G = 32;
`endif
    localparam integer NGQ = (QW + G - 1) / G, NGR = (RW + G - 1) / G;
    wire srst_n, hrst_n;
    ot_s81ph_sync u_srs (.clk(cks), .rst_n(rst), .d(1'b1), .q(srst_n));
    ot_s81ph_sync u_hrs (.clk(ckh), .rst_n(rst), .d(1'b1), .q(hrst_n));
`ifdef S81CTRL_NATIVE32
    // Two-stage reset landing is above; one release edge distributes it to
    // native kept regional leaves. Assertion remains asynchronous.
    wire [7:0] srl, hrl;
    ot_s81ph_reset_leafbank u_srbank (.clk(cks), .rst_n(srst_n), .q(srl));
    ot_s81ph_reset_leafbank u_hrbank (.clk(ckh), .rst_n(hrst_n), .q(hrl));
`else
    wire [7:0] srl = {8{srst_n}}, hrl = {8{hrst_n}};
`endif
    wire h_live, k_bad_s;
    ot_s81ph_sync u_hl (.clk(cks), .rst_n(srl[0]), .d(hrl[0]), .q(h_live));
    always @(posedge cks or negedge srl[0])
        if (!srl[0]) co <= 2'b00; else co <= {ci[1] | s_ovf | k_bad_s, ci[0] & h_live};
    // ---- stream side: request pin register -> request FIFO (unchanged)
    reg         rq_v_q;
    reg [339:0] rq_d_q;
    always @(posedge cks or negedge srl[0])
        if (!srl[0]) rq_v_q <= 1'b0; else rq_v_q <= rq[0];
    always @(posedge cks) rq_d_q <= rq[340:1];
    wire          q_v;
    wire [QW-1:0] q_d;
    wire          q_rdy_unused;
    wire          h_pop;
    wire [NGQ-1:0] h_pop_g;
`ifdef S81CTRL_SRAM_FIFO
    ot_s81ph_afifo_g_sram #(
`else
    ot_s81ph_afifo_g #(
`endif
        .W(QW), .DEPTH(DQ), .AF(1), .G(G)) u_q (
        .wclk(cks), .wrst_n(srl[1]), .w_v(rq_v_q), .w_d(rq_d_q), .w_rdy(q_rdy_unused), .w_credit(rk), .w_ovf(s_ovf),
        .rclk(ckh), .rrst_n(hrl[1]), .r_v(q_v), .r_pop(h_pop), .r_pop_g(h_pop_g), .r_d(q_d));
    // ---- HBM side: end-to-end credit issue (master state); see the S81-TRANSPORT-FIX note in the header
`ifdef S81CTRL_MUT_CREDIT
    localparam integer CRED = PQD + 1;          // mutant: one word too many (the PHY queue can refuse)
`else
    localparam integer CRED = PQD;
`endif
    wire          kr_qv;                        // a response beat landed this edge (kr_q below)
    wire  [3:0]   kr_qbeat;
    reg           wd_cr;                        // completed write (k_wr_done pin flop)
    reg  [3:0]    lq [0:(1 << $clog2(CRED)) - 1];    // read length - 1, per outstanding read, issue order
    reg  [$clog2(CRED)-1:0] lqw, lqr;
    wire          r_cpl = kr_qv && (kr_qbeat == lq[lqr]);    // last beat of the oldest outstanding read
    reg  [4:0]    o;                            // presented, not yet seen complete
    reg           r_cpl_q;                      // one edge late: a later credit release only widens the margin
    wire [4:0]    o_n = o + 5'(k_v) - 5'(r_cpl_q) - 5'(wd_cr);
    reg           cr_ok;                        // registered o_n < CRED: the next decision may present
    wire          ld = !k_v && cr_ok;           // hold register free and a credit is held
    assign h_pop = ld;                          // the FIFO ignores a pop while empty
    reg krq, k_arm, k_bad;                      // k_rdy pin flop; armed by the first word; sticky: k_rdy low while nothing is outstanding
    always @(posedge ckh or negedge hrl[0])
        if (!hrl[0]) begin
            k_v <= 1'b0; krq <= 1'b0; k_arm <= 1'b0; k_bad <= 1'b0; o <= 5'd0; cr_ok <= 1'b1; lqw <= '0; lqr <= '0; wd_cr <= 1'b0; r_cpl_q <= 1'b0;
        end else begin
            krq <= k_rdy; k_arm <= k_arm | k_v; k_bad <= k_bad | (k_arm && (o == 5'd0) && !krq);
            k_v <= k_v ? 1'b0 : ld ? q_v : 1'b0;
            o <= o_n; cr_ok <= o_n < 5'(CRED);
            wd_cr <= k_wr_done; r_cpl_q <= r_cpl;
            if (k_v && !k_we) begin lq[lqw] <= k_len - 4'd1; lqw <= lqw + 1'b1; end
            if (r_cpl) lqr <= lqr + 1'b1;
        end
    // ---- hold register, per 32-bit group with kept copies of the issue state (each copy: <= 32 data enables)
    reg [QW-1:0] h;
    genvar gq;
    generate for (gq = 0; gq < NGQ; gq = gq + 1) begin : g_h
        localparam integer LO = gq * G;
        localparam integer WG = (gq == NGQ - 1) ? QW - LO : G;
        (* keep *) reg kv_c, cr_c;
        always @(posedge ckh or negedge hrl[2 + gq%6])
            if (!hrl[2 + gq%6]) begin kv_c <= 1'b0; cr_c <= 1'b1; end
            else begin
                kv_c <= kv_c ? 1'b0 : (!kv_c && cr_c) ? q_v : 1'b0;
                cr_c <= o_n < 5'(CRED);
            end
        wire ld_g = !kv_c && cr_c;
        assign h_pop_g[gq] = ld_g;
        always @(posedge ckh) if (ld_g) h[LO +: WG] <= q_d[LO +: WG];
    end endgenerate
`ifdef S81PH_MUT_PACK
    assign {k_wdata, k_wstrb, k_tag, k_len, k_addr, k_we} = h ^ {{(QW-36){1'b0}}, 1'b1, 35'd0};   // mutant: tag bit 0 flipped
`else
    assign {k_wdata, k_wstrb, k_tag, k_len, k_addr, k_we} = h;
`endif
    ot_s81ph_sync u_kbs (.clk(cks), .rst_n(srl[0]), .d(k_bad), .q(k_bad_s));
    // ---- HBM side: response pin registers (plain flops, no input-gated enable) -> landing FIFO
    // kr_v lands in a plain pin flop (kr_vq); the ready this controller showed the PHY in that cycle (l_rdy, a register)
    // is captured beside it (kr_rq): the transfer was kr_v && kr_rdy at that edge, so the FIFO write valid is
    // kr_vq && kr_rq one cycle later -- no gate between the kr_v pin and its flop (native capture, cts_native_probe).
    reg           kr_vq, kr_rq;
    reg [RW-1:0]  krd_q;
    wire          l_rdy;
    assign kr_rdy = l_rdy;                       // registered (ot_s81ph_afifo_g.w_rdy)
    always @(posedge ckh or negedge hrl[0])
        if (!hrl[0]) begin kr_vq <= 1'b0; kr_rq <= 1'b0; end else begin kr_vq <= kr_v; kr_rq <= l_rdy; end
    wire          kr_q = kr_vq && kr_rq;
    always @(posedge ckh) krd_q <= {kr_data, kr_tag, kr_beat};
    assign kr_qv = kr_q;
    assign kr_qbeat = krd_q[3:0];
    wire          l_v;
    wire [RW-1:0] l_d;
    wire          l_ovf, l_cr;
`ifdef S81CTRL_SRAM_FIFO
    ot_s81ph_afifo_g_sram #(
`else
    ot_s81ph_afifo_g #(
`endif
        .W(RW), .DEPTH(DR), .AF(2), .G(G)) u_r (
        .wclk(ckh), .wrst_n(hrl[1]), .w_v(kr_q), .w_d(krd_q), .w_rdy(l_rdy), .w_credit(l_cr), .w_ovf(l_ovf),
        .rclk(cks), .rrst_n(srl[2]), .r_v(l_v), .r_pop(1'b1), .r_pop_g({NGR{1'b1}}), .r_d(l_d));
    // response output register: data loads every cycle (rv qualifies it; no enable fan-out on the FIFO's empty flop)
    always @(posedge cks or negedge srl[0])
        if (!srl[0]) rv <= 1'b0; else rv <= l_v;
    always @(posedge cks)
`ifdef S81PH_MUT_BEAT
        {r_data, r_tag, r_beat} <= {l_d[RW-1:4], l_d[2:0], l_d[3]};
`else
        {r_data, r_tag, r_beat} <= l_d;
`endif
    // ---- write done: HBM pin register -> pulse crossing (unchanged)
    reg wd_q;
    always @(posedge ckh or negedge hrl[0]) if (!hrl[0]) wd_q <= 1'b0; else wd_q <= k_wr_done;
    ot_s81ph_pulse_x #(.CW(4)) u_wd (.sclk(ckh), .srst_n(hrl[0]), .s_p(wd_q), .dclk(cks), .drst_n(srl[0]), .d_p(wd));
endmodule
// Separate kept outputs remain distinct after synth; the native census is
// required to prove that the mapper retained them and each consumer stays <=32.
module ot_s81ph_reset_leafbank #(parameter integer N=8)(
    input wire clk, rst_n, output wire [N-1:0] q
);
    (* keep *) reg [N-1:0] leaf_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) leaf_q <= {N{1'b0}};
        else leaf_q <= {N{1'b1}};
    assign q = leaf_q;
endmodule
`default_nettype wire
