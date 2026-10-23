// S81-DV 70-b horizontal lane relay stations (FT-S81 10-23: feedthrough stations inside the S81 frames carry the 70-b
// frame return lanes E<->W across a frame column).  Same body as dsfd_dvrly_70_NS / _SN (dsfd_rly_masters_dvw.sv) and
// dsfd_dvrly_276_EW / _WE (dsfd_rly_masters_dv276.sv): ot_s81_rly W=70 RSREG=1 = one register stage per bit (full cycle),
// rs = the regional reset relay leaf, released through the reset pin register; ck = the lane's forwarded clock;
// ck_o = ck through the kept ot_dvrly_ckinv pair = station k+1 ck.  <dir> = in face, out face.
// New file so the closed kits bound to dsfd_rly_masters_dv276.sv / dsfd_rly_masters_dvw.sv stay byte-identical.
// Views: ref_tile kits s81dv_rly_70_ew / s81dv_rly_70_we (tools/s81_ctrl/gen_dvrly70h_kits.py).
`default_nettype none
module dsfd_dvrly_70_EW (input wire ck, input wire rs, input wire [69:0] i, output wire [69:0] o, output wire ck_o);
    ot_s81_rly #(.W(70), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
module dsfd_dvrly_70_WE (input wire ck, input wire rs, input wire [69:0] i, output wire [69:0] o, output wire ck_o);
    ot_s81_rly #(.W(70), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
`default_nettype wire
