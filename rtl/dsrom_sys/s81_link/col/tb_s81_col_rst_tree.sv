`timescale 1ps/1fs
// tb_s81_col_rst_tree (S81-SERDES-RST-TREE, DIE-S81-85 2026-11-09): lock-step proof of ot_pdie_serdes_col RST_TREE=1 (the
// registered clk reset fan-out tree, +1 clk edge on the whole clk domain) against the released column RST_TREE=0.
// Build with +define+OT_S81_SERDES_RST_TREE (both columns elaborate; the parameter picks the form).
//   RM : ot_s81_rate_match (released) == ot_s81_rate_match_rt (all resets tied) every edge, random beats / idles, 300 ppm,
//        three reset epochs.
//   TX : the new column's tx input is the released column's tx delayed ONE clk edge (the compensation of the extra edge):
//        pma_tx(new, t+1) == pma_tx(old, t) every edge outside reset, three reset epochs (cold, warm, warm).
//   RX : both columns receive the same PMA lane (a reference ot_pdie_serdes peer, 300 ppm slow, one bit error in about every
//        second word): identical in-order non-IDLE beat sequence, >= NB - 400 beats, exact payloads, final st 2'b10 both.
//   Leaf: 2 clk edges after rst falls the new column is in reset (st 0, rx IDLE).
// Under OT_S81_RM_STAGED (the combined RCK form): RM compares ot_s81_rate_match RLEAF=0 vs RLEAF=1 (read side +1 rclk): the
//   in-order non-IDLE beat sequence per epoch (prefix equal, lengths within 2, no fault); the leaf check reads st at 2 edges
//   and rx IDLE at 6 edges (r_m / r_pipe / r_d carry no reset there).  RLAT: measured fixed RX/TX latencies (bench report).
// Form vC: RT=3 (two leaf stages, +2 clk edges) and RTT=1 (RST_RT retime flop, +1 pma_rck edge on the clk domain release):
//   the tx compensation is TXD = stages + RTT edges; the leaf check reads st at stages + 1 edges (assertion is not retimed).
//   Mutants RT=4 (encoder reset on the mid stage) and NOCOMP / TXD one short (TXSHORT=1) must FAIL.
// Mutants (must FAIL): RT=2 (encoder rst_n not moved with tx_v), NOCOMP=1 (no one-edge data shift on tx).
module tb_s81_col_rst_tree;
    parameter integer RT = 1, NOCOMP = 0, LS = 0, NB = 6000, RTT = 0, TXSHORT = 0;
    localparam integer STG = (RT >= 3) ? 2 : 1;
    localparam integer TXD = NOCOMP ? 0 : STG + RTT - TXSHORT;
    reg ca = 0, cb = 0, rst = 0;
    always #416.5 ca = ~ca;
    always #416.62495 cb = ~cb;
    function automatic [511:0] beat(input integer n);
        beat = {32'(n), 32'(n * 7 + 3), 32'(n ^ 32'h5A5A), 384'h0, 30'(n), 2'b00} ^ {64'h0, {448{n[0]}}} & ~512'h3;
    endfunction
    // ------------------------------------------------------------------ RM unit compare
    reg rm_wr = 0, rm_rr = 0, w_v = 0; reg [511:0] w_d = 512'd2;
    wire [511:0] rd_a, rd_b; wire fa, fb;
    ot_s81_rate_match    u_rma (.wclk(cb), .wrst_n(rm_wr), .w_v(w_v), .w_d(w_d), .rclk(ca), .rrst_n(rm_rr), .r_d(rd_a), .fault(fa));
`ifdef OT_S81_RM_STAGED
    ot_s81_rate_match #(.RLEAF(1)) u_rmb (.wclk(cb), .wrst_n(rm_wr), .w_v(w_v), .w_d(w_d), .rclk(ca), .rrst_n(rm_rr), .r_d(rd_b),
                                .fault(fb));
`else
    ot_s81_rate_match_rt u_rmb (.wclk(cb), .wrst_n(rm_wr), .w_v(w_v), .w_d(w_d), .rclk(ca), .rrst_nc(rm_rr), .rrst_nd({8{rm_rr}}),
                                .r_d(rd_b), .fault(fb));
`endif
    integer rm_chk = 0, rm_nonidle = 0;
    always @(negedge cb) begin
        w_v <= ($urandom % 8) != 0;
        w_d <= (($urandom % 3) == 0) ? 512'd2 : {$urandom, $urandom, 448'(0), 32'($urandom) & ~32'h3};
    end
`ifdef OT_S81_RM_STAGED
    reg [511:0] rq_a [0:4095]; reg [511:0] rq_b [0:4095]; integer na = 0, nb = 0, rm_on = 0, k;
    task rm_epoch_check; begin
        if (na - nb > 2 || nb - na > 2) $fatal(1, "RM: RLEAF beat count %0d vs %0d", na, nb);
        for (k = 0; k < na && k < nb; k = k + 1) if (rq_a[k] !== rq_b[k]) $fatal(1, "RM: RLEAF beat %0d differs", k);
        rm_chk = rm_chk + ((na < nb) ? na : nb); na = 0; nb = 0;
    end endtask
    always @(posedge ca) begin #1;
        rm_on = rm_rr ? rm_on + 1 : 0;
        if (rm_on > 0) begin
            if (fa || fb) $fatal(1, "RM: fault");
            if (!(rd_a[1] && !rd_a[0]) && na < 4096) begin rq_a[na] = rd_a; na = na + 1; rm_nonidle = rm_nonidle + 1; end
            if (!(rd_b[1] && !rd_b[0]) && nb < 4096) begin rq_b[nb] = rd_b; nb = nb + 1; end
        end
    end
`else
    task rm_epoch_check; begin end endtask
    always @(posedge ca) begin #1;
        if ({rd_a, fa} !== {rd_b, fb}) $fatal(1, "RM: ot_s81_rate_match_rt differs from ot_s81_rate_match");
        rm_chk = rm_chk + 1; if (!(rd_a[1] && !rd_a[0])) rm_nonidle = rm_nonidle + 1;
    end
`endif
    // ------------------------------------------------------------------ columns
    reg [511:0] tx_o = 512'd2, tx_n = 512'd2;
    wire [511:0] rx_o, rx_n, rx_p; wire [1:0] st_o, st_n, st_p;
    wire [543:0] pt_o, pt_n, pt_p; wire tc_o, tc_n, tc_p; reg [543:0] pt_p_e;
    ot_pdie_serdes_col #(.RST_TREE(0), .RST_RT(0), .LOCKSAFE(LS)) u_o (.clk(ca), .rst(rst), .tx(tx_o), .rx(rx_o), .st(st_o), .pma_tx(pt_o),
        .pma_tck(tc_o), .pma_rx(pt_p_e), .pma_rck(tc_p), .pma_lock(1'b1));
    ot_pdie_serdes_col #(.RST_TREE(RT), .RST_RT(RTT), .LOCKSAFE(LS)) u_n (.clk(ca), .rst(rst), .tx(tx_n), .rx(rx_n), .st(st_n), .pma_tx(pt_n),
        .pma_tck(tc_n), .pma_rx(pt_p_e), .pma_rck(tc_p), .pma_lock(1'b1));
    // peer: reference flat SerDes on cb, sends the beat stream; receives the released column's lane
    reg [511:0] tx_p = 512'd2;
    ot_pdie_serdes u_p (.clk(cb), .rst(rst), .tx(tx_p), .rx(rx_p), .st(st_p), .pma_tx(pt_p), .pma_tck(tc_p), .pma_rx(pt_o),
        .pma_rck(tc_o));
    reg err_on = 0; integer err_bit = 0;
    always @* begin pt_p_e = pt_p; if (err_on) pt_p_e[err_bit] = ~pt_p[err_bit]; end
    always @(posedge tc_p) begin err_on <= ($urandom % 2) == 0; err_bit <= $urandom % 544; end
    // tx streams: tx_n = tx_o one clk edge later (NOCOMP mutant: same edge)
    integer cyc = 0;
    reg [511:0] tx_src; reg [511:0] tx_h [0:7]; integer th;
    initial for (th = 0; th < 8; th = th + 1) tx_h[th] = 512'd2;
    always @(negedge ca) begin
        cyc = cyc + 1;
        tx_src = (cyc % 256 == 0) ? 512'd2 : beat(cyc * 13 + 5);
        tx_n <= (TXD == 0) ? tx_src : tx_h[TXD - 1];     // tx_h[k] = tx_src k + 1 edges ago (before the shift)
        for (th = 7; th > 0; th = th - 1) tx_h[th] = tx_h[th - 1];
        tx_h[0] = tx_src;
        tx_o <= tx_src;
    end
    integer sent = 0, pc = 0;
    always @(negedge cb) begin
        pc = pc + 1;
        if (pc > 200 && sent < NB) begin
            if (pc % 256 == 0) tx_p <= 512'd2; else begin tx_p <= beat(sent); sent = sent + 1; end
        end else tx_p <= 512'd2;
    end
    // TX lock-step
    reg [543:0] pt_h [0:7]; integer th2;
    reg [543:0] pt_o_d; reg rst_d1 = 0, rst_d2 = 0; reg [7:0] rst_dh = 8'hff; wire [7:0] rst_dm = (8'd1 << (STG + 1)) - 8'd1; integer tx_chk = 0, tx_bad = 0, lf_chk = 0;
    always @(posedge ca) begin
        #1;
        if (rst && rst_d2) begin
            if (pt_n !== pt_o_d) begin tx_bad = tx_bad + 1; if (tx_bad < 4) $display("TX lock-step mismatch at cyc %0d", cyc); end
            tx_chk = tx_chk + 1;
        end
`ifdef OT_S81_RM_STAGED
        if (!rst && (rst_dh & rst_dm) == 8'd0 && st_n !== 2'b00) $fatal(1, "RST_TREE leaf: new column st not in reset");
        if ((rst_dh & ((rst_dm << 5) | 8'h1f)) == 8'd0) begin
            if (rx_n !== 512'd2) $fatal(1, "RST_TREE leaf: new column rx not IDLE 6 edges after rst");
            lf_chk = lf_chk + 1;
        end
`else
        if (!rst && (rst_dh & rst_dm) == 8'd0) begin
            if (st_n !== 2'b00 || rx_n !== 512'd2) $fatal(1, "RST_TREE leaf: new column not in reset 2 edges after rst");
            lf_chk = lf_chk + 1;
        end
`endif
        for (th2 = 7; th2 > 0; th2 = th2 - 1) pt_h[th2] = pt_h[th2 - 1];
        pt_h[0] = pt_o; pt_o_d = pt_h[(TXD == 0) ? 0 : TXD - 1]; rst_d2 = rst_d1; rst_d1 = rst; rst_dh = {rst_dh[6:0], rst};
    end
    // RX sequences (only the last epoch carries the peer stream; earlier epochs compare idles / partial beats too)
    integer go = 0, gn = 0, bo = 0, bn = 0, eq_bad = 0;
    reg [511:0] seq_o [0:NB+16];
    reg [511:0] seq_n [0:NB+16];
    always @(posedge ca) if (rst && rst_d2) begin
        if (!(rx_o[1] && !rx_o[0])) begin if (go <= NB + 16) seq_o[go] = rx_o; go = go + 1; end
        if (!(rx_n[1] && !rx_n[0])) begin if (gn <= NB + 16) seq_n[gn] = rx_n; gn = gn + 1; end
    end
    integer i, ep;
    initial begin
        // RM epochs
        for (ep = 0; ep < 3; ep = ep + 1) begin
            rm_wr = 0; rm_rr = 0; repeat (5) @(posedge ca); #200 rm_wr = 1; #300 rm_rr = 1; repeat (2000) @(posedge ca); rm_epoch_check;
        end
        // column epochs 0, 1: warm resets mid-stream (TX lock-step through re-assertion / release); epoch 2 carries the RX run
        repeat (8) @(posedge ca); #100 rst = 1;
        repeat (700) @(posedge ca); #333 rst = 0; repeat (20) @(posedge ca); #77 rst = 1;
        repeat (900) @(posedge ca); #211 rst = 0; repeat (70) @(posedge ca);
        go = 0; gn = 0; sent = 0; pc = 0; #123 rst = 1;
        wait (sent == NB);
        repeat (600) @(posedge ca);
        for (i = 0; i < go && i < gn && i <= NB + 16; i = i + 1) begin
            if (seq_o[i] !== seq_n[i]) eq_bad = eq_bad + 1;
            if (seq_o[i] !== beat(i)) bo = bo + 1;
            if (seq_n[i] !== beat(i)) bn = bn + 1;
        end
        $display("TB_S81_COL_RST_TREE RT=%0d RTT=%0d TXD=%0d NOCOMP=%0d LS=%0d rm_checks=%0d rm_nonidle=%0d tx_checks=%0d tx_bad=%0d leaf_checks=%0d got_old=%0d got_new=%0d seq_diff=%0d bad_old=%0d bad_new=%0d st_old=%b st_new=%b",
                 RT, RTT, TXD, NOCOMP, LS, rm_chk, rm_nonidle, tx_chk, tx_bad, lf_chk, go, gn, eq_bad, bo, bn, st_o, st_n);
        if (tx_bad == 0 && tx_chk > 6000 && rm_nonidle > 1000 && lf_chk > 100 && go == gn && go >= NB - 400 && eq_bad == 0 &&
            bo == 0 && bn == 0 && st_o == 2'b10 && st_n == 2'b10)
            $display("TB_S81_COL_RST_TREE PASS"); else $display("TB_S81_COL_RST_TREE FAIL");
        $finish;
    end
endmodule
