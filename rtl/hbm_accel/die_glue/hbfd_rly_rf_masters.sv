// GENERATED (LH-RSTHOP 10-19, from hbfd_rly_masters.sv): reset-forest hop hosts.  hbfd_rly_<W>_<flow>_rf =
// hbfd_rly_<W>_<flow> + forest hop flop rfi -> rfo; hbfd_rly_<W>_<flow>_rrf = hbfd_rly_<W>_<flow>_rr (row reset rso) + the
// same hop (rtl/hbm_accel/die_glue/ot_hbm_rly_rf.sv).  Stage, RS_RELAY and row-reset semantics unchanged.
`default_nettype none
module hbfd_rly_8_WE_rf (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_8_WE_rrf (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_8_EW_rf (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_8_EW_rrf (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_8_SN_rf (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_8_SN_rrf (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_8_NS_rf (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_8_NS_rrf (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_WE_rf (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_WE_rrf (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_EW_rf (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_EW_rrf (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_SN_rf (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_SN_rrf (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_NS_rf (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_NS_rrf (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_WE_rf (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_WE_rrf (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_EW_rf (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_EW_rrf (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_SN_rf (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_SN_rrf (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_NS_rf (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_NS_rrf (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_WE_rf (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_WE_rrf (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_EW_rf (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_EW_rrf (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_SN_rf (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_SN_rrf (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_NS_rf (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_NS_rrf (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_WE_rf (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_WE_rrf (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_EW_rf (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_EW_rrf (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_SN_rf (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_SN_rrf (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_NS_rf (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_NS_rrf (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_WE_rf (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_WE_rrf (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_EW_rf (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_EW_rrf (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_SN_rf (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_SN_rrf (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_NS_rf (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_NS_rrf (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfhop uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
`default_nettype wire
