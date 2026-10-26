`timescale 1ns/1ps
// Canonical superset of all five S81 column-station base roles.  Missing role
// controls are explicitly strapped zero by the static die composition.  One
// production edge, immediate asynchronous clear only for the declared controls.
// S81-KITS-RTLB 10-24 (owner: register every pin, in RTL): the status inputs e0 e1 c0 c1 si nf land in their own pin
// registers (column reset, like status) before the OR, so every input bit loads exactly one flop: so = OR of the
// inputs two edges earlier (+1 cycle on the status chain).
// S81-KITS-RTLC 10-24 (same rule; the column station was a 1-flop pass-through cci->cc / xai->xa / xbi->xb, face_guard
// 'merged'): cci / xai / xbi land in their own pin registers (rcl / xvl column reset like their output registers, ral / rbl
// reset-free like ra / rb) before the output stage: 2 flops per bit, +1 cycle per column station on cc / xa / xb.
// Mutants: OT_SSTN_BASE_CONTROL_MUT (nf dropped), OT_SSTN_BASE_STATUS_UNREG_MUT (pre-fix: inputs ORed at the pin),
// OT_SSTN_BASE_DATA_1FLOP_MUT (pre-RTLC: cc / xa / xb single stage).
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
    reg [281:0] ra, ral;
    reg [265:0] rb, rbl;
    reg xv, xvl;
    reg [14:0] rc, rcl;
    reg [1:0] status;
    reg [1:0] e0l, e1l, c0l, c1l, sil;     // status input pin registers
    reg nfl;
`ifdef OT_SSTN_BASE_DATA_1FLOP_MUT
    always @(*) begin ral = xai[281:0]; rbl = xbi; xvl = xai[282]; rcl = cci; end
`else
    always @(posedge ck) begin ral <= xai[281:0]; rbl <= xbi; end      // data input pin registers (reset-free)
    always @(posedge ck or negedge rs)
        if (!rs) begin xvl <= 1'b0; rcl <= 15'd0; end
        else begin xvl <= xai[282]; rcl <= cci; end
`endif
    always @(posedge ck) begin ra <= ral; rb <= rbl; end
    always @(posedge ck or negedge rs)
        if (!rs) begin
            xv <= 1'b0; rc <= 15'd0; status <= 2'b00;
            e0l <= 2'b00; e1l <= 2'b00; c0l <= 2'b00; c1l <= 2'b00; sil <= 2'b00; nfl <= 1'b0;
        end
        else begin
            xv <= xvl; rc <= rcl;
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
