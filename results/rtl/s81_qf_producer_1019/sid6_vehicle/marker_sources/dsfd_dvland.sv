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
// LANDFIX-SQ (10-18): long-lane landing (S81 p4l lanes with E > 7 or a TT/FF arrival spread > ~2.5 ns: host plane
// hf/ht 24 mm E 28 spread 4.5 ns, seqhost job/jd/cw E 11-16, cross-tier tv E 8/9): D = 8 (window 8 T = 6.7 ns) and a
// 6-bit K strap (K = E + G - R0 up to 63, no reset-calendar offset).  Same ports as dsfd_dvland_276 except k[5:0].
`default_nettype none
module dsfd_dvland_276l (input wire ck_f, input wire [275:0] i, input wire ck, input wire rs, input wire [5:0] k, output wire [275:0] o, output wire fault);
    ot_s81_land #(.W(276), .D(8), .KW(6)) u (.ck_f(ck_f), .i(i), .ck(ck), .rs(rs), .k(k), .o(o), .fault(fault));
endmodule
`default_nettype wire
