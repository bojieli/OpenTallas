`timescale 1ns/1ps
// lockstep equivalence of ot_ratio_cdc_fifo before / after the LOCAL_CTRL change, at LOCAL_CTRL 0 (random traffic,
// random resets on both sides, related clocks 4:3 and 3:4, LAG 0 / 1, DEPTH 4 / 8)
module tb_eq;
    parameter integer LAG = 0, DEPTH = 4, TW = 4, TR = 3;
    reg wclk = 0, rclk = 0; always #(TW) wclk = ~wclk; always #(TR) rclk = ~rclk;
    reg wrst = 0, rrst = 0, w_v = 0, r_rdy = 0; reg [15:0] w_d = 0;
    wire a_wr, a_rv, a_wl, a_rl, b_wr, b_rv, b_wl, b_rl; wire [15:0] a_rd, b_rd;
    gold #(.W(16), .DEPTH(DEPTH), .HOLD(2), .LAG(LAG)) g (.wclk(wclk), .wrst_n(wrst), .w_v(w_v), .w_rdy(a_wr), .w_d(w_d),
        .rclk(rclk), .rrst_n(rrst), .r_v(a_rv), .r_rdy(r_rdy), .r_d(a_rd), .w_live(a_wl), .r_live(a_rl));
    gate #(.W(16), .DEPTH(DEPTH), .HOLD(2), .LAG(LAG), .LOCAL_CTRL(0)) t (.wclk(wclk), .wrst_n(wrst), .w_v(w_v), .w_rdy(b_wr), .w_d(w_d),
        .rclk(rclk), .rrst_n(rrst), .r_v(b_rv), .r_rdy(r_rdy), .r_d(b_rd), .w_live(b_wl), .r_live(b_rl));
    integer i, errs = 0, wfires = 0, rfires = 0;
    always @(posedge wclk) begin
        if ($urandom % 900 == 0) wrst <= 0; else if ($urandom % 20 == 0) wrst <= 1;
        w_v <= ($urandom % 3) != 0; w_d <= $urandom;
        if (w_v && a_wr) wfires = wfires + 1;
    end
    always @(posedge rclk) begin
        if ($urandom % 900 == 0) rrst <= 0; else if ($urandom % 20 == 0) rrst <= 1;
        r_rdy <= ($urandom % 4) != 0;
        if (a_rv && r_rdy) rfires = rfires + 1;
    end
    always @(negedge wclk) if (a_wr !== b_wr || a_wl !== b_wl) errs = errs + 1;
    always @(negedge rclk) if (a_rv !== b_rv || a_rl !== b_rl || (a_rv && a_rd !== b_rd)) errs = errs + 1;
    initial begin
        #2000000;
        $display("EQ LAG=%0d DEPTH=%0d TW=%0d TR=%0d wfires=%0d rfires=%0d mismatches=%0d %s", LAG, DEPTH, TW, TR, wfires, rfires, errs, errs == 0 ? "EQUAL" : "DIFFER");
        $finish;
    end
endmodule
