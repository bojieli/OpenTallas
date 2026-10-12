`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// el1011-hbm-coll 2026-10-11: hfd_lk_ep REBUILD as a hardened cluster (owner textbook audit class 1: 95,000 flops on one
// core_clk root over 1,728 x 1,015 um, CTS insertion 1,485..3,783 ps in hfd_lk_ep-0c493ddbb cc5).  hfd_lk_ep sits beside
// each of the 9 R25GQ SerDes (replicated cluster: harden once, step 9x).  The cluster = 3 x ot_lkep_sub (this file, ONE
// hard view, no parameter overrides at the cluster) + the shared glue in ot_hbm_lk_ep.
//
// Cut: the RL relay chains that already carried every per-sub bus between a retry macro and the shared logic are the
// seams.  Every tile input lands on a tile flop and every tile output leaves from a tile flop:
//   in : w_d / w_oh (glue regs)        -> w_dg / w_ohg (the existing per-sub bank copy stage)
//        adm (glue l0_v, the admission) -> adm_t (+1 edge, below)
//        tx_cr / o_cr (glue crq)         -> credit relay stage 1
//        fb_v / fb_d (glue fbv / fb_*)   -> fb relay stage 1
//        rx_v / rx_d (glue c_v / c_h)    -> rx relay stage 1
//   out: icr_ret (credit relay last stage), tx_v / tx_d and o_v / o_d (sink relay stage 1), ak (ack relay last stage),
//        drop / fault / rep (status capture registers)
// Cycle changes vs 0c493ddbb (transaction-level exact; bench tb_hfd_lk_ep / tb_lk_rate gate adoption):
//   * the TX bank read: the head advances on adm_t (the admission registered in the tile), the launch register l0 one
//     edge after it -> a TX flit reaches its pin buffer 2 edges later.  Bank occupancy stays <= ceil(TXQ/NS) + 2 <= QD.
//   * status (fault / replay count / drop) captured once more at the tile edge: +1 edge (status only).
// ---------------------------------------------------------------------------

// ot_lkep_sinkp: pin half of ot_lkep_sinkq (macro output port side): credit counter / m_rdy, capture registers, relay
// stage 1 (the tile's output register); the credit returns through N relay stages from the consumer's crq.
module ot_lkep_sinkp #(parameter integer W = 545, parameter integer D = 4, parameter integer N = 2) (
    input  wire         clk,
    input  wire         rst_p,
    input  wire         rst_c,
    input  wire         m_v,
    input  wire [W-1:0] m_d,
    output reg          m_rdy,
    output wire         o_v,           // relay stage 1 (registered)
    output wire [W-1:0] o_d,
    input  wire         crq            // consumer pop (a glue register)
);
    localparam integer CB = $clog2(D + 1);
    reg  [CB-1:0] cnt;
    reg           cap_v;
    reg  [W-1:0]  cap_d;
    wire          crb, crb_d;
    wire          hs = m_v && m_rdy;
    wire [CB-1:0] cnt_n = cnt - (hs ? 1'b1 : 1'b0) + (crb ? 1'b1 : 1'b0);
    always @(posedge clk or negedge rst_p)
        if (!rst_p) begin cnt <= D; m_rdy <= 1'b0; cap_v <= 1'b0; end
        else begin cnt <= cnt_n; m_rdy <= (cnt_n != 0); cap_v <= hs; end
    always @(posedge clk) cap_d <= m_d;
    ot_lkep_relay #(.W(W), .N(1)) u_f1 (.clk(clk), .rst_n(rst_c), .i_v(cap_v), .i_d(cap_d), .o_v(o_v), .o_vr(), .o_d(o_d));
    ot_lkep_relay #(.W(1), .N(N)) u_c (.clk(clk), .rst_n(rst_p), .i_v(crq), .i_d(1'b0), .o_v(crb), .o_d(crb_d));
endmodule

// ot_lkep_sinkc: consumer half of ot_lkep_sinkq: relay stages 2..N, the D-deep FIFO, pop -> crq (registered, to the
// pin half's credit relay).  ot_lkep_sinkp + ot_lkep_sinkc == ot_lkep_sinkq edge for edge.
module ot_lkep_sinkc #(parameter integer W = 545, parameter integer D = 4, parameter integer N = 2, parameter integer SL = 64) (
    input  wire         clk,
    input  wire         rst_c,
    input  wire         i_v,           // sink relay stage 1 (tile output register)
    input  wire [W-1:0] i_d,
    output wire         h_v,
    output wire [W-1:0] h_d,
    input  wire         pop,
    output reg          crq
);
    localparam integer NSL = (W + SL - 1) / SL;
    localparam integer CB = $clog2(D + 1);
    wire          f_v;
    wire [W-1:0]  f_d;
    wire [NSL-1:0] f_vs;
    ot_lkep_relay #(.W(W), .N(N - 1), .NV(NSL)) u_f (.clk(clk), .rst_n(rst_c), .i_v(i_v), .i_d(i_d), .o_v(f_v), .o_vr(f_vs), .o_d(f_d));
    reg  [D*W-1:0]   m;
    (* keep *) reg [NSL*D-1:0] wp;
    (* keep *) reg [NSL*D-1:0] rp;
    reg  [CB-1:0]    n;
    wire [W-1:0]     head;
    genvar s, e;
    generate for (s = 0; s < NSL; s = s + 1) begin : g_s
        localparam integer LO = s * SL;
        localparam integer HI = (LO + SL > W) ? W : LO + SL;
        for (e = 0; e < D; e = e + 1) begin : g_e
            always @(posedge clk) if (f_vs[s] && wp[s*D+e]) m[e*W+LO +: HI-LO] <= f_d[HI-1:LO];
        end
        reg [HI-LO-1:0] x;
        integer j;
        always @(*) begin
            x = {(HI-LO){1'b0}};
            for (j = 0; j < D; j = j + 1) x = x | ({(HI-LO){rp[s*D+j]}} & m[j*W+LO +: HI-LO]);
        end
        assign head[HI-1:LO] = x;
    end endgenerate
    assign h_v = (n != 0);
    assign h_d = head;
    integer t;
    always @(posedge clk or negedge rst_c)
        if (!rst_c) begin
            n <= {CB{1'b0}}; crq <= 1'b0;
            for (t = 0; t < NSL; t = t + 1) begin wp[t*D +: D] <= {{(D-1){1'b0}}, 1'b1}; rp[t*D +: D] <= {{(D-1){1'b0}}, 1'b1}; end
        end else begin
            n <= n + (f_v ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
            crq <= pop;
            for (t = 0; t < NSL; t = t + 1) begin
                if (f_v) wp[t*D +: D] <= {wp[t*D +: D], wp[t*D+D-1]};
                if (pop) rp[t*D +: D] <= {rp[t*D +: D], rp[t*D+D-1]};
            end
        end
endmodule

// ot_lkep_sub: one sub-channel tile (defaults = the hardened configuration of hfd_lk_ep: NS 3, TXQ 32 -> QD 16, RL 2).
module ot_lkep_sub #(
    parameter integer W = 545, parameter integer SW = 12, parameter integer EW = 24,
    parameter integer QD = 16, parameter integer RL = 2, parameter integer PBD = 4, parameter integer TFD = 4,
    parameter integer OFD = 4, parameter integer SQ = 4, parameter integer SL = 64,
    parameter integer TIMEOUT = 8192, parameter integer MAX_RETRY = 8, parameter integer NAKH_HW = 64
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [EW-1:0]         session,
    // TX bank write (glue w_d / this sub's w_oh slices) and admission (glue l0_v)
    input  wire [W-1:0]          w_d,
    input  wire [((W+SL-1)/SL)*QD-1:0] w_oh,
    input  wire                  adm,
    output wire                  icr_ret,
    // TX out (macro tx words) -> glue grant FIFO
    output wire                  tx_v,
    output wire [EW+SW+W-1:0]    tx_d,
    input  wire                  tx_cr,
    // reverse-frame ack level, feedback in
    output wire [SW+EW:0]        ak,
    input  wire                  fb_v,
    input  wire [SW:0]           fb_d,       // {nak, seq}
    // RX in (CRC-checked frame of this sub), RX out (macro out words) -> glue merge FIFO
    input  wire                  rx_v,
    input  wire [EW+SW+W-1:0]    rx_d,
    output wire                  o_v,
    output wire [W-1:0]          o_d,
    input  wire                  o_cr,
    // status (registered)
    output reg                   st_fault,
    output reg                   st_drop,
    output reg  [31:0]           st_rep
);
    localparam integer TW = EW + SW + W;
    localparam integer NSL = (W + SL - 1) / SL;
    localparam integer NSLT = (TW + SL - 1) / SL;
    // reset: own synchroniser (same depth as the glue's: identical release edge), replicated region copies
    reg  [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg [3:0] rl;                            // [0] macro / pin side, [1] TX bank, [2] TX-out, [3] RX
    always @(posedge clk) rl <= {4{rs[1]}};
    (* keep *) reg [EW-1:0] ses;
    always @(posedge clk) ses <= session;

    // ---------------------------------------------------------------- retry pipeline (hard macro)
    wire          p_in_v, p_in_r, p_tx_v, p_tx_r, p_rx_v, p_rx_r, p_out_v, p_out_r, p_fb_v, p_fault, p_fb_n, p_ack_n;
    wire [W-1:0]  p_in_dd, p_tx_d, p_out_d;
    wire [SW-1:0] p_tx_s, p_ack_s, p_ret, p_fb_s;
    wire [EW-1:0] p_tx_e, p_ack_e;
    wire [TW-1:0] p_rx_w;
    wire [31:0]   p_rep;
`ifdef SYNTHESIS
    ot_hbm_link_retry_pipeline u_rp (
`else
    ot_hbm_link_retry_pipeline #(.ENABLE(1), .W(W), .SW(SW), .EW(EW), .DEPTH(512), .TIMEOUT(TIMEOUT),
        .MAX_RETRY(MAX_RETRY), .RSTR(1), .RX_SLOT_SAMPLE(1), .TX_SLOT_SAMPLE(1), .IN_PIN(1), .IN_WPIN(1),
`ifndef OT_LKEP_MUT_NAKHOLD
        .NAK_HOLD(NAKH_HW)) u_rp (
`else
        .NAK_HOLD(0)) u_rp (                         // mutant: the pre-fix pipeline (a lost replay waits for TIMEOUT)
`endif
`endif
        .clk(clk), .rst_n(rl[0]), .session(ses),
        .in_valid(p_in_v), .in_ready(p_in_r), .in_data(p_in_dd),
        .tx_valid(p_tx_v), .tx_ready(p_tx_r), .tx_data(p_tx_d), .tx_seq(p_tx_s), .tx_session(p_tx_e),
        .rx_valid(p_rx_v), .rx_ready(p_rx_r), .rx_ue(1'b0), .rx_data(p_rx_w[W-1:0]),
        .rx_seq(p_rx_w[W +: SW]), .rx_session(p_rx_w[W+SW +: EW]),
        .out_valid(p_out_v), .out_ready(p_out_r), .out_data(p_out_d),
        .ack_seq(p_ack_s), .ack_nak(p_ack_n), .ack_session(p_ack_e),
        .fb_valid(p_fb_v), .fb_good(1'b1), .fb_nak(p_fb_n), .fb_seq(p_fb_s), .fb_session(ses),
        .fault(p_fault), .retained(p_ret), .replay_count(p_rep));

    // ---------------------------------------------------------------- TX queue bank (this sub's flits)
    (* keep *) reg [W-1:0]      w_dg;
    (* keep *) reg [NSL*QD-1:0] w_ohg;
    (* keep *) reg [NSL-1:0]    adm_t;                // admission, one copy per 64-b slice
    (* keep *) reg [NSL*QD-1:0] hd;
    reg  [QD*W-1:0] qs;
    reg  [W-1:0]    l0_d;
    reg             l0_v;
    always @(posedge clk) begin w_dg <= w_d; w_ohg <= w_oh; end
    genvar s, e;
    generate for (s = 0; s < NSL; s = s + 1) begin : g_s
        localparam integer LO = s * SL;
        localparam integer HI = (LO + SL > W) ? W : LO + SL;
        for (e = 0; e < QD; e = e + 1) begin : g_e
            always @(posedge clk) if (w_ohg[s*QD+e]) qs[e*W+LO +: HI-LO] <= w_dg[LO +: HI-LO];
        end
        reg [HI-LO-1:0] x;
        integer j;
        always @(*) begin
            x = {(HI-LO){1'b0}};
            for (j = 0; j < QD; j = j + 1) x = x | ({(HI-LO){hd[s*QD+j]}} & qs[j*W+LO +: HI-LO]);
        end
        always @(posedge clk) l0_d[LO +: HI-LO] <= x;
        always @(posedge clk or negedge rl[1])
            if (!rl[1]) begin adm_t[s] <= 1'b0; hd[s*QD +: QD] <= {{(QD-1){1'b0}}, 1'b1}; end
            else begin
                adm_t[s] <= adm;
                if (adm_t[s]) hd[s*QD +: QD] <= {hd[s*QD +: QD], hd[s*QD+QD-1]};
            end
    end endgenerate
    always @(posedge clk or negedge rl[1]) if (!rl[1]) l0_v <= 1'b0; else l0_v <= adm_t[0];

    // ---------------------------------------------------------------- l0 -> RL relays -> pin buffer; credit back
    wire          r_v_, cr_p, cr_d, dr;
    wire [W-1:0]  r_d;
    wire [NSL-1:0] r_vs;
    ot_lkep_relay #(.W(W), .N(RL), .NV(NSL)) u_tr (.clk(clk), .rst_n(rl[0]), .i_v(l0_v), .i_d(l0_d), .o_v(r_v_), .o_vr(r_vs), .o_d(r_d));
    ot_lkep_pinq #(.W(W), .D(PBD), .SL(SL)) u_tb (.clk(clk), .rst_n(rl[0]), .i_v(r_v_), .i_vs(r_vs), .i_d(r_d),
        .o_v(p_in_v), .o_d(p_in_dd), .o_rdy(p_in_r), .cr(cr_p), .drop(dr));
    ot_lkep_relay #(.W(1), .N(RL)) u_tc (.clk(clk), .rst_n(rl[1]), .i_v(cr_p), .i_d(1'b0), .o_v(icr_ret), .o_d(cr_d));

    // ---------------------------------------------------------------- TX out pin half
    ot_lkep_sinkp #(.W(TW), .D(TFD), .N(RL)) u_to (.clk(clk), .rst_p(rl[0]), .rst_c(rl[2]),
        .m_v(p_tx_v), .m_d({p_tx_e, p_tx_s, p_tx_d}), .m_rdy(p_tx_r), .o_v(tx_v), .o_d(tx_d), .crq(tx_cr));

    // ---------------------------------------------------------------- acks out (levels), feedback in
    wire akv, fbx;
    ot_lkep_relay #(.W(SW+EW+1), .N(RL+1)) u_ak (.clk(clk), .rst_n(rl[0]), .i_v(1'b0), .i_d({p_ack_e, p_ack_s, p_ack_n}),
        .o_v(akv), .o_d(ak));
    ot_lkep_relay #(.W(SW+1), .N(RL+1)) u_fb (.clk(clk), .rst_n(rl[0]), .i_v(fb_v), .i_d(fb_d),
        .o_v(p_fb_v), .o_d({p_fb_n, p_fb_s}));

    // ---------------------------------------------------------------- RX in: RL relays -> pin FIFO
    wire           q_v, cr_u, rdrop;
    wire [TW-1:0]  q_d;
    wire [NSLT-1:0] q_vs;
    ot_lkep_relay #(.W(TW), .N(RL), .NV(NSLT)) u_rr (.clk(clk), .rst_n(rl[0]), .i_v(rx_v), .i_d(rx_d), .o_v(q_v), .o_vr(q_vs), .o_d(q_d));
    ot_lkep_pinq #(.W(TW), .D(SQ), .SL(SL)) u_rb (.clk(clk), .rst_n(rl[0]), .i_v(q_v), .i_vs(q_vs), .i_d(q_d),
        .o_v(p_rx_v), .o_d(p_rx_w), .o_rdy(p_rx_r), .cr(cr_u), .drop(rdrop));

    // ---------------------------------------------------------------- RX out pin half
    ot_lkep_sinkp #(.W(W), .D(OFD), .N(RL)) u_oo (.clk(clk), .rst_p(rl[0]), .rst_c(rl[3]),
        .m_v(p_out_v), .m_d(p_out_d), .m_rdy(p_out_r), .o_v(o_v), .o_d(o_d), .crq(o_cr));

    // ---------------------------------------------------------------- status capture
    always @(posedge clk) st_rep <= p_rep;
    always @(posedge clk or negedge rl[3])
        if (!rl[3]) begin st_fault <= 1'b0; st_drop <= 1'b0; end
        else begin st_fault <= p_fault; st_drop <= rdrop; end
endmodule
