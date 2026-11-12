`timescale 1ns/1ps
// HBM-HALFWIDTH-1 lock-step bench: 1-beat reference lane (H+1 register stages) vs TX -> H stations -> RX, the DUT output
// compared with the reference delayed by exactly one more cycle (word_cycles = cycles + 1).
// Stimulus obeys the premises P1 (control only on slot0), P2 (levels change only on slot0), payload garbage on slot1 (GARB).
// BAD = 1: one control pulse on a slot1 cycle (TX fault must rise); BAD = 2: a level flips on a slot1 cycle (GUARD = 1 fault).
// HW = 0: the lane is a wire; q must equal the d delayed by exactly H cycles under unconstrained random stimulus.
module tb_hw_lane;
    parameter integer W = 64;
    parameter integer H = 3;
    parameter integer HW = 1;
    parameter integer BEATS = 2;
    parameter integer GARB = 1;
    parameter integer GUARD = 0;
    parameter integer BAD = 0;
    parameter integer MUTT = 0;
    parameter integer MUTR = 0;
    parameter integer NCYC = 20000;
    parameter integer SEED = 1;
    localparam integer BW = (W + BEATS - 1) / BEATS;
    localparam integer OW = (HW != 0) ? BW : W;

    function [W-1:0] cls(input integer k);   // k = 0 control, 1 payload, 2 level
        integer i;
        begin
            cls = {W{1'b0}};
            for (i = 0; i < W; i = i + 1)
                if (k == 0 ? (i % 8 == 0) : k == 1 ? (i % 8 >= 1 && i % 8 <= 3) : !(i % 8 <= 3)) cls[i] = 1'b1;
        end
    endfunction
    localparam [W-1:0] CM = cls(0);
    localparam [W-1:0] PM = cls(1);
    localparam [W-1:0] LM = cls(2);

    reg clk = 0, rst_n = 0;
    always #5 clk = ~clk;
    reg [W-1:0] d = {W{1'b0}};
    wire [OW-1:0] b_o;
    wire f_o, fault;
    wire [W-1:0] q;
    ot_hbm_hw_lane_tx #(.W(W), .HW(HW), .BEATS(BEATS), .CONTROL_MASK(CM), .PAYLOAD_MASK(PM), .GUARD_LEVELS(GUARD), .MUT(MUTT))
        tx (.clk(clk), .rst_n(rst_n), .d(d), .b_o(b_o), .f_o(f_o), .fault_o(fault));
    // H lane stations (boundary flops / ft stations): reset-less data, as ot_dp_st
    reg [OW-1:0] sb [0:H];
    reg [H:0] sf;
    integer s;
    wire [OW-1:0] b_i = (H == 0) ? b_o : sb[(H > 0) ? H - 1 : 0];
    wire f_i = (H == 0) ? f_o : sf[(H > 0) ? H - 1 : 0];
    always @(posedge clk) begin
        if (H > 0) begin
            sb[0] <= b_o; sf[0] <= f_o;
            for (s = 1; s < H; s = s + 1) begin sb[s] <= sb[s-1]; sf[s] <= sf[s-1]; end
        end
    end
    ot_hbm_hw_lane_rx #(.W(W), .HW(HW), .BEATS(BEATS), .CONTROL_MASK(CM), .MUT(MUTR))
        rx (.clk(clk), .rst_n(rst_n), .b_i(b_i), .f_i(f_i), .q(q));

    // reference: d delayed by DL cycles
    localparam integer DL = (HW != 0) ? H + BEATS : H;
    reg [W-1:0] rf [0:DL];
    integer r;
    initial for (r = 0; r <= DL; r = r + 1) rf[r] = {W{1'b0}};
    always @(posedge clk) begin
        rf[0] <= d;
        for (r = 1; r <= DL; r = r + 1) rf[r] <= rf[r-1];
    end
    wire [W-1:0] ref_q = (DL == 0) ? d : rf[(DL > 0) ? DL - 1 : 0];

    integer seed = SEED;
    integer cyc = 0, off, bad_at, mism = 0, cmp = 0, words = 0, ctl_pulses = 0;
    reg slot1;
    reg [W-1:0] rnd, lv, lastd;
    reg faulted = 0;
    integer k;
    function [W-1:0] rndw(input integer dummy);
        integer j;
        reg [W+31:0] t;
        begin
            t = {(W+32){1'b0}};
            for (j = 0; j < W; j = j + 32) t[j +: 32] = $random(seed);
            rndw = t[W-1:0];
        end
    endfunction
    initial begin
        off = 1 + ({$random(seed)} % 6);
        bad_at = 200 + 2 * ({$random(seed)} % 200) + 1;   // odd offset from slot grid chosen below
        lv = {W{1'b0}};
        rnd = rndw(0);
        repeat (4) @(posedge clk);
        #1 rst_n = 1;
    end
    always @(posedge clk) if (fault) faulted <= 1;
    // stimulus (applied 1 ns after the edge); slot0 cycles are cyc = off + 2n
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        #1;
        if (HW == 0) begin
            d <= rndw(0);                                         // unconstrained
        end else if (cyc < off) begin
            d <= {W{1'b0}};
        end else if (((cyc - off) % BEATS) == 0) begin              // slot0
            rnd = rndw(0);
            for (k = 0; k < W; k = k + 1) if (LM[k] && ({$random(seed)} % 16) == 0) lv[k] = rnd[k];
            lastd = (rnd & CM & rndw(0) & rndw(0)) | (lv & LM);
            if (lastd[0]) lastd = lastd | (rndw(0) & PM);        // payload only beside the valid control bit 0
            d <= lastd;
        end else begin                                           // slot1
            lastd = lastd & ~CM;
            if (GARB) lastd = (lastd & ~PM) | (rndw(0) & PM);
            if (BAD == 1 && cyc > 300 && !faulted && ({$random(seed)} % 8) == 0) lastd = lastd | (CM & rndw(0)) | 1'b1;
            if (BAD == 2 && cyc > 300 && ({$random(seed)} % 8) == 0) lastd = lastd ^ (LM & rndw(0)) ^ (1'b1 << 4);
            d <= lastd;
        end
    end

    wire [W-1:0] vmask = ref_q[0] ? {W{1'b1}} : ~PM;     // payload compared only beside the valid
    reg [W-1:0] diff;
    always @(negedge clk) if (rst_n && cyc > 20 + H + BEATS) begin
        diff = (q ^ ref_q) & ((HW != 0 && GARB) ? vmask : {W{1'b1}});
        cmp = cmp + 1;
        if (diff !== {W{1'b0}}) begin
            mism = mism + 1;
            if (mism < 4) $display("MISMATCH cyc %0d diff %h", cyc, diff);
        end
        if (|(ref_q & CM)) ctl_pulses = ctl_pulses + 1;
    end
    initial begin
        wait (cyc >= NCYC);
        #2;
        if (BAD != 0) begin
            $display("RESULT %s W=%0d H=%0d BAD=%0d fault=%0d (expected 1) mism=%0d", faulted ? "PASS" : "FAIL", W, H, BAD, faulted, mism);
        end else begin
            $display("%s cmp=%0d mism=%0d ctl_pulses=%0d fault=%0d W=%0d H=%0d HW=%0d GARB=%0d MUTT=%0d MUTR=%0d",
                     (mism == 0 && !faulted && ctl_pulses > 50) ? "RESULT PASS" : "RESULT FAIL", cmp, mism, ctl_pulses, faulted, W, H, HW, GARB, MUTT, MUTR);
        end
        $finish;
    end
endmodule
