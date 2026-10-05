`timescale 1ns/1ps
module tb_v41_w2_y_pack2;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0, in_valid = 0;
    reg [1:0] in_rank = 0;
    reg [6:0] in_word = 0;
    reg [511:0] in_data = 0;
    wire in_ready, out_valid, fault;
    wire [1:0] out_rank;
    wire [5:0] out_word;
    wire [511:0] out_data;
    reg [511:0] unpacked [0:319], packed_exp [0:159];
    integer k, outputs = 0, errors = 0;
    string dir;
    ot_chip_v41x_w2_y_pack2 u_pack (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready),
        .in_rank(in_rank), .in_word(in_word), .in_data(in_data),
        .out_valid(out_valid), .out_ready(1'b1), .out_rank(out_rank),
        .out_word(out_word), .out_data(out_data), .fault(fault));
    initial begin
        if (!$value$plusargs("VEC=%s", dir)) $fatal(1, "missing +VEC");
        $readmemh({dir, "/y_unpacked.hex"}, unpacked);
        $readmemh({dir, "/y_flit.hex"}, packed_exp);
        repeat (4) @(negedge clk);
        rst_n = 1;
        for (k = 0; k < 320; k = k + 1) begin
            @(negedge clk);
            in_valid = 1;
            in_rank = 2'(k / 80);
            in_word = 7'(k % 80);
            in_data = unpacked[k];
            @(posedge clk); #1;
            if (!in_ready) $fatal(1, "unexpected packer backpressure");
            if (out_valid) begin
                if (out_rank !== 2'(outputs / 40) || out_word !== 6'(outputs % 40) ||
                    out_data !== packed_exp[outputs]) errors = errors + 1;
                outputs = outputs + 1;
            end
        end
        @(negedge clk); in_valid = 0;
        @(posedge clk); #1;
        if (out_valid) begin
            if (out_rank !== 2'(outputs / 40) || out_word !== 6'(outputs % 40) ||
                out_data !== packed_exp[outputs]) errors = errors + 1;
            outputs = outputs + 1;
        end
        if (fault || outputs != 160 || errors != 0)
            $fatal(1, "y pack2 failed outputs=%0d errors=%0d fault=%0d", outputs, errors, fault);
        $display("Y_PACK2_PASS real_l0_200k input_words=320 packed_flits=160 mismatches=0");
        $finish;
    end
endmodule
