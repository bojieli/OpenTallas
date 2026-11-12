`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// BUS-GEAR-1 (2026-11-12, DIE-S81-87 ask for ready12b): S81 x feed 2:1, die integration glue.
//
// Slice side: ot_s81_xc_gear_tx sits in the slice C partition (bind map: u_xg_<slice> -> <slice>_C) between the slice's
// xc port (NG groups x 4 lanes x 276 b; lane l of group g is launched on the slice's forwarded lane clock ck_xc[4g + l])
// and the hop-0 relay station.  Each lane samples a word on alternate edges of its own lane clock: a parity flop set by
// the slice reset makes the first edge after release a word edge.  COMPILER CONTRACT (x cadence 2): an x word leaves the
// slice on an even edge counted from the slice C reset release; the contents of odd edges are not sent.  The TX beat
// register is the new face flop of the slice x pins.  Groups with GEN[g] = 0 (no x lane in the plan) send nothing.
//
// Frame side: ot_s81_xframe_gear lands the 4 beat lanes on the frame r0 clock with ot_bus_gear_rx OGATE 0 (every pin
// feeds a flop directly; the crs4 bundle markers x[0] / x[566] are in beat 0, so non-word edges land as bubbles) and
// forwards the BEATS to the next frame through FW relay stages (= the frame's own x -> xo forward stages), so a frame
// hop adds no edge.
//
// Word latency of every geared x lane: + 2 edges (TX face flop + second beat).  Declared on the plan lanes as DEC12
// beats 2 / word_bits 1104 / beat_index_bits 4 (port 552 + 4 = 556; word_cycles = cycles + 1) plus the TX register
// (+1 station cycle).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_xc_gear_tx #(
    parameter integer NG = 4,
    parameter [3:0] GEN = 4'b1111,
    localparam integer LW = 276,
    localparam integer BL = 139
) (
    input  wire [4*NG-1:0] ck,                        // lane clocks = the slice's ck_xc
    input  wire rst_n,                                // slice C reset (synchronous)
    input  wire [NG*4*LW-1:0] xc,                     // the slice's xc port
    output wire [NG*4*BL-1:0] xb                      // beat lanes, lane l of group g = xb[BL*(4g+l) +: BL]
);
    genvar g, l;
    generate for (g = 0; g < NG; g = g + 1) begin : g_g
        for (l = 0; l < 4; l = l + 1) begin : g_l
            if (GEN[g]) begin : g_on
                reg ph;                               // word-edge parity (control flop, reset)
                always @(posedge ck[4*g+l]) if (!rst_n) ph <= 1'b1; else ph <= ~ph;
                /* verilator lint_off PINCONNECTEMPTY */   // spacing is 2 by construction, the fault cannot rise
                ot_bus_gear_tx #(.W(LW), .BEATS(2)) u_tx (.clk(ck[4*g+l]), .rst_n(rst_n), .v_i(ph),
                    .d_i(xc[LW*(4*g+l) +: LW]), .b_o(xb[BL*(4*g+l) +: BL-1]), .f_o(xb[BL*(4*g+l)+BL-1]), .fault_o());
                /* verilator lint_on PINCONNECTEMPTY */
            end else begin : g_off
                /* verilator lint_off UNUSEDSIGNAL */
                wire [LW-1:0] unused = xc[LW*(4*g+l) +: LW];
                /* verilator lint_on UNUSEDSIGNAL */
                assign xb[BL*(4*g+l) +: BL] = {BL{1'b0}};
            end
        end
    end endgenerate
endmodule

module ot_s81_xframe_gear #(
    parameter integer FW = 2,                         // beat forward stages (0 = no xo: last frame of a chain)
    localparam integer LW = 276,
    localparam integer BL = 139
) (
    input  wire ck,                                   // frame r0 clock (the LP frame lands x on its own clock)
    input  wire rst_n,
    input  wire [4*BL-1:0] xb_i,                      // 4 beat lanes in
    output wire [4*LW-1:0] x_o,                       // landed word to the frame r0 band (x_i0)
    output wire [4*BL-1:0] xb_o                       // the 4 beat lanes forwarded to the next frame, FW edges later
);
    /* verilator lint_off PINCONNECTEMPTY */
    ot_s81_xlane_gear_rx #(.OGATE(0)) u_rx (.xk({4{ck}}), .rst_n({4{rst_n}}), .xb_i(xb_i), .x_o(x_o), .v_o());
    /* verilator lint_on PINCONNECTEMPTY */
    genvar k, j;
    generate if (FW == 0) begin : g_nofw
        assign xb_o = {4*BL{1'b0}};
    end else begin : g_fw
        for (k = 0; k < 4; k = k + 1) begin : g_l
            wire [BL-1:0] s [0:FW];
            assign s[0] = xb_i[BL*k +: BL];
            for (j = 0; j < FW; j = j + 1) begin : g_st
                ot_s81_rly #(.W(BL), .RSREG(1)) u_y (.ck(ck), .rs(rst_n), .i(s[j]), .o(s[j+1]));
            end
            assign xb_o[BL*k +: BL] = s[FW];
        end
    end endgenerate
endmodule

// 139-b half-cycle forwarded-clock relay stations (dsfd_dvrlyh_<W>_<dir> family, rtl/dsrom_sys/s81_glue/
// dsfd_rly_masters_dvh.sv) for the geared x beat lanes.
module dsfd_dvrlyh_139_NS (input wire ck, input wire rs, input wire [138:0] i, output wire [138:0] o, output wire ck_o);
    ot_dvrly_st #(.W(139), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_139_SN (input wire ck, input wire rs, input wire [138:0] i, output wire [138:0] o, output wire ck_o);
    ot_dvrly_st #(.W(139), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_139_EW (input wire ck, input wire rs, input wire [138:0] i, output wire [138:0] o, output wire ck_o);
    ot_dvrly_st #(.W(139), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
module dsfd_dvrlyh_139_WE (input wire ck, input wire rs, input wire [138:0] i, output wire [138:0] o, output wire ck_o);
    ot_dvrly_st #(.W(139), .HC(1)) u_st (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o(ck_o));
endmodule
`default_nettype wire
