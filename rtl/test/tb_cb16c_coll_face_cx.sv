`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// CB16c-COLL 10-22: LOCKSTEP bench of the regional-split collective face (qfd_coll_face_cx, rtl/physical/
// qwen_coll_cb16c_1022/) against the ORIGINAL face RTL (qfd_coll_static_face, the body of qfd_coll_face_<p>_pl).
// Two pairs run on the same clocks and the SAME compiled send schedule (tb_coll_static_face stimulus):
//   REF pair  = two original faces (profile + mirrored partner) joined by PHY pipes, latency L0
//   DUT pair  = two split faces (face 0 = the HARD profile body, face 1 = mirrored partner) joined by identical pipes
// Checked every cycle after reset:
//   (1) DUT functional: every word arrives at the receiver's collective at exactly t + L0 + 2, exact value, no
//       unexpected rx_valid, zero faults (4 CDC, epoch_abort, 8 codec causes) on both DUT faces;
//   (2) REF functional at t + L0 (the reference itself is a passing face);
//   (3) lockstep, per face: DUT phy_tx_valid / phy_tx_slot / phy_rx_slot (t) == REF (t-1); DUT phy_tx (t) == REF phy_tx
//       (t-1) whenever valid; DUT rx_valid (t) == REF rx_valid (t-2) and rx_data equal when valid; DUT faults == REF.
// Clocks as tb_coll_static_face: core roots (cal_ck, tx_wck, rx_rck + entries cal_ck_t*, rx_rck_r*) on clk, link roots
// on lck (PHI 1 = 0.25 T later), PHY region (codec0p + entries codec0p_*) on pck (PPH/8 T after lck).
// ---------------------------------------------------------------------------
module tb_cb16c_coll_face_cx #(
    parameter integer PHY = 350, L0 = 381, R = 0, PEER_R = 5, HARD = 1,
    parameter integer PHI = 0, PPH = 0, NW = 240, START = 80, PLD = 2, PLK = 1,
    parameter integer FW = 546   // CB16c-COLL2-SR: 514 = the R face (qfd_coll_face_r_cx)
) ();
    localparam integer PW = FW + 51, XL = 2;
    localparam real T = 0.8333333;
    reg clk = 0, lck = 0, pck = 0;
    always #(T / 2) clk = ~clk;
    generate if (PHI == 0) begin : g_phi0
        always @(clk) lck = clk;
    end else begin : g_phi1
        always @(clk) lck <= #(T / 4) clk;
    end endgenerate
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
    function automatic [15:0] lfsr(input [15:0] x);
        lfsr = {x[14:0], x[15] ^ x[13] ^ x[12] ^ x[10]};
    endfunction
    reg [1:0] send = 0;
    integer sent0 = 0, sent1 = 0, run0 = 0, run1 = 0;
    reg [15:0] lf0 = 16'hACE1, lf1 = 16'h1D2B;
    integer tsend0 [0:NW-1];
    integer tsend1 [0:NW-1];
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

    // ---- per pair p (0 = REF original, 1 = DUT split), per face f ----
    wire [1:0] rxv [0:1], ptv [0:1], prv [0:1], ptslot [0:1], prslot [0:1], abort [0:1], rxv_c [0:1];
    wire [FW-1:0] rxd [0:1][0:1];
    wire [FW-1:0] rxd_c [0:1][0:1];
    wire [PW-1:0] ptx [0:1][0:1];
    wire [PW-1:0] prx [0:1][0:1];
    wire [3:0] cdcf [0:1][0:1];
    wire [7:0] cause [0:1][0:1];
    genvar p, f;
    generate for (p = 0; p < 2; p = p + 1) begin : g_pair
        for (f = 0; f < 2; f = f + 1) begin : g_face
            localparam integer RF = (f == 0) ? R : PEER_R;
            localparam integer PRF = (f == 0) ? PEER_R : R;
            wire f_ts, f_ps, f_tv, f_rv;
            wire [FW-1:0] f_td, f_rd;
            tb_face_relay #(.W(FW + 3), .N(RF)) u_rly_in (.clk(clk), .d_in({send[f], send[1 - f], send[f], f == 0 ? txd0 : txd1}),
                .d_out({f_ts, f_ps, f_tv, f_td}));
            if (p == 0) begin : g_ref
                qfd_coll_static_face #(.FW(FW), .PHY(PHY), .L(L0), .R(RF), .PEER_R(PRF), .TOK_REG(1), .SAFE(1),
                    .PLAND(1), .PLD(PLD), .PLK(PLK)) u_face (
                    .cal_ck(clk), .cal_lck(lck), .tx_wck(clk), .tx_rck(lck), .rx_wck(lck), .rx_rck(clk),
                    .codec_ck({5{lck}}), .codec_phy_ck(pck), .rst_n(rst_n),
                    .tx_slot(f_ts), .peer_slot(f_ps), .tx_valid(f_tv), .tx_data(f_td),
                    .rx_valid(f_rv), .rx_data(f_rd),
                    .phy_up(1'b1), .phy_rx_valid(prv[p][f]), .phy_rx(prx[p][f]),
                    .phy_tx_valid(ptv[p][f]), .phy_tx(ptx[p][f]), .phy_tx_slot(ptslot[p][f]), .phy_rx_slot(prslot[p][f]),
                    .cdc_fault(cdcf[p][f]), .epoch_abort(abort[p][f]), .fault_cause(cause[p][f]));
            end else if (FW == 514) begin : g_dut_r
                qfd_coll_face_r_cx #(.PHY(PHY), .L(L0 + XL), .R(RF), .PEER_R(PRF), .PLD(PLD), .PLK(PLK),
                    .HARD(f == 0 ? HARD : 0)) u_face (
                    .cal_ck(clk), .cal_lck(lck), .tx_wck(clk), .tx_rck(lck), .rx_wck(lck), .rx_rck(clk),
                    .codec0(lck), .codec1(lck), .codec2(lck), .codec3(lck), .codec4(lck), .codec0p(pck), .rst_n(rst_n),
                    .cal_ck_t0(clk), .cal_ck_t1(clk), .rx_rck_r0(clk), .rx_rck_r1(clk),
                    .codec0p_t0(pck), .codec0p_t1(pck), .codec0p_t2(pck), .codec0p_t3(pck), .codec0p_t4(pck),
                    .codec0p_r0(pck), .codec0p_r1(pck), .codec0p_r2(pck), .codec0p_r3(pck), .codec0p_r4(pck),
                    .tx_slot(f_ts), .peer_slot(f_ps), .tx_valid(f_tv), .tx_data(f_td),
                    .rx_valid(f_rv), .rx_data(f_rd),
                    .phy_up(1'b1), .phy_rx_valid(prv[p][f]), .phy_rx(prx[p][f]),
                    .phy_tx_valid(ptv[p][f]), .phy_tx(ptx[p][f]), .phy_tx_slot(ptslot[p][f]), .phy_rx_slot(prslot[p][f]),
                    .cdc_fault(cdcf[p][f]), .epoch_abort(abort[p][f]), .fault_cause(cause[p][f]));
            end else begin : g_dut
                qfd_coll_face_cx #(.PHY(PHY), .L(L0 + XL), .R(RF), .PEER_R(PRF), .PLD(PLD), .PLK(PLK),
                    .HARD(f == 0 ? HARD : 0)) u_face (
                    .cal_ck(clk), .cal_lck(lck), .tx_wck(clk), .tx_rck(lck), .rx_wck(lck), .rx_rck(clk),
                    .codec0(lck), .codec1(lck), .codec2(lck), .codec3(lck), .codec4(lck), .codec0p(pck), .rst_n(rst_n),
                    .cal_ck_t0(clk), .cal_ck_t1(clk), .cal_ck_t2(clk), .rx_rck_r0(clk), .rx_rck_r1(clk), .rx_rck_r2(clk),
                    .codec0p_t0(pck), .codec0p_t1(pck), .codec0p_t2(pck), .codec0p_r0(pck), .codec0p_r1(pck), .codec0p_r2(pck),
                    .tx_slot(f_ts), .peer_slot(f_ps), .tx_valid(f_tv), .tx_data(f_td),
                    .rx_valid(f_rv), .rx_data(f_rd),
                    .phy_up(1'b1), .phy_rx_valid(prv[p][f]), .phy_rx(prx[p][f]),
                    .phy_tx_valid(ptv[p][f]), .phy_tx(ptx[p][f]), .phy_tx_slot(ptslot[p][f]), .phy_rx_slot(prslot[p][f]),
                    .cdc_fault(cdcf[p][f]), .epoch_abort(abort[p][f]), .fault_cause(cause[p][f]));
            end
            assign rxv[p][f] = f_rv;
            assign rxd[p][f] = f_rd;
            tb_face_relay #(.W(FW + 1), .N(RF)) u_rly_out (.clk(clk), .d_in({f_rv, f_rd}), .d_out({rxv_c[p][f], rxd_c[p][f]}));
            tb_face_phy_pipe #(.W(PW), .L(PHY)) u_phy (.clk(pck), .rst_n(rst_n), .v_in(ptv[p][f]), .d_in(ptx[p][f]),
                .v_out(prv[p][1 - f]), .d_out(prx[p][1 - f]));
        end
    end endgenerate

    // ---- (1)(2) functional checks at the collective ----
    integer got [0:1][0:1];             // got[p][receiver]
    integer errors [0:1], faults [0:1], unexpected [0:1], lat_seen [0:1];
    integer lk_err = 0, lk_cmp = 0, lk_rx = 0, lk_tx = 0;
    initial begin
        got[0][0] = 0; got[0][1] = 0; got[1][0] = 0; got[1][1] = 0;
        errors[0] = 0; errors[1] = 0; faults[0] = 0; faults[1] = 0; unexpected[0] = 0; unexpected[1] = 0;
        lat_seen[0] = -1; lat_seen[1] = -1;
    end
    task automatic check(input integer p, input integer r, input v, input [FW-1:0] d, input integer nsent,
                         input integer ts, input [FW-1:0] exp_d);
        integer lat;
        begin
            lat = (p == 0) ? L0 : L0 + XL;
            if (v) begin
                if (got[p][r] >= nsent) begin
                    unexpected[p] = unexpected[p] + 1;
                    if (unexpected[p] <= 4) $display("ERR pair %0d face %0d unexpected rx_valid at %0d", p, r, cyc);
                end else begin
                    if (lat_seen[p] < 0) lat_seen[p] = cyc - ts;
                    if (cyc != ts + lat || d !== exp_d) begin
                        errors[p] = errors[p] + 1;
                        if (errors[p] <= 6)
                            $display("ERR pair %0d face %0d word %0d at %0d (sent %0d, expected %0d) data %s", p, r, got[p][r],
                                     cyc, ts, ts + lat, d === exp_d ? "ok" : "BAD");
                    end
                    got[p][r] = got[p][r] + 1;
                end
            end else if (got[p][r] < nsent && cyc > ts + lat) begin
                errors[p] = errors[p] + 1;
                if (errors[p] <= 6) $display("ERR pair %0d face %0d word %0d missing (expected %0d)", p, r, got[p][r], ts + lat);
                got[p][r] = got[p][r] + 1;
            end
        end
    endtask
    // ---- (3) lockstep history of the REF pair ----
    reg [1:0] h_ptv [1:2], h_pts [1:2], h_prs [1:2], h_rxv [1:2];
    reg [PW-1:0] h_ptx [1:2][0:1];
    reg [FW-1:0] h_rxd [1:2][0:1];
    integer k;
    always @(posedge clk) begin
        h_ptv[2] <= h_ptv[1]; h_pts[2] <= h_pts[1]; h_prs[2] <= h_prs[1]; h_rxv[2] <= h_rxv[1];
        h_ptv[1] <= ptv[0]; h_pts[1] <= ptslot[0]; h_prs[1] <= prslot[0]; h_rxv[1] <= rxv[0];
        for (k = 0; k < 2; k = k + 1) begin
            h_ptx[2][k] <= h_ptx[1][k]; h_ptx[1][k] <= ptx[0][k];
            h_rxd[2][k] <= h_rxd[1][k]; h_rxd[1][k] <= rxd[0][k];
        end
    end
    integer w;
    always @(posedge clk) if (rst_n) begin
        check(0, 1, rxv_c[0][1], rxd_c[0][1], sent0, tsend0[got[0][1] < NW ? got[0][1] : 0], word(0, got[0][1]));
        check(0, 0, rxv_c[0][0], rxd_c[0][0], sent1, tsend1[got[0][0] < NW ? got[0][0] : 0], word(1, got[0][0]));
        check(1, 1, rxv_c[1][1], rxd_c[1][1], sent0, tsend0[got[1][1] < NW ? got[1][1] : 0], word(0, got[1][1]));
        check(1, 0, rxv_c[1][0], rxd_c[1][0], sent1, tsend1[got[1][0] < NW ? got[1][0] : 0], word(1, got[1][0]));
        for (w = 0; w < 2; w = w + 1) begin
            if ((|cdcf[w][0]) || abort[w][0] || (|cause[w][0]) || (|cdcf[w][1]) || abort[w][1] || (|cause[w][1])) begin
                faults[w] = faults[w] + 1;
                if (faults[w] <= 4) $display("ERR pair %0d fault at %0d cdc %b/%b abort %b cause %b/%b", w, cyc,
                                             cdcf[w][0], cdcf[w][1], abort[w], cause[w][0], cause[w][1]);
            end
        end
        if (cyc > 40) begin
            lk_cmp = lk_cmp + 1;
            for (w = 0; w < 2; w = w + 1) begin
                if (ptv[1][w] !== h_ptv[1][w] || ptslot[1][w] !== h_pts[1][w] || prslot[1][w] !== h_prs[1][w]
                    || (h_ptv[1][w] === 1'b1 && ptx[1][w] !== h_ptx[1][w]) || rxv[1][w] !== h_rxv[2][w]
                    || (h_rxv[2][w] === 1'b1 && rxd[1][w] !== h_rxd[2][w])
                    || cdcf[1][w] !== cdcf[0][w] || abort[1][w] !== abort[0][w] || cause[1][w] !== cause[0][w]) begin
                    lk_err = lk_err + 1;
                    if (lk_err <= 6)
                        $display("ERR lockstep face %0d at %0d: ptv %b/%b pts %b/%b prs %b/%b ptx %s rxv %b/%b rxd %s", w, cyc,
                                 ptv[1][w], h_ptv[1][w], ptslot[1][w], h_pts[1][w], prslot[1][w], h_prs[1][w],
                                 (h_ptv[1][w] !== 1'b1 || ptx[1][w] === h_ptx[1][w]) ? "ok" : "BAD",
                                 rxv[1][w], h_rxv[2][w], (h_rxv[2][w] !== 1'b1 || rxd[1][w] === h_rxd[2][w]) ? "ok" : "BAD");
                end
                if (h_ptv[1][w] === 1'b1) lk_tx = lk_tx + 1;
                if (h_rxv[2][w] === 1'b1) lk_rx = lk_rx + 1;
            end
        end
    end
    initial begin
        wait (sent0 == NW && sent1 == NW);
        repeat (L0 + XL + 40) @(posedge clk);
        $display("CB16C_COLL_FACE_CX FW=%0d HARD=%0d PHY=%0d L0=%0d R=%0d PEER_R=%0d PHI=%0d PPH=%0d words %0d %0d | REF got %0d %0d lat %0d err %0d flt %0d unx %0d | DUT got %0d %0d lat %0d err %0d flt %0d unx %0d | lockstep cycles %0d tx frames %0d rx words %0d mismatches %0d",
                 FW, HARD, PHY, L0, R, PEER_R, PHI, PPH, sent0, sent1, got[0][1], got[0][0], lat_seen[0], errors[0], faults[0],
                 unexpected[0], got[1][1], got[1][0], lat_seen[1], errors[1], faults[1], unexpected[1], lk_cmp, lk_tx, lk_rx, lk_err);
        if (errors[0] == 0 && faults[0] == 0 && unexpected[0] == 0 && got[0][0] == NW && got[0][1] == NW
            && errors[1] == 0 && faults[1] == 0 && unexpected[1] == 0 && got[1][0] == NW && got[1][1] == NW
            && lat_seen[1] == L0 + XL && lk_err == 0 && lk_tx > 0 && lk_rx > 0)
            $display("CB16C_COLL_FACE_CX PASS");
        else
            $display("CB16C_COLL_FACE_CX FAIL");
        $finish;
    end
endmodule
