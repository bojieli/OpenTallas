// GENERATED (L2H-RSTFB 10-19, from hbfd_rly_rf_masters.sv): station-hosted reset-forest CARRIER stages.
// hbfd_rly_<W>_<flow>_rfc = hbfd_rly_<W>_<flow> (ot_hbm_rly, unchanged) + carrier stage rfi -> 2-stage landing -> rfo;
// hbfd_rly_<W>_<flow>_rrfc = hbfd_rly_<W>_<flow>_rr (ot_hbm_rly_rr, row reset rso, unchanged) + the same carrier stage
// (rtl/hbm_accel/die_glue/ot_hbm_rly_rfc.sv: assert immediate, release exactly 3 edges after rfi).
// Stage, RS_RELAY, row-reset and data semantics unchanged; rfi/rfo never touch rs/rso/i/o.
`default_nettype none
module hbfd_rly_8_WE_rfc (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_8_WE_rrfc (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_8_EW_rfc (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_8_EW_rrfc (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_8_SN_rfc (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_8_SN_rrfc (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_8_NS_rfc (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_8_NS_rrfc (input wire ck, input wire rs, input wire [7:0] i, output wire [7:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(8)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_WE_rfc (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_WE_rrfc (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_EW_rfc (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_EW_rrfc (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_SN_rfc (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_SN_rrfc (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_NS_rfc (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_48_NS_rrfc (input wire ck, input wire rs, input wire [47:0] i, output wire [47:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(48)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_WE_rfc (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_WE_rrfc (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_EW_rfc (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_EW_rrfc (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_SN_rfc (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_SN_rrfc (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_NS_rfc (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_NS_rrfc (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(136), .RS_RELAY(1)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_WE_rfc (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_WE_rrfc (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_EW_rfc (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_EW_rrfc (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_SN_rfc (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_SN_rrfc (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_NS_rfc (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_304_NS_rrfc (input wire ck, input wire rs, input wire [303:0] i, output wire [303:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(304)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_WE_rfc (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_WE_rrfc (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_EW_rfc (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_EW_rrfc (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_SN_rfc (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_SN_rrfc (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_NS_rfc (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_624_NS_rrfc (input wire ck, input wire rs, input wire [623:0] i, output wire [623:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(624)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_WE_rfc (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_WE_rrfc (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_EW_rfc (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_EW_rrfc (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_SN_rfc (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_SN_rrfc (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_NS_rfc (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_NS_rrfc (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
`default_nettype wire
