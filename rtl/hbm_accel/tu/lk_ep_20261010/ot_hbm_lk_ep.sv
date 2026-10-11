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
module ot_lkep_relay #(parameter integer W = 1, parameter integer N = 1) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         i_v,
    input  wire [W-1:0] i_d,
    output wire         o_v,
    output wire [W-1:0] o_d
);
    generate if (N == 0) begin : g_w
        assign o_v = i_v; assign o_d = i_d;
    end else begin : g_r
        reg [N-1:0] v;
        reg [W-1:0] d [0:N-1];
        integer k;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) v <= {N{1'b0}};
            else begin v[0] <= i_v; for (k = 1; k < N; k = k + 1) v[k] <= v[k-1]; end
        always @(posedge clk) begin d[0] <= i_d; for (k = 1; k < N; k = k + 1) d[k] <= d[k-1]; end
        assign o_v = v[N-1]; assign o_d = d[N-1];
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
    genvar s, e;
    generate for (s = 0; s < NSL; s = s + 1) begin : g_s
        localparam integer LO = s * SL;
        localparam integer HI = (LO + SL > W) ? W : LO + SL;
        for (e = 0; e < D; e = e + 1) begin : g_e
            always @(posedge clk) if (we && wp[s*D+e]) m[e*W+LO +: HI-LO] <= i_d[HI-1:LO];
        end
        reg [HI-LO-1:0] x;
        integer j;
        always @(*) begin
            x = {(HI-LO){1'b0}};
            for (j = 0; j < D; j = j + 1) x = x | ({(HI-LO){rp[s*D+j]}} & m[j*W+LO +: HI-LO]);
        end
        assign head[HI-1:LO] = x;
    end endgenerate
    always @(posedge clk) if (!o_v) o_d <= head;
    integer t;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            n <= {CB{1'b0}}; o_v <= 1'b0; cr <= 1'b0;
            for (t = 0; t < NSL; t = t + 1) begin wp[t*D +: D] <= {{(D-1){1'b0}}, 1'b1}; rp[t*D +: D] <= {{(D-1){1'b0}}, 1'b1}; end
        end else begin
            n <= n + (we ? 1'b1 : 1'b0) - (ld ? 1'b1 : 1'b0);
            o_v <= ld || (o_v && !o_rdy);
            cr <= o_v && o_rdy;
            for (t = 0; t < NSL; t = t + 1) begin
                if (we) wp[t*D +: D] <= {wp[t*D +: D], wp[t*D+D-1]};
                if (ld) rp[t*D +: D] <= {rp[t*D +: D], rp[t*D+D-1]};
            end
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
    ot_lkep_relay #(.W(W), .N(N)) u_f (.clk(clk), .rst_n(rst_c), .i_v(cap_v), .i_d(cap_d), .o_v(f_v), .o_d(f_d));
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
            always @(posedge clk) if (f_v && wp[s*D+e]) m[e*W+LO +: HI-LO] <= f_d[HI-1:LO];
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
    // retry pipeline parameters (simulation only; the hard macro is the closed view_wpin_hm10)
    parameter integer TIMEOUT = 8192,
    parameter integer MAX_RETRY = 8
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [23:0]     session,
    input  wire            t_v,
    input  wire [W-1:0]    t_flit,
    output reg             t_cr,
    output reg             r_v,
    output reg  [W-1:0]    r_flit,
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
`ifndef SYNTHESIS
    initial if (NS < 1 || NS > 3 || HB + 14 != FFW || (1 << QB) != TXQ || SQ < 2 || PBD < 2 || TFD < 2 || OFD < 2)
        $fatal(1, "hfd_lk_ep: geometry");
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
    // session: one register per macro (+ one for the reverse-frame check); changes only under the coordinated reset
    (* keep *) reg [NS*EW-1:0] ses_p;
    reg  [EW-1:0] ses_c;
    always @(posedge clk) begin ses_p <= {NS{session}}; ses_c <= session; end

    // ---------------------------------------------------------------- retry pipelines
    wire [NS-1:0]    p_in_v, p_in_r, p_tx_v, p_tx_r, p_rx_v, p_rx_r, p_out_v, p_out_r, p_fb_v, p_fault, p_fb_n;
    wire [W-1:0]     p_in_dd [0:NS-1];
    wire [W-1:0]     p_tx_d  [0:NS-1];
    wire [SW-1:0]    p_tx_s  [0:NS-1];
    wire [EW-1:0]    p_tx_e  [0:NS-1];
    wire [TW-1:0]    p_rx_w  [0:NS-1];
    wire [W-1:0]     p_out_d [0:NS-1];
    wire [SW-1:0]    p_ack_s [0:NS-1];
    wire [NS-1:0]    p_ack_n;
    wire [EW-1:0]    p_ack_e [0:NS-1];
    wire [SW-1:0]    p_ret   [0:NS-1];
    wire [31:0]      p_rep   [0:NS-1];
    wire [SW-1:0]    p_fb_s  [0:NS-1];
    genvar g;
    generate for (g = 0; g < NS; g = g + 1) begin : g_p
`ifdef SYNTHESIS
        ot_hbm_link_retry_pipeline u_rp (
`else
        ot_hbm_link_retry_pipeline #(.ENABLE(1), .W(W), .SW(SW), .EW(EW), .DEPTH(512), .TIMEOUT(TIMEOUT),
            .MAX_RETRY(MAX_RETRY), .RSTR(1), .RX_SLOT_SAMPLE(1), .TX_SLOT_SAMPLE(1), .IN_PIN(1), .IN_WPIN(1)) u_rp (
`endif
            .clk(clk), .rst_n(rl[g]), .session(ses_p[g*EW +: EW]),
            .in_valid(p_in_v[g]), .in_ready(p_in_r[g]), .in_data(p_in_dd[g]),
            .tx_valid(p_tx_v[g]), .tx_ready(p_tx_r[g]), .tx_data(p_tx_d[g]), .tx_seq(p_tx_s[g]), .tx_session(p_tx_e[g]),
            .rx_valid(p_rx_v[g]), .rx_ready(p_rx_r[g]), .rx_ue(1'b0), .rx_data(p_rx_w[g][W-1:0]),
            .rx_seq(p_rx_w[g][W +: SW]), .rx_session(p_rx_w[g][W+SW +: EW]),
            .out_valid(p_out_v[g]), .out_ready(p_out_r[g]), .out_data(p_out_d[g]),
            .ack_seq(p_ack_s[g]), .ack_nak(p_ack_n[g]), .ack_session(p_ack_e[g]),
            .fb_valid(p_fb_v[g]), .fb_good(1'b1), .fb_nak(p_fb_n[g]), .fb_seq(p_fb_s[g]), .fb_session(ses_p[g*EW +: EW]),
            .fault(p_fault[g]), .retained(p_ret[g]), .replay_count(p_rep[g]));
    end endgenerate

    // ---------------------------------------------------------------- TX queues (per sub), far credits, admission
    // Flit k goes to sub k mod NS (esel), so the a-th oldest queued flit is the head of sub (wsel + a) mod NS: admitting
    // in striping order from wsel (stopping at the first sub without a flit, a far credit or a pin-buffer credit) is the
    // same order as one shared queue.  The write enables are registered one-hot vectors (one copy per 64-b slice), the
    // read is a one-hot head (one copy per slice) AND-OR into the launch register l0 (free-running; l0_v = admitted).
    reg  [1:0]          esel;
    reg  [NS*QD-1:0]    tl;
    reg                 w_v;
    reg  [W-1:0]        w_d;
    (* keep *) reg [NS*NSL*QD-1:0] w_oh;
    (* keep *) reg [NS*NSL*QD-1:0] hd;
    reg  [NS*QD*W-1:0]  qs;
    reg  [NS*W-1:0]     l0_d;
    reg  [NS-1:0]       l0_v;
    reg  [QB:0]         qn;                             // written, not yet admitted
    reg  [8:0]          fc;                             // far-end credits held (FCR <= 511)
    reg  [1:0]          wsel;                           // sub of the next admitted flit
    reg                 q_ovf;
    reg  [QB+1:0]       crp;                            // die-side credits owed
    reg  [NS*CI-1:0]    icr;                            // pin-buffer credits by sub
    wire [NS-1:0]       icr_ret;
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
    genvar e, s;
    generate for (g = 0; g < NS; g = g + 1) begin : g_q
        for (s = 0; s < NSL; s = s + 1) begin : g_s
            localparam integer LO = s * SL;
            localparam integer HI = (LO + SL > W) ? W : LO + SL;
            for (e = 0; e < QD; e = e + 1) begin : g_e
                always @(posedge clk) if (w_oh[(g*NSL+s)*QD+e]) qs[(g*QD+e)*W+LO +: HI-LO] <= w_d[HI-1:LO];
            end
            reg [HI-LO-1:0] x;
            integer j;
            always @(*) begin
                x = {(HI-LO){1'b0}};
                for (j = 0; j < QD; j = j + 1) x = x | ({(HI-LO){hd[(g*NSL+s)*QD+j]}} & qs[(g*QD+j)*W+LO +: HI-LO]);
            end
            always @(posedge clk) l0_d[g*W+LO +: HI-LO] <= x;
        end
    end endgenerate
    always @(posedge clk or negedge rtq)
        if (!rtq) begin
            esel <= 0; w_v <= 1'b0; w_oh <= 0; l0_v <= 0;
            for (gg = 0; gg < NS; gg = gg + 1) begin
                tl[gg*QD +: QD] <= {{(QD-1){1'b0}}, 1'b1};
                icr[gg*CI +: CI] <= PBD + 1;
                for (ss = 0; ss < NSL; ss = ss + 1) hd[(gg*NSL+ss)*QD +: QD] <= {{(QD-1){1'b0}}, 1'b1};
            end
            qn <= 0; fc <= FCR[8:0]; wsel <= 0; t_cr <= 1'b0; q_ovf <= 1'b0; crp <= 0;
        end else begin
            w_v <= t_v;
            for (gg = 0; gg < NS; gg = gg + 1) begin
                for (ss = 0; ss < NSL; ss = ss + 1)
                    w_oh[(gg*NSL+ss)*QD +: QD] <= (t_v && esel == gg) ? tl[gg*QD +: QD] : {QD{1'b0}};
                if (t_v && esel == gg) tl[gg*QD +: QD] <= {tl[gg*QD +: QD], tl[gg*QD+QD-1]};
                if (admv[gg]) for (ss = 0; ss < NSL; ss = ss + 1)
                    hd[(gg*NSL+ss)*QD +: QD] <= {hd[(gg*NSL+ss)*QD +: QD], hd[(gg*NSL+ss)*QD+QD-1]};
                icr[gg*CI +: CI] <= icr[gg*CI +: CI] - (admv[gg] ? 1'b1 : 1'b0) + (icr_ret[gg] ? 1'b1 : 1'b0);
            end
            if (t_v) esel <= (esel == NS - 1) ? 2'd0 : esel + 1'b1;
            l0_v <= admv;
            qn <= qn + (w_v ? 1'b1 : 1'b0) - nadm;
            wsel <= (wsel + nadm) % NS;
            if ({1'b0, qn} + w_v + t_v > TXQ + nadm) q_ovf <= 1'b1;
`ifndef OT_LKEP_MUT_CREDIT
            t_cr <= (crp + nadm) != 0;
            crp <= crp + nadm - (((crp + nadm) != 0) ? 1'b1 : 1'b0);
`else
            t_cr <= t_v;                                // mutant: credit returned on arrival, not on admission
`endif
            fc <= fc + {1'b0, fc_add} - {6'b0, nadm};
        end
    // l0 -> RL relay stages -> pin buffer at the macro; one credit back per word the macro took
    generate for (g = 0; g < NS; g = g + 1) begin : g_ti
        wire         r_v_, cr_p, cr_d, dr;
        wire [W-1:0] r_d;
        ot_lkep_relay #(.W(W), .N(RL)) u_r (.clk(clk), .rst_n(rl[g]), .i_v(l0_v[g]), .i_d(l0_d[g*W +: W]), .o_v(r_v_), .o_d(r_d));
        ot_lkep_pinq #(.W(W), .D(PBD), .SL(SL)) u_b (.clk(clk), .rst_n(rl[g]), .i_v(r_v_), .i_d(r_d),
            .o_v(p_in_v[g]), .o_d(p_in_dd[g]), .o_rdy(p_in_r[g]), .cr(cr_p), .drop(dr));
        ot_lkep_relay #(.W(1), .N(RL)) u_c (.clk(clk), .rst_n(rtq), .i_v(cr_p), .i_d(1'b0), .o_v(icr_ret[g]), .o_d(cr_d));
    end endgenerate

    // ---------------------------------------------------------------- TX out: macro tx -> per-sub FIFO -> grant
    wire [NS-1:0]    th_v;
    wire [TW-1:0]    th_d [0:NS-1];
    reg  [NS-1:0]    gnt;
    generate for (g = 0; g < NS; g = g + 1) begin : g_to
        ot_lkep_sinkq #(.W(TW), .D(TFD), .N(RL), .SL(SL)) u_q (.clk(clk), .rst_p(rl[g]), .rst_c(rto),
            .m_v(p_tx_v[g]), .m_d({p_tx_e[g], p_tx_s[g], p_tx_d[g]}), .m_rdy(p_tx_r[g]), .h_v(th_v[g]), .h_d(th_d[g]), .pop(gnt[g]));
    end endgenerate

    // ---------------------------------------------------------------- gearbox pacer (exact mirror of its slot FIFO)
    reg  [9:0]    m_ic; reg m_idle; reg [1:0] m_ph; reg [2:0] m_sn;
    reg           a_v, x_v, b_v;                        // grant -> A (select) -> X (CRC partials) -> B (CRC) -> gearbox push
    wire          m_need = !m_idle && (m_ph != 2'd3);
    wire          m_take = m_need && (m_sn != 0);
    wire [1:0]    pend = {1'b0, a_v} + {1'b0, x_v} + {1'b0, b_v};
    wire          room = ({1'b0, m_sn} + {2'b0, pend}) <= 4'd3;
    reg  [1:0]    tsel;                                 // round-robin start for the tx grant
    integer       k, j;
    always @(*) begin
        gnt = 0;
        if (room)
            for (k = NS - 1; k >= 0; k = k - 1) begin
                j = (tsel + k) % NS;
                if (th_v[j]) gnt = {{(NS-1){1'b0}}, 1'b1} << j;
            end
    end
    reg  [HB-1:0] a_h, x_h;
    wire [13:0]   x_crc;
    reg  [FFW-1:0] b_f;
    integer i2;
    always @(posedge clk) begin
        for (i2 = 0; i2 < NS; i2 = i2 + 1)
            if (gnt[i2]) a_h <= {th_d[i2][TW-1:W], i2[1:0], th_d[i2][W-1:0]};
        x_h <= a_h;
        b_f <= {x_crc, x_h};
    end
    ot_crc_pipe #(.W(HB), .N(14), .POLY(14'h0805), .INIT(14'h3FFF), .NP(4)) u_crc_t (.clk(clk), .d(a_h), .crc(x_crc));
    always @(posedge clk or negedge rto)
        if (!rto) begin
            m_ic <= 0; m_idle <= (IDLE_P == 1); m_ph <= 0; m_sn <= 0; a_v <= 0; x_v <= 0; b_v <= 0; tsel <= 0;
        end else begin
            m_ic <= m_idle ? 10'd0 : m_ic + 1'b1;
            m_idle <= !m_idle && (m_ic == IDLE_P - 2);
            if (!m_idle) m_ph <= m_ph + 1'b1;
            m_sn <= m_sn + (b_v ? 3'd1 : 3'd0) - (m_take ? 3'd1 : 3'd0);
            a_v <= |gnt; x_v <= a_v; b_v <= x_v;
            if (|gnt) tsel <= (tsel == NS - 1) ? 2'd0 : tsel + 1'b1;
        end

    // ---------------------------------------------------------------- reverse frame out (acks + credit count)
    // acks captured at the macro pins (free-running) and carried RL stages; they are levels (the latest ack state)
    wire [SW+EW:0] ak [0:NS-1];
    generate for (g = 0; g < NS; g = g + 1) begin : g_ak
        wire akv;
        ot_lkep_relay #(.W(SW+EW+1), .N(RL+1)) u_a (.clk(clk), .rst_n(rl[g]), .i_v(1'b0), .i_d({p_ack_e[g], p_ack_s[g], p_ack_n[g]}),
            .o_v(akv), .o_d(ak[g]));
    end endgenerate
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
    reg  [LW-1:0] x_rx_q; reg x_rx_vq;
    always @(posedge clk) x_rx_q <= x_rx;
    always @(posedge clk or negedge rgb) if (!rgb) x_rx_vq <= 1'b0; else x_rx_vq <= 1'b1;
    wire          f_rx_v, r_rx_v, gbx_fault;
    wire [FFW-1:0] f_rx;
    wire [RFW-1:0] r_rx;
    ot_s81ph_link_gbx #(.FMT(1), .FFW(FFW), .RFW(RFW), .IDLE_P(IDLE_P), .BW(LW)) u_gbx (
        .clk(clk), .rst_n(rgb), .f_tx_v(b_v), .f_tx(b_f), .r_tx_v(1'b1), .r_tx(r_tx), .beat_tx(x_tx),
        .beat_rx_v(x_rx_vq), .beat_rx(x_rx_q), .f_rx_v(f_rx_v), .f_rx(f_rx), .r_rx_v(r_rx_v), .r_rx(r_rx),
        .locked(locked), .fault(gbx_fault));

    // ---------------------------------------------------------------- reverse frame in -> feedback, credits
    reg  [NS-1:0] fbv;
    reg           fb_nak; reg [SW-1:0] fb_seq;
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
    // feedback to each macro: RL + 1 stages, the last one at the macro pins
    generate for (g = 0; g < NS; g = g + 1) begin : g_fb
        ot_lkep_relay #(.W(SW+1), .N(RL+1)) u_f (.clk(clk), .rst_n(rl[g]), .i_v(fbv[g]), .i_d({fb_nak, fb_seq}),
            .o_v(p_fb_v[g]), .o_d({p_fb_n[g], p_fb_s[g]}));
    end endgenerate

    // ---------------------------------------------------------------- forward frame in -> CRC (pipelined) -> per-sub FIFO
    reg           p_v, c_v; reg [HB-1:0] p_h, c_h; reg [13:0] p_c;
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
    wire [1:0]    c_sub = c_h[W +: 2];
    wire [NS-1:0] rdrop;
    generate for (g = 0; g < NS; g = g + 1) begin : g_rx
        wire          q_v, cr_u;
        wire [TW-1:0] q_d;
        ot_lkep_relay #(.W(TW), .N(RL)) u_r (.clk(clk), .rst_n(rl[g]), .i_v(c_v && (c_sub == g)),
            .i_d({c_h[HB-1:W+2], c_h[W-1:0]}), .o_v(q_v), .o_d(q_d));
        ot_lkep_pinq #(.W(TW), .D(SQ), .SL(SL)) u_b (.clk(clk), .rst_n(rl[g]), .i_v(q_v), .i_d(q_d),
            .o_v(p_rx_v[g]), .o_d(p_rx_w[g]), .o_rdy(p_rx_r[g]), .cr(cr_u), .drop(rdrop[g]));
    end endgenerate
    reg           drop;
    always @(posedge clk or negedge rrx)
        if (!rrx) drop <= 1'b0;
        else drop <= (|rdrop) || (c_v && (c_sub >= NS)) || (p_v && !p_ok);

    // ---------------------------------------------------------------- macro out -> per-sub FIFO -> strict round-robin merge
    wire [NS-1:0]    oh_v;
    wire [W-1:0]     oh_d [0:NS-1];
    reg  [NS-1:0]    opop;
    generate for (g = 0; g < NS; g = g + 1) begin : g_out
        ot_lkep_sinkq #(.W(W), .D(OFD), .N(RL), .SL(SL)) u_q (.clk(clk), .rst_p(rl[g]), .rst_c(rrx),
            .m_v(p_out_v[g]), .m_d(p_out_d[g]), .m_rdy(p_out_r[g]), .h_v(oh_v[g]), .h_d(oh_d[g]), .pop(opop[g]));
    end endgenerate
    reg  [1:0]    msel;
    reg  [W-1:0]  o_d;
    integer       u;
    always @(*) begin
        opop = 0;
`ifndef OT_LKEP_MUT_MERGE
        for (u = 0; u < NS; u = u + 1) if (msel == u) opop[u] = oh_v[u];
`else
        for (u = 0; u < NS; u = u + 1) if (msel == u) opop[u] = oh_v[u];   // mutant: an empty turn takes the first non-empty sub
        if (opop == 0) for (u = NS - 1; u >= 0; u = u - 1) if (oh_v[u]) opop = {{(NS-1){1'b0}}, 1'b1} << u;
`endif
        o_d = {W{1'b0}};
        for (u = 0; u < NS; u = u + 1) o_d = o_d | ({W{opop[u]}} & oh_d[u]);
    end
    always @(posedge clk) r_flit <= o_d;
    always @(posedge clk or negedge rrx)
        if (!rrx) begin r_v <= 1'b0; msel <= 0; end
        else begin
            r_v <= |opop;
            if (oh_v[msel]) msel <= (msel == NS - 1) ? 2'd0 : msel + 1'b1;
        end

    // ---------------------------------------------------------------- status (macro status pins captured first)
    reg  [NS-1:0] pf_q;
    reg  [31:0]   rp_q [0:NS-1];
    integer v;
    reg [31:0] rep_sum;
    always @(*) begin rep_sum = 0; for (v = 0; v < NS; v = v + 1) rep_sum = rep_sum + rp_q[v]; end
    always @(posedge clk) for (v = 0; v < NS; v = v + 1) rp_q[v] <= p_rep[v];
    always @(posedge clk or negedge rto)
        if (!rto) begin pf_q <= 0; fault <= 1'b0; st_replays <= 0; st_drops <= 0; end
        else begin
            pf_q <= p_fault;
            fault <= fault | (|pf_q) | gbx_fault | q_ovf;
            st_replays <= rep_sum;
            if (drop) st_drops <= st_drops + 1'b1;
        end
endmodule
