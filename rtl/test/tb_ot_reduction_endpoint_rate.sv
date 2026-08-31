`timescale 1ns/1ps
// Throughput measurement for the routed reduction endpoint.
//
// ``ot_reduction_endpoint`` is one of the two blocks with a full place-and-route
// result in both the SKY130 and the ASAP7 view, so its *rate* is worth knowing
// as precisely as its *frequency*.  This bench answers exactly one question:
// back to back, with the downstream always ready, how many source flits --
// which is what ``runtime/sim`` counts as ``reduction.elements`` -- does one
// endpoint retire per clock?  That number is what
// ``runtime/cycle/machine.py`` calls ``engine.reduction.work_per_lane_cycle``,
// and until now it was a hand-written 1.0 with nothing behind it.
//
// Stimulus changes on the negative edge.  Driving inputs at the same
// simulation time as the sampling edge is a race whose result differs between
// simulators, and this bench exists to produce a number two simulators agree
// on.
//
// The bench also refuses a wrong answer rather than reporting a fast one: an
// endpoint that dropped or duplicated a flit would retire fewer results in
// fewer cycles and look better, so the result count and the error flags are
// checked before the rate is printed.
module tb_ot_reduction_endpoint_rate;
    localparam integer SOURCES = 8;
    localparam integer GROUPS  = 2;
    localparam integer DATA_W  = 32;
    localparam integer TAG_W   = 16;
    localparam integer BATCHES = 512;   // groups of SOURCES flits

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    reg in_valid = 1'b0;
    reg [TAG_W-1:0] in_tag = 0;
    reg [2:0] in_source = 0;
    reg signed [DATA_W-1:0] in_data = 0;
    reg in_poison = 1'b0;
    reg in_last = 1'b0;
    wire in_ready;
    wire out_valid;
    reg  out_ready = 1'b1;
    wire [TAG_W-1:0] out_tag;
    wire signed [DATA_W-1:0] out_data;
    wire out_poison, duplicate_error, unexpected_error;

    integer cycles = 0;
    integer flits = 0;
    integer results = 0;
    integer started = 0;

    ot_reduction_endpoint #(
        .SOURCES(SOURCES), .DATA_W(DATA_W), .GROUPS(GROUPS), .TAG_W(TAG_W)
    ) dut (
        .clk(clk), .rst_n(rst_n),
        .in_valid(in_valid), .in_ready(in_ready), .in_tag(in_tag),
        .in_source(in_source), .in_data(in_data), .in_poison(in_poison),
        .in_last(in_last),
        .out_valid(out_valid), .out_ready(out_ready), .out_tag(out_tag),
        .out_data(out_data), .out_poison(out_poison),
        .duplicate_error(duplicate_error), .unexpected_error(unexpected_error)
    );

    always #0.5 clk = ~clk;

    integer b, s;
    initial begin
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        @(negedge clk);
        started = 1;
        for (b = 0; b < BATCHES; b = b + 1) begin
            for (s = 0; s < SOURCES; s = s + 1) begin
                in_valid  = 1'b1;
                in_tag    = b[TAG_W-1:0];
                in_source = s[2:0];
                in_data   = b + s;
                in_last   = (s == SOURCES - 1);
                @(posedge clk);
                if (in_valid && in_ready) flits = flits + 1;
                @(negedge clk);
            end
        end
        in_valid = 1'b0;
        in_last = 1'b0;
        // Let the last group drain.
        repeat (8) @(posedge clk);
        started = 0;
        if (duplicate_error || unexpected_error) begin
            $display("FAIL: duplicate=%0d unexpected=%0d flits=%0d results=%0d",
                     duplicate_error, unexpected_error, flits, results);
            $finish;
        end
        if (results != BATCHES) begin
            $display("FAIL: emitted %0d results, expected %0d", results, BATCHES);
            $finish;
        end
        $display("PASS: reduction endpoint SOURCES=%0d GROUPS=%0d flits=%0d results=%0d cycles=%0d elements_per_cycle=%f",
                 SOURCES, GROUPS, flits, results, cycles, flits * 1.0 / cycles);
        $finish;
    end

    always @(posedge clk) begin
        if (started) cycles <= cycles + 1;
        if (out_valid && out_ready) results <= results + 1;
    end
endmodule
