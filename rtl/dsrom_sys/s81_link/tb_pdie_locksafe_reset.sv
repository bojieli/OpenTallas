`timescale 1ns/1ps
// Smallest reset mechanism: candidate guard plus the unchanged real rate matcher.
module tb_pdie_locksafe_reset;
    parameter integer HOLD = 64, IGNORE_LOCK = 0;
    reg clk = 0, pck = 0, run_pck = 0, rst = 1, lock = 1, wv = 0;
    always #5 clk = ~clk;
    always #7 if (run_pck) pck = ~pck; else pck = 0;
    wire guarded, ready; wire [511:0] rd; wire fault;
    ot_pdie_pma_reset_hold #(.HOLD_EDGES(HOLD)) guard
        (.rst_n(rst), .pma_lock(IGNORE_LOCK ? 1'b1 : lock), .pma_rck(pck), .core_rst_n(guarded), .hold_ready(ready));
    ot_s81_rate_match rm (.wclk(pck), .wrst_n(guarded), .w_v(wv), .w_d(512'h123401),
        .rclk(clk), .rrst_n(guarded), .r_d(rd), .fault(fault));
    integer n, epoch;
    task assert_empty;
        begin
            if ({rm.wp,rm.rp,rm.wp_g,rm.rp_g,rm.rp_g1,rm.rp_g2,rm.wp_g1,rm.wp_g2} !== 32'd0 ||
                rd !== 512'd2 || fault !== 1'b0 || guarded !== 1'b0)
                $fatal(1,"unsafe FIFO/reset state epoch=%0d",epoch);
        end
    endtask
    task release_and_check;
        begin
            run_pck = 1;
            for(n=1;n<=66;n=n+1) begin
                @(posedge pck); #1;
                if (n<66 && guarded !== 1'b0) $fatal(1,"early release edge%0d",n);
                if (n==66 && guarded !== 1'b1) $fatal(1,"late release edge%0d",n);
            end
            $display("RESET_READY epoch=%0d recovered_edges=66",epoch);
        end
    endtask
    initial begin
        epoch=0; #1 rst=0; #2; assert_empty(); rst=1;
        repeat(8) @(posedge clk); #1; assert_empty(); // PMA stopped throughout reset release
        release_and_check(); wv=1;
        repeat(20) @(posedge pck); #1;
        if (rm.wp === 0 || rm.rp === 0) $fatal(1,"FIFO stimulus vacuous");
        @(negedge pck); run_pck=0; #20;
        epoch=1; lock=0; #1; assert_empty(); // lock loss must reset BOTH pointers with PMA stopped
        lock=1; repeat(8) @(posedge clk); #1; assert_empty();
        release_and_check(); repeat(20) @(posedge pck);
        @(negedge pck); run_pck=0; #20;
        epoch=2; rst=0; #1; assert_empty(); rst=1;
        repeat(8) @(posedge clk); #1; assert_empty();
        release_and_check();
        $display("LOCKSAFE_RESET PASS cold/stopped/warm/relock/actual_fifo_nonzero_pointer_reset"); $finish;
    end
    initial begin #100000; $fatal(1,"fixture did not finish"); end
endmodule
