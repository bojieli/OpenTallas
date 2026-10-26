// GENERATED (L2H-RSTFB 10-19, from hbfd_rly_rf_masters.sv): station-hosted reset-forest CARRIER stages.
// hbfd_rly_<W>_<flow>_rfc = hbfd_rly_<W>_<flow> (ot_hbm_rly, unchanged) + carrier stage rfi -> 2-stage landing -> rfo;
// hbfd_rly_<W>_<flow>_rrfc = hbfd_rly_<W>_<flow>_rr (ot_hbm_rly_rr, row reset rso, unchanged) + the same carrier stage
// (rtl/hbm_accel/die_glue/ot_hbm_rly_rfc.sv: assert immediate, release exactly 3 edges after rfi).
// Stage, RS_RELAY, row-reset and data semantics unchanged; rfi/rfo never touch rs/rso/i/o.
// HBM-RSTFB10 10-21: the 136 EW/NS/SN _rfc/_rrfc and 1136 EW/WE _rfc masters use ot_hbm_rly(_rr)_f32 (same function and
// reset timing, stage reset fanned out <= 32 loads per driver; native census refused the 136/256-load relay copy).
`default_nettype none
// HBM-RSTFB10 10-21: ot_hbm_rly_f32 = ot_hbm_rly with the stage reset fanned out <= 32 loads per driver (pre-gate native
// census: the closed-station relay copy u_rst.rst_n drove all 136 / 256 data-flop clears).  Same function and the same
// reset timing as ot_hbm_rly with the registered relay (RS_RELAY=1 or W > 256): assert asynchronous and immediate,
// release 3 clock edges after rs (first data capture at the 4th edge).  Tree: rs -> s0 -> NS1 copies s1 (all async-cleared
// by rs) -> NL2 = ceil(W/32) leaves l2 (D = s1, async-cleared by its s1: assert stays immediate) -> <= 32 data flops each.
// Loads: rs 1+NS1 (+1 rq in _rr); s0 NS1; s1 2*(<= 16) pins; l2 <= 32.  All copies keep/dont_touch (no merge-back).
module ot_hbm_rly_f32 #(
    parameter int W = 136
) (
    input  wire         ck,
    input  wire         rs,
    input  wire [W-1:0] i,
    output wire [W-1:0] o
);
    localparam int NL2 = (W + 31) / 32;
    localparam int NS1 = (NL2 + 15) / 16;
    (* keep = "true", dont_touch = "true" *) reg s0;
    (* keep = "true", dont_touch = "true" *) reg [NS1-1:0] s1;
    (* keep = "true", dont_touch = "true" *) reg [NL2-1:0] l2;
    always @(posedge ck or negedge rs)
        if (!rs) s0 <= 1'b0; else s0 <= 1'b1;
    reg [W-1:0] r;
    genvar a, g;
    generate
        for (a = 0; a < NS1; a = a + 1) begin : g_s1
            always @(posedge ck or negedge rs)
                if (!rs) s1[a] <= 1'b0; else s1[a] <= s0;
        end
        for (g = 0; g < NL2; g = g + 1) begin : g_l2
            localparam int LO = g * 32;
            localparam int N  = (W - LO > 32) ? 32 : W - LO;
            always @(posedge ck or negedge s1[g / 16])
                if (!s1[g / 16]) l2[g] <= 1'b0; else l2[g] <= s1[g / 16];
            always @(posedge ck or negedge l2[g])
                if (!l2[g]) r[LO +: N] <= {N{1'b0}};
`ifdef OT_HBM_RLY_MUT
                else r[LO +: N] <= (g == 0) ? i[LO +: N] ^ {{(N-1){1'b0}}, 1'b1} : i[LO +: N];   // bench mutant: bit 0 inverted
`else
                else r[LO +: N] <= i[LO +: N];
`endif
        end
    endgenerate
    assign o = r;
endmodule
// ot_hbm_rly_rr_f32 = ot_hbm_rly_rr (row reset rso: release exactly 1 edge after rs) over ot_hbm_rly_f32.
module ot_hbm_rly_rr_f32 #(
    parameter int W = 136
) (
    input  wire         ck,
    input  wire         rs,
    input  wire [W-1:0] i,
    output wire [W-1:0] o,
    output wire         rso
);
    ot_hbm_rly_f32 #(.W(W)) u_stage (.ck(ck), .rs(rs), .i(i), .o(o));
`ifdef OT_HBM_RLY_RR_MUT_COMB
    assign rso = rs;
`else
    (* keep = "true", dont_touch = "true" *) reg rq;
    always @(posedge ck or negedge rs)
        if (!rs) rq <= 1'b0; else rq <= 1'b1;
`ifdef OT_HBM_RLY_RR_MUT_2
    (* keep = "true", dont_touch = "true" *) reg rq2;
    always @(posedge ck or negedge rs)
        if (!rs) rq2 <= 1'b0; else rq2 <= rq;
    assign rso = rq2;
`else
    assign rso = rq;
`endif
`endif
endmodule
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
    ot_hbm_rly_f32 #(.W(136)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_EW_rrfc (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr_f32 #(.W(136)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_SN_rfc (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly_f32 #(.W(136)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_SN_rrfc (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr_f32 #(.W(136)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_NS_rfc (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly_f32 #(.W(136)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_136_NS_rrfc (input wire ck, input wire rs, input wire [135:0] i, output wire [135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr_f32 #(.W(136)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
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
    ot_hbm_rly_f32 #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_WE_rrfc (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, output wire rso, input wire rfi, output wire rfo);
    ot_hbm_rly_rr #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
    ot_hbm_rly_rfc uf (.ck(ck), .rfi(rfi), .rfo(rfo));
endmodule
module hbfd_rly_1136_EW_rfc (input wire ck, input wire rs, input wire [1135:0] i, output wire [1135:0] o, input wire rfi, output wire rfo);
    ot_hbm_rly_f32 #(.W(1136)) u (.ck(ck), .rs(rs), .i(i), .o(o));
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
