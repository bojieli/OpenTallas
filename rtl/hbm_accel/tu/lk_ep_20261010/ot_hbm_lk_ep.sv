`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// hfd_lk_ep ([link] 2026-10-10, lead decision): the per-link endpoint beside each of the 9 R25GQ SerDes
// (ot_pdie_serdes: clk, tx[512], rx[512]).  It takes the PHY-side packing OUT of hfd_coll: hfd_coll keeps the
// collective endpoint (ot_hbm_accel_tu_endpoint / ot_hgi_coll_ep) and talks to this block over a 545-b flit bus
// with credit feedback each way; this block owns link-level reliability and the lane format.
//
//   die side (clk = clk_link, the PHY-interface clock; the core <-> link CDC stays in the endpoint):
//     t_v / t_flit[545]  flit to send            t_cr   pulse: one local TX-queue slot freed (the sender holds TXQ
//                                                       credits for this queue)
//     r_v / r_flit[545]  flit received           r_cr   pulse: the die's receive buffer freed one flit; carried to the
//                                                       far end as a cumulative 8-bit count (lost frames lose nothing)
//   link side: x_tx[LW] (registered) / x_rx[LW] (registered at the pin here); LW = 487 = the die's SerDes lane contract
//   (fp R25GQ f0624cc33: 974 b a SerDes = 487 tx + 487 rx); the macro has no rx-valid pin (alignment is the gearbox's markers)
//
//   TX   t_flit -> per-sub TX queues (flit k -> sub k mod NS, the striping order) -> admitted in striping order while a
//        far-end credit (FC, initial FCR = the far die's receive buffer) and a pin-buffer credit are held -> RL relay
//        stages -> per-sub pin buffer at the closed retry pipeline (ot_hbm_link_retry_pipeline, the view_wpin_hm10
//        macro: SECDED replay SRAM, ACK/NAK, timeout, bounded retries) -> the pipelines' tx words {seq, session, data}
//        captured at the macro pins -> RL relay stages -> per-sub TX FIFO -> round-robin grant {sub, seq, session,
//        data} + CRC-14 (one register stage of partial matrices) -> ot_s81ph_link_gbx FMT 1 at BW = LW (S81 lane
//        format: 3 forward slots per 4 beats at fixed bit positions, marker / idle beats, one 35-b reverse frame in
//        every beat).
//   RX   gearbox slots -> CRC-14 check (pipelined; bad frame: dropped; the pipeline's sequence check NAKs the gap or its
//        timeout replays it) -> RL relay stages per sub -> per-sub FIFO at the macro (full: dropped, same recovery) ->
//        pin slot -> pipeline rx -> pipeline out captured at the macro pins -> RL relay stages -> per-sub out FIFO ->
//        strict round-robin merge in the striping order -> r_v / r_flit.  No backpressure towards the die: the far
//        sender only admits a flit while it holds one of this die's receive-buffer credits.
//   Reverse frame (35 b, every beat, rotating over the subs): {crc12, ccnt8, ack_nak, ack_seq12, sub2}; the ack session is
//        NOT sent: the CRC-12 covers {ack_session, body}, so a frame of another session fails the CRC and is dropped
//        (fb_session = the local session); -> the far pipeline's fb_*; ccnt = cumulative r_cr count.
//
// Physical structure ([link] 2026-10-10 after 304cd8c93 preroute -3,354 ps: the TX queue read mux (wsel select over a
// 32 x 545 queue, three read ports) drove the macro in_data pins combinationally, the macro tx / out / ack pins fed the
// grant / merge / CRC logic combinationally, and rst_n / session fanned out unregistered): every retry-pipeline pin is
// now a register (pin buffers / pin slots on its inputs, free-running capture registers on its outputs, credits instead
// of combinational ready), RL free-running relay stages carry each sub's buses between its macro and the shared logic,
// the queue / FIFO read selects are one-hot pointers replicated per 64-b slice (no select net drives more than ~64
// data bits), the write enables are registered one-hot vectors, rst_n is synchronised and replicated per region, the
// session register is replicated per macro.  +2 RL + ~6 edges a flit each way; rates are unchanged (credits sized).
// Exactness is at transaction level: every flit is delivered once, in order, bit-exact (bench tb_hfd_lk_ep: two
// endpoints back to back, random lane bit errors, die-side stalls under credits).
// Throughput: one retry pipeline admits one word per 4 edges (545 / 4 b a cycle); NS = 3 fills the gearbox's 3 slots
// per 4 beats (0.75 flit a beat less the 1/IDLE_P idle beats).  The pacer mirrors the gearbox slot FIFO (sn) exactly,
// so the gearbox overflow fault cannot fire.
// Mutants (bench only): OT_LKEP_MUT_NOCRC (forward CRC not checked), OT_LKEP_MUT_MERGE (merge does not wait for the
// sub whose turn it is), OT_LKEP_MUT_CREDIT (die credit returned on arrival, not on admission).
// ---------------------------------------------------------------------------

// ot_lkep_relay: N free-running register stages (valid reset, data not); N = 0 is a wire.
// el1011-hbm-lkep 2026-10-11: data and valid are FLAT (* keep *) vectors.  Root cause it removes: the RX per-sub relays
// (g_rx[g].u_r) and feedback relays (g_fb[g].u_f) all take the SAME i_d (c_h / {fb_nak, fb_seq}); without keep yosys
// merged the three chains into one, so g_rx[0].u_r.o_d drove the pin queues of all three subs across the die (6cf72efa6
// preroute -2,452 ps g_rx[0].u_r.o_d[349] -> g_rx[1].u_b.m[1511]).  NV valid copies (o_vr, keep): one per consumer slice,
// so a slice-local enable never waits on one shared valid net.  Function unchanged (copies of the same register).
module ot_lkep_relay #(parameter integer W = 1, parameter integer N = 1, parameter integer NV = 1) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          i_v,
    input  wire [W-1:0]  i_d,
    output wire          o_v,
    output wire [NV-1:0] o_vr,
    output wire [W-1:0]  o_d
);
    generate if (N == 0) begin : g_w
        assign o_v = i_v; assign o_vr = {NV{i_v}}; assign o_d = i_d;
    end else begin : g_r
        (* keep *) reg [N*NV-1:0] v;
        (* keep *) reg [N*W-1:0]  d;
        integer k;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) v <= {(N*NV){1'b0}};
            else begin v[NV-1:0] <= {NV{i_v}}; for (k = 1; k < N; k = k + 1) v[k*NV +: NV] <= v[(k-1)*NV +: NV]; end
        always @(posedge clk) begin d[W-1:0] <= i_d; for (k = 1; k < N; k = k + 1) d[k*W +: W] <= d[(k-1)*W +: W]; end
        assign o_v = v[(N-1)*NV]; assign o_vr = v[(N-1)*NV +: NV]; assign o_d = d[(N-1)*W +: W];
    end endgenerate
endmodule

// ot_lkep_pinq: the input side of a macro port.  Free-running (i_v, i_d) -> D-deep FIFO -> a pin slot register
// (o_v / o_d drive the macro pins straight from flops; the slot loads only while empty, so the macro's ready pin
// reaches one flop).  cr pulses (registered) once per word the macro took.  drop = i_v while full.
// Pointers are one-hot, replicated per SL-bit slice (keep).
module ot_lkep_pinq #(parameter integer W = 545, parameter integer D = 4, parameter integer SL = 64) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         i_v,
    input  wire [(W+SL-1)/SL-1:0] i_vs,   // per-slice copies of i_v (relay o_vr)
    input  wire [W-1:0] i_d,
    output reg          o_v,
    output reg  [W-1:0] o_d,
    input  wire         o_rdy,
    output reg          cr,
    output wire         drop
);
    localparam integer NSL = (W + SL - 1) / SL;
    localparam integer CB = $clog2(D + 1);
    reg  [D*W-1:0]   m;
    (* keep *) reg [NSL*D-1:0] wp;
    (* keep *) reg [NSL*D-1:0] rp;
    reg  [CB-1:0]    n;
    wire             full = (n == D);
    wire             we = i_v && !full;
    wire             ld = !o_v && (n != 0);
    assign drop = i_v && full;
    wire [W-1:0]     head;
    // el1011-hbm-lkep: per-slice control copies (keep).  n / o_v above are the master (macro in_valid pin, cr, drop);
    // slice s computes its own we / ld from ns / ovs and i_vs[s], so no control net leaves its 64-b slice (6cf72efa6
    // dh1404 preroute -2,247 ps: u_b.n[1] -> 20 wire repeaters -> u_b.m[987] across the 4 x 545 pin queue).
    (* keep *) reg [NSL*CB-1:0] ns;
    (* keep *) reg [NSL-1:0]    ovs;
    genvar s, e;
    generate for (s = 0; s < NSL; s = s + 1) begin : g_s
        localparam integer LO = s * SL;
        localparam integer HI = (LO + SL > W) ? W : LO + SL;
        reg [HI-LO-1:0] x;
        integer j;
        wire we_s = i_vs[s] && (ns[s*CB +: CB] != D);
        wire ld_s = !ovs[s] && (ns[s*CB +: CB] != 0);
        for (e = 0; e < D; e = e + 1) begin : g_e
            always @(posedge clk) if (we_s && wp[s*D+e]) m[e*W+LO +: HI-LO] <= i_d[HI-1:LO];
        end
        always @(posedge clk) if (!ovs[s]) o_d[HI-1:LO] <= x;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin ns[s*CB +: CB] <= {CB{1'b0}}; ovs[s] <= 1'b0; wp[s*D +: D] <= {{(D-1){1'b0}}, 1'b1}; rp[s*D +: D] <= {{(D-1){1'b0}}, 1'b1}; end
            else begin
                ns[s*CB +: CB] <= ns[s*CB +: CB] + (we_s ? 1'b1 : 1'b0) - (ld_s ? 1'b1 : 1'b0);
                ovs[s] <= ld_s || (ovs[s] && !o_rdy);
                if (we_s) wp[s*D +: D] <= {wp[s*D +: D], wp[s*D+D-1]};
                if (ld_s) rp[s*D +: D] <= {rp[s*D +: D], rp[s*D+D-1]};
            end
        always @(*) begin
            x = {(HI-LO){1'b0}};
            for (j = 0; j < D; j = j + 1) x = x | ({(HI-LO){rp[s*D+j]}} & m[j*W+LO +: HI-LO]);
        end
        assign head[HI-1:LO] = x;
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            n <= {CB{1'b0}}; o_v <= 1'b0; cr <= 1'b0;
        end else begin
            n <= n + (we ? 1'b1 : 1'b0) - (ld ? 1'b1 : 1'b0);
            o_v <= ld || (o_v && !o_rdy);
            cr <= o_v && o_rdy;
        end
endmodule

// ot_lkep_sinkq: the output side of a macro port.  m_rdy is a register (= a credit for the consumer FIFO is held); the
// word is captured at the pins by free-running registers, carried by N relay stages into a D-deep FIFO at the consumer;
// the consumer pops (h_v / h_d = the head); each pop returns a credit through N relay stages.
module ot_lkep_sinkq #(parameter integer W = 545, parameter integer D = 4, parameter integer N = 1, parameter integer SL = 64) (
    input  wire         clk,
    input  wire         rst_p,          // pin-side region reset
    input  wire         rst_c,          // consumer-side region reset
    input  wire         m_v,
    input  wire [W-1:0] m_d,
    output reg          m_rdy,
    output wire         h_v,
    output wire [W-1:0] h_d,
    input  wire         pop
);
    localparam integer NSL = (W + SL - 1) / SL;
    localparam integer CB = $clog2(D + 1);
    // pin side
    reg  [CB-1:0] cnt;
    reg           cap_v;
    reg  [W-1:0]  cap_d;
    wire          crb;
    wire          hs = m_v && m_rdy;
    wire [CB-1:0] cnt_n = cnt - (hs ? 1'b1 : 1'b0) + (crb ? 1'b1 : 1'b0);
    always @(posedge clk or negedge rst_p)
        if (!rst_p) begin cnt <= D; m_rdy <= 1'b0; cap_v <= 1'b0; end
        else begin cnt <= cnt_n; m_rdy <= (cnt_n != 0); cap_v <= hs; end
    always @(posedge clk) cap_d <= m_d;
    wire          f_v;
    wire [W-1:0]  f_d;
    wire [NSL-1:0] f_vs;
    ot_lkep_relay #(.W(W), .N(N), .NV(NSL)) u_f (.clk(clk), .rst_n(rst_c), .i_v(cap_v), .i_d(cap_d), .o_v(f_v), .o_vr(f_vs), .o_d(f_d));
    // consumer FIFO (never overflows: the pin side holds at most D credits)
    reg  [D*W-1:0]   m;
    (* keep *) reg [NSL*D-1:0] wp;
    (* keep *) reg [NSL*D-1:0] rp;
    reg  [CB-1:0]    n;
    reg              crq;
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
    wire crb_d;
    ot_lkep_relay #(.W(1), .N(N)) u_c (.clk(clk), .rst_n(rst_p), .i_v(crq), .i_d(1'b0), .o_v(crb), .o_d(crb_d));
endmodule

module ot_hbm_lk_ep #(
    parameter integer MUT_TX_SHARED = 0,
    parameter integer MUT_RX_SHARED = 0,
    parameter integer HARD_CLOCKS = 0,     // physical parent delivers one compensated clock at each hard child pin
    parameter integer NS     = 3,          // retry pipelines (sub-channels) per link, 1..3
    parameter integer W      = 545,
    parameter integer TXQ    = 32,         // local TX queue depth (= the die sender's credits; covers the ~24-cycle die credit loop)
    parameter integer FCR    = 256,        // far-end receive-buffer credits at reset (ot_hcoll_port: 256-flit SRAM rb)
    parameter integer SQ     = 4,          // per-sub RX FIFO depth (power of 2)
    parameter integer IDLE_P = 1024,
    parameter integer LW     = 487,        // SerDes lanes each way
    parameter integer RL     = 2,          // relay stages between each retry macro and the shared logic, each bus, each way
    parameter integer PBD    = 4,          // per-sub TX pin-buffer FIFO depth (+1 pin slot = the admission credits)
    parameter integer TFD    = 4,          // per-sub TX-out FIFO depth (macro tx_ready credits)
    parameter integer OFD    = 4,          // per-sub RX-out FIFO depth (macro out_ready credits)
    parameter integer SL     = 64,         // data bits per replicated select copy
    parameter integer XR     = 2,          // lane relay stages each way between the east-face pin flops and the gearbox
                                           // (el1011-hbm-lkep centre-channel floorplan: the gearbox sits between the macros,
                                           // ~900 um from the phy pins; pin flop + XR relays keep every hop < ~350 um)
    // retry pipeline parameters (simulation only; the hard macro is the closed view_wpin_hm10)
    parameter integer TIMEOUT = 8192,
    parameter integer MAX_RETRY = 8
) (
    input  wire            clk,
    input  wire [NS*4-1:0] clk_sub,
    input  wire            clk_tx_shared,
    input  wire            clk_rx_shared,
    input  wire            rst_n,
    input  wire [23:0]     session,
    input  wire            t_v,
    input  wire [W-1:0]    t_flit,
    output reg             t_cr,
    output wire            r_v,
    output wire [W-1:0]    r_flit,
    input  wire            r_cr,
    output wire [LW-1:0]   x_tx,
    input  wire [LW-1:0]   x_rx,
    output reg             fault,
    output wire            locked
);
    reg  [31:0] st_replays;                             // status counters (bench / debug; no die pins)
    reg  [15:0] st_drops;
    localparam integer SW = 12, EW = 24;
    localparam integer FFW = 597, RFW = 35;
    localparam integer HB = 2 + SW + EW + W;           // 583: {session, seq, sub, data} before the CRC
    localparam integer TW = EW + SW + W;               // 581: {session, seq, data} at a macro port
    localparam integer QB = $clog2(TXQ);
    localparam integer QD = 1 << $clog2((TXQ + NS - 1) / NS);   // per-sub TX queue depth (flit k -> sub k mod NS)
    localparam integer NSL = (W + SL - 1) / SL;
    localparam integer CI = $clog2(PBD + 2);
    // Link round trip seen by a retry pipeline (its rewind -> the last stale NAK of that sequence), measured with the
    // tb_hfd_lk_ep trace: 48 / 52 / 56 edges at XR 0 / 1 / 2 (RL 2) -- 4 edges per relay stage (forward + reverse, both
    // ends).  NAKH (> RTT by two feedback phases) is the retry pipeline's NAK re-arm hold (NAK_HOLD): a NAK still standing
    // after it is a lost replay, replayed again instead of waiting for the 8,192-edge TIMEOUT.  The hardened retry macro
    // view is built with NAK_HOLD = NAKH_HW (physical/hbm_link_retry_pipeline_20261009 route_cl.sh NAK_HOLD=...).
    localparam integer RTT = 40 + 4 * RL + 4 * XR;
    localparam integer NAKH = RTT + 8;
    localparam integer NAKH_HW = 64;
`ifndef SYNTHESIS
    initial if (NS < 1 || NS > 3 || HB + 14 != FFW || (1 << QB) != TXQ || SQ < 2 || PBD < 2 || TFD < 2 || OFD < 2)
        $fatal(1, "hfd_lk_ep: geometry");
    initial if (NAKH > NAKH_HW) $fatal(1, "hfd_lk_ep: round trip %0d needs NAK_HOLD %0d > the hardened view's %0d", RTT, NAKH, NAKH_HW);
`endif
    // ---------------------------------------------------------------- reset: synchronised, replicated per region
    // rst_n reaches only the 2-flop synchroniser (async assert, sync release); every region owns a registered copy (keep):
    // [g] sub g (its macro's rst_n pin, pin buffers / captures, relays), [NS] TX queue, [NS+1] TX out, [NS+2] RX / merge,
    // [NS+3] gearbox.
    localparam integer NR = NS + 4;
    reg  [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg [NR-1:0] rl;
    always @(posedge clk) rl <= {NR{rs[1]}};
    wire rtq = rl[NS], rto = rl[NS+1], rrx = rl[NS+2], rgb = rl[NS+3];
    // session: the reverse-frame check copy (each tile holds its macro's copy)
    reg  [EW-1:0] ses_c;
    always @(posedge clk) ses_c <= session;

    // ---------------------------------------------------------------- sub tiles (el1011-hbm-coll rebuild, ot_lkep_sub.sv)
    // Each sub's retry macro, TX queue bank, pin buffers, pin halves of its sink queues and every relay chain live in one
    // hardened tile; the glue below talks to it only through registers on both sides (ot_lkep_sub header).
    wire [NS-1:0]    icr_ret, th_vt, oh_vt, sf_t, sd_t;
    wire [TW-1:0]    th_dt [0:NS-1];
    wire [W-1:0]     oh_dt [0:NS-1];
    wire [SW+EW:0]   ak    [0:NS-1];
    wire [31:0]      rp_t  [0:NS-1];
    wire [NS-1:0]    tcrq, ocrq;
    reg  [1:0]          esel;
    reg  [NS*QD-1:0]    tl;
    reg                 w_v;
    reg  [W-1:0]        w_d;
    (* keep *) reg [NS*NSL*QD-1:0] w_oh;
    reg                 w_v2;
    reg  [NS-1:0]       l0_v;
    reg  [NS-1:0]       fbv;
    reg                 fb_nak; reg [SW-1:0] fb_seq;
    reg           p_v, c_v; reg [HB-1:0] p_h, c_h; reg [13:0] p_c;
    wire [1:0]    c_sub = c_h[W +: 2];
    genvar g;
    generate for (g = 0; g < NS; g = g + 1) begin : g_t
`ifdef OT_LKEP_HARD
        ot_lkep_sub u_t (
`else
        ot_lkep_sub #(.W(W), .SW(SW), .EW(EW), .QD(QD), .RL(RL), .PBD(PBD), .TFD(TFD), .OFD(OFD), .SQ(SQ), .SL(SL),
            .TIMEOUT(TIMEOUT), .MAX_RETRY(MAX_RETRY), .NAKH_HW(NAKH_HW)) u_t (
`endif
            .clk(HARD_CLOCKS != 0 ? clk_sub[g*4] : clk), .rst_n(rst_n), .session(session),
            .clk_ti(HARD_CLOCKS != 0 ? clk_sub[g*4+1] : clk),
            .clk_ts(HARD_CLOCKS != 0 ? clk_sub[g*4+2] : clk),
            .clk_rp(HARD_CLOCKS != 0 ? clk_sub[g*4+3] : clk),       // el1013-lkep-split: one clock entry per hard child of the sub
            .rst_n_r(rst_n), .session_r(session),           // N-face copies for the RX leaf
            .w_d(w_d), .w_oh(w_oh[g*NSL*QD +: NSL*QD]), .adm(l0_v[g]), .icr_ret(icr_ret[g]),
            .tx_v(th_vt[g]), .tx_d(th_dt[g]), .tx_cr(tcrq[g]),
            .ak(ak[g]), .fb_v(fbv[g]), .fb_d({fb_nak, fb_seq}),
            .rx_v(c_v && (c_sub == g)), .rx_d({c_h[HB-1:W+2], c_h[W-1:0]}),
            .o_v(oh_vt[g]), .o_d(oh_dt[g]), .o_cr(ocrq[g]),
            .st_fault(sf_t[g]), .st_drop(sd_t[g]), .st_rep(rp_t[g]));
    end endgenerate
`ifdef OT_LKEP_HARD
    // a hard tile is a fixed cell: its defaults must be the configuration this cluster asks for
    initial if (W != 545 || SW != 12 || EW != 24 || QD != 16 || RL != 2 || PBD != 4 || TFD != 4 || OFD != 4 || SQ != 4 || SL != 64)
        $fatal(1, "hfd_lk_ep: hard ot_lkep_sub view is W545 QD16 RL2 PBD/TFD/OFD/SQ 4 SL64");
`endif

    // ---------------------------------------------------------------- TX queue control (banks live in the tiles)
    // Flit k goes to sub k mod NS (esel); admission in striping order from wsel (stopping at the first sub without a
    // flit, a far credit or a pin-buffer credit) = one shared queue's order.  l0_v[g] (registered admission) tells tile g
    // to advance its bank head; the bank read happens in the tile two edges later (ot_lkep_sub).
    reg  [QB:0]         qn;                             // written, not yet admitted
    reg  [8:0]          fc;                             // far-end credits held (FCR <= 511)
    reg  [1:0]          wsel;                           // sub of the next admitted flit
    reg                 q_ovf;
    reg  [QB+1:0]       crp;                            // die-side credits owed
    reg  [NS*CI-1:0]    icr;                            // pin-buffer credits by sub
    reg  [NS-1:0]       admv;                           // admitted this edge, by sub
    reg  [2:0]          nadm;
    reg  [7:0]          fc_add;                         // credits returned by the far end this edge (from the rev path)
    integer             a, sa, gg, ss;
    reg                 go;
    always @(*) begin
        admv = 0; nadm = 0; go = 1'b1;
        for (a = 0; a < NS; a = a + 1) begin
            sa = (wsel + a) % NS;
            if (go && (a < qn) && (a < fc) && (icr[sa*CI +: CI] != 0)) begin admv[sa] = 1'b1; nadm = nadm + 1'b1; end
            else go = 1'b0;
        end
    end
    always @(posedge clk) w_d <= t_flit;
    always @(posedge clk or negedge rtq)
        if (!rtq) begin
            esel <= 0; w_v <= 1'b0; w_oh <= 0; l0_v <= 0; w_v2 <= 1'b0;
            for (gg = 0; gg < NS; gg = gg + 1) begin
                tl[gg*QD +: QD] <= {{(QD-1){1'b0}}, 1'b1};
                icr[gg*CI +: CI] <= PBD + 1;
            end
            qn <= 0; fc <= FCR[8:0]; wsel <= 0; t_cr <= 1'b0; q_ovf <= 1'b0; crp <= 0;
        end else begin
            w_v <= t_v;
            w_v2 <= w_v;
            for (gg = 0; gg < NS; gg = gg + 1) begin
                for (ss = 0; ss < NSL; ss = ss + 1)
                    w_oh[(gg*NSL+ss)*QD +: QD] <= (t_v && esel == gg) ? tl[gg*QD +: QD] : {QD{1'b0}};
                if (t_v && esel == gg) tl[gg*QD +: QD] <= {tl[gg*QD +: QD], tl[gg*QD+QD-1]};
                icr[gg*CI +: CI] <= icr[gg*CI +: CI] - (admv[gg] ? 1'b1 : 1'b0) + (icr_ret[gg] ? 1'b1 : 1'b0);
            end
            if (t_v) esel <= (esel == NS - 1) ? 2'd0 : esel + 1'b1;
            l0_v <= admv;
            qn <= qn + (w_v2 ? 1'b1 : 1'b0) - nadm;
            wsel <= (wsel + nadm) % NS;
            if ({1'b0, qn} + w_v2 + w_v + t_v > TXQ + nadm) q_ovf <= 1'b1;
`ifndef OT_LKEP_MUT_CREDIT
            t_cr <= (crp + nadm) != 0;
            crp <= crp + nadm - (((crp + nadm) != 0) ? 1'b1 : 1'b0);
`else
            t_cr <= t_v;                                // mutant: credit returned on arrival, not on admission
`endif
            fc <= fc + {1'b0, fc_add} - {6'b0, nadm};
        end

    // Existing TX consumer FIFOs and the shared capture/CRC pipeline are one
    // hard leaf. All outward packet and credit pins leave existing registers.
    wire b_v;
    wire [FFW-1:0] b_f;
    wire [NS*TW-1:0] th_dt_flat;
    generate for(g=0;g<NS;g=g+1) begin:g_th_flat
      assign th_dt_flat[g*TW +: TW]=th_dt[g];
    end endgenerate
`ifdef OT_LKEP_HARD_LEAVES
    ot_lkep_tx_shared u_tx_shared(
`else
    ot_lkep_tx_shared #(.NS(NS),.W(W),.TFD(TFD),.RL(RL),.SL(SL),.IDLE_P(IDLE_P),.MUT_TX(MUT_TX_SHARED)) u_tx_shared(
`endif
      .clk(HARD_CLOCKS != 0 ? clk_tx_shared : clk),.rst_n(rst_n),
      .th_vt(th_vt),.th_dt_flat(th_dt_flat),.tcrq(tcrq),.b_v(b_v),.b_f(b_f));

    // ---------------------------------------------------------------- reverse frame out (acks + credit count)
    reg  [1:0]    rsub;
    reg  [7:0]    ccnt;
    reg  [RFW-1:0] r_tx;
    wire [SW+EW:0] akr = ak[rsub];
    wire [22:0]   rbody = {ccnt, akr[0], akr[SW:1], rsub};
    always @(posedge clk or negedge rto)
        if (!rto) begin rsub <= 0; ccnt <= 0; end
        else begin
            rsub <= (rsub == NS - 1) ? 2'd0 : rsub + 1'b1;
            if (r_cr) ccnt <= ccnt + 1'b1;
        end
    wire [11:0] r_crc;
    ot_crc_par #(.W(47), .N(12), .POLY(12'h80F), .INIT(12'hFFF)) u_crc_r (.d({akr[SW+EW:SW+1], rbody}), .crc(r_crc));
    always @(posedge clk) r_tx <= {r_crc, rbody};

    // ---------------------------------------------------------------- gearbox (closed S81 lane format, FMT 1)
    reg  [LW-1:0] x_rx_p; reg x_rx_vp;                 // pin capture (io_flop_at_pins), then XR relay stages
    always @(posedge clk) x_rx_p <= x_rx;
    always @(posedge clk or negedge rgb) if (!rgb) x_rx_vp <= 1'b0; else x_rx_vp <= 1'b1;
    wire [LW-1:0] x_rx_q; wire x_rx_vq;
    ot_lkep_relay #(.W(LW), .N(XR)) u_xrr (.clk(clk), .rst_n(rgb), .i_v(x_rx_vp), .i_d(x_rx_p), .o_v(x_rx_vq), .o_vr(), .o_d(x_rx_q));
    wire [LW-1:0] x_tx_g; wire x_tx_gv;
    ot_lkep_relay #(.W(LW), .N(XR)) u_xtr (.clk(clk), .rst_n(rgb), .i_v(1'b1), .i_d(x_tx_g), .o_v(x_tx_gv), .o_vr(), .o_d(x_tx));
    wire          f_rx_v, r_rx_v, gbx_fault;
    wire [FFW-1:0] f_rx;
    wire [RFW-1:0] r_rx;
    ot_s81ph_link_gbx #(.FMT(1), .FFW(FFW), .RFW(RFW), .IDLE_P(IDLE_P), .BW(LW)) u_gbx (
        .clk(clk), .rst_n(rgb), .f_tx_v(b_v), .f_tx(b_f), .r_tx_v(1'b1), .r_tx(r_tx), .beat_tx(x_tx_g),
        .beat_rx_v(x_rx_vq), .beat_rx(x_rx_q), .f_rx_v(f_rx_v), .f_rx(f_rx), .r_rx_v(r_rx_v), .r_rx(r_rx),
        .locked(locked), .fault(gbx_fault));

    // ---------------------------------------------------------------- reverse frame in -> feedback, credits
    reg  [7:0]    ccnt_far;
    wire [11:0]   r_crc_rx;
    ot_crc_par #(.W(47), .N(12), .POLY(12'h80F), .INIT(12'hFFF)) u_crc_rr (.d({ses_c, r_rx[22:0]}), .crc(r_crc_rx));
    wire          r_ok = r_rx_v && (r_crc_rx == r_rx[34:23]);
    always @(posedge clk) begin fb_nak <= r_rx[14]; fb_seq <= r_rx[13:2]; end
    always @(posedge clk or negedge rgb)
        if (!rgb) begin fbv <= 0; ccnt_far <= 0; fc_add <= 0; end
        else begin
            fbv <= r_ok ? ({{(NS-1){1'b0}}, 1'b1} << r_rx[1:0]) & {NS{1'b1}} : {NS{1'b0}};
            fc_add <= r_ok ? r_rx[22:15] - ccnt_far : 8'd0;
            if (r_ok) ccnt_far <= r_rx[22:15];
        end

    // ---------------------------------------------------------------- forward frame in -> CRC (pipelined) -> tiles
    wire [13:0]   p_crc;                                // CRC of the frame now in p_h
    ot_crc_pipe #(.W(HB), .N(14), .POLY(14'h0805), .INIT(14'h3FFF), .NP(4)) u_crc_f (.clk(clk), .d(f_rx[HB-1:0]), .crc(p_crc));
    wire          p_ok = (p_crc == p_c);
    always @(posedge clk) begin p_h <= f_rx[HB-1:0]; p_c <= f_rx[FFW-1:HB]; c_h <= p_h; end
    always @(posedge clk or negedge rrx)
        if (!rrx) begin p_v <= 1'b0; c_v <= 1'b0; end
        else begin
            p_v <= f_rx_v;
`ifndef OT_LKEP_MUT_NOCRC
            c_v <= p_v && p_ok;
`else
            c_v <= p_v;
`endif
        end
    reg           drop;
    always @(posedge clk or negedge rrx)
        if (!rrx) drop <= 1'b0;
        else drop <= (|sd_t) || (c_v && (c_sub >= NS)) || (p_v && !p_ok);

    // Existing RX consumer FIFOs and strict merge stay together with their registered outputs.
    wire [NS*W-1:0] oh_dt_flat;
    generate for(g=0;g<NS;g=g+1) begin:g_oh_flat
      assign oh_dt_flat[g*W +: W]=oh_dt[g];
    end endgenerate
`ifdef OT_LKEP_HARD_LEAVES
    ot_lkep_rx_shared u_rx_shared(
`else
    ot_lkep_rx_shared #(.NS(NS),.W(W),.OFD(OFD),.RL(RL),.SL(SL),.MUT_RX(MUT_RX_SHARED)) u_rx_shared(
`endif
      .clk(HARD_CLOCKS != 0 ? clk_rx_shared : clk),.rst_n(rst_n),
      .oh_vt(oh_vt),.oh_dt_flat(oh_dt_flat),.ocrq(ocrq),.r_v(r_v),.r_flit(r_flit));

    // ---------------------------------------------------------------- status (tile status registers)
    integer v;
    reg [31:0] rep_sum;
    always @(*) begin rep_sum = 0; for (v = 0; v < NS; v = v + 1) rep_sum = rep_sum + rp_t[v]; end
    always @(posedge clk or negedge rto)
        if (!rto) begin fault <= 1'b0; st_replays <= 0; st_drops <= 0; end
        else begin
            fault <= fault | (|sf_t) | gbx_fault | q_ovf;
            st_replays <= rep_sum;
            if (drop) st_drops <= st_drops + 1'b1;
        end
endmodule
