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
//   out: icr_ret (credit relay last stage), tx_v / tx_d and o_v / o_d (sink relay last stage), ak (ack relay last stage),
//        drop / fault / rep (status capture registers)
// Cycle changes vs 0c493ddbb (transaction-level exact; bench tb_hfd_lk_ep / tb_lk_rate gate adoption):
//   * the TX bank read: the head advances on adm_t (the admission registered in the tile), the launch register l0 one
//     edge after it -> a TX flit reaches its pin buffer 2 edges later.  Bank occupancy stays <= ceil(TXQ/NS) + 2 <= QD.
//   * status (fault / replay count / drop) captured once more at the tile edge: +1 edge (status only).
// ---------------------------------------------------------------------------

// ot_lkep_sinkp: pin half of ot_lkep_sinkq (macro output port side): credit counter / m_rdy, capture registers, relay
// stages 1..N (the last one is the tile's output register: all N relay stages live in the tile because the macro's out /
// rx pins sit ~600 um from the tile's seam face); the credit returns through N relay stages from the consumer's crq.
module ot_lkep_sinkp #(parameter integer W = 545, parameter integer D = 4, parameter integer N = 2) (
    input  wire         clk,
    input  wire         rst_p,
    input  wire         rst_c,
    input  wire         m_v,
    input  wire [W-1:0] m_d,
    output reg          m_rdy,
    output wire         o_v,           // relay stage N (registered)
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
    ot_lkep_relay #(.W(W), .N(N)) u_f1 (.clk(clk), .rst_n(rst_c), .i_v(cap_v), .i_d(cap_d), .o_v(o_v), .o_vr(), .o_d(o_d));
    ot_lkep_relay #(.W(1), .N(N)) u_c (.clk(clk), .rst_n(rst_p), .i_v(crq), .i_d(1'b0), .o_v(crb), .o_d(crb_d));
endmodule

// ot_lkep_sinkc: consumer half of ot_lkep_sinkq: the D-deep FIFO (fed straight from the tile's last relay stage), pop -> crq (registered, to the
// pin half's credit relay).  ot_lkep_sinkp + ot_lkep_sinkc == ot_lkep_sinkq edge for edge.
module ot_lkep_sinkc #(parameter integer W = 545, parameter integer D = 4, parameter integer N = 2, parameter integer SL = 64) (
    input  wire         clk,
    input  wire         rst_c,
    input  wire         i_v,           // sink relay stage N (tile output register)
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
    ot_lkep_relay #(.W(W), .N(0), .NV(NSL)) u_f (.clk(clk), .rst_n(rst_c), .i_v(i_v), .i_d(i_d), .o_v(f_v), .o_vr(f_vs), .o_d(f_d));
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

// ot_lkep_sub_flat: the 10-11 one-root tile (21,881 sinks; lkep_sub_cx-r1 spine diverged).  Kept as the LOCKSTEP REFERENCE of
// the 10-13 partition below (simulation only, never synthesized).
`ifndef SYNTHESIS
module ot_lkep_sub_flat #(
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
    ot_hbm_link_retry_pipeline #(.ENABLE(1), .W(W), .SW(SW), .EW(EW), .DEPTH(512), .TIMEOUT(TIMEOUT),
        .MAX_RETRY(MAX_RETRY), .RSTR(1), .RX_SLOT_SAMPLE(1), .TX_SLOT_SAMPLE(1), .IN_PIN(1), .IN_WPIN(1),
`ifndef OT_LKEP_MUT_NAKHOLD
        .NAK_HOLD(NAKH_HW)) u_rp (
`else
        .NAK_HOLD(0)) u_rp (                         // mutant: the pre-fix pipeline (a lost replay waits for TIMEOUT)
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
`endif

// ---------------------------------------------------------------------------
// el1013-lkep-split 2026-10-13 (owner clock rule: <= 15,000 sinks a root; lkep_sub_cx-r1-31def6706: 21,881 sinks on one
// cluster spine, leaf arrival 709-1,744 ps -> 4,794-7,985 ps, never converged).  ot_lkep_sub is now a WIRES-ONLY parent
// over the closed retry macro and three hardened leaves, each with its own clock root, placed at the macro face it serves:
//   ot_lkep_ti  macro W face: TX queue bank (ot_lkep_tq: w_dg / w_ohg / adm_t / hd / qs / l0), l0 relays, TX pin
//               buffer, admission-credit relay, macro reset + session copies                        14,085 flops
//   ot_lkep_ts  macro S face: TX-out pin half (capture, credit counter, RL relays)                   ~1.8k flops
//   ot_lkep_rp  macro N + E faces: RX relays, RX pin buffer, RX-out pin half, ack / feedback relays,
//               status capture, feedback-session copy, the two macro constants                      ~6.0k flops
// NO register is added or removed: every flop of ot_lkep_sub_flat is in exactly one leaf (the 2-flop reset synchroniser,
// its region copies and the session register are per leaf: copies of the same register, same release edge), so the tile
// is edge-for-edge the flat one (bench: OT_LKEP_LOCKSTEP runs both on the same pins and compares every output every edge).
// Seams: the leaves talk only to the macro and to the sub face (no leaf-to-leaf net).  Every sub-face input lands on a
// leaf flop, every sub-face output leaves a leaf flop (as in the flat tile).  Macro handshakes (in_ready, tx_valid, rx_ready,
// out_valid) keep their <= 3 gate levels behind the leaf pin: the leaf abuts the macro face it serves.
// Clock: one entry per child: four clock ports (clk -> macro, clk_ti, clk_ts, clk_rp), no tree in the parent.  The TX
// side (ti, ts) faces S, the RX side (rp) faces N: rst_n_r / session_r are the N-face copies of rst_n / session (the
// macro N face is > 500 um of detour from the S pins); the cluster drives both from the same register.
// Stage mutants (bench only, one per leaf): OT_LKEP_MUT_SEAM_L0 (ti: one extra l0 relay stage), OT_LKEP_MUT_SEAM_CR (ti:
// admission credit relay one stage longer), OT_LKEP_MUT_SEAM_TX (ts: TX-out relay one stage longer), OT_LKEP_MUT_SEAM_RX
// (rp: the RX pin relay loses a stage).
// ---------------------------------------------------------------------------
module ot_lkep_tq #(
    parameter integer W = 545, parameter integer QD = 16, parameter integer SL = 64
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [W-1:0]          w_d,
    input  wire [((W+SL-1)/SL)*QD-1:0] w_oh,
    input  wire                  adm,
    output reg                   l0_v,
    output reg  [W-1:0]          l0_d
);
    localparam integer NSL = (W + SL - 1) / SL;
    reg  [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg rl1;
    always @(posedge clk) rl1 <= rs[1];
    (* keep *) reg [W-1:0]      w_dg;
    (* keep *) reg [NSL*QD-1:0] w_ohg;
    (* keep *) reg [NSL-1:0]    adm_t;                // admission, one copy per 64-b slice
    (* keep *) reg [NSL*QD-1:0] hd;
    reg  [QD*W-1:0] qs;
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
        always @(posedge clk or negedge rl1)
            if (!rl1) begin adm_t[s] <= 1'b0; hd[s*QD +: QD] <= {{(QD-1){1'b0}}, 1'b1}; end
            else begin
                adm_t[s] <= adm;
                if (adm_t[s]) hd[s*QD +: QD] <= {hd[s*QD +: QD], hd[s*QD+QD-1]};
            end
    end endgenerate
    always @(posedge clk or negedge rl1) if (!rl1) l0_v <= 1'b0; else l0_v <= adm_t[0];
endmodule

module ot_lkep_ti #(
    parameter integer W = 545, parameter integer EW = 24, parameter integer QD = 16,
    parameter integer RL = 2, parameter integer PBD = 4, parameter integer SL = 64
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [EW-1:0]         session,
    // sub face (S): TX bank write, admission, admission credit
    input  wire [W-1:0]          w_d,
    input  wire [((W+SL-1)/SL)*QD-1:0] w_oh,
    input  wire                  adm,
    output wire                  icr_ret,
    // retry macro W face: reset, session, in
    output wire                  m_rst_n,
    output wire [EW-1:0]         m_session,
    output wire                  m_in_v,
    output wire [W-1:0]          m_in_d,
    input  wire                  m_in_r
);
    localparam integer NSL = (W + SL - 1) / SL;
    reg  [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg [2:0] rl;                            // [0] pin side, [1] credit relay (TX bank region), [2] macro reset pin
    always @(posedge clk) rl <= {3{rs[1]}};
    (* keep *) reg [EW-1:0] ses;
    always @(posedge clk) ses <= session;
    assign m_rst_n = rl[2];
    assign m_session = ses;
    wire          l0_v, r_v_, cr_p, cr_d, dr;
    wire [W-1:0]  l0_d, r_d;
    wire [NSL-1:0] r_vs;
    ot_lkep_tq #(.W(W), .QD(QD), .SL(SL)) u_tq (.clk(clk), .rst_n(rst_n), .w_d(w_d), .w_oh(w_oh), .adm(adm), .l0_v(l0_v), .l0_d(l0_d));
`ifdef OT_LKEP_MUT_SEAM_L0
    ot_lkep_relay #(.W(W), .N(RL+1), .NV(NSL)) u_tr (.clk(clk), .rst_n(rl[0]), .i_v(l0_v), .i_d(l0_d), .o_v(r_v_), .o_vr(r_vs), .o_d(r_d));
`else
    ot_lkep_relay #(.W(W), .N(RL), .NV(NSL)) u_tr (.clk(clk), .rst_n(rl[0]), .i_v(l0_v), .i_d(l0_d), .o_v(r_v_), .o_vr(r_vs), .o_d(r_d));
`endif
    ot_lkep_pinq #(.W(W), .D(PBD), .SL(SL)) u_tb (.clk(clk), .rst_n(rl[0]), .i_v(r_v_), .i_vs(r_vs), .i_d(r_d),
        .o_v(m_in_v), .o_d(m_in_d), .o_rdy(m_in_r), .cr(cr_p), .drop(dr));
`ifdef OT_LKEP_MUT_SEAM_CR
    ot_lkep_relay #(.W(1), .N(RL+1)) u_tc (.clk(clk), .rst_n(rl[1]), .i_v(cr_p), .i_d(1'b0), .o_v(icr_ret), .o_d(cr_d));
`else
    ot_lkep_relay #(.W(1), .N(RL)) u_tc (.clk(clk), .rst_n(rl[1]), .i_v(cr_p), .i_d(1'b0), .o_v(icr_ret), .o_d(cr_d));
`endif
endmodule

module ot_lkep_ts #(
    parameter integer W = 545, parameter integer SW = 12, parameter integer EW = 24,
    parameter integer RL = 2, parameter integer TFD = 4
) (
    input  wire                  clk,
    input  wire                  rst_n,
    // sub face (S)
    output wire                  tx_v,
    output wire [EW+SW+W-1:0]    tx_d,
    input  wire                  tx_cr,
    // retry macro S face (tx)
    input  wire                  m_tx_v,
    output wire                  m_tx_r,
    input  wire [W-1:0]          m_tx_d,
    input  wire [SW-1:0]         m_tx_s,
    input  wire [EW-1:0]         m_tx_e
);
    localparam integer TW = EW + SW + W;
    reg  [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg [1:0] rl;                            // [0] pin side, [1] TX-out relays
    always @(posedge clk) rl <= {2{rs[1]}};
`ifdef OT_LKEP_MUT_SEAM_TX
    ot_lkep_sinkp #(.W(TW), .D(TFD), .N(RL+1)) u_to (.clk(clk), .rst_p(rl[0]), .rst_c(rl[1]),
`else
    ot_lkep_sinkp #(.W(TW), .D(TFD), .N(RL)) u_to (.clk(clk), .rst_p(rl[0]), .rst_c(rl[1]),
`endif
        .m_v(m_tx_v), .m_d({m_tx_e, m_tx_s, m_tx_d}), .m_rdy(m_tx_r), .o_v(tx_v), .o_d(tx_d), .crq(tx_cr));
endmodule

module ot_lkep_rp #(
    parameter integer W = 545, parameter integer SW = 12, parameter integer EW = 24,
    parameter integer RL = 2, parameter integer OFD = 4, parameter integer SQ = 4, parameter integer SL = 64
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [EW-1:0]         session,
    // sub face
    output wire [SW+EW:0]        ak,
    input  wire                  fb_v,
    input  wire [SW:0]           fb_d,       // {nak, seq}
    input  wire                  rx_v,
    input  wire [EW+SW+W-1:0]    rx_d,
    output wire                  o_v,
    output wire [W-1:0]          o_d,
    input  wire                  o_cr,
    output reg                   st_fault,
    output reg                   st_drop,
    output reg  [31:0]           st_rep,
    // retry macro N face (rx) and E face (out, ack, feedback, status)
    output wire                  m_rx_v,
    input  wire                  m_rx_r,
    output wire [EW+SW+W-1:0]    m_rx_w,     // {session, seq, data}
    output wire                  m_rx_ue,    // constant 0
    input  wire                  m_out_v,
    output wire                  m_out_r,
    input  wire [W-1:0]          m_out_d,
    input  wire [SW-1:0]         m_ack_s,
    input  wire                  m_ack_n,
    input  wire [EW-1:0]         m_ack_e,
    output wire                  m_fb_v,
    output wire                  m_fb_good,  // constant 1
    output wire                  m_fb_n,
    output wire [SW-1:0]         m_fb_s,
    output wire [EW-1:0]         m_fb_e,     // the session copy
    input  wire                  m_fault,
    input  wire [31:0]           m_rep
);
    localparam integer TW = EW + SW + W;
    localparam integer NSLT = (TW + SL - 1) / SL;
    reg  [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg [1:0] rl;                            // [0] pin side, [1] RX-out / status
    always @(posedge clk) rl <= {2{rs[1]}};
    (* keep *) reg [EW-1:0] ses;
    always @(posedge clk) ses <= session;
    assign m_fb_e = ses;
    assign m_rx_ue = 1'b0;
    assign m_fb_good = 1'b1;
    wire akv;
    ot_lkep_relay #(.W(SW+EW+1), .N(RL+1)) u_ak (.clk(clk), .rst_n(rl[0]), .i_v(1'b0), .i_d({m_ack_e, m_ack_s, m_ack_n}),
        .o_v(akv), .o_d(ak));
    ot_lkep_relay #(.W(SW+1), .N(RL+1)) u_fb (.clk(clk), .rst_n(rl[0]), .i_v(fb_v), .i_d(fb_d),
        .o_v(m_fb_v), .o_d({m_fb_n, m_fb_s}));
    wire           q_v, cr_u, rdrop;
    wire [TW-1:0]  q_d;
    wire [NSLT-1:0] q_vs;
`ifdef OT_LKEP_MUT_SEAM_RX
    ot_lkep_relay #(.W(TW), .N(RL-1), .NV(NSLT)) u_rr (.clk(clk), .rst_n(rl[0]), .i_v(rx_v), .i_d(rx_d), .o_v(q_v), .o_vr(q_vs), .o_d(q_d));
`else
    ot_lkep_relay #(.W(TW), .N(RL), .NV(NSLT)) u_rr (.clk(clk), .rst_n(rl[0]), .i_v(rx_v), .i_d(rx_d), .o_v(q_v), .o_vr(q_vs), .o_d(q_d));
`endif
    ot_lkep_pinq #(.W(TW), .D(SQ), .SL(SL)) u_rb (.clk(clk), .rst_n(rl[0]), .i_v(q_v), .i_vs(q_vs), .i_d(q_d),
        .o_v(m_rx_v), .o_d(m_rx_w), .o_rdy(m_rx_r), .cr(cr_u), .drop(rdrop));
    ot_lkep_sinkp #(.W(W), .D(OFD), .N(RL)) u_oo (.clk(clk), .rst_p(rl[0]), .rst_c(rl[1]),
        .m_v(m_out_v), .m_d(m_out_d), .m_rdy(m_out_r), .o_v(o_v), .o_d(o_d), .crq(o_cr));
    always @(posedge clk) st_rep <= m_rep;
    always @(posedge clk or negedge rl[1])
        if (!rl[1]) begin st_fault <= 1'b0; st_drop <= 1'b0; end
        else begin st_fault <= m_fault; st_drop <= rdrop; end
endmodule

// ot_lkep_sub: one sub-channel tile = wires only (defaults = the hardened configuration of hfd_lk_ep: NS 3, TXQ 32 -> QD 16, RL 2).
module ot_lkep_sub #(
    parameter integer W = 545, parameter integer SW = 12, parameter integer EW = 24,
    parameter integer QD = 16, parameter integer RL = 2, parameter integer PBD = 4, parameter integer TFD = 4,
    parameter integer OFD = 4, parameter integer SQ = 4, parameter integer SL = 64,
    parameter integer TIMEOUT = 8192, parameter integer MAX_RETRY = 8, parameter integer NAKH_HW = 64
) (
    input  wire                  clk,        // clock entry of the retry macro (S face)
    input  wire                  clk_ti,     // one clock entry per hard child: the same clock, delivered at phi - R of each child
    input  wire                  clk_ts,
    input  wire                  clk_rp,     // N face
    input  wire                  rst_n,      // S face: ti + ts synchronisers
    input  wire                  rst_n_r,    // N face: the same reset for the rp synchroniser
    input  wire [EW-1:0]         session,    // S face (ti copy -> macro session)
    input  wire [EW-1:0]         session_r,  // N face (rp copy -> macro fb_session); the same static value
    input  wire [W-1:0]          w_d,
    input  wire [((W+SL-1)/SL)*QD-1:0] w_oh,
    input  wire                  adm,
    output wire                  icr_ret,
    output wire                  tx_v,
    output wire [EW+SW+W-1:0]    tx_d,
    input  wire                  tx_cr,
    output wire [SW+EW:0]        ak,
    input  wire                  fb_v,
    input  wire [SW:0]           fb_d,       // {nak, seq}
    input  wire                  rx_v,
    input  wire [EW+SW+W-1:0]    rx_d,
    output wire                  o_v,
    output wire [W-1:0]          o_d,
    input  wire                  o_cr,
    output wire                  st_fault,
    output wire                  st_drop,
    output wire [31:0]           st_rep
);
    localparam integer TW = EW + SW + W;
    wire          m_rst_n, p_in_v, p_in_r, p_tx_v, p_tx_r, p_rx_v, p_rx_r, p_rx_ue, p_out_v, p_out_r;
    wire          p_fb_v, p_fb_good, p_fault, p_fb_n, p_ack_n;
    wire [W-1:0]  p_in_dd, p_tx_d, p_out_d;
    wire [SW-1:0] p_tx_s, p_ack_s, p_ret, p_fb_s;
    wire [EW-1:0] p_tx_e, p_ack_e, m_ses, m_fb_e;
    wire [TW-1:0] p_rx_w;
    wire [31:0]   p_rep;
`ifdef OT_LKEP_HARD_LEAVES
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
        .clk(clk), .rst_n(m_rst_n), .session(m_ses),
        .in_valid(p_in_v), .in_ready(p_in_r), .in_data(p_in_dd),
        .tx_valid(p_tx_v), .tx_ready(p_tx_r), .tx_data(p_tx_d), .tx_seq(p_tx_s), .tx_session(p_tx_e),
        .rx_valid(p_rx_v), .rx_ready(p_rx_r), .rx_ue(p_rx_ue), .rx_data(p_rx_w[W-1:0]),
        .rx_seq(p_rx_w[W +: SW]), .rx_session(p_rx_w[W+SW +: EW]),
        .out_valid(p_out_v), .out_ready(p_out_r), .out_data(p_out_d),
        .ack_seq(p_ack_s), .ack_nak(p_ack_n), .ack_session(p_ack_e),
        .fb_valid(p_fb_v), .fb_good(p_fb_good), .fb_nak(p_fb_n), .fb_seq(p_fb_s), .fb_session(m_fb_e),
        .fault(p_fault), .retained(p_ret), .replay_count(p_rep));
`ifdef OT_LKEP_HARD_LEAVES
    ot_lkep_ti u_ti (
`else
    ot_lkep_ti #(.W(W), .EW(EW), .QD(QD), .RL(RL), .PBD(PBD), .SL(SL)) u_ti (
`endif
        .clk(clk_ti), .rst_n(rst_n), .session(session), .w_d(w_d), .w_oh(w_oh), .adm(adm), .icr_ret(icr_ret),
        .m_rst_n(m_rst_n), .m_session(m_ses), .m_in_v(p_in_v), .m_in_d(p_in_dd), .m_in_r(p_in_r));
`ifdef OT_LKEP_HARD_LEAVES
    ot_lkep_ts u_ts (
`else
    ot_lkep_ts #(.W(W), .SW(SW), .EW(EW), .RL(RL), .TFD(TFD)) u_ts (
`endif
        .clk(clk_ts), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d), .tx_cr(tx_cr),
        .m_tx_v(p_tx_v), .m_tx_r(p_tx_r), .m_tx_d(p_tx_d), .m_tx_s(p_tx_s), .m_tx_e(p_tx_e));
`ifdef OT_LKEP_HARD_LEAVES
    ot_lkep_rp u_rq (
`else
    ot_lkep_rp #(.W(W), .SW(SW), .EW(EW), .RL(RL), .OFD(OFD), .SQ(SQ), .SL(SL)) u_rq (
`endif
        .clk(clk_rp), .rst_n(rst_n_r), .session(session_r),
        .ak(ak), .fb_v(fb_v), .fb_d(fb_d), .rx_v(rx_v), .rx_d(rx_d), .o_v(o_v), .o_d(o_d), .o_cr(o_cr),
        .st_fault(st_fault), .st_drop(st_drop), .st_rep(st_rep),
        .m_rx_v(p_rx_v), .m_rx_r(p_rx_r), .m_rx_w(p_rx_w), .m_rx_ue(p_rx_ue),
        .m_out_v(p_out_v), .m_out_r(p_out_r), .m_out_d(p_out_d),
        .m_ack_s(p_ack_s), .m_ack_n(p_ack_n), .m_ack_e(p_ack_e),
        .m_fb_v(p_fb_v), .m_fb_good(p_fb_good), .m_fb_n(p_fb_n), .m_fb_s(p_fb_s), .m_fb_e(m_fb_e),
        .m_fault(p_fault), .m_rep(p_rep));

`ifndef SYNTHESIS
`ifdef OT_LKEP_LOCKSTEP
    // lockstep reference: the flat one-root tile on the same pins; every output compared on every edge
    wire                  f_icr_ret, f_tx_v, f_o_v, f_st_fault, f_st_drop;
    wire [EW+SW+W-1:0]    f_tx_d;
    wire [SW+EW:0]        f_ak;
    wire [W-1:0]          f_o_d;
    wire [31:0]           f_st_rep;
    ot_lkep_sub_flat #(.W(W), .SW(SW), .EW(EW), .QD(QD), .RL(RL), .PBD(PBD), .TFD(TFD), .OFD(OFD), .SQ(SQ), .SL(SL),
        .TIMEOUT(TIMEOUT), .MAX_RETRY(MAX_RETRY), .NAKH_HW(NAKH_HW)) u_flat (
        .clk(clk), .rst_n(rst_n), .session(session), .w_d(w_d), .w_oh(w_oh), .adm(adm), .icr_ret(f_icr_ret),
        .tx_v(f_tx_v), .tx_d(f_tx_d), .tx_cr(tx_cr), .ak(f_ak), .fb_v(fb_v), .fb_d(fb_d), .rx_v(rx_v), .rx_d(rx_d),
        .o_v(f_o_v), .o_d(f_o_d), .o_cr(o_cr), .st_fault(f_st_fault), .st_drop(f_st_drop), .st_rep(f_st_rep));
    integer ls_n = 0, ls_tx = 0, ls_o = 0;
    always @(posedge clk) if (rst_n) begin
        ls_n <= ls_n + 1; if (tx_v) ls_tx <= ls_tx + 1; if (o_v) ls_o <= ls_o + 1;
        if ({icr_ret, tx_v, o_v, st_fault, st_drop} !== {f_icr_ret, f_tx_v, f_o_v, f_st_fault, f_st_drop} ||
            tx_d !== f_tx_d || ak !== f_ak || o_d !== f_o_d || st_rep !== f_st_rep) begin
            $display("LKEP_LOCKSTEP mismatch %m edge %0d: ctl %b / %b tx %0d ak %0d o %0d rep %0d", ls_n,
                     {icr_ret, tx_v, o_v, st_fault, st_drop}, {f_icr_ret, f_tx_v, f_o_v, f_st_fault, f_st_drop},
                     tx_d !== f_tx_d, ak !== f_ak, o_d !== f_o_d, st_rep !== f_st_rep);
            $fatal(1, "LKEP_LOCKSTEP FAIL");
        end
    end
    final $display("LKEP_LOCKSTEP PASS %m edges %0d tx_words %0d out_words %0d", ls_n, ls_tx, ls_o);
`endif
`endif
endmodule
