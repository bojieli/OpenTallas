`timescale 1ns/1ps
module tb_v41_w2_pack4;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg in_valid = 0;
    reg [1:0] in_rank = 0;
    reg [2:0] in_expert = 0;
    reg [5:0] in_word = 0;
    reg [511:0] in_data = 0;
    wire in_ready, out_valid, fault;
    wire [1:0] out_rank;
    wire [6:0] out_word;
    wire [511:0] out_data;
    reg [511:0] unpacked [0:1063], packed_exp [0:307];
    integer k, outputs = 0, errors = 0;
    string dir;
    ot_chip_v41x_w2_pack4 u_pack (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready),
        .in_rank(in_rank), .in_expert(in_expert), .in_word(in_word), .in_data(in_data),
        .out_valid(out_valid), .out_ready(1'b1), .out_rank(out_rank),
        .out_word(out_word), .out_data(out_data), .fault(fault));
    initial begin
        if (!$value$plusargs("VEC=%s", dir)) $fatal(1, "missing +VEC");
        $readmemh({dir, "/unpacked.hex"}, unpacked);
        $readmemh({dir, "/act_flit.hex"}, packed_exp);
        repeat (4) @(negedge clk);
        rst_n = 1;
        for (k = 0; k < 1064; k = k + 1) begin
            @(negedge clk);
            in_valid = 1;
            in_rank = 2'(k / 266);
            in_expert = 3'((k % 266) / 38);
            in_word = 6'(k % 38);
            in_data = unpacked[k];
            @(posedge clk); #1;
            if (!in_ready) $fatal(1, "unexpected packer backpressure");
            if (out_valid) begin
                if (out_rank !== 2'(outputs / 77) || out_word !== 7'(outputs % 77) ||
                    out_data !== packed_exp[outputs]) begin
                    errors = errors + 1;
                    if (errors < 5) $display("PACK_ERROR output=%0d rank=%0d word=%0d", outputs, out_rank, out_word);
                end
                outputs = outputs + 1;
            end
        end
        @(negedge clk); in_valid = 0;
        @(posedge clk); #1;
        if (out_valid) begin
            if (out_rank !== 2'(outputs / 77) || out_word !== 7'(outputs % 77) ||
                out_data !== packed_exp[outputs]) errors = errors + 1;
            outputs = outputs + 1;
        end
        if (fault || outputs != 308 || errors != 0)
            $fatal(1, "pack4 failed outputs=%0d errors=%0d fault=%0d", outputs, errors, fault);
        $display("PACK4_PASS real_l0_200k input_words=1064 packed_flits=308 mismatches=0");
        $finish;
    end
endmodule
