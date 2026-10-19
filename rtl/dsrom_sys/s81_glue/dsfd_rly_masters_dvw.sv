// S81-DV exact-width F1 lane relay stations for the non-276-b die links (stub audit S-9; S81-BIND p4f, extended for
// p4g/p4h/p4i by S81-DIE 10-17: 68-b frame return lanes (p4i; retired p4j: 70 b = the frame ret RTL width), 512-b collective + svc_rs chain lanes, 562-b / 682-b regional
// HBM rd / rq links).  Same body as dsfd_dvrly_276_* (ot_s81_rly RSREG=1: one register stage, rs = the regional reset
// relay leaf, released through the reset pin register; ck = the lane's forwarded clock; ck_o = ck through the kept
// ot_dvrly_ckinv pair = station k+1 ck).  <dir> = in face, out face.  GENERATED (one module per width x direction).
// Views owed: ref_tile kits s81dv_rly_<W>_<dir> cloned from s81dv_rly_276_* (recipe 4, hold_budget die).
`default_nettype none
module dsfd_dvrly_68_EW (input wire ck, input wire rs, input wire [67:0] i, output wire [67:0] o, output wire ck_o);
    ot_s81_rly #(.W(68), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_68_WE (input wire ck, input wire rs, input wire [67:0] i, output wire [67:0] o, output wire ck_o);
    ot_s81_rly #(.W(68), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_68_NS (input wire ck, input wire rs, input wire [67:0] i, output wire [67:0] o, output wire ck_o);
    ot_s81_rly #(.W(68), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_68_SN (input wire ck, input wire rs, input wire [67:0] i, output wire [67:0] o, output wire ck_o);
    ot_s81_rly #(.W(68), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_70_NS (input wire ck, input wire rs, input wire [69:0] i, output wire [69:0] o, output wire ck_o);
    ot_s81_rly #(.W(70), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_70_SN (input wire ck, input wire rs, input wire [69:0] i, output wire [69:0] o, output wire ck_o);
    ot_s81_rly #(.W(70), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_512_EW (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o, output wire ck_o);
    ot_s81_rly #(.W(512), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_512_WE (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o, output wire ck_o);
    ot_s81_rly #(.W(512), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_512_NS (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o, output wire ck_o);
    ot_s81_rly #(.W(512), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_512_SN (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o, output wire ck_o);
    ot_s81_rly #(.W(512), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_562_EW (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o, output wire ck_o);
    ot_s81_rly #(.W(562), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_562_WE (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o, output wire ck_o);
    ot_s81_rly #(.W(562), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_562_NS (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o, output wire ck_o);
    ot_s81_rly #(.W(562), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_562_SN (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o, output wire ck_o);
    ot_s81_rly #(.W(562), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_682_EW (input wire ck, input wire rs, input wire [681:0] i, output wire [681:0] o, output wire ck_o);
    ot_s81_rly #(.W(682), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_682_WE (input wire ck, input wire rs, input wire [681:0] i, output wire [681:0] o, output wire ck_o);
    ot_s81_rly #(.W(682), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_682_NS (input wire ck, input wire rs, input wire [681:0] i, output wire [681:0] o, output wire ck_o);
    ot_s81_rly #(.W(682), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_682_SN (input wire ck, input wire rs, input wire [681:0] i, output wire [681:0] o, output wire ck_o);
    ot_s81_rly #(.W(682), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
`default_nettype wire
