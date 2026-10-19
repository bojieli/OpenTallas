// S81-LAND2 10-17 (lanes/LANDING-CONTRACT.md H3, hold fix (a)): HALF-CYCLE forwarded-clock lane relay stations.
// ot_dvrly_st #(W, HC): the dsfd_dvrly_* body (ot_s81_rly RSREG=1: one register stage, rs through the reset pin
// register) with the ck -> ck_o forward selected by HC:
//   HC = 0  ck_o = ck  through the kept ot_dvrly_ckinv pair (today's dsfd_dvrly_<W>_<dir>: station k+1 captures one
//           period after station k; relay->relay hold -120..-195 ps in the p4j pilot: clock leg > data leg)
//   HC = 1  ck_o = ~ck through ONE kept ot_dvrly_ckinv: station k+1 captures on the opposite edge, half a period
//           after station k (hold gains ~T/2, setup keeps T/2 - (clock-data skew); two stations per root cycle).
// dsfd_dvrlyh_<W>_<dir> = HC 1 successors of the closed dsfd_dvrly_<W>_<dir> views (same ports, same pins).
// OT_DVRLYH_MUT (bench mutant only): HC 1 masters built with the non-inverting pair.  ot_dvrly_ckinv is defined in
// dsfd_rly_masters_dv276.sv (byte-identical).
`default_nettype none
module ot_dvrly_st #(parameter integer W = 276, parameter integer HC = 0) (input wire ck, input wire rs, input wire [W-1:0] i,
                                                                      output wire [W-1:0] o, output wire ck_o);
    ot_s81_rly #(.W(W), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
`ifdef OT_DVRLYH_MUT
    localparam integer INV = 0;
`else
    localparam integer INV = HC;
`endif
    generate if (INV != 0) begin : g_half
        ot_dvrly_ckinv u_ck0 (.a(ck), .y(ck_o));
    end else begin : g_full
        wire ckn;
        ot_dvrly_ckinv u_ck0 (.a(ck), .y(ckn));
        ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
    end endgenerate
endmodule
module dsfd_dvrlyh_276_EW (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o, output wire ck_o);
    ot_dvrly_st #(.W(276), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_276_WE (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o, output wire ck_o);
    ot_dvrly_st #(.W(276), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_276_NS (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o, output wire ck_o);
    ot_dvrly_st #(.W(276), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_276_SN (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o, output wire ck_o);
    ot_dvrly_st #(.W(276), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_512_EW (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o, output wire ck_o);
    ot_dvrly_st #(.W(512), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_512_WE (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o, output wire ck_o);
    ot_dvrly_st #(.W(512), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_562_EW (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o, output wire ck_o);
    ot_dvrly_st #(.W(562), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_562_SN (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o, output wire ck_o);
    ot_dvrly_st #(.W(562), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_562_WE (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o, output wire ck_o);
    ot_dvrly_st #(.W(562), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_682_EW (input wire ck, input wire rs, input wire [681:0] i, output wire [681:0] o, output wire ck_o);
    ot_dvrly_st #(.W(682), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_682_NS (input wire ck, input wire rs, input wire [681:0] i, output wire [681:0] o, output wire ck_o);
    ot_dvrly_st #(.W(682), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_682_WE (input wire ck, input wire rs, input wire [681:0] i, output wire [681:0] o, output wire ck_o);
    ot_dvrly_st #(.W(682), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_70_NS (input wire ck, input wire rs, input wire [69:0] i, output wire [69:0] o, output wire ck_o);
    ot_dvrly_st #(.W(70), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_70_SN (input wire ck, input wire rs, input wire [69:0] i, output wire [69:0] o, output wire ck_o);
    ot_dvrly_st #(.W(70), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
// MU-S81/DIE (10-19): vertical 512 / 562 stations for the copy-B lane pair of the AB die variant (s_0N -> lk_WN2/3 along
// the PHY faces).  Same ot_dvrly_st HC 1 body as every master above; NO closed physical view yet (stand-in relays).
module dsfd_dvrlyh_512_NS (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o, output wire ck_o);
    ot_dvrly_st #(.W(512), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_512_SN (input wire ck, input wire rs, input wire [511:0] i, output wire [511:0] o, output wire ck_o);
    ot_dvrly_st #(.W(512), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_562_NS (input wire ck, input wire rs, input wire [561:0] i, output wire [561:0] o, output wire ck_o);
    ot_dvrly_st #(.W(562), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
`default_nettype wire
