`timescale 1ns/1ps
// Campaign for the packed lane. PACK products are summed per cycle, so a K-term
// dot product takes K/PACK cycles; the accumulated value must still be
// bit-identical to the reference, which sums the same K terms in the same window.
module tb_mac_lane_packed #(
    parameter integer PACK        = 8,
    parameter integer W_EXP_BITS  = 2,
    parameter integer W_FRAC_BITS = 1,
    parameter integer K           = 32
);
    localparam integer ACC_W   = 40;
    localparam integer W_FMT_W = 1 + W_EXP_BITS + W_FRAC_BITS;
    localparam integer STEPS   = K / PACK;

    reg clk = 1'b0, rst_n = 1'b0;
    always #5 clk = ~clk;

    reg [15:0]      act_mem [0:K-1];
    reg [31:0]      wgt_mem [0:K-1];
    reg [ACC_W-1:0] expected;
    reg [4095:0]    act_path, wgt_path, exp_path;
    reg [31:0]      scale_arg;

    reg                     clear = 1'b0, accept = 1'b0;
    reg [16*PACK-1:0]       a = {(16*PACK){1'b0}};
    reg [W_FMT_W*PACK-1:0]  b = {(W_FMT_W*PACK){1'b0}};

    wire [ACC_W-1:0] result;
    wire             dropped;

    integer st, j;

    ot_mac_lane_packed #(.PACK(PACK), .W_EXP_BITS(W_EXP_BITS),
                         .W_FRAC_BITS(W_FRAC_BITS)) dut (
        .clk(clk), .rst_n(rst_n), .clear(clear), .accept(accept),
        .a(a), .b(b), .scale_exp(scale_arg[7:0]),
        .result(result), .dropped(dropped)
    );

    initial begin
        if (!$value$plusargs("act=%s", act_path)) begin $display("FAIL: +act="); $finish; end
        if (!$value$plusargs("wgt=%s", wgt_path)) begin $display("FAIL: +wgt="); $finish; end
        if (!$value$plusargs("exp=%s", exp_path)) begin $display("FAIL: +exp="); $finish; end
        if (!$value$plusargs("scale=%d", scale_arg)) begin $display("FAIL: +scale="); $finish; end
        $readmemh(act_path, act_mem);
        $readmemh(wgt_path, wgt_mem);
        begin : le
            reg [ACC_W-1:0] em [0:1];
            $readmemh(exp_path, em);
            expected = em[0];
        end

        repeat (4) @(posedge clk); rst_n = 1'b1;
        @(posedge clk); clear = 1'b1; @(posedge clk); clear = 1'b0;

        for (st = 0; st < STEPS + 3; st = st + 1) begin
            if (st < STEPS)
                for (j = 0; j < PACK; j = j + 1) begin
                    a[16*j +: 16]      = act_mem[st*PACK + j];
                    b[W_FMT_W*j +: W_FMT_W] = wgt_mem[st*PACK + j][W_FMT_W-1:0];
                end
            accept = (st >= 2) && (st < STEPS + 2);
            @(posedge clk);
        end
        accept = 1'b0;
        repeat (6) @(posedge clk);

        if (result === expected)
            $display("PASS PACK=%0d E%0dM%0d: bit-identical to the reference (%010x), %0d cycles for K=%0d, dropped=%0d",
                     PACK, W_EXP_BITS, W_FRAC_BITS, result, STEPS, K, dropped);
        else
            $display("FAIL PACK=%0d E%0dM%0d: observed %010x expected %010x",
                     PACK, W_EXP_BITS, W_FRAC_BITS, result, expected);
        $finish;
    end
endmodule
