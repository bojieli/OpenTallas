// S81-DV p4c-lanes (claude/s81dv-1016 d5a2a52ca): straight 276-b lane relay stations, one register stage, flop-first
// (recipe 4, hold_budget die).  Same body as the rs1s56 relays (ot_s81_rly, reset pin register RSREG=1); ck is the
// lane's forwarded clock.  Own names: dsfd_rly_276_EW/WE (gth-lane, recipe 1) stay byte-identical.  <fi><fo> = in face, out face.
`default_nettype none
module dsfd_dvrly_276_EW (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o, output wire ck_o);
    ot_s81_rly #(.W(276), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_276_WE (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o, output wire ck_o);
    ot_s81_rly #(.W(276), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_276_NS (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o, output wire ck_o);
    ot_s81_rly #(.W(276), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_276_SN (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o, output wire ck_o);
    ot_s81_rly #(.W(276), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
// ck_o (S81-DV 10-17, DIE-CLOCK F1: station k+1 ck = station k ck_o on a single-sink hop net): the lane's forwarded
// clock re-driven non-inverted by two KEPT inverter cells (the dsfd_stnv_566x1 fn0 form), so the ETM carries the
// ck -> ck_o arc and the next station captures on the same phase.  Kept hierarchy: flattened, yosys would fold the
// inverter pair into a wire (no cell, no drive).
(* keep_hierarchy *)
module ot_dvrly_ckinv (input wire a, output wire y);
    assign y = ~a;
endmodule
`default_nettype wire
