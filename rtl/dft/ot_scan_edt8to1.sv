// Additive opt-in linear scan decompressor and space compactor.
// Tester sets pattern_reset with scan_en=1 on the first unload/load edge.
// That edge shifts zero into every chain and observes its OLD output; it
// clears only the codec state. Follow it by L encoded load edges. Never use
// an extra functional capture edge to seed/reset the codec.
// chain_in and edt_out are PREEDGE combinational values. The caller owns
// actual scan clock/ICG/test-mode binding and capture; this module adds none.
// Unknown responses propagate through XOR; the encoder's expected-known mask
// cannot credit an aliased or unknown signature as fault detection.
module ot_scan_edt8to1 #(
    parameter bit ENABLE = 1'b0,
    parameter integer CHAIN_COUNT = 32,
    parameter integer CHANNELS = 4
) (
    input wire clk,
    input wire rst_n,
    input wire pattern_reset,
    input wire scan_en,
    input wire [CHANNELS-1:0] edt_in,
    input wire [CHAIN_COUNT-1:0] chain_out,
    output wire [CHAIN_COUNT-1:0] chain_in,
    output wire [CHANNELS-1:0] edt_out
);
    generate if (ENABLE) begin : on
        if (CHANNELS < 1 || CHANNELS > 16 || CHAIN_COUNT < CHANNELS)
            initial $fatal(1, "Invalid EDT channel/chain dimensions");
        reg [63:0] state_q;
        wire [CHANNELS-1:0] feedback;
        for (genvar j=0; j<CHANNELS; j=j+1) begin : f
            assign feedback[j] = state_q[64-CHANNELS+j] ^
                                 state_q[32+j] ^ state_q[16+j] ^ edt_in[j];
        end
        always @(posedge clk) begin
            if (!rst_n || pattern_reset) state_q <= 64'd0;
            else if (scan_en) state_q <= {state_q[63-CHANNELS:0], feedback};
        end
        for (genvar c=0; c<CHAIN_COUNT; c=c+1) begin : p
            assign chain_in[c] = scan_en && !pattern_reset &&
                (state_q[(7*c)%64] ^ state_q[(7*c+19)%64] ^
                 state_q[(7*c+43)%64] ^ edt_in[c%CHANNELS]);
        end
        reg [CHANNELS-1:0] compact;
        integer c;
        always @* begin
            compact = {CHANNELS{1'b0}};
            for (c=0; c<CHAIN_COUNT; c=c+1)
                compact[c%CHANNELS] = compact[c%CHANNELS] ^ chain_out[c];
        end
        assign edt_out = scan_en ? compact : {CHANNELS{1'b0}};
    end else begin : off
        assign chain_in = {CHAIN_COUNT{1'b0}};
        assign edt_out = {CHANNELS{1'b0}};
    end endgenerate
endmodule
