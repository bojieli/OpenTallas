`timescale 1ns/1ps
module ot_rom_8192x266_m8 (
    input wire clk, input wire ce_in, input wire [12:0] addr_in,
    output reg [265:0] rd_out
);
    always @(posedge clk)
        if (ce_in) rd_out <= {10'd0, {16{16'h3f80}}};
endmodule

module tb_scale_registered_probe;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg valid = 0;
    reg scale_group_re = 0;
    reg [255:0] hbm_scale_word = {16{16'h3f80}};
    reg [511:0] completed_sum = {16{32'h3f800000}};
    wire direct_valid, registered_valid, rom_valid;
    wire direct_fault, registered_fault, rom_fault;
    wire [511:0] direct_result, registered_result, rom_result;
    ot_qwen_o4_scale_ingress_probe #(.HBM_SOURCE(1)) u_direct (
        .clk(clk), .rst_n(rst_n), .valid(valid),
        .scale_group_re(scale_group_re), .rom_addr(13'd0),
        .hbm_scale_word(hbm_scale_word), .completed_sum(completed_sum),
        .out_valid(direct_valid), .scaled_result(direct_result), .fault(direct_fault));
    ot_qwen_o4_scale_registered_probe #(.HBM_SOURCE(1)) u_registered (
        .clk(clk), .rst_n(rst_n), .valid(valid),
        .scale_group_re(scale_group_re), .rom_addr(13'd0),
        .hbm_scale_word(hbm_scale_word), .completed_sum(completed_sum),
        .out_valid(registered_valid), .scaled_result(registered_result),
        .fault(registered_fault));
    ot_qwen_o4_scale_registered_probe #(.HBM_SOURCE(0)) u_registered_rom (
        .clk(clk), .rst_n(rst_n), .valid(valid),
        .scale_group_re(scale_group_re), .rom_addr(13'd0),
        .hbm_scale_word(hbm_scale_word), .completed_sum(completed_sum),
        .out_valid(rom_valid), .scaled_result(rom_result), .fault(rom_fault));
    reg prior_valid = 0;
    reg [511:0] prior_result;
    reg prior_fault;
    integer seen = 0;
    always @(posedge clk) begin
        #1;
        if (registered_valid) begin
            if (!prior_valid || registered_result !== prior_result ||
                registered_fault !== prior_fault)
                $fatal(1, "registered scale result is not the direct result delayed one cycle");
            if (rom_valid !== registered_valid || rom_result !== registered_result ||
                rom_fault !== registered_fault)
                $fatal(1, "registered ROM and HBM scale boundaries differ");
            seen = seen + 1;
        end
        prior_valid = direct_valid;
        prior_result = direct_result;
        prior_fault = direct_fault;
    end
    initial begin
        repeat (3) @(negedge clk);
        rst_n = 1;
        scale_group_re = 1;
        repeat (2) @(negedge clk);
        valid = 1;
        repeat (2) @(negedge clk);
        valid = 0;
        repeat (12) @(negedge clk);
        if (seen != 2) $fatal(1, "expected two registered results, saw %0d", seen);
        $display("PASS: two 16-lane ROM/HBM products, exact +1-cycle shift");
        $finish;
    end
endmodule
