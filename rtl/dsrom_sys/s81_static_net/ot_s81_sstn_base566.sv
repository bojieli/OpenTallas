`timescale 1ns/1ps
// Canonical superset of all five S81 column-station base roles.  Missing role
// controls are explicitly strapped zero by the static die composition.  One
// production edge, immediate asynchronous clear only for the declared controls.
// S81-KITS-RTLB 10-24 (owner: register every pin, in RTL): the status inputs e0 e1 c0 c1 si nf land in their own pin
// registers (column reset, like status) before the OR, so every input bit loads exactly one flop: so = OR of the
// inputs two edges earlier (+1 cycle on the status chain only; cc / xa / xb keep their single production edge).
// Mutants: OT_SSTN_BASE_CONTROL_MUT (nf dropped), OT_SSTN_BASE_STATUS_UNREG_MUT (pre-fix: inputs ORed at the pin).
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
    reg [1:0] e0l, e1l, c0l, c1l, sil;     // status input pin registers
    reg nfl;
    always @(posedge ck) begin ra <= xai[281:0]; rb <= xbi; end
    always @(posedge ck or negedge rs)
        if (!rs) begin
            xv <= 1'b0; rc <= 15'd0; status <= 2'b00;
            e0l <= 2'b00; e1l <= 2'b00; c0l <= 2'b00; c1l <= 2'b00; sil <= 2'b00; nfl <= 1'b0;
        end
        else begin
            xv <= xai[282]; rc <= cci;
            e0l <= e0; e1l <= e1; c0l <= c0; c1l <= c1; sil <= si; nfl <= nf;
`ifdef OT_SSTN_BASE_CONTROL_MUT
            status <= e0l | e1l | c0l | c1l | sil; // mutant omits nf bit
`elsif OT_SSTN_BASE_STATUS_UNREG_MUT
            status <= e0 | e1 | c0 | c1 | si | {nf, 1'b0}; // mutant: pre-fix, inputs ORed at the pin
`else
            status <= e0l | e1l | c0l | c1l | sil | {nfl, 1'b0};
`endif
        end
    assign xa = {xv, ra};
    assign xb = rb;
    assign cc = rc;
    assign so = status;
endmodule
