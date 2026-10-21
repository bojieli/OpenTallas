`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Q-DIE11-COLL 2026-10-18: production-shape bench of ONE hardened collective face leaf, qfd_coll_static_face
// (rtl/physical/ot_qfd_coll_static_face.sv), the element the compute-die io_collective owes before its parent can be
// kitted (HANDOFF 0ea item 3).  Two identical faces A and B (SerDes profile: FW 546, PHY 339 link cycles, L 376 core
// cycles, R / PEER_R 0) are joined through fixed-latency PHY pipes (PHY + XS link cycles, the off-chip PHY model of
// tb_coll_tp8_static_links).  Both directions run at once with every-cycle bursts.
// Clocks: the core roots (cal_ck, tx_wck, rx_rck) on clk; the link roots (cal_lck, tx_rck, rx_wck, codec_ck[0..4])
// on lck, the PHY's FDI clock.  lck is mesochronous with clk (one PLL, 833.3 ps): PHI 0 = same edge, PHI 1 = the
// link edge 0.25 T after the core edge (both phases exercise the related-clock token crossings).
// Compiled schedule only: the sender's tx_slot = tx_valid at its compiled core cycle t, the receiver's peer_slot = the
// peer's send slot at the same compiled cycle t (the peer runs the identical calendar).  Checked: every word arrives
// on the receiver's rx_valid/rx_data at EXACTLY t + L - R with the exact value, no unexpected rx_valid, and zero
// faults (4 CDC w/r faults, epoch_abort, 8 codec fault causes) on both faces.  Negative controls (expect FAIL):
// +define+OT_LCAL_MUT_RX_EARLY (RX CDC read one core cycle early), +define+OT_STATIC_MUT_LATENCY (CDC read pipe one
// edge short), XS=1 (a PHY one link cycle longer than compiled).  TOK_REG 1 (default) = the hardened-leaf
// configuration (one pin register per face input, compensated calendar); TOK_REG 0 = the original face.
// ---------------------------------------------------------------------------
module tb_coll_static_face #(
    parameter integer FW = 546, PHY = 339, L = 376, R = 0, PEER_R = 0,
    parameter integer XS = 0, PHI = 0, NW = 240, START = 80, TOK_REG = 1, SAFE = 0,
    // QW-COLLIO2: PLAND=1 = codec PHY pins on their own region clock pck (= lck delayed by PPH/8 T), landed by rings
    parameter integer PLAND = 0, PLD = 2, PLK = 1, PPH = 0
) ();
    localparam integer PW = FW + 51;
    localparam real T = 0.8333333;
    reg clk = 0, lck = 0;
    always #(T / 2) clk = ~clk;
    generate if (PHI == 0) begin : g_phi0
        always @(clk) lck = clk;
    end else begin : g_phi1
        always @(clk) lck <= #(T / 4) clk;
    end endgenerate
    reg pck = 0;
    generate if (PPH == 0) begin : g_pph0
        always @(lck) pck = lck;
    end else begin : g_pph
        always @(lck) pck <= #(T * PPH / 8.0) lck;
    end endgenerate
    reg [4:0] rcnt = 0;
    wire rst_n = rcnt[4];
    integer cyc = 0;
    always @(posedge clk) begin
        if (!rst_n) rcnt <= rcnt + 1'b1;
        cyc <= cyc + 1;
    end
    // compiled send schedule: bursts of 1..16 words with 0..7 idle cycles, from a fixed LFSR (both faces differ)
    function automatic [FW-1:0] word(input integer face, input integer k);
        integer i;
        reg [31:0] x;
        begin
            x = 32'h9E3779B9 ^ (face * 32'h85EBCA6B) ^ k;
            for (i = 0; i < FW; i = i + 1) begin
                if (i % 32 == 0) begin x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5); end
                word[i] = x[i % 32];
            end
        end
    endfunction
    // per-face compiled send schedule; tsend = the compiled core cycle of each word (the edge that samples it)
    reg [1:0] send = 0;
    integer sent0 = 0, sent1 = 0, run0 = 0, run1 = 0;
    reg [15:0] lf0 = 16'hACE1, lf1 = 16'h1D2B;
    integer tsend0 [0:NW-1];
    integer tsend1 [0:NW-1];
    function automatic [15:0] lfsr(input [15:0] x);
        lfsr = {x[14:0], x[15] ^ x[13] ^ x[12] ^ x[10]};
    endfunction
    always @(posedge clk) begin
        send <= 2'b00;
        if (cyc >= START - 1) begin
            lf0 <= lfsr(lf0); lf1 <= lfsr(lf1);
            if (sent0 + send[0] < NW) begin
                if (run0 > 0) begin send[0] <= 1'b1; run0 <= run0 - 1; end
                else if (lf0[2:0] == 3'd0) begin send[0] <= 1'b1; run0 <= lf0[7:4]; end
            end
            if (sent1 + send[1] < NW) begin
                if (run1 > 0) begin send[1] <= 1'b1; run1 <= run1 - 1; end
                else if (lf1[2:0] == 3'd0) begin send[1] <= 1'b1; run1 <= lf1[7:4]; end
            end
        end
        if (send[0]) begin tsend0[sent0] <= cyc; sent0 <= sent0 + 1; end
        if (send[1]) begin tsend1[sent1] <= cyc; sent1 <= sent1 + 1; end
    end
    wire [FW-1:0] txd0 = send[0] ? word(0, sent0) : {FW{1'b0}};
    wire [FW-1:0] txd1 = send[1] ? word(1, sent1) : {FW{1'b0}};
    wire [1:0] rxv, ptv, prv;
    wire [FW-1:0] rxd [0:1];
    wire [PW-1:0] ptx [0:1], prx [0:1];
    wire [3:0] cdcf [0:1];
    wire [1:0] abort;
    wire [7:0] cause [0:1];
    wire [1:0] ptslot, prslot;
    genvar f;
    // QW-C3-COLLIO 10-21: on-die relay stages R (core domain, each direction) between the collective and the face, as in
    // production (qfd_coll_static_relay rows): tx_slot/tx_valid/tx_data/peer_slot reach the face R cycles late and
    // rx_valid/rx_data reach the collective R cycles after the face pin.  Face 0 = the profile (R, PEER_R); face 1 = its
    // mirrored partner (R = PEER_R, PEER_R = R) so asymmetric S0/S2 profiles meet a consistent peer.  Checked at the
    // collective: t + L.  R = PEER_R = 0 is the previous bench exactly (zero-length relays).
    wire [1:0] rxv_c;
    wire [FW-1:0] rxd_c [0:1];
    generate for (f = 0; f < 2; f = f + 1) begin : g_face
        localparam integer RF = (f == 0) ? R : PEER_R;
        localparam integer PRF = (f == 0) ? PEER_R : R;
        wire f_ts, f_ps, f_tv;
        wire [FW-1:0] f_td;
        tb_face_relay #(.W(FW + 3), .N(RF)) u_rly_in (.clk(clk), .d_in({send[f], send[1 - f], send[f], f == 0 ? txd0 : txd1}),
            .d_out({f_ts, f_ps, f_tv, f_td}));
        wire f_rv;
        wire [FW-1:0] f_rd;
        qfd_coll_static_face #(.FW(FW), .PHY(PHY), .L(L), .R(RF), .PEER_R(PRF), .TOK_REG(TOK_REG), .SAFE(SAFE),
            .PLAND(PLAND), .PLD(PLD), .PLK(PLK)) u_face (
            .cal_ck(clk), .cal_lck(lck), .tx_wck(clk), .tx_rck(lck), .rx_wck(lck), .rx_rck(clk),
            .codec_ck({5{lck}}), .codec_phy_ck(pck), .rst_n(rst_n),
            .tx_slot(f_ts), .peer_slot(f_ps), .tx_valid(f_tv), .tx_data(f_td),
            .rx_valid(f_rv), .rx_data(f_rd),
            .phy_up(1'b1), .phy_rx_valid(prv[f]), .phy_rx(prx[f]),
            .phy_tx_valid(ptv[f]), .phy_tx(ptx[f]), .phy_tx_slot(ptslot[f]), .phy_rx_slot(prslot[f]),
            .cdc_fault(cdcf[f]), .epoch_abort(abort[f]), .fault_cause(cause[f]));
        assign rxv[f] = f_rv;
        assign rxd[f] = f_rd;
        tb_face_relay #(.W(FW + 1), .N(RF)) u_rly_out (.clk(clk), .d_in({f_rv, f_rd}), .d_out({rxv_c[f], rxd_c[f]}));
        tb_face_phy_pipe #(.W(PW), .L(PHY + XS)) u_phy (.clk(PLAND ? pck : lck), .rst_n(rst_n), .v_in(ptv[f]), .d_in(ptx[f]),
            .v_out(prv[1 - f]), .d_out(prx[1 - f]));
    end endgenerate
    // receiver check (at the collective, after the R output relays): face 1's collective receives face 0's words (and
    // face 0's face 1's) at exactly t + LAT, LAT = L (= L - R at the face pin + R relays)
    localparam integer LAT = L;
    integer got0 = 0, got1 = 0;          // words received BY face 0 (from face 1) / BY face 1 (from face 0)
    integer errors = 0, faults = 0, unexpected = 0, lat_seen = -1;
    task automatic check(input integer r, input v, input [FW-1:0] d, inout integer got, input integer nsent,
                         input integer ts, input [FW-1:0] exp_d);
        begin
            if (v) begin
                if (got >= nsent) begin
                    unexpected = unexpected + 1;
                    if (unexpected <= 4) $display("ERR face %0d unexpected rx_valid at %0d", r, cyc);
                end else begin
                    if (lat_seen < 0) lat_seen = cyc - ts;
                    if (cyc != ts + LAT || d !== exp_d) begin
                        errors = errors + 1;
                        if (errors <= 6)
                            $display("ERR face %0d word %0d at %0d (sent %0d, expected %0d) data %s", r, got, cyc, ts,
                                     ts + LAT, d === exp_d ? "ok" : "BAD");
                    end
                    got = got + 1;
                end
            end else if (got < nsent && cyc > ts + LAT) begin
                errors = errors + 1;
                if (errors <= 6) $display("ERR face %0d word %0d missing (expected %0d)", r, got, ts + LAT);
                got = got + 1;
            end
        end
    endtask
    always @(posedge clk) if (rst_n) begin
        check(1, rxv_c[1], rxd_c[1], got1, sent0, tsend0[got1 < NW ? got1 : 0], word(0, got1));
        check(0, rxv_c[0], rxd_c[0], got0, sent1, tsend1[got0 < NW ? got0 : 0], word(1, got0));
        if ((|cdcf[0]) || abort[0] || (|cause[0]) || (|cdcf[1]) || abort[1] || (|cause[1])) begin
            faults = faults + 1;
            if (faults <= 4) $display("ERR fault at %0d cdc %b/%b abort %b cause %b/%b", cyc, cdcf[0], cdcf[1], abort,
                                      cause[0], cause[1]);
        end
    end
    initial begin
        wait (sent0 == NW && sent1 == NW);
        repeat (LAT + 40) @(posedge clk);
        $display("COLL_FACE_BENCH PLAND=%0d PLD=%0d PLK=%0d PPH=%0d TOK_REG=%0d FW=%0d PHY=%0d L=%0d R=%0d PEER_R=%0d XS=%0d PHI=%0d words %0d %0d got %0d %0d latency %0d errors %0d faults %0d unexpected %0d",
                 PLAND, PLD, PLK, PPH, TOK_REG, FW, PHY, L, R, PEER_R, XS, PHI, sent0, sent1, got1, got0, lat_seen, errors, faults, unexpected);
        if (errors == 0 && faults == 0 && unexpected == 0 && got0 == NW && got1 == NW)
            $display("COLL_STATIC_FACE PASS");
        else
            $display("COLL_STATIC_FACE FAIL");
        $finish;
    end
endmodule

// PHY model: fixed-latency register pipe of the codec frame (off-chip, modelled), as tb_coll_tp8_static_links
module tb_face_phy_pipe #(parameter integer W = 597, parameter integer L = 14) (
    input wire clk, input wire rst_n, input wire v_in, input wire [W-1:0] d_in,
    output wire v_out, output wire [W-1:0] d_out);
    reg [L-1:0] vp = 0;
    reg [W-1:0] dm [0:L-1];
    integer wp = 0;
    always @(posedge clk) begin
        if (!rst_n) vp <= 0; else vp <= {vp[L-2:0], v_in};
        dm[wp] <= d_in;
        wp <= (wp == L - 1) ? 0 : wp + 1;
    end
    assign v_out = vp[L-1];
    assign d_out = dm[wp];
endmodule

// QW-C3-COLLIO 10-21: on-die relay row model, N core-cycle register pipe (N = 0: wire); no reset (datapath + valid
// relays, as qfd_coll_static_relay with an unreset datapath: valid is 0 from the tb before START).
module tb_face_relay #(parameter integer W = 1, parameter integer N = 0) (
    input wire clk, input wire [W-1:0] d_in, output wire [W-1:0] d_out);
    generate if (N == 0) begin : g_w
        assign d_out = d_in;
    end else begin : g_p
        reg [W-1:0] p [0:N-1];
        integer i;
        initial for (i = 0; i < N; i = i + 1) p[i] = {W{1'b0}};
        always @(posedge clk) begin
            p[0] <= d_in;
            for (i = 1; i < N; i = i + 1) p[i] <= p[i - 1];
        end
        assign d_out = p[N - 1];
    end endgenerate
endmodule
