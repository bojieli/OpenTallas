// Exactness of ot_qwen_w12_bmul LAT 6 / 7 / 8 against LAT 5 (the qualified product): random BF16-in-FP32 operands
// (random exponents incl. 0 / 255, every mantissa), one per cycle with random valid; DUT y / fault at cycle t + DLAT
// must equal the reference's at t + 5.  NEG = 1 compares one cycle short (must fail).
`timescale 1ns/1ps
module tb_qwen_w12_bmul_lat;
    parameter integer DLAT = 8, N = 2000000, NEG = 0, SEED = 1;
    reg clk = 0, rst_n = 0, v = 0;
    reg [31:0] a = 0, b = 0;
    wire [31:0] yr, yd; wire fr, fd;
    ot_qwen_w12_bmul #(.LAT(5))    u_r (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(yr), .fault(fr));
    ot_qwen_w12_bmul #(.LAT(DLAT)) u_d (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(yd), .fault(fd));
    localparam integer D = DLAT - 5 - NEG;
    reg [32:0] hist [0:15];
    integer i, k, mism = 0, checked = 0, seed = SEED;
    always #1 clk = ~clk;
    function [31:0] rnd_op(input integer s);
        reg [7:0] e; reg [31:0] r;
        begin
            r = $random(seed);
            case (r[3:0]) 0: e = 8'd0; 1: e = 8'hFF; 2: e = 8'd1; 3: e = 8'hFE; default: e = r[11:4]; endcase
            rnd_op = {r[31], e, r[22:16], 16'd0};
        end
    endfunction
    initial begin
        repeat (3) @(posedge clk); rst_n = 1;
        for (i = 0; i < N + 20; i = i + 1) begin
            @(negedge clk);
            v = (i < N) ? ($random(seed) & 3) != 0 : 0; a = rnd_op(0); b = rnd_op(1);
            for (k = 15; k > 0; k = k - 1) hist[k] = hist[k-1];
            hist[0] = {fr, yr};
            if (i > 20) begin
                checked = checked + 1;
                if (D >= 0 && {fd, yd} !== hist[D]) mism = mism + 1;
            end
        end
        if (mism == 0) $display("PASS bmul LAT %0d == LAT 5 (+%0d cycles) on %0d cycles", DLAT, DLAT - 5, checked);
        else $display("FAIL bmul LAT %0d: %0d mismatches of %0d (NEG=%0d)", DLAT, mism, checked, NEG);
        $finish;
    end
endmodule
