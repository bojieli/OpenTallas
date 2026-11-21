`timescale 1ns/1ps
// S81-A2 bk_sel__t2 relay stations (S81-ARCH-RTL-2 11-11, COORD ruling 11-11; S81-TRIAGE-3 relay sites): the
// quarter <-> control hops are 852-1604 um, so the plan carries reset-less register stations on them: OT_BKSEL_RC on
// t_c / t_cr (control -> quarter), OT_BKSEL_RS on t_s, OT_BKSEL_RO on t_o (quarter -> control), OT_BKSEL_RLN on the
// four lanes ln0..ln3 (glue -> quarter).  The control's fixed-latency waits take the added round trip
// (XDX + ceil((RC + RS) / 2)), the landing FIFO / initial credits grow by OT_BKSEL_DMX (control AND quarter), and
// OT_BKSEL_SLX adds status latency.  All 0 = as built.  The stations are reset-less: they flush to the quarters'
// reset zeros while rst is held (S81 boot holds rst_n >= 64 clk, more than any station depth).
// S81-GEOM-OPUS 11-19 (bank-leaf; FABLE-FIX-S81-LEAF netlist trace, main 35d4334b5b42: bk_sel__t2 had 22 core-to-core links,
// 0 stages, 16 over 405 um): OT_BKSEL_A2P = the S81-A2 station profile as ONE bare macro name, because plan verilog_defines take
// bare names only (gen_phys.type_verilog_defines): RC 3, RS 3, RO 4, RLN 3, for the re-placed bk_sel__t2 core layout where every
// control <-> quarter / glue -> quarter link is <= (D + 1) x 405 um.  The control core dsdv_bksel_c MUST be hardened with the same
// macro (XDX = 1 + ceil((RC + RS + QRX) / 2) = 5 with the eco3 QRX 1); quarters unchanged (DMX 0).  Explicit OT_BKSEL_* defines win.
// FABLE-FIX-S81-BKSEL-R2 11-20 (J3 placed bk_sel__t2 BAD: core links 0 stages; 300 um hop cap): OT_BKSEL_A3P = the S81-A2 station
// profile for the 300-um hop cap as ONE bare macro name: RC 5, RS 5, RO 7, RLN 5 (BK-PLACE core layout: control <-> quarter /
// glue -> quarter links <= 1,613 / 1,590 / 2,265 / 1,602 um pin to pin, every hop <= 283 um).  The control core dsdv_bksel_c MUST be
// hardened with the same macro (XDX = 1 + ceil((RC + RS + QRX) / 2) = 7 with the eco3 QRX 1); quarters unchanged (DMX 0).
// Listed before OT_BKSEL_A2P, so A3P wins when both are set; explicit OT_BKSEL_* defines win over both.  Inert when undefined.
// OPUS-FIX-S81-BKSEL-R4 11-20: OT_BKSEL_L4 sets RO 8 (t_o stations only; this core's XDX does not use RO), so file order never matters.
`ifdef OT_BKSEL_L4
`ifndef OT_BKSEL_RO
`define OT_BKSEL_RO 8
`endif
`endif
`ifdef OT_BKSEL_A3P
`ifndef OT_BKSEL_RC
`define OT_BKSEL_RC 5
`endif
`ifndef OT_BKSEL_RS
`define OT_BKSEL_RS 5
`endif
`ifndef OT_BKSEL_RO
`define OT_BKSEL_RO 7
`endif
`ifndef OT_BKSEL_RLN
`define OT_BKSEL_RLN 5
`endif
`endif
`ifdef OT_BKSEL_A2P
`ifndef OT_BKSEL_RC
`define OT_BKSEL_RC 3
`endif
`ifndef OT_BKSEL_RS
`define OT_BKSEL_RS 3
`endif
`ifndef OT_BKSEL_RO
`define OT_BKSEL_RO 4
`endif
`ifndef OT_BKSEL_RLN
`define OT_BKSEL_RLN 3
`endif
`endif
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
    parameter integer RNF = 0,
    // S81-CORES-R3 11-17 (S81-DIE-R3 NEEDS-LANE (a)): QRX = extra input edges inside each quarter (dsdv_bksel_q RFH 2: the
    // rising-edge face stage on lane / f_c / f_cr = 1).  The command -> status round trip grows by QRX, so the fixed waits
    // take it with the plan stations: XDX = 1 + ceil((RC + RS + QRX) / 2).  QRX 0 = as built.
    parameter integer QRX = 0,
    parameter integer LQH = 0,  // DIE-S81-52 11-03 (47046ce95e0): 1 = one-hot landing FIFO count in u_c (0 cycles; dsfd_selt_c LQH)
    parameter integer TKR = 0   // OPUS-FIX-S81-BKSEL-R3 11-20: 1 = take from the registered new-fault flag (0 cycles; dsfd_selt_c TKR)
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
        .SLAT(4 + `OT_BKSEL_SLX), .XDX(1 + (`OT_BKSEL_RC + `OT_BKSEL_RS + QRX + 1) / 2 - `OT_BKSEL_XDM), .LQH(LQH), .TKR(TKR)) u_c (.ck(ck), .rst(RNF != 0 ? rst_nf : rst[0]),
        .f_s({f_s_n, f_s_s}), .f_o({f_o_n, f_o_s}), .t_c(tc), .t_cr(tcr), .vd(vdw), .vf(vf_unused));
    // vdw[513], vdw[501:357]: constant 0; vdw[0]: unread (dropped pins).  Every port bit leaves a flop (+ OLL latch)
    dsdv_bk_oll #(.W(367 + 4*CB + 4), .EN(OLL)) u_oll (.ck(ck[0]),
        .d({vdw[512:502], vdw[356:1], tc[2*CB +: 2*CB], tc[0 +: 2*CB], tcr[3:2], tcr[1:0]}),
        .q({vd, t_c_n, t_c_s, t_cr_n, t_cr_s}));
endmodule

// S81U-BK3: the selector quarter leaf dsfd_selt_q2 (DM 4, SAFE, CMP_RETIME, PIPE2, QIO, ILD, FRPR: the closed s81b-selt_q2-frprildb
// configuration)
// S81-CORES-R3 11-17 merge (S81-DIE-R3 NEEDS-LANE (a)): the S81-A2 station hooks (DM 4 + OT_BKSEL_DMX) of main b281e1b5 and the
// RFH / HLAT form of the signed eco3 core (legacy profile bkr1c8_hlat_1113 dsdv_bksel_c.sv 651f2895, kit params OLL 2 RFH 2
// HLAT 1) in one file.  RFH 0 / HLAT 0 / DMX 0 = byte-identical function to both parents' defaults.  RFH 2 = +1 edge on lane /
// f_c / f_cr / rst -> t_s / t_o: the control takes it as dsdv_bksel_c QRX 1 (dsdv_bk_sel passes both from OT_BKQ_RFH).
`ifndef OT_BKQ_HLAT_DEF
`define OT_BKQ_HLAT_DEF 0   // bench hook only (layer benches instantiate dsdv_bksel_q without HLAT); kits pass HLAT
`endif
module dsdv_bksel_q #(
    parameter integer OLL = 0,  // RF-C/bk 11-03: 1 = negative-level lockup latch, 2 = negedge flop, on every output port (dsdv_bk_oll)
    // DIE-S81-51/RF-H 11-03 (S81-054 conservative form, OWNER 18:57): RFH 1 = every input pin (lane, f_c, f_cr, rst) lands
    // in ONE negative-edge face flop (0 cycles vs RFH 0 on lane / f_c / f_cr: the posedge sender value is sampled half an
    // edge later, so the zero-logic face hold window is ~T/2 inside the core; legacy IO contract in_min -40 / max 166.6,
    // NO sender lockup latch); dsfd_selt_q_hq FACE 1 then registers the type-8 selects as kept copies (no raw-type
    // broadcast from s0) and relays the reset through posedge kept copies per consumer group (reset assert / release
    // +1 edge, synchronous both ways).  RFH 0 = the RF-C form (face flops unloaded, removed by synthesis).
    parameter integer RFH = 0,
    // S81-ARCH-RTL-2 11-12 (DIE-S81-87 / COORD bksel hold, structural): HLAT 1 = a NEGATIVE-level lockup latch
    // (ot_s81ph_hlk u_fl_*, transparent while ck is LOW) on the launch side of the measured zero-logic intra-core hops
    // (vC4r HOLD_SPLIT: x_* -> i0_*, c1_* -> c2_*, pend_d1 -> pend_eff, o0_m -> o_in / u_ofq wd).  0 cycles; the
    // capture's hold window becomes ~T/2 - skew.  Legal only with the latch clocked from its launch flop's tap
    // (regional_taps.tcl OT_RT_HLAT_FOLLOW_D 1).  HLAT 0 = byte-identical function and structure to the old form.
    parameter integer HLAT = `OT_BKQ_HLAT_DEF
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
    // RF-H face flops: module-scope public names (LEC matches registers by name)
    reg [514:0] lane_nf; reg [65:0] f_c_nf; reg f_cr_nf, rst_nf;
`ifdef OT_RFH_MUT_FACE   // bench mutant: face flops on the RISING edge (every input one edge late)
    always @(posedge ck) begin lane_nf <= lane; f_c_nf <= f_c; f_cr_nf <= f_cr; rst_nf <= rst; end
`else
    always @(negedge ck) begin lane_nf <= lane; f_c_nf <= f_c; f_cr_nf <= f_cr; rst_nf <= rst; end
`endif
    // DIE-S81-53 11-04 (rfh3, rfh2 stopped at GRT TT -64.75 on 59 eps: negedge lane face -> long wire + type decode -> g_fr /
    // s0c / s0d in T/2, with the 145-ps tree gap between pin flops and core): RFH 2 = RFH 1 + one rising-edge stage on every
    // input (lane, f_c, f_cr, rst), +1 cycle lane / f_c / f_cr -> outputs (owner 11-03: core-pin cycles are a lever).
    reg [514:0] lane_p; reg [65:0] f_c_p; reg f_cr_p, rst_p;
`ifdef OT_RFH_MUT_P2     // bench mutant: f_cr bypasses the added stage
    always @(posedge ck) begin lane_p <= lane_nf; f_c_p <= f_c_nf; f_cr_p <= f_cr_nf; rst_p <= rst_nf; end
    wire f_cr_pm = f_cr_nf;
`else
    always @(posedge ck) begin lane_p <= lane_nf; f_c_p <= f_c_nf; f_cr_p <= f_cr_nf; rst_p <= rst_nf; end
    wire f_cr_pm = f_cr_p;
`endif
    wire [514:0] lane_i = RFH == 2 ? lane_p : RFH != 0 ? lane_nf : lane;
    wire [65:0]  f_c_i  = RFH == 2 ? f_c_p : RFH != 0 ? f_c_nf : f_c;
    wire         f_cr_i = RFH == 2 ? f_cr_pm : RFH != 0 ? f_cr_nf : f_cr;
    wire         rst_i  = RFH == 2 ? rst_p : RFH != 0 ? rst_nf : rst;
`ifdef OT_S81PH_SEL_HQ
    // S81-TOPK7 hierarchical quarter (ot_s81ph_hq_tile.sv): same ports / function / edges, native-census-clean structure
`ifndef OT_S81PH_SEL_HQ_MUT
`define OT_S81PH_SEL_HQ_MUT 0
`endif
    dsfd_selt_q_hq #(.DM(4 + `OT_BKSEL_DMX), .MUT(`OT_S81PH_SEL_HQ_MUT), .FACE(RFH != 0), .HLAT(HLAT)) u_q (.ck(ck), .rst(rst_i),
        .lane(lane_i), .f_c(f_c_i), .f_cr(f_cr_i), .t_s(t_s_f), .t_o(t_o_f));
`else
    dsfd_selt_q2 #(.DM(4 + `OT_BKSEL_DMX), .CMP_RETIME(1), .PIPE2(1), .QIO(1), .ILD(1), .FRPR(1)) u_q (.ck(ck), .rst(rst_i),
        .lane(lane_i), .f_c(f_c_i), .f_cr(f_cr_i), .t_s(t_s_f), .t_o(t_o_f));
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
