`timescale 1ns/1ps
// ot_v41_bf_col3 (DIE-S81-51/RF-H 2026-11-03): ot_v41_bf_col as three hard cores, wires only.  u_c = ot_v41_bf_col3_c
// (pins, ROMs, FP lanes, chains, pair, segment tree, outputs, BF root adder); u_ha / u_hb = ot_v41_bf16_half (BF16 lanes
// 0-7 / 8-15).  Same ports and parameters as ot_v41_bf_col; every partial leaves 2 + BRNECUT cycles later, BF and FP
// partials keep the original spacing (ot_v41_bf_col3_c DEQ).  Requires the TCG / QBF >= 2 / BF16 configuration and HDLY 0.
module ot_v41_bf_col3 #(
    parameter integer NSEG = 8,
    parameter integer NCH = 16,
    parameter integer XF = 4,
    parameter integer LV = 5,
    parameter integer BF16 = 0,       // 1: the 16-lane BF16 path (ot_v41_bf16_lanes) and its x port
    parameter integer NCHB = 8,
    parameter integer NB = 1,
    parameter integer MTP = 0,        // 1: up to 6 positions time-multiplexed position-outer (2 tree banks by parity)
    parameter integer EARLY = 0,      // 1: segment tree early exit (fill cut)
    parameter integer CG = 1,         // 1: one integrated clock gate for the element (pair): clocked only from go
                                      //    until DRAIN cycles after its last word issued
    parameter integer DRAIN = 127,
    // 1.2 GHz at SS (W10, 2026-09-30): FAST = 1 builds the lanes, chains, pair adder and segment tree on the re-cut
    // modules (ot_v41_bterm2_w10, ot_v41_fadd with stage mask CUT); PP = 1 replaces each macro with two
    // ot_rom_4096x274_m8 read alternately (ping-pong), each a 2-cycle path, addressed in issue order
    parameter integer FAST = 0,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer PP = 0,
    // W10 SS frontend: remove class selection from the address carry/compare
    // cone. Opt-in, no added cycles or changes to capture/walker sequencing.
    parameter integer FRONT_PAR = 0,
    // BF16_PAIR (root decision 2026-09-30, option iii): BF16 rows on the standard pair.  A BF16 word (16 weights,
    // lane l = element b of golden chunk 16u + l) is held 4 cycles; 4 multipliers per macro take lanes 4k..4k+3 in
    // cycle k into 4 chunk chains (NCH >= 24 slots: slot = 4 x word-in-round + k); at the round b = 7 the 4 chunk
    // sums of a cycle meet in 2 pair adds and 1 add (golden levels 1-2) and the 4-chunk node is the segment tree's
    // base node.  A BF16 sub-block is 2 units.  Requires FAST = 1.
    parameter integer BP = 0,
    parameter integer QTIMING_FIX = 0,  // see the header; 0 = the original circuit
    parameter integer HC = 3,           // QTIMING_FIX: duplicated match copies (0: walker + fw_v, 1: nA, 2: nB)
    parameter integer QPIPE = 0,        // see the header; 0 = the qt circuit
    parameter integer QP_XS = 1,        // QPIPE: register the x beats at the boundary (0: the spine issues go, the
                                        // configuration and reset one cycle early and the beats keep their timing)
    parameter integer QP_CAP = 0,       // QPIPE: +1 cycle, registered capture select
    parameter integer QP_P1 = 1,        // QPIPE: +1 cycle, split lane P1
    parameter integer QP_CSAM = 10,     // QPIPE: lane first carry-save outputs (7 = bterm2)
    parameter integer QZ = 0,           // see the header; 0 = the qp circuit
    parameter integer QZ_NS = 8,        // QZ: copies of the capture bank / FP4 selects per macro
    parameter integer QZ_NE = 4,        // QZ: copies of each capture register's load enable per macro
    parameter integer QY = 0,           // see the header; 0 = the qz circuit
    parameter integer QX = 0,           // see the header; 0 = the QY circuit
    // QBF (BF rowfix re-cut A, 2026-10-07, default 0 = unchanged): permit BF16 = 1 under QPIPE / QZ (the S81 BF pair on
    // the q-element's closed walker / issue / tree / chain fixes); GRADUAL_RNE is passed to the BF16 lanes (mandatory
    // multiplier repair of the BF view).  With QBF = 0 or BF16 = 0 nothing below changes.
    parameter integer QBF = 0,
    // QZE (BF ICG enable retime, 2026-10-08, default 0 = unchanged; QZ only): the ICG ENA is driven by ze, a register
    // with no logic in front of the ICG and a single 2-input OR cone, ze(t+1) = go_pin(t) || z(t), instead of by u_z
    // directly (u_z sits in its deep enable cone, ~100 ps of wire from the root-level ICG: plain BF recut TT -16 on
    // u_z -> ICG ENA).  ze(t) >= z(t) every cycle: z(t) = go_pin(t-1) || rst_n(t-1) && en(t-1) with every en term
    // inside cg_en_q(t-1) = z(t-1) (en_r_d(t) <= go || en_r = go_e || drain != 0 <= cg_en; go, en_r, ext_lo <= cg_en_q),
    // and ze closes at most one cycle after z.  Zero added cycles; one extra gated edge per busy period.
    parameter integer QZE = 0,
    // TCG (bf-arch 2026-10-09, default 0 = unchanged; requires QZ = QZE = CG = 1): clock / reset TILES.  The element's
    // single root-level gate (u_cg) keeps only the front end; each macro column gets its own tile (ot_v41_tile_clk: a
    // local copy of the registered gate enable ze, its own gate) and, with BF16 under QBF, the BF lanes are
    // ot_v41_bf16_lanes3 (one tile per lane and one for the tag line and pairwise tree, each with its own enable copy,
    // gate and reset-synchroniser copy).  Every copy is the same register function of the same inputs as the element's
    // ze / reset synchroniser: every register keeps its clock edges and reset release (exact by construction, zero
    // cycles).  BXST (TCG only): extra pipelined input stages of the BF lanes (ot_v41_bf16_lanes3 XST; +BXST cycles of
    // BF lane latency, transaction-level exact).
    parameter integer TCG = 0,
    parameter integer BXST = 0,
    // BRNECUT (RF-H conservative form, 2026-11-03; default 0 = unchanged): ot_v41_bf16_lanes3 RNECUT -- one more register
    // cut in the BF16 subnormal RNE encode + round, BF lane latency +1 cycle (transaction level, as one more BXST stage).
    parameter integer BRNECUT = 0,
    parameter integer FXST = 0,         // TCG only: pipelined FP8/FP4 lane input stages (+FXST cycles; see g_l3)
    parameter integer GRADUAL_RNE = 0,
    parameter INSTANCE = "",
    parameter integer HDLY = 0,       // bf-hier-1011: HB4 hold-delay cells per input bit ahead of the boundary registers
    parameter integer MB = 0,         // which column (simulation ROM image name only)
    // RCG (S81-CORE-LAT-R2/BF 2026-10-26, METHODOLOGY 12.8): TCG regional clock gates.  The TCG column tile u_tc gated
    // 15,936 flops + both ROMs and the lanes' tree tile u_bf.u_tt 14,219 (measured, Yosys elaboration of the kit
    // parameters), against 1,284 per lane tile: two whole-core gated trees under one ICG each, which set the core's
    // 491-663 ps clock insertion.  RCG = 1 gives every unit group its own tile (ot_v41_tile_clk: a LOCAL copy of the
    // same registered enable ze, same d / clock / reset as u_tc.u_ze, and a LOCAL ICG), all on the core root clock, so
    // every gate drives ~0.5-4.5k sinks at ONE gate level: segment tree (u_tc_tr), FP lanes l0 / l1 (u_tc_l0/l1), their
    // FXST input stages (u_tc_fx), chunk chains c0 / c1 (u_tc_c0/c1), sibling pair + delays (u_tc_pa); u_tc keeps the
    // capture / x / control registers and the ROM macros; lanes3 gets one tile per tree adder node (TNODE).  Every copy
    // is the same register function of the same inputs, so every register keeps exactly its clock edges (clock-network
    // change only; bench + LEC: physical/die_plan/s81/core_lat/bf_col_gates.json).  RCG = 0: the original network.
    parameter integer RCG = 0,
    parameter integer TAG_GROUPS = 0, // opt-in final BF tag-stage replication; zero cycles
    parameter integer KEEP_XPOS = 0   // opt-in: segtree5 x_pos as a kept register (LEC correspondence; see ot_v41_segtree5)
) (
    input  wire          clk,
    input  wire          rst_n_pin,
    input  wire          ze_d,          // element gate-enable next state (qx tcg_ze_d)
    input  wire          issue,
    input  wire [13:0]   a_ctr,
    input  wire          i1_v,
    input  wire          i1_bk,
    input  wire          i1_bf,
    input  wire [$clog2(NCH)+3+$clog2(NSEG)+(MTP != 0 ? 1 : 0)+6-1:0] i1_t,
    input  wire [255:0]  i2x_q0,
    input  wire [9:0]    i2x_e0,
    input  wire [255:0]  i2x_q1,
    input  wire [9:0]    i2x_e1,
    input  wire [16*NSEG-1:0] so_row,   // this column's NSEG output rows
    input  wire [5*NSEG-1:0]  so_idx,
    input  wire [5*NSEG-1:0]  so_n,
    output wire          pv,
    output wire [31:0]   pval,
    output wire [15:0]   prow,
    output wire [4:0]    pseg,
    output wire [4:0]    pnseg,
    output wire          perr,
    output wire [2:0]    ppos,
    output wire          qy_bkf
);
    localparam integer HTG = 3 + $clog2(NSEG) + (MTP != 0 ? 1 : 0);
    localparam integer HTT = $clog2(NCHB) + 3 + HTG;
    wire          h_v_a, h_v_b, r_v_a, r_v_b, r_err_a, r_err_b, r_f_a, r_f_b;
    wire          h_rst_a, h_ze_a, h_rst_b, h_ze_b;   // the halves' reset / gate-enable (column face copies)
    wire [127:0]  h_w_a, h_x_a, h_w_b, h_x_b;
    wire [HTT-1:0] h_t_a, h_t_b;
    wire [31:0]   r_val_a, r_val_b;
    wire [HTG:0]  r_t_a, r_t_b;
    ot_v41_bf_col3_c #(
.NSEG(NSEG),
.NCH(NCH),
.XF(XF),
.LV(LV),
.BF16(BF16),
.NCHB(NCHB),
.NB(NB),
.MTP(MTP),
.EARLY(EARLY),
.CG(CG),
.DRAIN(DRAIN),
.FAST(FAST),
.CUT(CUT),
.PP(PP),
.FRONT_PAR(FRONT_PAR),
.BP(BP),
.QTIMING_FIX(QTIMING_FIX),
.HC(HC),
.QPIPE(QPIPE),
.QP_XS(QP_XS),
.QP_CAP(QP_CAP),
.QP_P1(QP_P1),
.QP_CSAM(QP_CSAM),
.QZ(QZ),
.QZ_NS(QZ_NS),
.QZ_NE(QZ_NE),
.QY(QY),
.QX(QX),
.QBF(QBF),
.QZE(QZE),
.TCG(TCG),
.BXST(BXST),
.BRNECUT(BRNECUT),
.FXST(FXST),
.GRADUAL_RNE(GRADUAL_RNE),
.INSTANCE(INSTANCE),
.HDLY(HDLY),
.MB(MB),
.RCG(RCG),
.TAG_GROUPS(TAG_GROUPS),
.KEEP_XPOS(KEEP_XPOS)) u_c (
        .clk(clk), .rst_n_pin(rst_n_pin), .ze_d(ze_d), .issue(issue), .a_ctr(a_ctr), .i1_v(i1_v), .i1_bk(i1_bk), .i1_bf(i1_bf),
        .i1_t(i1_t), .i2x_q0(i2x_q0), .i2x_e0(i2x_e0), .i2x_q1(i2x_q1), .i2x_e1(i2x_e1), .so_row(so_row), .so_idx(so_idx),
        .so_n(so_n), .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr), .ppos(ppos), .qy_bkf(qy_bkf),
        .h_v_a(h_v_a), .h_v_b(h_v_b), .h_w_a(h_w_a), .h_x_a(h_x_a), .h_w_b(h_w_b), .h_x_b(h_x_b), .h_t_a(h_t_a), .h_t_b(h_t_b),
        .r_v_a(r_v_a), .r_val_a(r_val_a), .r_val_b(r_val_b), .r_err_a(r_err_a), .r_err_b(r_err_b), .r_t_a(r_t_a),
        .r_f_a(r_f_a), .r_f_b(r_f_b),
        .h_rst_a(h_rst_a), .h_ze_a(h_ze_a), .h_rst_b(h_rst_b), .h_ze_b(h_ze_b));
    ot_v41_bf16_half #(.NCHB(NCHB), .GRADUAL_RNE(GRADUAL_RNE), .TRW(HTG), .CUT(CUT), .RC(QBF >= 3 ? 2 : QBF >= 2 ? 1 : 0),
        .TNODE(RCG), .RNECUT(BRNECUT)) u_ha (.clk(clk), .rst_c(h_rst_a), .ze_c(h_ze_a), .v(h_v_a), .w(h_w_a), .x(h_x_a),
        .t(h_t_a), .ov(r_v_a), .oval(r_val_a), .oerr(r_err_a), .otag(r_t_a), .fault(r_f_a));
    ot_v41_bf16_half #(.NCHB(NCHB), .GRADUAL_RNE(GRADUAL_RNE), .TRW(HTG), .CUT(CUT), .RC(QBF >= 3 ? 2 : QBF >= 2 ? 1 : 0),
        .TNODE(RCG), .RNECUT(BRNECUT)) u_hb (.clk(clk), .rst_c(h_rst_b), .ze_c(h_ze_b), .v(h_v_b), .w(h_w_b), .x(h_x_b),
        .t(h_t_b), .ov(r_v_b), .oval(r_val_b), .oerr(r_err_b), .otag(r_t_b), .fault(r_f_b));
`ifndef SYNTHESIS
    initial if (!(TCG != 0 && BF16 != 0 && FAST != 0 && QBF >= 2 && HDLY == 0 && TAG_GROUPS == 0 && BXST == 2))
        $fatal(1, "ot_v41_bf_col3: unsupported configuration");
`endif
endmodule
