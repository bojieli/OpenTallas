`timescale 1ns/1ps
`default_nettype none
// S81-LAND lane-tail landing tiles, one hardened view per S81-DV lane width (ot_s81_land, D = 4).  k[2:0] = the lane's
// read offset K, an identity STRAP tied by the die binder from the die STA (one K per lane, the same at TT and FF).
// Ports: ck_f / i = the last relay station's ck_o / o; ck / rs = the receiving block's root clock and regional reset;
// o -> the block's input pins (abutted face); fault -> the block's sticky fault OR.  LANDING-CONTRACT.md.
module dsfd_dvland_70  (input wire ck_f, input wire [69:0]  i, input wire ck, input wire rs, input wire [2:0] k, output wire [69:0]  o, output wire fault);
    ot_s81_land #(.W(70),  .D(4)) u (.ck_f(ck_f), .i(i), .ck(ck), .rs(rs), .k(k), .o(o), .fault(fault));
endmodule
module dsfd_dvland_276 (input wire ck_f, input wire [275:0] i, input wire ck, input wire rs, input wire [2:0] k, output wire [275:0] o, output wire fault);
    ot_s81_land #(.W(276), .D(4)) u (.ck_f(ck_f), .i(i), .ck(ck), .rs(rs), .k(k), .o(o), .fault(fault));
endmodule
module dsfd_dvland_512 (input wire ck_f, input wire [511:0] i, input wire ck, input wire rs, input wire [2:0] k, output wire [511:0] o, output wire fault);
    ot_s81_land #(.W(512), .D(4)) u (.ck_f(ck_f), .i(i), .ck(ck), .rs(rs), .k(k), .o(o), .fault(fault));
endmodule
module dsfd_dvland_562 (input wire ck_f, input wire [561:0] i, input wire ck, input wire rs, input wire [2:0] k, output wire [561:0] o, output wire fault);
    ot_s81_land #(.W(562), .D(4)) u (.ck_f(ck_f), .i(i), .ck(ck), .rs(rs), .k(k), .o(o), .fault(fault));
endmodule
module dsfd_dvland_682 (input wire ck_f, input wire [681:0] i, input wire ck, input wire rs, input wire [2:0] k, output wire [681:0] o, output wire fault);
    ot_s81_land #(.W(682), .D(4)) u (.ck_f(ck_f), .i(i), .ck(ck), .rs(rs), .k(k), .o(o), .fault(fault));
endmodule
`default_nettype wire
