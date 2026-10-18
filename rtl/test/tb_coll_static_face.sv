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
    parameter integer XS = 0, PHI = 0, NW = 240, START = 80, TOK_REG = 1
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
    generate for (f = 0; f < 2; f = f + 1) begin : g_face
        qfd_coll_static_face #(.FW(FW), .PHY(PHY), .L(L), .R(R), .PEER_R(PEER_R), .TOK_REG(TOK_REG)) u_face (
            .cal_ck(clk), .cal_lck(lck), .tx_wck(clk), .tx_rck(lck), .rx_wck(lck), .rx_rck(clk),
            .codec_ck({5{lck}}), .rst_n(rst_n),
            .tx_slot(send[f]), .peer_slot(send[1 - f]), .tx_valid(send[f]), .tx_data(f == 0 ? txd0 : txd1),
            .rx_valid(rxv[f]), .rx_data(rxd[f]),
            .phy_up(1'b1), .phy_rx_valid(prv[f]), .phy_rx(prx[f]),
            .phy_tx_valid(ptv[f]), .phy_tx(ptx[f]), .phy_tx_slot(ptslot[f]), .phy_rx_slot(prslot[f]),
            .cdc_fault(cdcf[f]), .epoch_abort(abort[f]), .fault_cause(cause[f]));
        tb_face_phy_pipe #(.W(PW), .L(PHY + XS)) u_phy (.clk(lck), .rst_n(rst_n), .v_in(ptv[f]), .d_in(ptx[f]),
            .v_out(prv[1 - f]), .d_out(prx[1 - f]));
    end endgenerate
    // receiver check: face 1 receives face 0's words (and face 0 face 1's) at exactly t + LAT, LAT = L - R
    localparam integer LAT = L - R;
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
        check(1, rxv[1], rxd[1], got1, sent0, tsend0[got1 < NW ? got1 : 0], word(0, got1));
        check(0, rxv[0], rxd[0], got0, sent1, tsend1[got0 < NW ? got0 : 0], word(1, got0));
        if ((|cdcf[0]) || abort[0] || (|cause[0]) || (|cdcf[1]) || abort[1] || (|cause[1])) begin
            faults = faults + 1;
            if (faults <= 4) $display("ERR fault at %0d cdc %b/%b abort %b cause %b/%b", cyc, cdcf[0], cdcf[1], abort,
                                      cause[0], cause[1]);
        end
    end
    initial begin
        wait (sent0 == NW && sent1 == NW);
        repeat (LAT + 40) @(posedge clk);
        $display("COLL_FACE_BENCH TOK_REG=%0d FW=%0d PHY=%0d L=%0d R=%0d PEER_R=%0d XS=%0d PHI=%0d words %0d %0d got %0d %0d latency %0d errors %0d faults %0d unexpected %0d",
                 TOK_REG, FW, PHY, L, R, PEER_R, XS, PHI, sent0, sent1, got1, got0, lat_seen, errors, faults, unexpected);
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
