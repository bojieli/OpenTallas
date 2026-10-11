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
//   TX   t_flit -> TXQ-deep queue -> striped round-robin over NS closed retry pipelines (ot_hbm_link_retry_pipeline,
//        the view_wpin_hm10 macro: SECDED replay SRAM, ACK/NAK, timeout, bounded retries) -- a flit is admitted only
//        while a far-end credit is held (FC, initial FCR = the far die's receive buffer) -> the pipelines' tx words
//        {sub, seq, session, data} + CRC-14 -> ot_s81ph_link_gbx FMT 1 at BW = LW (S81 lane format: 3 forward slots
//        per 4 beats at fixed bit positions, marker / idle beats, one 35-b reverse frame in every beat).
//   RX   gearbox slots -> CRC-14 check (bad frame: dropped; the pipeline's sequence check NAKs the gap or its timeout
//        replays it) -> per-sub FIFO (full: dropped, same recovery) -> pipeline rx -> strict round-robin merge in the
//        striping order -> r_v / r_flit.  No backpressure towards the die: the far sender only admits a flit while it
//        holds one of this die's receive-buffer credits.
//   Reverse frame (35 b, every beat, rotating over the subs): {crc12, ccnt8, ack_nak, ack_seq12, sub2}; the ack session is
//        NOT sent: the CRC-12 covers {ack_session, body}, so a frame of another session fails the CRC and is dropped
//        (fb_session = the local session); -> the far pipeline's fb_*; ccnt = cumulative r_cr count.
// Exactness is at transaction level: every flit is delivered once, in order, bit-exact (bench tb_hfd_lk_ep: two
// endpoints back to back, random lane bit errors, die-side stalls under credits).
// Throughput: one retry pipeline admits one word per 4 edges (545 / 4 b a cycle); NS = 3 fills the gearbox's 3 slots
// per 4 beats (0.75 flit a beat less the 1/IDLE_P idle beats).  The pacer mirrors the gearbox slot FIFO (sn) exactly,
// so the gearbox overflow fault cannot fire.
// Mutants (bench only): OT_LKEP_MUT_NOCRC (forward CRC not checked), OT_LKEP_MUT_MERGE (merge does not wait for the
// sub whose turn it is).
// ---------------------------------------------------------------------------
module ot_hbm_lk_ep #(
    parameter integer NS     = 3,          // retry pipelines (sub-channels) per link, 1..4
    parameter integer W      = 545,
    parameter integer TXQ    = 32,         // local TX queue depth (= the die sender's credits; covers the ~24-cycle die credit loop)
    parameter integer FCR    = 256,        // far-end receive-buffer credits at reset (ot_hcoll_port: 256-flit SRAM rb)
    parameter integer SQ     = 4,          // per-sub RX FIFO depth (power of 2)
    parameter integer IDLE_P = 1024,
    parameter integer LW     = 487,        // SerDes lanes each way
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
    localparam integer QB = $clog2(TXQ);
    localparam integer SB = $clog2(SQ);
`ifndef SYNTHESIS
    initial if (NS < 1 || NS > 3 || HB + 14 != FFW || (1 << QB) != TXQ || (1 << SB) != SQ) $fatal(1, "hfd_lk_ep: geometry");
`endif
    // ---------------------------------------------------------------- CRCs (parallel, MSB first)
    function automatic [13:0] crc14(input [HB-1:0] d);
        reg [13:0] c; integer i;
        begin c = 14'h3FFF;
            for (i = HB - 1; i >= 0; i = i - 1) c = {c[12:0], 1'b0} ^ ((c[13] ^ d[i]) ? 14'h0805 : 14'h0000);
            crc14 = c; end
    endfunction
    function automatic [11:0] crc12(input [46:0] d);
        reg [11:0] c; integer i;
        begin c = 12'hFFF;
            for (i = 46; i >= 0; i = i - 1) c = {c[10:0], 1'b0} ^ ((c[11] ^ d[i]) ? 12'h80F : 12'h000);
            crc12 = c; end
    endfunction
    // ---------------------------------------------------------------- retry pipelines
    wire [NS-1:0]    p_in_v, p_in_r, p_tx_v, p_tx_r, p_rx_v, p_rx_r, p_out_v, p_out_r, p_fb_v, p_fault;
    wire [W-1:0]     p_in_dd [0:NS-1];
    wire [W-1:0]     p_tx_d  [0:NS-1];
    wire [SW-1:0]    p_tx_s  [0:NS-1];
    wire [EW-1:0]    p_tx_e  [0:NS-1];
    wire [W-1:0]     p_rx_d  [0:NS-1];
    wire [SW-1:0]    p_rx_s  [0:NS-1];
    wire [EW-1:0]    p_rx_e  [0:NS-1];
    wire [W-1:0]     p_out_d [0:NS-1];
    wire [SW-1:0]    p_ack_s [0:NS-1];
    wire [NS-1:0]    p_ack_n;
    wire [EW-1:0]    p_ack_e [0:NS-1];
    wire [SW-1:0]    p_ret   [0:NS-1];
    wire [31:0]      p_rep   [0:NS-1];
    reg              fb_nak; reg [SW-1:0] fb_seq; reg [EW-1:0] fb_ses;
    genvar g;
    generate for (g = 0; g < NS; g = g + 1) begin : g_p
`ifdef SYNTHESIS
        ot_hbm_link_retry_pipeline u_rp (
`else
        ot_hbm_link_retry_pipeline #(.ENABLE(1), .W(W), .SW(SW), .EW(EW), .DEPTH(512), .TIMEOUT(TIMEOUT),
            .MAX_RETRY(MAX_RETRY), .RSTR(1), .RX_SLOT_SAMPLE(1), .TX_SLOT_SAMPLE(1), .IN_PIN(1), .IN_WPIN(1)) u_rp (
`endif
            .clk(clk), .rst_n(rst_n), .session(session),
            .in_valid(p_in_v[g]), .in_ready(p_in_r[g]), .in_data(p_in_dd[g]),
            .tx_valid(p_tx_v[g]), .tx_ready(p_tx_r[g]), .tx_data(p_tx_d[g]), .tx_seq(p_tx_s[g]), .tx_session(p_tx_e[g]),
            .rx_valid(p_rx_v[g]), .rx_ready(p_rx_r[g]), .rx_ue(1'b0), .rx_data(p_rx_d[g]), .rx_seq(p_rx_s[g]),
            .rx_session(p_rx_e[g]),
            .out_valid(p_out_v[g]), .out_ready(p_out_r[g]), .out_data(p_out_d[g]),
            .ack_seq(p_ack_s[g]), .ack_nak(p_ack_n[g]), .ack_session(p_ack_e[g]),
            .fb_valid(p_fb_v[g]), .fb_good(1'b1), .fb_nak(fb_nak), .fb_seq(fb_seq), .fb_session(fb_ses),
            .fault(p_fault[g]), .retained(p_ret[g]), .replay_count(p_rep[g]));
    end endgenerate

    // ---------------------------------------------------------------- TX queue, far credits, striping
    // All NS pipelines admit on the same edge (their 4-edge admission phases are aligned by the common reset), so the
    // queue pops up to NS heads at once, to wsel, wsel+1, ... in striping order (stops at the first sub not ready,
    // at the queue depth or at the far credits).  The die-side credit returns one pulse a cycle from a counter.
    reg  [W-1:0]  q [0:TXQ-1];
    reg  [QB:0]   qn;
    reg  [QB-1:0] qh, qt;
    reg  [8:0]    fc;                                   // far-end credits held (FCR <= 511)
    reg  [1:0]    wsel;                                 // sub of the next admitted flit
    reg           q_ovf;
    reg  [QB+1:0] crp;                                  // die-side credits owed
    reg  [NS-1:0] admv;                                 // admitted this edge, by sub
    reg  [2:0]    nadm;
    integer       a, sa;
    reg           go;
    always @(*) begin
        admv = 0; nadm = 0; go = 1'b1;
        for (a = 0; a < NS; a = a + 1) begin
            sa = (wsel + a) % NS;
            if (go && (a < qn) && (a < fc) && p_in_r[sa]) begin admv[sa] = 1'b1; nadm = nadm + 1'b1; end
            else go = 1'b0;
        end
    end
    generate for (g = 0; g < NS; g = g + 1) begin : g_in
        wire [1:0] off = (g >= wsel) ? (g - wsel) : (g + NS - wsel);
        wire       pre = (off == 0) || (off == 1 ? p_in_r[(g + NS - 1) % NS] : (p_in_r[(g + NS - 1) % NS] && p_in_r[(g + NS - 2) % NS]));
        assign p_in_v[g] = (off < qn) && (off < fc) && pre;
        assign p_in_dd[g] = q[qh + off];
    end endgenerate
    reg  [7:0]    fc_add;                               // credits returned by the far end this edge (from the rev path)
    always @(posedge clk) if (t_v) q[qt] <= t_flit;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin qn <= 0; qh <= 0; qt <= 0; fc <= FCR[8:0]; wsel <= 0; t_cr <= 1'b0; q_ovf <= 1'b0; crp <= 0; end
        else begin
            if (t_v) qt <= qt + 1'b1;
            qh <= qh + nadm[QB-1:0];
            wsel <= (wsel + nadm) % NS;
            qn <= qn + (t_v ? 1'b1 : 1'b0) - nadm;
            if (t_v && qn == TXQ && nadm == 0) q_ovf <= 1'b1;
`ifndef OT_LKEP_MUT_CREDIT
            t_cr <= (crp + nadm) != 0;
            crp <= crp + nadm - (((crp + nadm) != 0) ? 1'b1 : 1'b0);
`else
            t_cr <= t_v;                                // mutant: credit returned on arrival, not on admission
`endif
            fc <= fc + {1'b0, fc_add} - {6'b0, nadm};
        end

    // ---------------------------------------------------------------- gearbox pacer (exact mirror of its slot FIFO)
    reg  [9:0]    m_ic; reg m_idle; reg [1:0] m_ph; reg [2:0] m_sn;
    reg           a_v, b_v;                             // grant -> A (select) -> B (CRC) -> gearbox push
    wire          m_need = !m_idle && (m_ph != 2'd3);
    wire          m_take = m_need && (m_sn != 0);
    wire [1:0]    pend = {1'b0, a_v} + {1'b0, b_v};
    wire          room = ({1'b0, m_sn} + {2'b0, pend}) <= 4'd3;
    reg  [1:0]    tsel;                                 // round-robin start for the tx grant
    reg  [NS-1:0] gnt;
    integer       k, j;
    always @(*) begin
        gnt = 0;
        if (room)
            for (k = NS - 1; k >= 0; k = k - 1) begin
                j = (tsel + k) % NS;
                if (p_tx_v[j]) gnt = {{(NS-1){1'b0}}, 1'b1} << j;
            end
    end
    assign p_tx_r = gnt;
    reg  [HB-1:0] a_h;
    reg  [FFW-1:0] b_f;
    integer s;
    always @(posedge clk) begin
        for (s = 0; s < NS; s = s + 1)
            if (gnt[s]) a_h <= {p_tx_e[s], p_tx_s[s], 2'(s), p_tx_d[s]};
        b_f <= {crc14(a_h), a_h};
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            m_ic <= 0; m_idle <= (IDLE_P == 1); m_ph <= 0; m_sn <= 0; a_v <= 0; b_v <= 0; tsel <= 0;
        end else begin
            m_ic <= m_idle ? 10'd0 : m_ic + 1'b1;
            m_idle <= !m_idle && (m_ic == IDLE_P - 2);
            if (!m_idle) m_ph <= m_ph + 1'b1;
            m_sn <= m_sn + (b_v ? 3'd1 : 3'd0) - (m_take ? 3'd1 : 3'd0);
            a_v <= |gnt; b_v <= a_v;
            if (|gnt) tsel <= (tsel == NS - 1) ? 2'd0 : tsel + 1'b1;
        end

    // ---------------------------------------------------------------- reverse frame out (acks + credit count)
    reg  [1:0]    rsub;
    reg  [7:0]    ccnt;
    reg  [RFW-1:0] r_tx;
    wire [22:0]   rbody = {ccnt, p_ack_n[rsub], p_ack_s[rsub], rsub};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rsub <= 0; ccnt <= 0; end
        else begin
            rsub <= (rsub == NS - 1) ? 2'd0 : rsub + 1'b1;
            if (r_cr) ccnt <= ccnt + 1'b1;
        end
    always @(posedge clk) r_tx <= {crc12({p_ack_e[rsub], rbody}), rbody};

    // ---------------------------------------------------------------- gearbox (closed S81 lane format, FMT 1)
    reg  [LW-1:0] x_rx_q; reg x_rx_vq;
    always @(posedge clk) x_rx_q <= x_rx;
    always @(posedge clk or negedge rst_n) if (!rst_n) x_rx_vq <= 1'b0; else x_rx_vq <= 1'b1;
    wire          f_rx_v, r_rx_v, gbx_fault;
    wire [FFW-1:0] f_rx;
    wire [RFW-1:0] r_rx;
    ot_s81ph_link_gbx #(.FMT(1), .FFW(FFW), .RFW(RFW), .IDLE_P(IDLE_P), .BW(LW)) u_gbx (
        .clk(clk), .rst_n(rst_n), .f_tx_v(b_v), .f_tx(b_f), .r_tx_v(1'b1), .r_tx(r_tx), .beat_tx(x_tx),
        .beat_rx_v(x_rx_vq), .beat_rx(x_rx_q), .f_rx_v(f_rx_v), .f_rx(f_rx), .r_rx_v(r_rx_v), .r_rx(r_rx),
        .locked(locked), .fault(gbx_fault));

    // ---------------------------------------------------------------- reverse frame in -> feedback, credits
    reg  [NS-1:0] fbv;
    reg  [7:0]    ccnt_far;
    wire          r_ok = r_rx_v && (crc12({session, r_rx[22:0]}) == r_rx[34:23]);
    assign p_fb_v = fbv;
    always @(posedge clk) begin fb_nak <= r_rx[14]; fb_seq <= r_rx[13:2]; fb_ses <= session; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fbv <= 0; ccnt_far <= 0; fc_add <= 0; end
        else begin
            fbv <= r_ok ? ({{(NS-1){1'b0}}, 1'b1} << r_rx[1:0]) & {NS{1'b1}} : {NS{1'b0}};
            fc_add <= r_ok ? r_rx[22:15] - ccnt_far : 8'd0;
            if (r_ok) ccnt_far <= r_rx[22:15];
        end

    // ---------------------------------------------------------------- forward frame in -> CRC -> per-sub FIFO
    reg           c_v; reg [HB-1:0] c_h;
    wire          f_ok = (crc14(f_rx[HB-1:0]) == f_rx[FFW-1:HB]);
    always @(posedge clk) c_h <= f_rx[HB-1:0];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) c_v <= 1'b0;
`ifndef OT_LKEP_MUT_NOCRC
        else c_v <= f_rx_v && f_ok;
`else
        else c_v <= f_rx_v;
`endif
    wire [1:0]    c_sub = c_h[W +: 2];
    reg  [HB-1:0] sq   [0:NS*SQ-1];
    reg  [SB:0]   sn_  [0:NS-1];
    reg  [SB-1:0] sh_  [0:NS-1];
    reg  [SB-1:0] st_  [0:NS-1];
    reg           drop;
    generate for (g = 0; g < NS; g = g + 1) begin : g_rx
        wire push = c_v && (c_sub == g) && (sn_[g] != SQ);
        wire pop  = p_rx_v[g] && p_rx_r[g];
        assign p_rx_v[g] = (sn_[g] != 0);
        assign p_rx_d[g] = sq[g*SQ + sh_[g]][W-1:0];
        assign p_rx_s[g] = sq[g*SQ + sh_[g]][W+2 +: SW];
        assign p_rx_e[g] = sq[g*SQ + sh_[g]][W+2+SW +: EW];
        always @(posedge clk) if (push) sq[g*SQ + st_[g]] <= c_h;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin sn_[g] <= 0; sh_[g] <= 0; st_[g] <= 0; end
            else begin
                if (push) st_[g] <= st_[g] + 1'b1;
                if (pop) sh_[g] <= sh_[g] + 1'b1;
                sn_[g] <= sn_[g] + (push ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
            end
    end endgenerate
    always @(*) drop = c_v && ((c_sub >= NS) || (sn_[c_sub] == SQ));

    // ---------------------------------------------------------------- strict round-robin merge -> die
    reg  [1:0]    msel;
    generate for (g = 0; g < NS; g = g + 1) begin : g_out
`ifndef OT_LKEP_MUT_MERGE
        assign p_out_r[g] = (msel == g);
`else
        assign p_out_r[g] = (msel == g) || !p_out_v[msel];
`endif
    end endgenerate
    reg           o_v; reg [W-1:0] o_d;
    integer       u;
    always @(*) begin
        o_v = 1'b0; o_d = p_out_d[0];
        for (u = 0; u < NS; u = u + 1) if (p_out_v[u] && p_out_r[u] && !o_v) begin o_v = 1'b1; o_d = p_out_d[u]; end
    end
    always @(posedge clk) r_flit <= o_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin r_v <= 1'b0; msel <= 0; end
        else begin
            r_v <= o_v;
            if (p_out_v[msel]) msel <= (msel == NS - 1) ? 2'd0 : msel + 1'b1;
        end

    // ---------------------------------------------------------------- status
    integer v;
    reg [31:0] rep_sum;
    always @(*) begin rep_sum = 0; for (v = 0; v < NS; v = v + 1) rep_sum = rep_sum + p_rep[v]; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fault <= 1'b0; st_replays <= 0; st_drops <= 0; end
        else begin
            fault <= fault | (|p_fault) | gbx_fault | q_ovf;
            st_replays <= rep_sum;
            if (drop || (f_rx_v && !f_ok)) st_drops <= st_drops + 1'b1;
        end
endmodule
