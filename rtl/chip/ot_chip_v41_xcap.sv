// ot_chip_v41_xcap -- 50% concurrent-pair cap of the V4.1 ROM field (W18), at the x-broadcast root.
//
// Mechanism (RTL terms):
//   * every pair carries one static configuration bit ``ph`` = (pair column + pair row) mod 2, written with
//     its other configuration at load (a checkerboard at pair granularity, so every cluster and every IR
//     window draws half its pairs: interleaved, not per region);
//   * the x broadcast gains one wire, ``xs_sub``.  In capped mode this module, between the x root (SU) and
//     the spine, emits every x word twice, first with xs_sub = 0 then with xs_sub = 1, and back-pressures the
//     root for the second beat; uncapped, each word goes out once with xs_sub = 0 and every pair takes it;
//   * a pair consumes a word when the beat transfers (xs_v && xs_rdy) and (xs_cap ? xs_sub == ph : !xs_sub) -- ot_chip_v41_xcap_take below,
//     one comparator in the element's x capture;
//   * the cap is per op: the root asserts ``in_cap`` with the words of a field-wide op (the model's six per
//     layer); narrow ops stay uncapped.
// Effect: on any cycle at most the pairs of one parity consume x and read their ROM, so the field draws
// half its busy current, spatially uniform; a capped op takes twice its x-issue cycles (priced by W16).
module ot_chip_v41_xcap #(
    parameter int W = 549
) (
    input  logic         clk,
    input  logic         rst_n,
    input  logic         in_v,
    output logic         in_rdy,
    input  logic         in_cap,
    input  logic [W-1:0] in_d,
    output logic         xs_v,
    output logic         xs_sub,
    output logic         xs_cap,      // the op's cap flag travels with the word
    output logic [W-1:0] xs_d,
    input  logic         xs_rdy       // the spine's first station (registered, credit-free when 1)
);
    logic         held;              // the second (sub = 1) beat of a capped word is pending
    logic [W-1:0] d_q;
    assign in_rdy = xs_rdy && !held;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            xs_v <= 1'b0; xs_sub <= 1'b0; xs_cap <= 1'b0; held <= 1'b0;
        end else if (xs_rdy) begin
            if (held) begin
                xs_v <= 1'b1; xs_sub <= 1'b1; held <= 1'b0;
            end else if (in_v) begin
                xs_v <= 1'b1; xs_sub <= 1'b0; xs_cap <= in_cap; held <= in_cap;
            end else begin
                xs_v <= 1'b0; xs_sub <= 1'b0;
            end
        end
    end
    always_ff @(posedge clk) if (xs_rdy && !held && in_v) d_q <= in_d;
    assign xs_d = d_q;
endmodule

// The element-side filter: whether this pair takes the word on the bus this cycle.
module ot_chip_v41_xcap_take (
    input  logic xs_v,
    input  logic xs_sub,
    input  logic cap,     // the op's cap flag, carried with the word (xs control) or latched per op
    input  logic ph,      // the pair's static parity (configuration)
    output logic take
);
    assign take = xs_v && (cap ? (xs_sub == ph) : !xs_sub);
endmodule
