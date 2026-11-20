`timescale 1ns/1ps
module tb_svc_wq_capture;
    parameter integer MUTANT = 0;
    reg clk = 0;
    always #0.5 clk = ~clk;

    reg [340:0] heads [0:2];
    reg [340:0] read_req;
    reg valid;
    reg [2:0] source;
    reg [2:0] old_source;
    reg [340:0] reference_req;
    wire [340:0] request;
    always @(posedge clk) begin
        old_source <= source;
        if (!valid) reference_req <= '0;
        else if (source <= 2) reference_req <= heads[source];
        else reference_req <= read_req;
    end

    dsdv_svc_wq_capture dut (
        .clk(clk), .head_0(heads[0]), .head_1(heads[1]), .head_2(heads[2]),
        .valid(valid), .source(MUTANT ? old_source : source), .read_req(read_req),
        .request(request));

    integer mismatches = 0;
    initial begin
        for (int i = 0; i < 2048; i++) begin
            @(negedge clk);
            valid = i % 7 != 0;
            source = i % 4 == 3 ? 3'd7 : 3'(i % 4);
            for (int g = 0; g < 3; g++)
                for (int b = 0; b < 341; b++)
                    heads[g][b] = 1'((i >> (b % 11)) ^ (b >> g) ^ g);
            read_req = {341{1'b1}} ^ heads[0];
            @(posedge clk);
            #0.01;
            if (request !== reference_req) mismatches++;
        end
        if ((mismatches != 0) != (MUTANT != 0))
            $fatal(1, "WQ capture mutant=%0d mismatches=%0d", MUTANT, mismatches);
        $display("PASS WQ capture mutant=%0d checks=2048 mismatches=%0d", MUTANT, mismatches);
        $finish;
    end
endmodule
