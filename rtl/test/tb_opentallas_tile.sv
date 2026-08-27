`timescale 1ns/1ps

module tb_opentallas_tile;
    reg clk = 1'b0;
    reg rst_n = 1'b0;
    reg in_valid = 1'b0;
    reg [3:0] selected_expert_ids = 4'b0;
    reg [1:0] selected_valid = 2'b0;
    reg [1:0] word_index = 2'b0;
    reg [31:0] activations = 32'b0;
    wire out_valid;
    wire signed [31:0] partial_sum;
    integer failures = 0;

    always #5 clk = ~clk;

    opentallas_tile #(
        .NUM_EXPERTS(4),
        .TOP_K(2),
        .WORDS_PER_EXPERT(4),
        .LANES(4),
        .ACT_W(8),
        .WEIGHT_W(8),
        .ACC_W(32),
        .INIT_FILE("test/weights.hex")
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(in_valid),
        .selected_expert_ids(selected_expert_ids),
        .selected_valid(selected_valid),
        .word_index(word_index),
        .activations(activations),
        .out_valid(out_valid),
        .partial_sum(partial_sum)
    );

    task issue_and_check;
        input [1:0] expert0;
        input [1:0] expert1;
        input [1:0] valids;
        input [1:0] word;
        input signed [31:0] expected;
        begin
            @(negedge clk);
            selected_expert_ids = {expert1, expert0};
            selected_valid = valids;
            word_index = word;
            // Lane order in the flattened bus is [lane3 ... lane0].
            activations = {8'sd4, 8'sd3, 8'sd2, 8'sd1};
            in_valid = 1'b1;
            @(negedge clk);
            in_valid = 1'b0;
            wait(out_valid === 1'b1);
            #1;
            if (partial_sum !== expected) begin
                $display("FAIL word=%0d ids=%0d,%0d got=%0d expected=%0d",
                         word, expert0, expert1, partial_sum, expected);
                failures = failures + 1;
            end
            @(negedge clk);
        end
    endtask

    initial begin
        repeat (3) @(negedge clk);
        rst_n = 1'b1;
        issue_and_check(2'd0, 2'd2, 2'b11, 2'd0, 32'sd140);
        issue_and_check(2'd1, 2'd0, 2'b01, 2'd0, 32'sd70);
        issue_and_check(2'd0, 2'd1, 2'b11, 2'd1, 32'sd15);
        issue_and_check(2'd0, 2'd1, 2'b00, 2'd0, 32'sd0);
        if (failures == 0) begin
            $display("PASS: wordline mask, interleaved ROM, and signed MAC pipeline");
            $finish;
        end
        $fatal(1, "%0d checks failed", failures);
    end
endmodule
