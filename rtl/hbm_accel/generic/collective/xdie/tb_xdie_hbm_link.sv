`timescale 1ns/1fs
// tb_xdie_hbm_link (TOKEN-XDIE-HBM 2026-10-18): the HBM d4g GEN2 cross-die collective transport, two dies, both
// directions at once (the pairwise exchange every cross-die collective step is made of), on the CURRENT die RTL:
//
//   die X COLL rail endpoint  ot_hgi_coll_link_e         (the exact per-rail module hb_coll_<q> = ot_hfd_coll_q{2,3}_hard_v8g
//                                                         instantiates, g_link[k].u_link: ot_hgi_coll_static_capture_ctl
//                                                         + 4 replay stores: sequence, CRC-32, 64-deep replay, epoch)
//   -> die lane relays        RLY registered stages each way (the GEN2 hb_coll -> ep_<face> lane relays; COLL_EP 9.6)
//   -> link endpoint           hfd_ep_static              (lane gearbox, IDLE calendar, elastic RX pingpong = THE ONLY
//                                                         flow-control point, block_ready per block)
//   -> SerDes digital          ot_pdie_serdes             (KP4 RS(544,514) encoder/decoder, rate matcher; behavioural PMA)
//   -> OFF-CHIP MODEL          SW_NS fixed flight          (Tomahawk-Ultra switch 250 ns + 2 x 3 m twinax 27.6 ns,
//                                                         tools/dshbm_1m_coll.py TU constants; PMA analog = the macro's
//                                                         behavioural PMA_LAT; one crossing = one switch chip)
//   -> the same chain mirrored on die Y (die Y clock 300 ppm slow: plesiochronous dies; pad bit errors inside FEC t=15).
//
// Static schedule (the compiler's): on-die every event is a fixed cycle -- COLL wr / rd reservations on the endpoint's TX
// slot calendar (beat phase 0..3, never the IDLE beat), endpoint arm / release / drain slots, COLL rx_expect at the
// fixed edge after each drain slot.  No ready / credit reaches COLL.  The ONLY dynamic quantity is the off-die arrival,
// absorbed by the elastic RX blocks: the drain of block b is released at the STATIC time t_tx_last(b) + LXB, and at that
// edge the compiler's ready-per-block check must hold (block_ready of the bank) -- otherwise FAIL (never waited for).
//
// Measured per instance and direction: E = first COLL wr reservation (producer issue) -> last frame published by the far
// COLL endpoint (rx_v), and the first-frame latency; every frame compared bit-exact (545 b) in order.
// Mutants (each must FAIL; +MUT=n):  1 far endpoint RX does not skip IDLE beats (hfd_ep_static MUT 2)
//   2 drain released 60 ns before the static bound (ready-per-block check)   3 far COLL rx_expect sequence off by one
//   4 TX calendar ignores the IDLE beat (endpoint calendar fault)             5 far endpoint pingpong slot-bank mutant
// Plusargs: +MUT=n (2,3,4; 1 and 5 need the EPMUT_B build) +NI=n +P0..P11 frames per instance +LXB_PS=static release bound
// +DRX=edges drain-slot->COLL rx pin +SWD=off-chip flight in 1.2 GHz words +NOBER.  Prints XDIE_PROBE / XDIE_INST / XDIE_HBM PASS|FAIL.
module tb_xdie_rly #(parameter integer W = 613, parameter integer N = 10) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    reg [W-1:0] s [1:N];
    always @(posedge clk) s[1] <= d;
    for (genvar i = 2; i <= N; i = i + 1) begin : g
        always @(posedge clk) s[i] <= s[i-1];
    end
    assign q = s[N];
endmodule

// off-chip flight: D transmitter-clock PMA words (registered), optional single pad bit error in every second word
module tb_xdie_chan #(parameter integer DMAX = 1024) (input wire ck, input wire [543:0] d, output reg [543:0] q,
                                                      input wire ber, input integer D);
    reg [543:0] m [0:DMAX-1];
    integer w = 0, b;
    reg e;
    always @(posedge ck) begin
        e = ber && (($urandom % 2) == 0); b = $urandom % 544;
        q <= m[w];
        m[w] <= e ? (d ^ (544'd1 << b)) : d;
        w = (w >= D - 1) ? 0 : w + 1;
    end
endmodule

module tb_xdie_side #(parameter integer RLY = 10, parameter integer EPMUT = 0, parameter integer IDLE_K = 204) (
    input wire clk, input wire rst_n,
    input wire epoch_begin, input wire wr_v, input wire [15:0] wr_seq, input wire [544:0] wr_flit,
    input wire rd_v, input wire [15:0] rd_seq, input wire ex_v, input wire [15:0] ex_seq,
    input wire arm_v, input wire arm_b, input wire [6:0] words, input wire rel_v, input wire rel_b,
    input wire slot_v, input wire slot_b, input wire [5:0] slot_i,
    output wire c_tx_v, output wire c_rx_v, output wire [544:0] c_rx_f, output wire r_rx_v, output wire [1:0] bready,
    output wire [511:0] sd_tx, input wire [511:0] sd_rx, input wire [1:0] sd_st,
    output wire link_fault, output wire [10:0] link_cause, output wire ep_fault, output wire [10:0] ep_cause, output wire up
);
    // ---- COLL rail endpoint: the current GEN2 module (hb_coll_<q>.u_body.g_link[k].u_link) ----
    wire [611:0] c_tx_f; wire abort, retry; wire [611:0] r_rx_f; wire r_up;
    ot_hgi_coll_link_e u_coll (.ck({5{clk}}), .rst_n(rst_n), .epoch_begin(epoch_begin), .epoch_new(8'h3a), .held_epoch(8'h3a),
        .wr_v(wr_v), .wr_observed_v(wr_v), .wr_seq(wr_seq), .wr_flit(wr_flit), .rd_v(rd_v), .rd_seq(rd_seq),
        .rx_expect_v(ex_v), .rx_expect_seq(ex_seq), .phy_up(r_up), .tx_pin_v(c_tx_v), .tx_pin_flit(c_tx_f),
        .rx_pin_v(r_rx_v), .rx_pin_flit(r_rx_f), .rx_v(c_rx_v), .rx_flit(c_rx_f),
        .epoch_abort(abort), .retry_requested(retry), .fault_cause(link_cause));
    assign link_fault = abort | (|link_cause);
    // ---- die lane relays (fixed registered hops, both directions) ----
    wire e_tx_v; wire [611:0] e_tx_f; wire e_rx_v; wire [611:0] e_rx_f; wire e_up;
    tb_xdie_rly #(.W(613), .N(RLY)) u_rt (.clk(clk), .d({c_tx_v, c_tx_f}), .q({e_tx_v, e_tx_f}));
    tb_xdie_rly #(.W(614), .N(RLY)) u_rr (.clk(clk), .d({e_up, e_rx_v, e_rx_f}), .q({r_up, r_rx_v, r_rx_f}));
    // ---- link endpoint: the off-die boundary (elastic RX pingpong) ----
    hfd_ep_static #(.IDLE_K(IDLE_K), .MUT(EPMUT)) u_ep (.clk(clk), .rst_n(rst_n),
        .tx_v(e_tx_v), .tx_frame(e_tx_f), .rx_arm_v(arm_v), .rx_arm_bank(arm_b), .rx_block_words(words),
        .rx_release_v(rel_v), .rx_release_bank(rel_b), .rx_slot_v(slot_v), .rx_slot_bank(slot_b),
        .rx_slot_index(slot_i), .rx_pin_v(e_rx_v), .rx_pin_flit(e_rx_f), .rx_block_ready(bready),
        .phy_up(e_up), .fault(ep_fault), .fault_cause(ep_cause), .sd_tx(sd_tx), .sd_rx(sd_rx), .sd_st(sd_st));
    assign up = e_up;
endmodule

module tb_xdie_hbm_link;
    parameter integer EPMUT_B = 0, RLY = 10, IDLE_K = 204;
    localparam real TA = 0.833333, TB = 0.833333 * 1.0003;          // die B 300 ppm slow (plesiochronous dies)
    localparam integer LTX = 8 + RLY;                                // rd sample -> gearbox state that consumes it
    localparam integer WR2RD = 8;
    integer MUT = 0, SWD = 333, DRX = 6 + RLY;                       // SWD 333 words = 277.6 ns (switch 250 + cable 27.6)
    reg ca = 0, cb = 0, rst = 0;
    always #(TA / 2) ca = ~ca;
    always #(TB / 2) cb = ~cb;
    wire ck [0:1]; assign ck[0] = ca; assign ck[1] = cb;
    wire [511:0] txa, txb, rxa, rxb; wire [1:0] sta, stb; wire [543:0] pa, pb, pa_c, pb_c; wire tca, tcb;
    reg ber = 1;
    ot_pdie_serdes u_sa (.clk(ca), .rst(rst), .tx(txa), .rx(rxa), .st(sta), .pma_tx(pa), .pma_tck(tca), .pma_rx(pb_c), .pma_rck(tcb));
    ot_pdie_serdes u_sb (.clk(cb), .rst(rst), .tx(txb), .rx(rxb), .st(stb), .pma_tx(pb), .pma_tck(tcb), .pma_rx(pa_c), .pma_rck(tca));
    tb_xdie_chan u_ab (.ck(tca), .d(pa), .q(pa_c), .ber(ber), .D(SWD));
    tb_xdie_chan u_ba (.ck(tcb), .d(pb), .q(pb_c), .ber(ber), .D(SWD));
    // static-schedule drives (the compiler's calendars), one set per die
    reg epb [0:1]; reg wr_v [0:1]; reg [15:0] wr_seq [0:1]; reg [544:0] wr_flit [0:1]; reg rd_v [0:1]; reg [15:0] rd_seq [0:1];
    reg ex_v [0:1]; reg [15:0] ex_seq [0:1]; reg arm_v [0:1]; reg arm_b [0:1]; reg [6:0] words [0:1]; reg rel_v [0:1];
    reg rel_b [0:1]; reg slot_v [0:1]; reg slot_b [0:1]; reg [5:0] slot_i [0:1];
    wire c_tx_v [0:1]; wire c_rx_v [0:1]; wire [544:0] c_rx_f [0:1]; wire r_rx_v [0:1]; wire [1:0] bready [0:1];
    wire lf [0:1]; wire ef [0:1]; wire up [0:1]; wire [10:0] lc [0:1]; wire [10:0] ec [0:1];
    initial for (int s = 0; s < 2; s++) begin
        epb[s] = 0; wr_v[s] = 0; wr_seq[s] = 0; wr_flit[s] = 0; rd_v[s] = 0; rd_seq[s] = 0; ex_v[s] = 0; ex_seq[s] = 0;
        arm_v[s] = 0; arm_b[s] = 0; words[s] = 0; rel_v[s] = 0; rel_b[s] = 0; slot_v[s] = 0; slot_b[s] = 0; slot_i[s] = 0;
    end
    tb_xdie_side #(.RLY(RLY), .EPMUT(0), .IDLE_K(IDLE_K)) sA (.clk(ca), .rst_n(rst),
        .epoch_begin(epb[0]), .wr_v(wr_v[0]), .wr_seq(wr_seq[0]), .wr_flit(wr_flit[0]), .rd_v(rd_v[0]), .rd_seq(rd_seq[0]),
        .ex_v(ex_v[0]), .ex_seq(ex_seq[0]), .arm_v(arm_v[0]), .arm_b(arm_b[0]), .words(words[0]), .rel_v(rel_v[0]),
        .rel_b(rel_b[0]), .slot_v(slot_v[0]), .slot_b(slot_b[0]), .slot_i(slot_i[0]),
        .c_tx_v(c_tx_v[0]), .c_rx_v(c_rx_v[0]), .c_rx_f(c_rx_f[0]), .r_rx_v(r_rx_v[0]), .bready(bready[0]),
        .sd_tx(txa), .sd_rx(rxa), .sd_st(sta), .link_fault(lf[0]), .link_cause(lc[0]), .ep_fault(ef[0]), .ep_cause(ec[0]), .up(up[0]));
    tb_xdie_side #(.RLY(RLY), .EPMUT(EPMUT_B), .IDLE_K(IDLE_K)) sB (.clk(cb), .rst_n(rst),
        .epoch_begin(epb[1]), .wr_v(wr_v[1]), .wr_seq(wr_seq[1]), .wr_flit(wr_flit[1]), .rd_v(rd_v[1]), .rd_seq(rd_seq[1]),
        .ex_v(ex_v[1]), .ex_seq(ex_seq[1]), .arm_v(arm_v[1]), .arm_b(arm_b[1]), .words(words[1]), .rel_v(rel_v[1]),
        .rel_b(rel_b[1]), .slot_v(slot_v[1]), .slot_b(slot_b[1]), .slot_i(slot_i[1]),
        .c_tx_v(c_tx_v[1]), .c_rx_v(c_rx_v[1]), .c_rx_f(c_rx_f[1]), .r_rx_v(r_rx_v[1]), .bready(bready[1]),
        .sd_tx(txb), .sd_rx(rxb), .sd_st(stb), .link_fault(lf[1]), .link_cause(lc[1]), .ep_fault(ef[1]), .ep_cause(ec[1]), .up(up[1]));
    // gearbox state of each die's endpoint TX (read, to place reservations on its static slot calendar)
    wire [2:0] g_ph [0:1]; wire [12:0] g_gc [0:1];
    assign g_ph[0] = sA.u_ep.u_tx.ph; assign g_gc[0] = sA.u_ep.u_tx.gc;
    assign g_ph[1] = sB.u_ep.u_tx.ph; assign g_gc[1] = sB.u_ep.u_tx.gc;

    function automatic [544:0] flit(input integer side, input integer k);
        reg [31:0] x; reg [575:0] acc;
        begin
            x = 32'h9E3779B9 ^ (side * 32'h85EBCA6B) ^ (k * 32'hC2B2AE35);
            for (int i = 0; i < 18; i++) begin
                x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5); x = x + 32'(i * 7919 + k);
                acc[i*32 +: 32] = x;
            end
            flit = acc[544:0];
        end
    endfunction

    // ---------------- instance plan ----------------
    integer NI = 1, LXB_PS = 600000, LA_PS = 400000, GAPB = 32, PROBE = 0;
    real lmin = 1.0e9, lmax = 0.0;
    integer P [0:11]; integer base [0:12];
    integer nb = 0; integer bs [0:511]; integer bw [0:511];
    initial begin
        integer r, o;
        for (int i = 0; i < 12; i++) P[i] = 64;
        void'($value$plusargs("NI=%d", NI)); void'($value$plusargs("MUT=%d", MUT)); void'($value$plusargs("SWD=%d", SWD));
        void'($value$plusargs("DRX=%d", DRX)); void'($value$plusargs("LXB_PS=%d", LXB_PS));
        void'($value$plusargs("LA_PS=%d", LA_PS)); void'($value$plusargs("GAPB=%d", GAPB)); if ($test$plusargs("PROBE")) PROBE = 1;
        void'($value$plusargs("P0=%d", P[0])); void'($value$plusargs("P1=%d", P[1])); void'($value$plusargs("P2=%d", P[2]));
        void'($value$plusargs("P3=%d", P[3])); void'($value$plusargs("P4=%d", P[4])); void'($value$plusargs("P5=%d", P[5]));
        void'($value$plusargs("P6=%d", P[6])); void'($value$plusargs("P7=%d", P[7])); void'($value$plusargs("P8=%d", P[8]));
        void'($value$plusargs("P9=%d", P[9])); void'($value$plusargs("P10=%d", P[10])); void'($value$plusargs("P11=%d", P[11]));
        if ($test$plusargs("NOBER")) ber = 0;
        base[0] = 0; for (int i = 1; i <= 12; i++) base[i] = base[i-1] + P[i-1];
        nb = 0;
        for (int i = 0; i < NI; i++) begin
            r = P[i]; o = base[i];
            while (r > 0) begin bs[nb] = o; bw[nb] = (r > 64) ? 64 : r; o = o + bw[nb]; r = r - bw[nb]; nb = nb + 1; end
        end
    end

    // ---------------- bookkeeping (times in ns) ----------------
    integer errors = 0, sched_fail = 0, start_go = 0, drx_obs = -1, drx_bad = 0;
    real t_issue [0:1][0:11]; real t_first [0:1][0:11]; real t_last [0:1][0:11];
    real t_txf [0:1][0:8191]; integer ntxf [0:1]; real t_ready [0:1][0:511];
    integer got [0:1][0:11]; integer inst_go [0:11]; integer done_tx [0:1];
    real worst_slack = 1.0e12, worst_ready_lat = 0.0;
    integer cyc [0:1];

    task automatic gstep(inout reg [2:0] ph, inout reg [12:0] gc);
        if (gc == 13'(IDLE_K)) gc = 0;
        else if (ph == 4) begin ph = 0; gc = gc + 1; end
        else ph = ph + 1;
    endtask

    for (genvar s = 0; s < 2; s = s + 1) begin : g_side
        // ---- sender: COLL wr then rd (WR2RD later) on the endpoint TX slot calendar ----
        integer inst = 0, sent = 0, q_head = 0, q_tail = 0;
        reg [15:0] rdq [0:255]; integer rdt [0:255];
        reg [2:0] ph; reg [12:0] gc; reg ok; integer gapc = 0;
        initial begin cyc[s] = 0; ntxf[s] = 0; done_tx[s] = 0; end
        always @(posedge ck[s]) cyc[s] <= cyc[s] + 1;
        always @(negedge ck[s]) begin
            wr_v[s] <= 0; rd_v[s] <= 0;
            if (gapc > 0) gapc = gapc - 1;
            else if (start_go && inst < NI && inst_go[inst]) begin
                ph = g_ph[s]; gc = g_gc[s];
                for (int j = 0; j < WR2RD + LTX; j++) gstep(ph, gc);
                ok = (MUT == 4) ? (ph != 4) : (ph != 4 && gc != 13'(IDLE_K));
                if (ok) begin
                    wr_v[s] <= 1; wr_seq[s] <= 16'(base[inst] + sent); wr_flit[s] <= flit(s, base[inst] + sent);
                    if (sent == 0) t_issue[s][inst] = $realtime;
                    rdq[q_tail % 256] = 16'(base[inst] + sent); rdt[q_tail % 256] = cyc[s] + WR2RD; q_tail = q_tail + 1;
                    sent = sent + 1;
                    // static inter-block TX gap (the compiler's elastic-RX window: the far bank of the next block is
                    // armed inside it, after the last frame of this block has landed and before the next one lands)
                    if (sent % 64 == 0 && sent < P[inst]) gapc = GAPB;
                    if (sent == P[inst]) begin inst = inst + 1; sent = 0; end
                end
            end
            if (q_head < q_tail && rdt[q_head % 256] == cyc[s]) begin
                rd_v[s] <= 1; rd_seq[s] <= rdq[q_head % 256]; q_head = q_head + 1;
            end
            if (inst == NI && q_head == q_tail) done_tx[s] = 1;
        end
        always @(posedge ck[s]) if (c_tx_v[s]) begin t_txf[s][ntxf[s] % 8192] = $realtime; ntxf[s] = ntxf[s] + 1; end

        // ---- receiver (the peer's frames): static arm / release / drain + COLL rx_expect ----
        // Block b (global frames [bs, bs+bw)) of the peer.  STATIC times (from the peer's TX time of the block's last frame,
        // which the compiler knows): arm of block b+1 at +LA, release of block b at +LXB.  +PROBE: calibration run that arms
        // on the observed landing of the last frame and releases on block_ready (dynamic; it only measures the bounds).
        integer b = 0, armed = 1, sl = -1, exq_h = 0, exq_t = 0, rb = 0, nr = 0, narr = 0;
        integer exc [0:4095]; reg [15:0] exs [0:4095]; integer sdrv [0:4095];
        real trel, tarm, tl; reg [1:0] br_prev = 0; reg first_arm = 1;
        always @(negedge ck[s]) begin
            arm_v[s] <= 0; rel_v[s] <= 0; slot_v[s] <= 0; ex_v[s] <= 0;
            if (start_go && first_arm) begin
                arm_v[s] <= 1; arm_b[s] <= 0; words[s] <= 7'(bw[0]); first_arm = 0;   // block 0: both banks empty
            end else if (start_go) begin
                // arm block `armed` (bank armed%2) once the previous block's last frame has landed
                if (armed < nb && bs[armed - 1] + bw[armed - 1] - 1 < ntxf[1 - s]) begin
                    tarm = t_txf[1 - s][(bs[armed - 1] + bw[armed - 1] - 1) % 8192] + LA_PS / 1000.0;
                    // ... and not before its bank (block armed-2) has drained and flushed: static release of that block
                    // + its drain slots + 8 edges (flush 5, pin registers 2, 1 guard)
                    if (armed >= 2 && t_txf[1 - s][(bs[armed - 2] + bw[armed - 2] - 1) % 8192] + LXB_PS / 1000.0
                                      + (bw[armed - 2] + 8) * 0.833333 > tarm)
                        tarm = t_txf[1 - s][(bs[armed - 2] + bw[armed - 2] - 1) % 8192] + LXB_PS / 1000.0 + (bw[armed - 2] + 8) * 0.833333;
                    if (PROBE ? (narr >= bs[armed - 1] + bw[armed - 1]) : ($realtime >= tarm)) begin
                        arm_v[s] <= 1; arm_b[s] <= armed[0]; words[s] <= 7'(bw[armed]); armed = armed + 1;
                    end
                end
                if (b < nb && sl < 0 && b < armed && bs[b] + bw[b] - 1 < ntxf[1 - s]) begin
                    // STATIC release: the TX time of the block's last frame + LXB (MUT 2: 60 ns early)
                    trel = t_txf[1 - s][(bs[b] + bw[b] - 1) % 8192] + LXB_PS / 1000.0 - ((MUT == 2) ? 60.0 : 0.0);
                    if (PROBE ? bready[s][b % 2] : ($realtime >= trel)) begin
                        if (!bready[s][b % 2]) begin
                            sched_fail = sched_fail + 1;
                            if (sched_fail < 4) $display("XDIE_SCHED_FAIL die%0d block%0d not ready at its static release (LXB %0d ps)", s, b, LXB_PS);
                        end else if ($realtime - t_ready[s][b] < worst_slack) worst_slack = $realtime - t_ready[s][b];
                        rel_v[s] <= 1; rel_b[s] <= b[0]; sl = 0;
                    end
                end else if (sl >= 0) begin
                    slot_v[s] <= 1; slot_b[s] <= b[0]; slot_i[s] <= 6'(sl);
                    exc[exq_t % 4096] = cyc[s] + DRX; exs[exq_t % 4096] = 16'(bs[b] + sl); sdrv[exq_t % 4096] = cyc[s] + 1;
                    exq_t = exq_t + 1; sl = sl + 1;
                    if (sl == bw[b]) begin sl = -1; b = b + 1; end
                end
            end
            // COLL rx_expect, sampled on the same edge as the RX pin (MUT 3: die B expects the next sequence number)
            if (exq_h < exq_t && exc[exq_h % 4096] == cyc[s]) begin
                ex_v[s] <= 1; ex_seq[s] <= exs[exq_h % 4096] + ((MUT == 3 && s == 1) ? 16'd1 : 16'd0); exq_h = exq_h + 1;
            end
        end
        // landing of every peer frame at this endpoint's RX gearbox output (the elastic boundary): arrival-latency bounds
        always @(posedge ck[s]) if ((s == 0) ? sA.u_ep.f_v : sB.u_ep.f_v) begin
            tl = $realtime - t_txf[1 - s][narr % 8192];
            if (tl < lmin) lmin = tl;
            if (tl > lmax) lmax = tl;
            narr = narr + 1;
        end
        // probes: the block-ready time stamp, the drain->COLL pin edge distance (must equal DRX)
        integer npin = 0;
        always @(posedge ck[s]) begin
            if (rb < nb && bready[s][rb % 2] && !br_prev[rb % 2]) begin
                t_ready[s][rb] = $realtime;
                if (bs[rb] + bw[rb] - 1 < ntxf[1 - s] && $realtime - t_txf[1 - s][(bs[rb] + bw[rb] - 1) % 8192] > worst_ready_lat)
                    worst_ready_lat = $realtime - t_txf[1 - s][(bs[rb] + bw[rb] - 1) % 8192];
                rb = rb + 1;
            end
            br_prev = bready[s];
            if (r_rx_v[s]) begin
                // r_rx_v visible after this edge -> COLL samples it on the next edge (cyc + 1)
                if (drx_obs < 0) begin drx_obs = cyc[s] + 1 - sdrv[npin % 4096]; $display("XDIE_PROBE die%0d drain->COLL pin %0d edges (DRX %0d)", s, drx_obs, DRX); end
                if (cyc[s] + 1 - sdrv[npin % 4096] != DRX) drx_bad = drx_bad + 1;
                npin = npin + 1;
            end
        end
        // COLL publication: bit-exact, in order
        always @(posedge ck[s]) if (c_rx_v[s]) begin
            if (c_rx_f[s] !== flit(1 - s, nr)) begin errors = errors + 1; if (errors < 4) $display("XDIE_ERR die%0d frame %0d mismatch", s, nr); end
            for (int ii = 0; ii < NI; ii++) if (nr >= base[ii] && nr < base[ii] + P[ii]) begin
                if (nr == base[ii]) t_first[s][ii] = $realtime;
                t_last[s][ii] = $realtime; got[s][ii] = got[s][ii] + 1;
            end
            nr = nr + 1;
        end
    end

    // ---------------- control ----------------
    integer tmo = 0; real cn = 0.833333; reg okall;
    initial begin
        for (int i = 0; i < 12; i++) begin inst_go[i] = 0; got[0][i] = 0; got[1][i] = 0; end
        repeat (8) @(posedge ca); rst = 1;
        fork
            begin wait (up[0] && up[1]); end
            begin repeat (40000) @(posedge ca); end
        join_any
        if (!(up[0] && up[1])) begin $display("XDIE_HBM FAIL link never came up st=%b/%b", sta, stb); $finish; end
        @(negedge ca); epb[0] <= 1; @(negedge ca); epb[0] <= 0;
        @(negedge cb); epb[1] <= 1; @(negedge cb); epb[1] <= 0;
        repeat (64) @(posedge ca);
        start_go = 1;
        for (int n = 0; n < NI; n++) begin
            inst_go[n] = 1;
            // instances run one after another: each collective step is measured in isolation
            fork
                begin wait (got[0][n] == P[n] && got[1][n] == P[n]); end
                begin repeat (100000) @(posedge ca); tmo = 1; end
            join_any
            disable fork;
            if (tmo) begin $display("XDIE_HBM FAIL timeout instance %0d got %0d/%0d of %0d", n, got[0][n], got[1][n], P[n]); break; end
            repeat (32) @(posedge ca);
        end
        repeat (64) @(posedge ca);
        if (!tmo) for (int n = 0; n < NI; n++)
            $display("XDIE_INST %0d P=%0d A->B E=%0.1f first=%0.1f | B->A E=%0.1f first=%0.1f (1.2 GHz cycles: COLL wr issue -> last / first far COLL rx_v)",
                     n, P[n], (t_last[1][n] - t_issue[0][n]) / cn, (t_first[1][n] - t_issue[0][n]) / cn,
                     (t_last[0][n] - t_issue[1][n]) / cn, (t_first[0][n] - t_issue[1][n]) / cn);
        okall = !tmo && errors == 0 && sched_fail == 0 && drx_bad == 0 && !lf[0] && !lf[1] && !ef[0] && !ef[1] && up[0] && up[1];
        $display("XDIE_STATIC worst_ready_after_tx_last=%0.2f ns LXB=%0.2f ns worst_slack=%0.2f ns sched_fail=%0d drx_bad=%0d",
                 worst_ready_lat, LXB_PS / 1000.0, worst_slack, sched_fail, drx_bad);
        $display("XDIE_LAND arrival_after_tx min=%0.2f max=%0.2f ns LA=%0.2f ns GAPB=%0d probe=%0d", lmin, lmax, LA_PS / 1000.0, GAPB, PROBE);
        $display("XDIE_HBM MUT=%0d EPMUT_B=%0d RLY=%0d SWD=%0d NI=%0d errors=%0d link_fault=%b/%b cause=%h/%h ep_fault=%b/%b cause=%h/%h st=%b/%b %s",
                 MUT, EPMUT_B, RLY, SWD, NI, errors, lf[0], lf[1], lc[0], lc[1], ef[0], ef[1], ec[0], ec[1], sta, stb, okall ? "PASS" : "FAIL");
        $finish;
    end
endmodule
