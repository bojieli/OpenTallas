// ot_qwen_die_station: b_d / t_d / c_d == a_d one cycle later, a_r == b_r & t_r & c_r two cycles later, on random
// stimulus.  NEG = 1 checks the data one cycle short (must fail).
`timescale 1ns/1ps
module tb_qwen_die_station;
    parameter integer N = 200000, NEG = 0, SPLIT = 1;
    localparam integer DW = 508;
    reg clk = 0, rst_n = 0, b_r = 0, t_r = 0, c_r = 0;
    reg [DW-1:0] a_d = 0;
    wire [DW-1:0] b_d, t_d, c_d; wire a_r;
    ot_qwen_die_station #(.DW(DW), .TAP(1), .SPLIT(SPLIT)) u (.clk(clk), .rst_n(rst_n), .a_d(a_d), .a_r(a_r), .b_d(b_d),
        .b_r(b_r), .t_d(t_d), .t_r(t_r), .c_d(c_d), .c_r(c_r));
    always #1 clk = ~clk;
    reg [DW-1:0] dprev; reg rq [0:3];
    integer i, k, bad = 0, seed = 7;
    initial begin
        repeat (3) @(posedge clk); rst_n = 1;
        for (i = 0; i < N; i = i + 1) begin
            @(negedge clk);
            // outputs now hold what the last posedge captured: the stimulus driven one iteration ago
            if (i > 4) begin
                if (b_d !== (NEG ? dprev : a_d) || t_d !== (NEG ? dprev : a_d) || (SPLIT && c_d !== (NEG ? dprev : a_d)))
                    bad = bad + 1;
                if (a_r !== rq[1]) bad = bad + 1;
            end
            dprev = a_d;
            for (k = 0; k < DW; k = k + 32) a_d[k +: 32] = $random(seed);
            rq[3] = rq[2]; rq[2] = rq[1]; rq[1] = rq[0];
            b_r = $random(seed); t_r = $random(seed); c_r = SPLIT ? $random(seed) : 1'b1;
            rq[0] = b_r & t_r & c_r;
        end
        if (bad == 0) $display("PASS station SPLIT=%0d: %0d cycles", SPLIT, N);
        else $display("FAIL station SPLIT=%0d NEG=%0d: %0d mismatches", SPLIT, NEG, bad);
        $finish;
    end
endmodule
