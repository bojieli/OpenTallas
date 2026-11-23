`timescale 1ns/1ps
// FIX-KV-PV-MESOFIFO 11-23: ot_dp_dly_ram == ot_dp_dly (bind.py) cycle for cycle after the D-cycle fill, for W/D corners;
// pointer power-up is random (--x-initial unique), so any start value is covered across seeds.
module ref_dly #(parameter integer W = 1, parameter integer D = 1) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    reg [W-1:0] r [0:D-1];
    integer i;
    always @(posedge clk) begin
        r[0] <= d;
        for (i = 1; i < D; i = i + 1) r[i] <= r[i-1];
    end
    assign q = r[D-1];
endmodule

module one #(parameter integer W = 1, parameter integer D = 4) (input wire clk, input wire [31:0] cyc, output reg [31:0] bad);
    reg [W-1:0] d;
    wire [W-1:0] qa, qb;
    integer k;
    always @(posedge clk) for (k = 0; k < W; k = k + 1) d[k] <= $urandom;
    ot_dp_dly_ram #(.W(W), .D(D)) dut (.clk(clk), .d(d), .q(qa));
    ref_dly #(.W(W), .D(D)) gold (.clk(clk), .d(d), .q(qb));
    initial bad = 0;
    // d changes on the edge, so the first meaningful sample of both lines is D + 2 edges in
    always @(negedge clk) if (cyc > D + 3 && qa !== qb) begin
        if (bad < 3) $display("MISMATCH W=%0d D=%0d cyc=%0d", W, D, cyc);
        bad <= bad + 1;
    end
endmodule

module tb_dp_dly_ram;
    reg clk = 0;
    reg [31:0] cyc = 0;
    always #0.4165 clk = ~clk;
    always @(posedge clk) cyc <= cyc + 1;
    wire [31:0] b0, b1, b2, b3, b4, b5, b6, b7;
    one #(.W(1),   .D(4))   u0 (.clk(clk), .cyc(cyc), .bad(b0));
    one #(.W(7),   .D(5))   u1 (.clk(clk), .cyc(cyc), .bad(b1));
    one #(.W(256), .D(46))  u2 (.clk(clk), .cyc(cyc), .bad(b2));
    one #(.W(300), .D(59))  u3 (.clk(clk), .cyc(cyc), .bad(b3));
    one #(.W(768), .D(67))  u4 (.clk(clk), .cyc(cyc), .bad(b4));
    one #(.W(64),  .D(129)) u5 (.clk(clk), .cyc(cyc), .bad(b5));
    one #(.W(33),  .D(130)) u6 (.clk(clk), .cyc(cyc), .bad(b6));
    one #(.W(512), .D(8))   u7 (.clk(clk), .cyc(cyc), .bad(b7));
    initial begin
        #(0.833 * 2000);
        $display("DLYRAM_BENCH cycles=%0d bad=%0d %0d %0d %0d %0d %0d %0d %0d", cyc, b0, b1, b2, b3, b4, b5, b6, b7);
        if ((b0|b1|b2|b3|b4|b5|b6|b7) == 0) $display("DLYRAM_BENCH PASS"); else $display("DLYRAM_BENCH FAIL");
        $finish;
    end
endmodule
