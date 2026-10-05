`timescale 1ns/1ps
// Campaign for rtl/proto/ot_mac_lane_fmt.sv against runtime.reference.mac_tile,
// one instance per weight format. BF16 activations throughout, which is what the
// checkpoints ship; the weight format is what the ROM and HBM paths differ in.
module tb_mac_lane_fmt #(
    parameter integer W_EXP_BITS  = 8,
    parameter integer W_FRAC_BITS = 7,
    parameter integer K           = 32
);
    localparam integer ACC_W   = 40;
    localparam integer W_FMT_W = 1 + W_EXP_BITS + W_FRAC_BITS;
    reg [31:0] scale_arg;   // the window centre differs per format

    reg clk = 1'b0; reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg [15:0]        act_mem [0:K-1];
    reg [31:0]        wgt_mem [0:K-1];
    reg [ACC_W-1:0]   expected;
    reg [3:0]         exp_drop;

    reg [4095:0] act_path, wgt_path, exp_path;

    reg               accept = 1'b0, clear = 1'b0;
    reg [15:0]        a = 16'b0;
    reg [W_FMT_W-1:0] b = {W_FMT_W{1'b0}};

    wire [ACC_W-1:0] result;
    wire             dropped;

    integer k;

    ot_mac_lane_fmt #(.W_EXP_BITS(W_EXP_BITS), .W_FRAC_BITS(W_FRAC_BITS)) dut (
        .clk(clk), .rst_n(rst_n), .clear(clear), .accept(accept),
        .a_sign(a[15]), .a_exp(a[14:7]), .a_man({1'b1, a[6:0]}),
        .a_zero(a[14:0] == 15'b0), .b(b), .scale_exp(scale_arg[7:0]),
        .result(result), .dropped(dropped)
    );

    initial begin
        if (!$value$plusargs("act=%s", act_path))  begin $display("FAIL: +act="); $finish; end
        if (!$value$plusargs("wgt=%s", wgt_path))  begin $display("FAIL: +wgt="); $finish; end
        if (!$value$plusargs("exp=%s", exp_path))  begin $display("FAIL: +exp="); $finish; end
        if (!$value$plusargs("scale=%d", scale_arg)) begin $display("FAIL: +scale="); $finish; end
        $readmemh(act_path, act_mem);
        $readmemh(wgt_path, wgt_mem);
        begin : load_expected
            reg [ACC_W-1:0] em [0:1];
            reg [3:0]       dm [0:1];
            $readmemh(exp_path, em);
            expected = em[0];
        end

        repeat (4) @(posedge clk); rst_n = 1'b1;
        @(posedge clk); clear = 1'b1; @(posedge clk); clear = 1'b0;

        // operands are presented registered by the tile in the real design; here
        // they are driven directly, so accept follows two cycles behind.
        for (k = 0; k < K + 3; k = k + 1) begin
            if (k < K) begin
                a = act_mem[k];
                b = wgt_mem[k][W_FMT_W-1:0];
            end
            accept = (k >= 2) && (k < K + 2);
            @(posedge clk);
        end
        accept = 1'b0;
        repeat (6) @(posedge clk);

        if (result === expected)
            $display("PASS E%0dM%0d: accumulator bit-identical to the reference (%010x), dropped=%0d",
                     W_EXP_BITS, W_FRAC_BITS, result, dropped);
        else
            $display("FAIL E%0dM%0d: observed %010x expected %010x dropped=%0d",
                     W_EXP_BITS, W_FRAC_BITS, result, expected, dropped);
        $finish;
    end
endmodule
