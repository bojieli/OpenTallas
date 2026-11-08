`timescale 1ps/1fs
// S81-RCK-11: RE-FORM column (OT_S81_RCK_REFORM: RX-SYN / RX-BACK / TX hard-core grouping) vs the vJ column, lock-step.
// Both columns get the same clocks (core 833 ps, recovered pma_rck 300 ppm slow), the same TX stream and the same
// corrupted PMA loopback (each copy's own pma_tx fed back with the same error pattern).  Every output (rx, st, pma_tx,
// pma_tck) must be EQUAL every edge: the re-form adds zero cycles.
module tb;
    reg clk = 0, rck = 0, rst = 0, lock = 0;
    always #416.5 clk = ~clk;
    always #416.62495 rck = ~rck;
    reg [511:0] tx = 0; reg [543:0] pe = 0;
    wire [511:0] rx_r, rx_n; wire [1:0] st_r, st_n; wire [543:0] pt_r, pt_n; wire tc_r, tc_n;
    reg [543:0] pr_r = 0, pr_n = 0;
    integer nerr_rate = 0, b;
    always @(posedge clk) tx <= {16{$urandom}};
    always @(posedge rck) begin
        pe = 0;
        if (nerr_rate > 0) for (b = 0; b < 4; b++) if (($urandom % 100) < nerr_rate) pe[$urandom % 544] = 1'b1;
        if (nerr_rate > 40) for (b = 0; b < 30; b++) pe[($urandom % 54) * 10 +: 10] = $urandom;
        pr_r <= pt_r ^ pe; pr_n <= pt_n ^ pe;
    end
    col_r #(.PMA_LAT(4), .TXL(7), .LOCKSAFE(1), .HOLD_EDGES(64)) R (.clk(clk), .rst(rst), .tx(tx), .rx(rx_r), .st(st_r),
        .pma_tx(pt_r), .pma_tck(tc_r), .pma_rx(pr_r), .pma_rck(rck), .pma_lock(lock));
    col_n #(.PMA_LAT(4), .TXL(7), .LOCKSAFE(1), .HOLD_EDGES(64)) N (.clk(clk), .rst(rst), .tx(tx), .rx(rx_n), .st(st_n),
        .pma_tx(pt_n), .pma_tck(tc_n), .pma_rx(pr_n), .pma_rck(rck), .pma_lock(lock));
    integer checks = 0, err = 0, live = 0, lk = 0, qv = 0;
    always @(posedge clk) if (rst) begin
        checks++;
        if (rx_n !== rx_r || st_n !== st_r || pt_n !== pt_r) begin
            err++; if (err < 20) $display("BAD t=%0t rx%0d st%0d pt%0d", $time, rx_n !== rx_r, st_n !== st_r, pt_n !== pt_r);
        end
        if (rx_r != 0) live++; if (st_r[1]) lk++;
    end
    always @(posedge rck) if (R.q_v) qv++;
    integer i;
    initial begin
        for (i = 0; i < 4; i++) begin
            nerr_rate = (i == 0) ? 0 : (i == 1) ? 30 : (i == 2) ? 90 : 60;
            rst = 0; lock = 0; repeat (20) @(posedge clk); lock = 1; repeat (5) @(posedge clk); rst = 1;
            repeat (3000) @(posedge clk);
        end
        $display("RF_RESULT checks=%0d errors=%0d rx_live=%0d st_lock=%0d dec_q_v=%0d", checks, err, live, lk, qv);
        if (err || live < 1000 || lk < 1000 || qv < 1000) $fatal(1, "RF lockstep FAILED");
        $display("RF lockstep PASS");
        $finish;
    end
endmodule
