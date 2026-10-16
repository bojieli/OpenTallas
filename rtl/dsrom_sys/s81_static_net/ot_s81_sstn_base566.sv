`timescale 1ns/1ps
// Canonical superset of all five S81 column-station base roles.  Missing role
// controls are explicitly strapped zero by the static die composition.  One
// production edge, immediate asynchronous clear only for the declared controls.
module ot_s81_sstn_base566 (
    input wire ck, rs,
    input wire [14:0] cci,
    input wire [282:0] xai,
    input wire [265:0] xbi,
    input wire [1:0] e0, e1, c0, c1, si,
    input wire nf,
    output wire [14:0] cc,
    output wire [282:0] xa,
    output wire [265:0] xb,
    output wire [1:0] so
);
    reg [281:0] ra;
    reg [265:0] rb;
    reg xv;
    reg [14:0] rc;
    reg [1:0] status;
    always @(posedge ck) begin ra <= xai[281:0]; rb <= xbi; end
    always @(posedge ck or negedge rs)
        if (!rs) begin xv <= 1'b0; rc <= 15'd0; status <= 2'b00; end
        else begin
            xv <= xai[282]; rc <= cci;
`ifdef OT_SSTN_BASE_CONTROL_MUT
            status <= e0 | e1 | c0 | c1 | si; // mutant omits nf bit
`else
            status <= e0 | e1 | c0 | c1 | si | {nf, 1'b0};
`endif
        end
    assign xa = {xv, ra};
    assign xb = rb;
    assign cc = rc;
    assign so = status;
endmodule
