`timescale 1ns/1ps
// tb_s81ph_coll_rstc (CLAUDE S81-PH collective): directed checks of ot_s81ph_coll_rstc.
//   1 power-on: all resets low until lock has been held LOCK_HOLD refclk cycles; release order stream, serial,
//     hbm, GAP refclk cycles apart; pll_pd = !por_n.
//   2 por glitch (1 ns low between edges): every reset asserts immediately (asynchronously) and the full sequence
//     reruns from the hold count.
//   3 lock loss (lock low for 3 refclk cycles): immediate assertion, full sequence again after relock.
//   4 lock chatter shorter than LOCK_HOLD never releases anything.
// PASS line "TB_S81PH_COLL_RSTC PASS".
module tb_s81ph_coll_rstc;
    localparam integer LH = 64, GAP = 8;
    reg refclk = 0; always #5 refclk = ~refclk;
    reg por_n = 0, lock = 0;
    wire pd, rs, rv, rh;
    ot_s81ph_coll_rstc #(.LOCK_HOLD(LH), .GAP(GAP)) u (.refclk(refclk), .por_n(por_n), .lock(lock), .pll_pd(pd),
        .rst_stream_n(rs), .rst_serial_n(rv), .rst_hbm_n(rh), .seq_state());
    integer errs = 0, t_s, t_v, t_h, n;
    task expect_low(input [127:0] what);
        if (rs || rv || rh) begin errs = errs + 1; $display("FAIL %0s: resets %b%b%b", what, rs, rv, rh); end
    endtask
    task seq_check(input [127:0] what);
        begin
            t_s = -1; t_v = -1; t_h = -1;
            for (n = 0; n < LH + 3 * GAP + 20; n = n + 1) begin
                @(posedge refclk); #1;
                if (rs && t_s < 0) t_s = n; if (rv && t_v < 0) t_v = n; if (rh && t_h < 0) t_h = n;
                if ((rv && !rs) || (rh && !rv)) begin errs = errs + 1; $display("FAIL %0s: order", what); end
            end
            if (t_s < LH || t_v - t_s != GAP || t_h - t_v != GAP) begin
                errs = errs + 1; $display("FAIL %0s: release at %0d %0d %0d", what, t_s, t_v, t_h); end
            else $display("OK %0s: stream %0d serial %0d hbm %0d refclk cycles after lock", what, t_s, t_v, t_h);
        end
    endtask
    initial begin
        #23; expect_low("por");
        if (!pd) begin errs = errs + 1; $display("FAIL pd while por"); end
        por_n = 1; #1; if (pd) begin errs = errs + 1; $display("FAIL pd after por"); end
        repeat (10) @(posedge refclk); expect_low("no lock");
        #2 lock = 1;
        seq_check("power-on");
        // por glitch between edges
        #3 por_n = 0; #1; expect_low("por glitch (async)"); por_n = 1;
        seq_check("after por glitch");
        // lock loss
        @(posedge refclk); #2 lock = 0; #1; expect_low("lock loss (async)");
        repeat (3) @(posedge refclk); #2 lock = 1;
        seq_check("after relock");
        // chatter
        repeat (5) begin @(posedge refclk); #2 lock = 0; @(posedge refclk); #2 lock = 1; repeat (LH / 2) @(posedge refclk); expect_low("chatter"); end
        lock = 0; repeat (3) @(posedge refclk);
        if (errs == 0) $display("TB_S81PH_COLL_RSTC PASS"); else $display("TB_S81PH_COLL_RSTC FAIL %0d", errs);
        $finish;
    end
endmodule
