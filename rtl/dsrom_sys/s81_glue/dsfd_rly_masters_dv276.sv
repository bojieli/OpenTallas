// S81-DV p4c-lanes (claude/s81dv-1016 d5a2a52ca): straight 276-b lane relay stations, one register stage, flop-first
// (recipe 4, hold_budget die).  Same body as the rs1s56 relays (ot_s81_rly, reset pin register RSREG=1); ck is the
// lane's forwarded clock.  Own names: dsfd_rly_276_EW/WE (gth-lane, recipe 1) stay byte-identical.  <fi><fo> = in face, out face.
`default_nettype none
module dsfd_dvrly_276_EW (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o);
    ot_s81_rly #(.W(276), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module dsfd_dvrly_276_WE (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o);
    ot_s81_rly #(.W(276), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module dsfd_dvrly_276_NS (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o);
    ot_s81_rly #(.W(276), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module dsfd_dvrly_276_SN (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o);
    ot_s81_rly #(.W(276), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
`default_nettype wire
