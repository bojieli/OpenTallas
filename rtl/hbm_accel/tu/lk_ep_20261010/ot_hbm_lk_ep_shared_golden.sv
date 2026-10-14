`timescale 1ns/1ps
// Immutable pre-shared-leaf endpoint core, exact comparator only.
module ot_hbm_lk_ep_shared_golden #(
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

    // ---------------------------------------------------------------- TX out: tile sink stage 1 -> consumer FIFO -> grant
    wire [NS-1:0]    th_v;
    wire [TW-1:0]    th_d [0:NS-1];
    reg  [NS-1:0]    gnt;
    generate for (g = 0; g < NS; g = g + 1) begin : g_to
        ot_lkep_sinkc #(.W(TW), .D(TFD), .N(RL), .SL(SL)) u_q (.clk(clk), .rst_c(rto), .i_v(th_vt[g]), .i_d(th_dt[g]),
            .h_v(th_v[g]), .h_d(th_d[g]), .pop(gnt[g]), .crq(tcrq[g]));
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

    // ---------------------------------------------------------------- tile out stage 1 -> consumer FIFO -> strict round-robin merge
    wire [NS-1:0]    oh_v;
    wire [W-1:0]     oh_d [0:NS-1];
    reg  [NS-1:0]    opop;
    generate for (g = 0; g < NS; g = g + 1) begin : g_out
        ot_lkep_sinkc #(.W(W), .D(OFD), .N(RL), .SL(SL)) u_q (.clk(clk), .rst_c(rrx), .i_v(oh_vt[g]), .i_d(oh_dt[g]),
            .h_v(oh_v[g]), .h_d(oh_d[g]), .pop(opop[g]), .crq(ocrq[g]));
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
