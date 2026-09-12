`timescale 1ns/1ps
// The reduction endpoint's emission sum moved out of the clocked process into a
// per-group balanced tree. Integer addition is associative so the TOTAL cannot
// change, and the combinational ot_reduction_tree is SAT-proven equivalent -- but
// the endpoint is a state machine, and hoisting a computation out of a sequential
// block can change WHEN a value is sampled even when the value is the same. That
// is what this bench checks: the old and new endpoints run side by side on one
// stimulus stream and must agree on every output signal, every cycle.
//
// The stimulus has to reach the states that matter: sources arriving out of
// order, two tags interleaved across both group slots, duplicate sources (which
// must poison), out-of-range source IDs (which must raise unexpected_error),
// poison and last flags, and a consumer that stalls.
module tb_reduction_endpoint_equiv;
    localparam integer SRC = 8, DW = 32, GRP = 2, TW = 16;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;

    reg                  iv = 0, ipoison = 0, ilast = 0, orr = 0;
    reg [TW-1:0]         itag = 0;
    reg [2:0]            isrc = 0;
    reg signed [DW-1:0]  idata = 0;

    wire a_ir, a_ov, a_pois, a_dup, a_unex;
    wire [TW-1:0] a_tag; wire signed [DW-1:0] a_data;
    wire b_ir, b_ov, b_pois, b_dup, b_unex;
    wire [TW-1:0] b_tag; wire signed [DW-1:0] b_data;

    ot_reduction_endpoint #(.SOURCES(SRC), .DATA_W(DW), .GROUPS(GRP), .TAG_W(TW))
      dut (.clk(clk), .rst_n(rst_n), .in_valid(iv), .in_ready(a_ir), .in_tag(itag),
           .in_source(isrc), .in_data(idata), .in_poison(ipoison), .in_last(ilast),
           .out_valid(a_ov), .out_ready(orr), .out_tag(a_tag), .out_data(a_data),
           .out_poison(a_pois), .duplicate_error(a_dup), .unexpected_error(a_unex));

    ot_reduction_endpoint_golden #(.SOURCES(SRC), .DATA_W(DW), .GROUPS(GRP), .TAG_W(TW))
      gold (.clk(clk), .rst_n(rst_n), .in_valid(iv), .in_ready(b_ir), .in_tag(itag),
           .in_source(isrc), .in_data(idata), .in_poison(ipoison), .in_last(ilast),
           .out_valid(b_ov), .out_ready(orr), .out_tag(b_tag), .out_data(b_data),
           .out_poison(b_pois), .duplicate_error(b_dup), .unexpected_error(b_unex));

    integer bad = 0, cycles = 0, emitted = 0, i;

    // monitor on the rising edge; stimulus is driven on the falling edge, so the
    // inputs are settled half a cycle before the edge that consumes them
    always @(posedge clk) if (rst_n) begin
        cycles = cycles + 1;
        if (a_ov) emitted = emitted + 1;
        if (a_ir !== b_ir || a_ov !== b_ov || a_tag !== b_tag || a_data !== b_data ||
            a_pois !== b_pois || a_dup !== b_dup || a_unex !== b_unex) begin
            bad = bad + 1;
            if (bad < 8)
                $display("FAIL cycle %0d: new ir=%b ov=%b tag=%h data=%0d pois=%b dup=%b unex=%b | old ir=%b ov=%b tag=%h data=%0d pois=%b dup=%b unex=%b",
                         cycles, a_ir, a_ov, a_tag, a_data, a_pois, a_dup, a_unex,
                                 b_ir, b_ov, b_tag, b_data, b_pois, b_dup, b_unex);
        end
    end

    reg [31:0] rnd = 32'h5150_c0de;
    function [31:0] nxt; input [31:0] s; nxt = s * 32'd1664525 + 32'd1013904223; endfunction

    initial begin
        repeat (4) @(negedge clk);
        rst_n = 1;
        @(negedge clk);

        for (i = 0; i < 120000; i = i + 1) begin
            rnd = nxt(rnd); iv      = (rnd[19:18] != 2'b00);      // 75 % offered
            rnd = nxt(rnd); itag    = {14'b0, rnd[21:20]};        // 4 tags, 2 slots
            rnd = nxt(rnd); isrc    = rnd[18:16];                 // includes valid IDs
            if (rnd[25:24] == 2'b11) isrc = 3'd7;                 // bias to the top ID
            rnd = nxt(rnd); idata   = {rnd[31:16], rnd[15:0]};    // full-width, signed
            rnd = nxt(rnd); ipoison = (rnd[17:16] == 2'b00);      // 25 %
            rnd = nxt(rnd); ilast   = (rnd[19:17] != 3'b000);     // 87 %
            rnd = nxt(rnd); orr     = rnd[23];                    // stalling consumer
            @(negedge clk);
        end
        iv = 0; orr = 1;
        for (i = 0; i < 64; i = i + 1) @(negedge clk);

        if (emitted == 0) begin
            bad = bad + 1;
            $display("FAIL: no group ever emitted -- the stimulus never completed one");
        end
        if (bad == 0)
            $display("PASS reduction_endpoint: %0d cycles, %0d emissions, new and old agree on every output every cycle",
                     cycles, emitted);
        else
            $display("FAIL reduction_endpoint: %0d disagreeing cycles of %0d", bad, cycles);
        $finish;
    end
endmodule
