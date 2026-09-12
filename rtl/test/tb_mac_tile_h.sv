`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Campaign for rtl/proto/ot_mac_tile.sv against runtime.reference.mac_tile.
//
// The reference computes the same dot products in Python integers with no
// floating-point arithmetic anywhere, so a disagreement is the RTL's and cannot
// be a host rounding mode. The comparison is per lane over the full
// ACC_W-bit accumulator word, not over a tolerance: block-floating-point
// accumulation is exact by construction, so anything other than bit equality is
// a defect.
//
// The vectors deliberately include an exact zero activation, an exact zero
// weight, and one weight whose product lands far outside the exponent window.
// The last of those must set exactly one lane's dropped bit -- a tile that
// silently loses the term would otherwise pass.
// ---------------------------------------------------------------------------
module tb_mac_tile_h;
    localparam integer LANES      = 16;
    localparam integer K          = 32;
    localparam integer ACC_W      = 40;
    localparam integer EXP_WINDOW = 16;
    localparam [7:0]   SCALE_EXP  = 8'd240;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg [15:0] act_mem [0:K-1];
    reg [15:0] wgt_mem [0:K*LANES-1];
    reg [ACC_W-1:0] expected_mem [0:LANES-1];
    reg [3:0]  dropped_mem [0:LANES-1];

    reg [4095:0] act_path, wgt_path, expected_path, dropped_path;

    reg                clear = 1'b0;
    reg                valid_in = 1'b0;
    reg [15:0]         act = 16'b0;
    reg [16*LANES-1:0] wgt = {(16*LANES){1'b0}};

    wire [ACC_W*LANES-1:0] result;
    wire [LANES-1:0]       dropped_mask;
    wire                   result_valid;

    integer i, k, l, mism, dmism;

    ot_mac_tile_h #(.LANES(LANES), .ACC_W(ACC_W), .EXP_WINDOW(EXP_WINDOW)) dut (
        .clk(clk), .rst_n(rst_n), .clear(clear), .valid_in(valid_in),
        .act(act), .wgt(wgt), .scale_exp(SCALE_EXP),
        .result(result), .dropped_mask(dropped_mask), .result_valid(result_valid)
    );

    initial begin
        if (!$value$plusargs("act=%s", act_path))           begin $display("FAIL: missing +act="); $finish; end
        if (!$value$plusargs("wgt=%s", wgt_path))           begin $display("FAIL: missing +wgt="); $finish; end
        if (!$value$plusargs("expected=%s", expected_path)) begin $display("FAIL: missing +expected="); $finish; end
        if (!$value$plusargs("dropped=%s", dropped_path))   begin $display("FAIL: missing +dropped="); $finish; end
        $readmemh(act_path, act_mem);
        $readmemh(wgt_path, wgt_mem);
        $readmemh(expected_path, expected_mem);
        $readmemh(dropped_path, dropped_mem);

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        @(posedge clk);
        clear = 1'b1; @(posedge clk); clear = 1'b0;

        // stream K activations; one per cycle, weights change with them
        for (k = 0; k < K; k = k + 1) begin
            act = act_mem[k];
            for (l = 0; l < LANES; l = l + 1)
                wgt[16*l +: 16] = wgt_mem[k*LANES + l];
            valid_in = 1'b1;
            @(posedge clk);
        end
        valid_in = 1'b0;

        // drain the five pipeline stages
        repeat (12) @(posedge clk);

        mism = 0; dmism = 0;
        for (l = 0; l < LANES; l = l + 1) begin
            if (result[ACC_W*l +: ACC_W] !== expected_mem[l]) begin
                if (mism < 6)
                    $display("LANE %0d VALUE: observed %010x expected %010x",
                             l, result[ACC_W*l +: ACC_W], expected_mem[l]);
                mism = mism + 1;
            end
            if (dropped_mask[l] !== dropped_mem[l][0]) begin
                $display("LANE %0d DROPPED: observed %0d expected %0d",
                         l, dropped_mask[l], dropped_mem[l][0]);
                dmism = dmism + 1;
            end
        end

        if (mism == 0 && dmism == 0)
            $display("PASS: %0d lanes bit-identical to the scalar reference over K=%0d, dropped flags agree",
                     LANES, K);
        else
            $display("FAIL: %0d value mismatches, %0d dropped-flag mismatches", mism, dmism);
        $finish;
    end
endmodule
