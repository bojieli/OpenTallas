`timescale 1ns/1ps
// S81-TYPES-9-RCK 11-08: TX core vG (OT_S81_RCK_TX_PPCYC) vs the current TX core, lock-step.
// Contract: p_v / p_d of the new core equal the current core's ONE clock later (the +1 pin cycle); fault equal on the
// same clock.  Stimulus: continuous stream, valid gaps (sets the sticky fault), warm resets, late start, random power-up
// state (+verilator+rand+reset+2).  A window of 12 clocks after each rst_n edge is not compared (the reset trees clear
// the two pipelines one clock apart by construction).
module tb;
    reg clk = 0;
    always #0.4165 clk = ~clk;
    reg rst_n = 0, tx_v = 0;
    reg [511:0] tx_d = 0;
    wire pv_r, pv_n, f_r, f_n;
    wire [543:0] pd_r, pd_n;
    ot_s81_rck_tx_r R (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d), .p_v(pv_r), .p_d(pd_r), .fault(f_r));
    ot_s81_rck_tx_n N (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d), .p_v(pv_n), .p_d(pd_n), .fault(f_n));
    reg pv_r1 = 0; reg [543:0] pd_r1 = 0; reg rst_q = 0;
    integer mask = 0, checks = 0, err = 0, live = 0, faults = 0, cyc = 0, frames0 = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        pv_r1 <= pv_r; pd_r1 <= pd_r; rst_q <= rst_n;
        if (rst_q != rst_n) mask <= 12; else if (mask > 0) mask <= mask - 1;
        if (mask == 0 && cyc > 4 && rst_n) begin
            checks <= checks + 1;
            if (pv_n !== pv_r1 || pd_n !== pd_r1 || f_n !== f_r) begin
                err = err + 1;
                if (err < 10) $display("BAD cyc=%0d pv %b/%b pd %0d f %b/%b", cyc, pv_n, pv_r1, pd_n !== pd_r1, f_n, f_r);
            end
            if (pv_r1 && pd_r1 != 0) live <= live + 1;
            if (f_r) faults <= faults + 1;
            if (pv_r1 && pd_r1[543:532] == 12'hA5C) frames0 <= frames0 + 1;
        end
    end
    integer ph, k, gap;
    task automatic beats(input integer n, input integer gaprate);
        for (k = 0; k < n; k = k + 1) begin
            @(negedge clk);
            tx_d = {16{$urandom}};
            tx_v = (gaprate == 0) ? 1'b1 : (($urandom % 100) >= gaprate);
        end
    endtask
    initial begin
        for (ph = 0; ph < 6; ph = ph + 1) begin
            @(negedge clk); rst_n = 0; tx_v = 0;
            repeat (10 + ph) @(negedge clk);
            rst_n = 1;
            repeat (3 * ph) @(negedge clk);                 // late start (0..15 idle clocks after reset)
            case (ph)
                0: beats(3000, 0);
                1: beats(3000, 0);
                2: beats(2000, 2);                          // valid gaps -> sticky fault
                3: begin beats(1500, 0); @(negedge clk); rst_n = 0; repeat (3) @(negedge clk); rst_n = 1; beats(1500, 0); end
                4: beats(2500, 0);
                default: beats(2000, 1);
            endcase
            tx_v = 0;
            repeat (20) @(negedge clk);
        end
        $display("TX_RESULT checks=%0d errors=%0d live=%0d am_words=%0d fault_cycles=%0d", checks, err, live, frames0, faults);
        if (err != 0 || live < 5000 || frames0 < 500 || faults < 10) $fatal(1, "TX lockstep FAILED");
        $display("TX lockstep PASS");
        $finish;
    end
endmodule
