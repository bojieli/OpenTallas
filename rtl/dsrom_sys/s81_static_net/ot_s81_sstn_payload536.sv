`timescale 1ns/1ps
// Exact x2 lane of the actual S81 column station: 534 raw payload bits and two
// column-reset valid bits at positions 0 and 4.
// S81-KITS-RTLC 10-24 (owner: register every partition pin, in RTL): every input bit lands in its own pin register
// (hil / lol / validl, same reset class as its output register) before the output stage: 2 flops per bit, +1 cycle per
// column station on the x2 payload.  Mutant OT_SSTN_PAYLOAD_1FLOP_MUT = the pre-fix single stage.
module ot_s81_sstn_payload536 (
    input wire ck, rs,
    input wire [535:0] i,
    output wire [535:0] o
);
    reg [530:0] hi, hil;
    reg [2:0] lo, lol;
    reg [1:0] valid, validl;
`ifdef OT_SSTN_PAYLOAD_1FLOP_MUT
    always @(*) begin hil = i[535:5]; lol = i[3:1]; validl = {i[4], i[0]}; end
`else
    always @(posedge ck) begin hil <= i[535:5]; lol <= i[3:1]; end
    always @(posedge ck or negedge rs)
        if (!rs) validl <= 2'b00;
        else validl <= {i[4], i[0]};
`endif
`ifdef OT_SSTN_PAYLOAD_EDGE_MUT
    always @(negedge ck) begin hi <= hil; lo <= lol; end
`else
    always @(posedge ck) begin hi <= hil; lo <= lol; end
`endif
`ifdef OT_SSTN_PAYLOAD_RESET_MUT
    always @(posedge ck) valid <= validl;
`else
    always @(posedge ck or negedge rs)
        if (!rs) valid <= 2'b00;
        else valid <= validl;
`endif
`ifdef OT_SSTN_PAYLOAD_BIT_MUT
    assign o = {hi, valid[1], lo, valid[0]} ^ (536'b1 << 23);
`else
    assign o = {hi, valid[1], lo, valid[0]};
`endif
endmodule
