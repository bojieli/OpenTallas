// GENERATED (S-ELEM ENGRAM-LKP 1815, 2026-10-16) from the closed sibling masters for the S81 c26l die census stand-ins
// with no closed view: dsfd_rly_536_EN (275 instances), dsfd_rly_66_SW (46), dsfd_rly_66_EN (46). Same body as the closed
// rs1s56 536 standards / r4 66 masters: one register stage, reset pin register (RSREG=1). Own file so the sources of
// the closed kits (dsfd_rly_masters_536.sv, dsfd_rly_masters_gen18.sv) stay byte-identical.
`default_nettype none
module dsfd_rly_536_EN (input wire ck, input wire rs, input wire [535:0] i, output wire [535:0] o);
    ot_s81_rly #(.W(536), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module dsfd_rly_66_SW (input wire ck, input wire rs, input wire [65:0] i, output wire [65:0] o);
    ot_s81_rly #(.W(66), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module dsfd_rly_66_EN (input wire ck, input wire rs, input wire [65:0] i, output wire [65:0] o);
    ot_s81_rly #(.W(66), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
`default_nettype wire
