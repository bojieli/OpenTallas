`timescale 1ns/1ps
// Exact x2 lane of the actual S81 column station: 534 raw payload bits and two
// column-reset valid bits at positions 0 and 4.  No production stage is added.
module ot_s81_sstn_payload536 (
    input wire ck, rs,
    input wire [535:0] i,
    output wire [535:0] o
);
    reg [530:0] hi;
    reg [2:0] lo;
    reg [1:0] valid;
`ifdef OT_SSTN_PAYLOAD_EDGE_MUT
    always @(negedge ck) begin hi <= i[535:5]; lo <= i[3:1]; end
`else
    always @(posedge ck) begin hi <= i[535:5]; lo <= i[3:1]; end
`endif
`ifdef OT_SSTN_PAYLOAD_RESET_MUT
    always @(posedge ck) valid <= {i[4], i[0]};
`else
    always @(posedge ck or negedge rs)
        if (!rs) valid <= 2'b00;
        else valid <= {i[4], i[0]};
`endif
`ifdef OT_SSTN_PAYLOAD_BIT_MUT
    assign o = {hi, valid[1], lo, valid[0]} ^ (536'b1 << 23);
`else
    assign o = {hi, valid[1], lo, valid[0]};
`endif
endmodule
