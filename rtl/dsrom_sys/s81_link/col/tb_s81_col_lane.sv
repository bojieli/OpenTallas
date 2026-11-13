`timescale 1ps/1fs
// tb_s81_col_lane (HARD-S81-SERDES-1 2026-11-13): lock-step proof of the ot_pdie_serdes_col LANE rows (LANE_PIN / LANE_TXA /
// LANE_RXI / LANE_RXO, ot_pdie_serdes_col.sv) against the same column with all four at 0 (u_o), one elaboration, LOCKSAFE=1,
// HOLD_EDGES=64, the same tx beats, the same PMA RX lane (a reference ot_pdie_serdes peer, 300 ppm slow, one bit error in
// about every second word), the same pma_lock.
//   TX  : pma_tx(new, t + PIN + TXA) == pma_tx(old, t) on every clk edge whose window [t - 4, t + PIN + TXA] is outside reset.
//   RCK : {q_v, q_first, q_unc, q_nerr, q_seq, q_d, lock} of the decoder (new, e + RXI) == (old, e) on every pma_rck edge
//         outside reset: the whole recovered-clock domain is the old one RXI edges later.
//   RX  : identical in-order non-IDLE beat sequence at the rx ports, exact payloads, >= NB - 400 beats, final st 2'b10.
//   Epochs: cold reset, warm die reset, PMA lock drop (the LOCKSAFE sequencer), warm die reset, then the RX run.
//   XTX / XRX (bench): expected TX / RCK shift offsets; a wrong expectation must FAIL (the checks have teeth).
//   Mutants (must FAIL): MUT 8 (one u_txl row short), 9 (rck reset not moved with the RXI rows), 10 (encoder reset not
//   moved with the PIN rows).
module tb_s81_col_lane;
    parameter integer PIN = 3, TXA = 4, RXI = 4, RXO = 3, MUT = 0, XTX = 0, XRX = 0, NB = 6000;
    localparam integer DT = PIN + TXA + XTX - ((MUT == 8) ? 0 : 0);
    localparam integer DR = RXI + XRX;
    reg ca = 0, cb = 0, rst = 0, lock = 1;
    always #416.5 ca = ~ca;
    always #416.62495 cb = ~cb;
    function automatic [511:0] beat(input integer n);
        beat = {32'(n), 32'(n * 7 + 3), 32'(n ^ 32'h5A5A), 384'h0, 30'(n), 2'b00} ^ {64'h0, {448{n[0]}}} & ~512'h3;
    endfunction
    reg [511:0] tx_s = 512'd2;
    wire [511:0] rx_o, rx_n, rx_p; wire [1:0] st_o, st_n, st_p;
    wire [543:0] pt_o, pt_n, pt_p; wire tc_o, tc_n, tc_p; reg [543:0] pt_p_e;
    ot_pdie_serdes_col #(.LOCKSAFE(1), .HOLD_EDGES(64), .LANE_PIN(0), .LANE_TXA(0), .LANE_RXI(0), .LANE_RXO(0)) u_o (
        .clk(ca), .rst(rst), .tx(tx_s), .rx(rx_o), .st(st_o), .pma_tx(pt_o), .pma_tck(tc_o), .pma_rx(pt_p_e), .pma_rck(tc_p),
        .pma_lock(lock));
    ot_pdie_serdes_col #(.LOCKSAFE(1), .HOLD_EDGES(64), .LANE_PIN(PIN), .LANE_TXA(TXA), .LANE_RXI(RXI), .LANE_RXO(RXO),
                         .MUT(MUT)) u_n (
        .clk(ca), .rst(rst), .tx(tx_s), .rx(rx_n), .st(st_n), .pma_tx(pt_n), .pma_tck(tc_n), .pma_rx(pt_p_e), .pma_rck(tc_p),
        .pma_lock(lock));
    reg [511:0] tx_p = 512'd2;
    ot_pdie_serdes u_p (.clk(cb), .rst(rst), .tx(tx_p), .rx(rx_p), .st(st_p), .pma_tx(pt_p), .pma_tck(tc_p), .pma_rx(pt_o),
        .pma_rck(tc_o));
    reg err_on = 0; integer err_bit = 0;
    always @* begin pt_p_e = pt_p; if (err_on) pt_p_e[err_bit] = ~pt_p[err_bit]; end
    always @(posedge tc_p) begin err_on <= ($urandom % 2) == 0; err_bit <= $urandom % 544; end
    integer cyc = 0;
    always @(negedge ca) begin
        cyc = cyc + 1;
        tx_s <= (cyc % 256 == 0) ? 512'd2 : beat(cyc * 13 + 5);
    end
    integer sent = 0, pc = 0;
    always @(negedge cb) begin
        pc = pc + 1;
        if (pc > 200 && sent < NB) begin
            if (pc % 256 == 0) tx_p <= 512'd2; else begin tx_p <= beat(sent); sent = sent + 1; end
        end else tx_p <= 512'd2;
    end
    // ---- TX lock-step (clk): history of the old lane and of "out of reset" (die reset high, lock high, old TX side released)
    localparam integer HN = 32;
    reg [543:0] pt_h [0:HN-1]; reg [HN-1:0] ok_h = 0; integer i1;
    integer tx_chk = 0, tx_bad = 0;
    wire tx_live = rst && lock && u_o.rn_te && u_n.rn_te;
    always @(posedge ca) begin
        #1;
        for (i1 = HN - 1; i1 > 0; i1 = i1 - 1) pt_h[i1] = pt_h[i1 - 1];
        pt_h[0] = pt_o; ok_h = {ok_h[HN-2:0], tx_live};
        if (&ok_h[DT+20:0]) begin
            if (pt_n !== pt_h[DT]) begin tx_bad = tx_bad + 1; if (tx_bad < 4) $display("TX lock-step mismatch at cyc %0d", cyc); end
            tx_chk = tx_chk + 1;
        end
    end
    // ---- RCK lock-step (pma_rck): decoder outputs
    localparam integer QW = 1 + 1 + 1 + 5 + 8 + 512 + 1;
    wire [QW-1:0] qo = {u_o.q_v, u_o.q_first, u_o.q_unc, u_o.q_nerr, u_o.q_seq, u_o.q_d, u_o.lock};
    wire [QW-1:0] qn = {u_n.q_v, u_n.q_first, u_n.q_unc, u_n.q_nerr, u_n.q_seq, u_n.q_d, u_n.lock};
    reg [QW-1:0] q_h [0:HN-1]; reg [HN-1:0] rk_h = 0; integer i2;
    integer rk_chk = 0, rk_bad = 0, rk_v = 0;
    wire rk_live = rst && lock && u_o.rn_r && u_n.rn_r;
    always @(posedge tc_p) begin
        #1;
        for (i2 = HN - 1; i2 > 0; i2 = i2 - 1) q_h[i2] = q_h[i2 - 1];
        q_h[0] = qo; rk_h = {rk_h[HN-2:0], rk_live};
        if (&rk_h[DR+4:0]) begin
            if (qn !== q_h[DR]) begin rk_bad = rk_bad + 1; if (rk_bad < 4) $display("RCK lock-step mismatch at %0t", $time); end
            rk_chk = rk_chk + 1; if (qn[QW-1]) rk_v = rk_v + 1;
        end
    end
    // ---- RX beat sequences (clk)
    integer go = 0, gn = 0, bo = 0, bn = 0, eq_bad = 0, run = 0;
    reg [511:0] seq_o [0:NB+16];
    reg [511:0] seq_n [0:NB+16];
    always @(posedge ca) if (run) begin
        if (!(rx_o[1] && !rx_o[0])) begin if (go <= NB + 16) seq_o[go] = rx_o; go = go + 1; end
        if (!(rx_n[1] && !rx_n[0])) begin if (gn <= NB + 16) seq_n[gn] = rx_n; gn = gn + 1; end
    end
    // ---- reset behaviour of the new column: RXO + 2 edges after the die reset falls rx is IDLE and st is 0
    reg [15:0] rl_h = 16'hffff; integer lf_chk = 0, lf_bad = 0;
    always @(posedge ca) begin
        #2; rl_h = {rl_h[14:0], rst};
        if (rl_h[RXO+3:0] == 0) begin
            if (rx_n !== 512'd2 || st_n !== 2'b00) lf_bad = lf_bad + 1;
            lf_chk = lf_chk + 1;
        end
    end
    integer i;
    initial begin
        repeat (8) @(posedge ca); #100 rst = 1;
        repeat (900) @(posedge ca); #333 rst = 0; repeat (40) @(posedge ca); #77 rst = 1;
        repeat (900) @(posedge ca); #55 lock = 0; repeat (30) @(posedge ca); #91 lock = 1;
        repeat (900) @(posedge ca); #211 rst = 0; repeat (70) @(posedge ca);
        go = 0; gn = 0; sent = 0; pc = 0; #123 rst = 1; run = 1;
        wait (sent == NB);
        repeat (700) @(posedge ca);
        for (i = 0; i < go && i < gn && i <= NB + 16; i = i + 1) begin
            if (seq_o[i] !== seq_n[i]) eq_bad = eq_bad + 1;
            if (seq_o[i] !== beat(i)) bo = bo + 1;
            if (seq_n[i] !== beat(i)) bn = bn + 1;
        end
        $display("TB_S81_COL_LANE PIN=%0d TXA=%0d RXI=%0d RXO=%0d MUT=%0d XTX=%0d XRX=%0d tx_checks=%0d tx_bad=%0d rck_checks=%0d rck_valid=%0d rck_bad=%0d leaf_checks=%0d leaf_bad=%0d got_old=%0d got_new=%0d seq_diff=%0d bad_old=%0d bad_new=%0d st_old=%b st_new=%b",
                 PIN, TXA, RXI, RXO, MUT, XTX, XRX, tx_chk, tx_bad, rk_chk, rk_v, rk_bad, lf_chk, lf_bad, go, gn, eq_bad, bo, bn, st_o, st_n);
        if (tx_bad == 0 && tx_chk > 6000 && rk_bad == 0 && rk_chk > 6000 && rk_v > 3000 && lf_bad == 0 && lf_chk > 50 &&
            go == gn && go >= NB - 400 && eq_bad == 0 && bo == 0 && bn == 0 && st_o == 2'b10 && st_n == 2'b10)
            $display("TB_S81_COL_LANE PASS"); else $display("TB_S81_COL_LANE FAIL");
        $finish;
    end
endmodule
