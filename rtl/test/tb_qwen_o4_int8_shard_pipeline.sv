`timescale 1ns/1ps
module tb_qwen_o4_int8_shard_pipeline;
    reg clk = 0, rst_n = 0, ce = 0;
    always #5 clk = ~clk;
    reg [12:0] addr = 0;
    reg [31:0] x = 0;
    reg [4:0] lane = 0;
    wire valid, fault;
    wire [31:0] product;
    ot_qwen_o4_int8_shard #(.VIAMAP("via.mem")) dut (
        .clk(clk), .rst_n(rst_n), .ce_in(ce), .addr_in(addr),
        .x_bf16(x), .lane_sel(lane), .scale_valid(1'b0),
        .completed_sum(32'd0), .row_scale_bf16(16'd0),
        .product_out_valid(valid), .product(product), .product_fault(fault),
        .scaled_out_valid(), .scaled_result(), .scale_fault()
    );
    // Request records: CE, ROM address, two group BF16 activations, lane,
    // expected FP32 product.
    reg [82:0] req [0:127];
    reg [31:0] expected [0:6];
    reg expected_valid [0:6];
    integer i, j, checked = 0;
    initial begin
        $readmemh("requests.mem", req);
        for (j = 0; j < 7; j = j + 1) begin
            expected[j] = 0;
            expected_valid[j] = 0;
        end
        repeat (3) @(negedge clk);
        rst_n = 1;
        for (i = 0; i < 135; i = i + 1) begin
            if (i < 128) begin
                {ce, addr, x, lane, expected[0]} = req[i];
                expected_valid[0] = ce;
            end else begin
                ce = 0;
                expected_valid[0] = 0;
            end
            @(posedge clk);
            #1;
            if (valid !== expected_valid[6])
                $fatal(1, "valid at request %0d got %b expected %b", i-6, valid, expected_valid[6]);
            if (expected_valid[6]) begin
                checked = checked + 1;
                if (product !== expected[6] || fault)
                    $fatal(1, "product at request %0d got %h expected %h fault %b",
                           i-6, product, expected[6], fault);
            end
            for (j = 6; j > 0; j = j - 1) begin
                expected[j] = expected[j-1];
                expected_valid[j] = expected_valid[j-1];
            end
            @(negedge clk);
        end
        if (checked != 112) $fatal(1, "checked %0d instead of 112", checked);
        $display("PASS Qwen INT8 ROM shard: %0d exact streamed products, 7-edge latency", checked);
        $finish;
    end
endmodule
