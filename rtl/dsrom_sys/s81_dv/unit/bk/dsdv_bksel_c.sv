`timescale 1ns/1ps
// S81-A2 bk_sel__t2 relay stations (S81-ARCH-RTL-2 11-11, COORD ruling 11-11; S81-TRIAGE-3 relay sites): the
// quarter <-> control hops are 852-1604 um, so the plan carries reset-less register stations on them: OT_BKSEL_RC on
// t_c / t_cr (control -> quarter), OT_BKSEL_RS on t_s, OT_BKSEL_RO on t_o (quarter -> control), OT_BKSEL_RLN on the
// four lanes ln0..ln3 (glue -> quarter).  The control's fixed-latency waits take the added round trip
// (XDX + ceil((RC + RS) / 2)), the landing FIFO / initial credits grow by OT_BKSEL_DMX (control AND quarter), and
// OT_BKSEL_SLX adds status latency.  All 0 = as built.  The stations are reset-less: they flush to the quarters'
// reset zeros while rst is held (S81 boot holds rst_n >= 64 clk, more than any station depth).
`ifndef OT_BKSEL_RC
`define OT_BKSEL_RC 0
`endif
`ifndef OT_BKSEL_RS
`define OT_BKSEL_RS 0
`endif
`ifndef OT_BKSEL_RO
`define OT_BKSEL_RO 0
`endif
`ifndef OT_BKSEL_RLN
`define OT_BKSEL_RLN 0
`endif
`ifndef OT_BKSEL_DMX
`define OT_BKSEL_DMX 0
`endif
`ifndef OT_BKSEL_XDM   // bench mutant only: the control under-counts the station round trip by XDM edges
`define OT_BKSEL_XDM 0
`endif
`ifndef OT_BKSEL_SLX
`define OT_BKSEL_SLX 0
`endif
// S81U-BK2 (2026-10-17): child leaf of dsdv_bk_sel (dsdv_bk_sel.sv).
// select control leaf: dsfd_selt_c (SEARCH_PIPE, DM 4, PACE 2, MRG_PIPE, RQPIPE, SLAT 4, XDX 1: the control the closed
// PIPE2 / QIO quarter tiles need) with per-face ports (a kit port sits on ONE face).
// S81U-BK3 (vertical cut): S face = quarters 0 (SW) / 1 (SE) (the S quarter row), N face = quarters 2 (NW) / 3 (NE),
// vd on the E face (the glue leaf sits E of it).  Its forwarded-clock output vf is not used on the V rung.
module dsdv_bksel_c #(
    parameter integer SELOH = 0, // DIE-S81-51 11-03 (S81-053): 1 = SEARCH_PIPE 4 (one-hot group select, res_above -217 ps)
    parameter integer OLL = 0,  // RF-C/bk 11-03: 1 = negative-level lockup latch, 2 = negedge flop, on every output port (dsdv_bk_oll)
    // RNF (DIE-S81-51/RF-D 11-03, S81-053: kits_seloh2 dsdv_bksel_c_rfc stopped at OT_HOLD_STRUCTURAL GRT FF hold -189.50 /
    // 172 ep; FF STA on 4_cts.odb: the structural endpoints are ONLY rst[0] -> u_c.rst_s[1:0] removal -213.5 (input min
    // -40 vs core insertion); the half-cycle f_* faces pass and the rest are reg -> reg >= -9.1 ps (hold repair)):
    // 1 = rst lands in a negative-edge flop before u_c (0 cycles: release edge unchanged, rst leaves a posedge flop;
    // assertion half an edge later; pin removal window ~T/2 by construction).  0 = the old form.
    parameter integer RNF = 0
) (
    input  wire [0:0]       ck,
    input  wire [0:0]       rst,
    input  wire [2*865-1:0] f_s_s, f_s_n,     // {quarter 1, quarter 0} / {quarter 3, quarter 2}
    input  wire [2*354-1:0] f_o_s, f_o_n,
    output wire [2*66-1:0]  t_c_s, t_c_n,
    output wire [1:0]       t_cr_s, t_cr_n,
    output wire [366:0]     vd    // S81-KITS-RTLC 10-24: packed {vd[512:502], vd[356:1]} (dsdv_bk_g VD_PK)
);
    localparam integer CB = 66, SB = 865, OB = 354;
    wire [4*CB-1:0] tc; wire [3:0] tcr; wire vf_unused; wire [513:0] vdw;
    // ONE public name for the negedge rst flop (rst_nf, module scope, no alias wire): the LEC matches registers by name
    // (the generate-scoped r_f + alias rst_c came out of synthesis as rst_c$_DFF_N_ -> unmatched, 6,182 points differ).
    // RNF 0: the flop is unloaded and removed by synthesis.
    reg rst_nf;
`ifdef OT_RFD_MUT_RNF   // bench mutant: rst sampled on the RISING edge (release one edge late)
    always @(posedge ck[0]) rst_nf <= rst[0];
`else
    always @(negedge ck[0]) rst_nf <= rst[0];
`endif
    dsfd_selt_c #(.SEARCH_PIPE(SELOH != 0 ? 4 : 1), .DM(4 + `OT_BKSEL_DMX), .PACE(2), .MRG_PIPE(1), .RQPIPE(1),
        .SLAT(4 + `OT_BKSEL_SLX), .XDX(1 + (`OT_BKSEL_RC + `OT_BKSEL_RS + 1) / 2 - `OT_BKSEL_XDM)) u_c (.ck(ck), .rst(RNF != 0 ? rst_nf : rst[0]),
        .f_s({f_s_n, f_s_s}), .f_o({f_o_n, f_o_s}), .t_c(tc), .t_cr(tcr), .vd(vdw), .vf(vf_unused));
    // vdw[513], vdw[501:357]: constant 0; vdw[0]: unread (dropped pins).  Every port bit leaves a flop (+ OLL latch)
    dsdv_bk_oll #(.W(367 + 4*CB + 4), .EN(OLL)) u_oll (.ck(ck[0]),
        .d({vdw[512:502], vdw[356:1], tc[2*CB +: 2*CB], tc[0 +: 2*CB], tcr[3:2], tcr[1:0]}),
        .q({vd, t_c_n, t_c_s, t_cr_n, t_cr_s}));
endmodule

// S81U-BK3: the selector quarter leaf dsfd_selt_q2 (DM 4, SAFE, CMP_RETIME, PIPE2, QIO, ILD, FRPR: the closed s81b-selt_q2-frprildb
// configuration)
module dsdv_bksel_q #(
    parameter integer OLL = 0   // RF-C/bk 11-03: 1 = negative-level lockup latch, 2 = negedge flop, on every output port (dsdv_bk_oll)
) (
    input  wire [0:0]   ck,
    input  wire [0:0]   rst,
    input  wire [514:0] lane,
    input  wire [65:0]  f_c,
    input  wire [0:0]   f_cr,
    output wire [864:0] t_s,
    output wire [353:0] t_o
);
    wire [864:0] t_s_f; wire [353:0] t_o_f;            // the quarter's registered outputs (source-registered QIO)
    dsdv_bk_oll #(.W(865 + 354), .EN(OLL)) u_oll (.ck(ck), .d({t_s_f, t_o_f}), .q({t_s, t_o}));
`ifdef OT_S81PH_SEL_HQ
    // S81-TOPK7 hierarchical quarter (ot_s81ph_hq_tile.sv): same ports / function / edges, native-census-clean structure
`ifndef OT_S81PH_SEL_HQ_MUT
`define OT_S81PH_SEL_HQ_MUT 0
`endif
    dsfd_selt_q_hq #(.DM(4 + `OT_BKSEL_DMX), .MUT(`OT_S81PH_SEL_HQ_MUT)) u_q (.ck(ck), .rst(rst), .lane(lane), .f_c(f_c), .f_cr(f_cr),
        .t_s(t_s_f), .t_o(t_o_f));
`else
    dsfd_selt_q2 #(.DM(4 + `OT_BKSEL_DMX), .CMP_RETIME(1), .PIPE2(1), .QIO(1), .ILD(1), .FRPR(1)) u_q (.ck(ck), .rst(rst), .lane(lane),
        .f_c(f_c), .f_cr(f_cr), .t_s(t_s_f), .t_o(t_o_f));
`endif
endmodule

// DIE-S81-51/RF-C/bk 11-03 (S81-RF1 hold-safe core face, DIE-S81-51/CLK crossing table row 1): EN 1 = a NEGATIVE-level
// lockup latch (transparent while ck is LOW) after every registered output flop, driving the output port.  Sampled at
// the next rising edge the port carries exactly the flop's value (0 cycles, no per-port cycle delta); it moves only
// after the falling edge, so the receiver's zero-logic hold margin is ~T/2 by construction.  EN 0 = wires (old form).
module dsdv_bk_oll #(parameter integer W = 1, parameter integer EN = 0) (
    input  wire         ck,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    // DIE-S81-51 11-03 (uniform out-face form ruling): EN 2 = negative-edge flop (DFFLQN) on every output bit, same
    // T/2 hold window as the EN 1 latch, 0 cycles; face_guard/face_flops/LEC already treat it as a state element.
    generate if (EN == 2) begin : g_nff
        reg [W-1:0] l;
        always @(negedge ck) l <= d;
        assign q = l;
    end else if (EN != 0) begin : g_lat
        reg [W-1:0] l;
`ifdef OT_BK_OLL_MUT
        always_latch if (ck) l <= d;      // bench mutant: positive-level latch (port moves in the high phase)
`else
        always_latch if (!ck) l <= d;
`endif
        assign q = l;
    end else begin : g_wire
        assign q = d;
    end endgenerate
endmodule
