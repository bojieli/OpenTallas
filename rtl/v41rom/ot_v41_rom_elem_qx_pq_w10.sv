`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_rom_elem_qx_pq_w10 (2026-10-06): SUCCESSOR of ot_v41_rom_elem_qx_w10 (the DS q-element, QX) with the PQ
// back-to-back-phase mechanism of ot_v41_rom_elem_pq_w10 (DS-ROM recovery lever field_spine_pq), so the q-element
// can run under the PQ field spine (ot_v41_spine_pq_w17w10).  PQ = 0: the qx element's logic exactly (the added
// ports are unused).  PQ = 1:
//   * output tags banked by op (ot_v41_elem_pq_tags, unchanged): every configuration load writes the next op's bank
//     of the segment row / index / count tables at once, the partial at the segment-tree exit reads its own op's
//     bank (tree parity), row bits [15:14] carry the op's 2-bit tag; the qx output tables (s_row / so_row) are not
//     read.  The tree id is {position parity ^ op parity, segment} (w_tree), as in the PQ element.
//   * configuration SHADOW by REPLAY: a load is written into a 48-bit shadow word file (one entry per address)
//     while the current op still runs; when the shadow is full and the walkers and issue pipeline are idle
//     (walk_busy) the tags module's swap starts a replay of the walker-side words (segments 0..NSEG-1, classes
//     NSEG..2NSEG-1, word 2NSEG; RPW = 2NSEG+1 words, one a cycle) into the qx element's own configuration port
//     after the QPIPE boundary, exactly as a load from the pins arrives there (the registered class decode qy_cdec
//     included).  Every register the qx element derives from a configuration write (QX one-hot walker facts, r_dp,
//     w_sf_r candidates, the registered sub-block facts) therefore sees an ordinary load.  The second-macro row
//     words 2NSEG+1.. only feed the output tables and are not replayed.
//   * `walking` (to the tags module and the port) = walk_busy or replay in progress or RT tail cycles after it, so
//     a go before the replayed configuration has settled is a FAULT (tags module), never a silent skip.
//   * cost against the PQ W10 element (one-cycle shadow copy): RPW + RT cycles more between the previous op's last
//     walk and the next go; the PQ spine's GAP / GUARD must cover them (reported with the measurement).
// ---------------------------------------------------------------------------
// Original header (ot_v41_rom_elem_qx_w10):
// ot_v41_rom_elem_qx_w10: ot_v41_rom_elem_qy_w10 (byte-identical body, renamed) plus the opt-in QX (default 0 = the qy
// circuit).  QX = 1 (requires FAST = 1; DS-V4.1 ROM q-pair SS closure, 2026-10-04, after route Z2: post-GRT SS -118.8 ps,
// all 125 post-CTS violators in the word walker, w_c -> walk2 encode -> 8:1 re-decode by w_nx_c -> w_lu_r / w_h /
// wA / wB / a_ctr / w_s / w_j / w_cl_r): the walker step is decided in one-hot form.  w_coh / w_cgt mirror w_c (one-hot
// and the mask k > w_c), loaded wherever w_c is; every per-class quantity the step needs (j + 1 < cur[k], the lookahead
// lu_f(wA, k, j + 1), lu_f(wA / wB, k, 0), the FP8 high-half start of c_s0[k], s + 1 == c_s1[k]) is formed for all
// classes in parallel from registers; the next class stays one-hot (lowest live class above w_c, or the next round's
// first class) and w_lu_r, w_h, w_s, w_c, w_cl_r, the sub-block advance (wA <= wB), the restart and the round end are
// AND-OR selects of those vectors.  QP_CHECK asserts the mirrors and every consequence equal the encoded walker's every
// cycle.  Zero added cycles; outputs cycle-identical to the qy element.
// QX = 2 (after route Z3b's post-CTS screen, SS -45.1 ps: every walker path starts at w_j through the per-class compare
// j + 1 < cur[k] and its OR, the "next unit of the same class" decision, ~300 ps before the select): that decision is
// held in a register w_ca_r loaded with its value for the walker's next state exactly where w_lu_r is (go, restart,
// step; the step value is an AND-OR select of per-class compares against the next state's wA / wB), and the x-need
// walker's nA / nB enables (sub-block advance, MTP restart) are formed from a decoded n_c and per-class vectors
// instead of the encoded walk2 output (Z3b: n_c -> nB -16.8 ps).  QP_CHECK asserts both.  Zero added cycles.
// QX = 3 (after routes Z5a / Z5b: post-GRT SS -18.6 / -17.6 ps, n_c -> per-class select -> nA / nB enables): the x-need
// walker's step in one-hot form exactly as the word walker's (mirrors n_coh / n_cgt, registered case-A decision n_ca_r,
// next class one-hot), which also feeds the QTIMING_FIX match copies.  QP_CHECK asserts it.  Zero added cycles.
// QX = 4 (after route Z6: post-GRT SS -36.6 ps on the lane's P2 shift + CSA, behind ~107 ps of CTS skew): the lanes
// are ot_v41_bterm4_w10 with P2S = 1 (two shifter levels moved into P1b, bit-identical).  ot_v41_bterm4_w10 with
// P2S = 0 is ot_v41_bterm3_w10, so QX < 4 is unchanged.  Zero added cycles.
// QX = 5 (after route Z7's post-CTS screen, SS -40.7 ps on w_cnt -> hazard compare -> issue -> walker enables): the
// issue hazard is a register loaded with its next-cycle value (three register-only candidates selected by go / issue).
// QP_CHECK asserts it equals the original every cycle.  Zero added cycles.
// QX = 10 (zero cycles, after routes Z15a / Z15b): lane NaN flag as 8-lane partials (bterm4 NS), chain adder step 0 on
// every forward candidate in parallel (ot_v41_chain4 PD / ot_v41_fadd2), r_dp by parallel prefix differences, and the
// go / restart segment-flag candidates of w_sf_r from registers formed a cycle earlier.
// QX = 9 (owner decision 2026-10-05, structural): the segment tree is ot_v41_segtree5, its decide stage split into a
// read stage (80-slot held / have / above selects reduced into 4 group partials, next-state forwarding) and a decide
// stage, so a tree level costs one more cycle and the element's partial outputs leave later (data-dependent; same
// values and per-segment order).  The walker, FIFO and issue are unchanged.
// QX = 8 (after routes Z12a-c, SS -41 to -43 ps on the segment tree's x_oh -> held[] select -> add_a): the tree is
// ot_v41_segtree4 with XC = 4 (four kept copies of x_oh, each selecting 8 of the 32 held bits; XC = 1 is segtree3).
// (The first QX = 8, XR = 1 early read, measured SS -175 ps in Z14a and is not used.)  Zero cycles.
// QX = 7 (after route Z11d, SS -3.8 ps on r_go's fan-out into nB): kept copies of the go boundary register for the
// nA / nB, wA / wB / fF and walker-state loads.  Zero added cycles.
// QX = 6 (after CTS screen Z9s2, SS -22.6 ps on w_s -> s_x[w_s] lookups -> w_seg_last -> w_h): w_s's segment flags
// are a register loaded wherever w_s is.  QP_CHECK asserts it.  Zero added cycles.
//
// ot_v41_rom_elem_qy_w10: ot_v41_rom_elem_qz_w10 (byte-identical body, renamed) plus the opt-in QY (default 0 = the qz
// circuit).  QY = 1 (requires QZ = 1; DS-V4.1 ROM q-pair SS closure, 2026-10-04, after route Z1's post-CTS screen):
//   (1) fault: each macro half's six sticky fault bits are ORed into a register, and the front-end fault and the two
//       halves' registers into a second one that drives the port: the fault port is a register (Z1: a 12-input OR
//       across the die straight to the port, -71.8 ps against the output budget).  Fault reporting is 2 cycles later
//       (QY_FL = 2); no data output, busy or state changes.
//   (2) x-need match pair offset (r_dp): the configuration-address decode (cfg_v && cfg_a == NSEG + c) is registered
//       at the boundary beside b_cfg_a (from the pins, one cycle early), so r_dp's cone is a 2:1 select and the
//       subtractor (Z1: decode -> 8-bit subtract -24.7 ps).
//   (3) walker: w_cl_r holds (w_s == c_s1[w_c]), the "last segment of the class" decision, loaded for the walker's
//       next (w_s, w_c) case by case exactly as the walker loads them (the step case uses a per-class table
//       c_s0[c] == c_s1[c] selected by w_nx_c), so the issue / step / pop / restart cone no longer starts with an 8:1
//       class select and a compare (Z1: w_c -> w_h -47.4 ps, -> w_lu_r -45.2 ps).  QP_CHECK asserts it equals the
//       original expression every cycle the walker runs.  Zero added cycles.
//
// ot_v41_rom_elem_qz_w10: ot_v41_rom_elem_qp_w10 (byte-identical body, renamed) plus the opt-in QZ (default 0 = the qp
// circuit).  QZ = 1 (DS-V4.1 ROM q-pair SS/FF closure, 2026-10-04; ZERO added cycles, requires QPIPE = 1, QTIMING_FIX
// = 1, FAST = 1, PP = 1, QP_CAP = 0, BF16 = 0, BP = 0):
//   (1) per-macro state that must stay per macro is held in ot_v41_kreg instances (keep_hierarchy).  Yosys opt_merge
//       merged the qp element's (* keep *) per-macro issue-control copies and, through them, the two macro halves'
//       lanes and chains, so single registers drove both halves across the die (R_cap0: r_i2_bk -236 ps, cap0 -> p0_we
//       -166 ps, fwd5 -67 ps at SS).  Per macro: the issue control (r_i2x_*, r_i3_v, r_i2_*), the x slices (a copy of
//       i2_* loaded from i2x_*, same cycle), the reset synchroniser (a copy of g_qb.rst_q), QZ_NS copies of the capture
//       bank select and the FP4 select (each driving 1 / QZ_NS of the 274-bit capture mux / 256-bit lane-0 word mux),
//       and QZ_NE copies of each capture register's load enable (mi2x_v && bank, loaded from i1 one cycle early).
//   (2) the clock-gate enable is a register: u_z (free clock, set while rst_n_pin is low) loads one cycle early the
//       value cg_en_q takes in the next cycle, z(t+1) = go_pin(t) || rst_n(t) && (en_r_D(t) || go(t) || en_r(t)
//       || ext[QK-2:0](t)), so no logic sits between a free-clock register (latency ~550 ps at SS, behind the CTS
//       delay chain that balances it against the gated tree) and the root-level ICG (CLK latency ~70 ps); R_cap0:
//       rst_q -> ICG ENA -82 ps at SS.  QP_CHECK asserts z == cg_en_q every cycle.
//   (3) the chains are ot_v41_chain3 (fwd5 / fwd6 in QZ_NS / 2 kept copies, each driving 1 / copies of the operand mux).
// Every output, the walker / FIFO / issue / drain state and the gating are cycle-identical to the qp element.
//
// ot_v41_rom_elem_qp_w10: ot_v41_rom_elem_qt_w10 (byte-identical body, renamed) plus the opt-in QPIPE (default 0 = the
// qt circuit).  QPIPE = 1 (DS-V4.1 ROM q-pair at SS 1.2 GHz, 2026-10-03) adds PRICED latency and never changes what
// is computed: every output is the qt element's output delayed by L = 1 + QP_CAP + QP_P1 cycles.
//   boundary (+1): go, go_bf and the configuration are registered on the free clock, rst_n passes a local
//       synchroniser (asynchronous assert, synchronous deassert), and with QP_XS the x beats are registered on the
//       gated clock, so every input is delayed by exactly one cycle and no primary input reaches the clock gate.
//       (A beat registered while the gate was closed is never used: the first gated edge after a closed gate is the
//       go edge, and no walker runs in that cycle.)
//   QP_CAP (+1): the per-macro capture select is registered before the lanes.
//   QP_P1 (+1): the lanes' decode / product stage is split (ot_v41_bterm3_w10 P1S); QP_CSAM re-balances the lanes'
//       carry-save levels (zero cycles, exact modulo 2^42).
//   zero-cycle restructures: per-macro copies of the issue pipeline's control (the two macro halves no longer share
//       synthesised control across the die), the segment tree's slot-local decisions (ot_v41_segtree3), the x-match
//       pair offset precomputed from the boundary register (one subtractor per class, against the class base the
//       configuration will hold in the match cycle), the FP8 half select retimed one stage later, busy / fault
//       delayed with the datapath (registered outputs), and the clock gate held QP_CAP + QP_P1 cycles longer.
//
// ot_v41_rom_elem_qt_w10: ot_v41_rom_elem_w10 (byte-identical body, renamed) plus the opt-in QTIMING_FIX
// (default 0 = the original circuit).  The original file is source-pinned by W10 records, so the fix lives in this
// copy; ot_v41_walk2_w10 / ot_v41_walk_w10 / ot_v41_first_w10 still come from ot_v41_rom_elem_w10.sv.
// QTIMING_FIX = 1 (DS-V4.1 ROM q-pair, 2026-10-03; zero added cycles, outputs and gating cycle-identical):
//   (1) clock-gate enable: cg_en = !rst_n || go || en_r, en_r a free-clock register loaded with
//       go_e_next || walk_busy || drain > 1, i.e. en_r(t) == go_e(t) || drain(t) != 0.  walk_busy(t) implies
//       go_e(t-1) || walk_busy(t-1), hence drain(t) != 0, so the enable equals the original cycle by cycle and no
//       gated-domain register drives the ICG ENA through logic any more.
//   (2) the x-capture match: HC duplicated (keep) copies of the need-walker state {run, fam, c, q, j, b, pos}, each
//       with its own per-class parallel pair compare, drive disjoint load groups (walker / nA / nB); the 532-bit fw_*
//       beat register loads every gated cycle (it is read only under fw_v, i.e. the cycle after a match), so the
//       match no longer drives 532 enables.
//
// ot_v41_rom_elem_w10: the V4.1 ROM-array element (docs/MICROARCH_MODEL.md build item 1; W10).
//
//   one ot_rom_8192x274_m8 macro + a 274-bit capture register at its pins
//   + 2 exact block-dot lanes (FP4: one 32-block each = 64 MACs/cycle; FP8: lane 0 = 32 MACs/cycle)
//   + per lane an NCH-slot golden chunk chain on one pipelined binary32 adder
//   + one pair adder (FP4 sibling chunks) + an NSEG-tree golden segment tree (LV levels)
//   -> one FP32 partial per K segment, tagged {row, segment, segments in the row}.
//
// Arithmetic: golden linear_q under R-ARITH chunk8 (tools/hdc_golden_v41.py): every 32-block dot is
// exact, rounded once to binary32 and scaled by 2^(xe + we) (ot_v41_bterm); each chunk of 8 blocks is
// summed sequentially from +0; chunk sums combine by the padded pairwise tree.  A segment is a
// power-of-two-aligned run of chunks, so its partial is a node of the row's golden tree; the array's
// return network finishes the tree (ot_v41_ret_node / ot_v41_ret_root).
//
// Units and words (tools/v41_rom_ksplit_bankmap.py): the x unit is a chunk PAIR (2p, 2p+1).  Word b of a
// unit holds block b: FP4 = {chunk 2p+1 (high 136 bits) | chunk 2p (low)}, two lanes; FP8 = one word per
// chunk of the pair that the segment covers (half h), lane 0.  Each segment's words are contiguous at its
// base in its read order: sub-block q (8 units), b, unit, half.
// Issue order (element_order): q, b, class (segments sharing one unit range; a macro's classes are
// disjoint) in ascending unit, unit, the class's segments, half.  One captured x slice (pair p, block b)
// serves every word of a (class, unit, b).  Each chain (word position in the round) is revisited once per
// round; rounds are >= 5 cycles by the stream schedule and an issue-side check stalls a re-visit that
// would come sooner than the adder's 5-cycle recurrence.
//
// X stream beat: {pair p, block b, slot valids, codes and exponents of chunk 2p (slot 0) and 2p+1 (1)};
// FP8 and FP4 share it.  The element captures the slices it needs, in stream order, into an XF-entry FIFO.
//
// Configuration (cfg_v, cfg_a, cfg_d[47:0]), loaded before `go`:
//   cfg_a = 0 .. NSEG-1      segment s: [15:0] row, [20:16] segment index, [25:21] segments in row, [26] fp4,
//                            [27] low half of its first unit present, [28] high half of its last unit
//                            present, [41:29] base address
//   cfg_a = NSEG .. 2NSEG-1  class c:   [0] valid, [8:1] first unit (pair / BF16 lane group), [15:9] units,
//                            [18:16] first segment, [21:19] last segment, [22] BF16 family (NSEG <= 8)
//   cfg_a = 2NSEG            [2:0] sub-blocks - 1 (a class of u units spans ceil(u / 8) sub-blocks), [5:3] MTP
//                            positions - 1, [19:6] PP: the phase's first word index (words stored in issue order,
//                            word i in bank i[0] at address i[13:1])
//   segment [42]             BF16
//   cfg_a = 2NSEG+1+s        (NB = 2) [15:0] the row of segment s on the second macro of the pair
//                            (a row with bit 15 set is an idle half: that macro emits no partial for it)
// ---------------------------------------------------------------------------
module ot_v41_rom_elem_qx_pq_w10 #(
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
    parameter integer PQ = 0,           // see the PQ header: 0 = the qx element
    parameter integer RT = 3,           // PQ: settle cycles after the replay
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         rst_n_pin,
    input  wire         cfg_v_pin,
    input  wire [4:0]   cfg_a_pin,
    input  wire [47:0]  cfg_d_pin,
    input  wire         go_pin,
    input  wire         go_bf_pin,        // the phase's family: 0 = FP8/FP4 (shared FP8 x stream), 1 = BF16
    input  wire [1:0]   go_tag_pin,       // PQ: the op's tag (rides in partial rows [15:14])
    output wire         walking,          // PQ: walkers / issue / configuration replay busy
    output wire         bank_free,        // PQ: the bank the next configuration load writes holds no live op
    output wire         sh_free,          // PQ: the configuration shadow is empty
    input  wire         xs_v_pin,
    input  wire [7:0]   xs_p_pin,
    input  wire [2:0]   xs_b_pin,
    input  wire [1:0]   xs_sv_pin,
    input  wire [255:0] xs_q0_pin,
    input  wire [9:0]   xs_e0_pin,
    input  wire [255:0] xs_q1_pin,
    input  wire [9:0]   xs_e1_pin,
    input  wire [2:0]   xs_pos_pin,       // MTP position of the beat
    input  wire [2:0]   xb_pos_pin,
    // BF16 x stream beat: 4 lane-group slices {unit, 16 BF16} for block b
    input  wire         xb_v_pin,
    input  wire [2:0]   xb_b_pin,
    input  wire [3:0]   xb_sv_pin,
    input  wire [31:0]  xb_u_pin,
    input  wire [1023:0] xb_d_pin,
    output wire [NB-1:0]    pv,
    output wire [32*NB-1:0] pval,
    output wire [16*NB-1:0] prow,
    output wire [5*NB-1:0]  pseg,
    output wire [5*NB-1:0]  pnseg,
    output wire [NB-1:0]    perr,
    output wire [3*NB-1:0]  ppos,
    output wire         busy,
    output wire         fault
);
    // ---------------- QPIPE boundary (see the header) --------------------------------------------------------
    wire         rst_n, cfg_v, go, go_bf, xs_v, xb_v;
    wire [4:0]   cfg_a;
    wire [47:0]  cfg_d;
    // PQ: the boundary's configuration (cfg_*_x, qy_cdec_x) reaches the element body (cfg_*, qy_cdec) directly
    // (PQ = 0) or through the shadow replay (PQ = 1, below)
    wire         cfg_v_x;
    wire [4:0]   cfg_a_x;
    wire [47:0]  cfg_d_x;
    wire [NSEG-1:0] qy_cdec_x;
    wire [1:0]   go_tag;
    wire [7:0]   xs_p;
    wire [2:0]   xs_b, xs_pos, xb_pos, xb_b;
    wire [1:0]   xs_sv;
    wire [255:0] xs_q0, xs_q1;
    wire [9:0]   xs_e0, xs_e1;
    wire [3:0]   xb_sv;
    wire [31:0]  xb_u;
    wire [1023:0] xb_d;
    wire gclk;
    wire [NSEG-1:0] qy_cdec;            // QY: registered class-configuration write decode (QPIPE boundary)
    localparam integer QK = QPIPE != 0 ? QP_CAP + QP_P1 : 0;   // datapath cycles added after the boundary
    if (QPIPE != 0) begin : g_qb
        // local reset: asserted with rst_n_pin, released on the clock edge after it (the parent's reset is
        // synchronous to clk, so one flop is a synchroniser; rst_n is then a register, not a primary input)
        (* keep, dont_touch = "true" *) reg rst_q;
        always @(posedge clk or negedge rst_n_pin) if (!rst_n_pin) rst_q <= 1'b0; else rst_q <= 1'b1;
        assign rst_n = rst_q;
        reg b_go, b_cfg_v, b_go_bf;
        reg [1:0] b_go_tag;
        reg [NSEG-1:0] b_cdec;          // QY: cfg_v_pin && cfg_a_pin == NSEG + c, registered with b_cfg_a
        always @(posedge clk or negedge rst_n_pin)
            if (!rst_n_pin) b_cdec <= '0;
            else for (int c = 0; c < NSEG; c++) b_cdec[c] <= cfg_v_pin && cfg_a_pin == 5'(NSEG + c);
        assign qy_cdec_x = b_cdec;
        reg [4:0] b_cfg_a; reg [47:0] b_cfg_d;
        always @(posedge clk or negedge rst_n_pin)
            if (!rst_n_pin) begin b_go <= 1'b0; b_cfg_v <= 1'b0; end
            else begin b_go <= go_pin; b_cfg_v <= cfg_v_pin; end
        always @(posedge clk) begin b_cfg_a <= cfg_a_pin; b_cfg_d <= cfg_d_pin; b_go_bf <= go_bf_pin; b_go_tag <= go_tag_pin; end
        assign go = b_go; assign cfg_v_x = b_cfg_v; assign cfg_a_x = b_cfg_a; assign cfg_d_x = b_cfg_d; assign go_bf = b_go_bf;
        assign go_tag = b_go_tag;
        if (QP_XS != 0) begin : g_bx
            reg b_xs_v, b_xb_v;
            reg [7:0] b_xs_p; reg [2:0] b_xs_b, b_xs_pos, b_xb_pos, b_xb_b; reg [1:0] b_xs_sv;
            reg [255:0] b_xs_q0, b_xs_q1; reg [9:0] b_xs_e0, b_xs_e1; reg [3:0] b_xb_sv; reg [31:0] b_xb_u;
            reg [1023:0] b_xb_d;
            always @(posedge gclk or negedge rst_n_pin)
                if (!rst_n_pin) begin b_xs_v <= 1'b0; b_xb_v <= 1'b0; end
                else begin b_xs_v <= xs_v_pin; b_xb_v <= xb_v_pin; end
            always @(posedge gclk) begin
                b_xs_p <= xs_p_pin; b_xs_b <= xs_b_pin; b_xs_sv <= xs_sv_pin; b_xs_q0 <= xs_q0_pin; b_xs_e0 <= xs_e0_pin;
                b_xs_q1 <= xs_q1_pin; b_xs_e1 <= xs_e1_pin; b_xs_pos <= xs_pos_pin; b_xb_pos <= xb_pos_pin;
                b_xb_b <= xb_b_pin; b_xb_sv <= xb_sv_pin; b_xb_u <= xb_u_pin; b_xb_d <= xb_d_pin;
            end
            assign xs_v = b_xs_v; assign xs_p = b_xs_p; assign xs_b = b_xs_b; assign xs_sv = b_xs_sv;
            assign xs_q0 = b_xs_q0; assign xs_e0 = b_xs_e0; assign xs_q1 = b_xs_q1; assign xs_e1 = b_xs_e1;
            assign xs_pos = b_xs_pos; assign xb_pos = b_xb_pos; assign xb_v = b_xb_v; assign xb_b = b_xb_b;
            assign xb_sv = b_xb_sv; assign xb_u = b_xb_u; assign xb_d = b_xb_d;
        end else begin : g_nbx
            assign xs_v = xs_v_pin; assign xs_p = xs_p_pin; assign xs_b = xs_b_pin; assign xs_sv = xs_sv_pin;
            assign xs_q0 = xs_q0_pin; assign xs_e0 = xs_e0_pin; assign xs_q1 = xs_q1_pin; assign xs_e1 = xs_e1_pin;
            assign xs_pos = xs_pos_pin; assign xb_pos = xb_pos_pin; assign xb_v = xb_v_pin; assign xb_b = xb_b_pin;
            assign xb_sv = xb_sv_pin; assign xb_u = xb_u_pin; assign xb_d = xb_d_pin;
        end
    end else begin : g_nqb
        assign qy_cdec_x = '0;
        assign rst_n = rst_n_pin; assign go = go_pin; assign cfg_v_x = cfg_v_pin; assign cfg_a_x = cfg_a_pin;
        assign cfg_d_x = cfg_d_pin; assign go_bf = go_bf_pin; assign go_tag = go_tag_pin;
        assign xs_v = xs_v_pin; assign xs_p = xs_p_pin; assign xs_b = xs_b_pin; assign xs_sv = xs_sv_pin;
        assign xs_q0 = xs_q0_pin; assign xs_e0 = xs_e0_pin; assign xs_q1 = xs_q1_pin; assign xs_e1 = xs_e1_pin;
        assign xs_pos = xs_pos_pin; assign xb_pos = xb_pos_pin; assign xb_v = xb_v_pin; assign xb_b = xb_b_pin;
        assign xb_sv = xb_sv_pin; assign xb_u = xb_u_pin; assign xb_d = xb_d_pin;
    end

    localparam integer SW = $clog2(NSEG);
    localparam integer TRW = SW + (MTP != 0 ? 1 : 0);   // tree id = {position parity, segment}
    localparam integer HW = $clog2(NCH);
    localparam integer LAT = FAST != 0 ? 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8] : 5;
    localparam integer XD = PP != 0 ? 3 : 2;       // issue -> captured ROM word (a PP read is a 2-cycle path)
    // BF16_PAIR: BP = 2 (root re-decision 2026-09-30, option ii, the product): 2 multipliers per macro, a word held
    // 8 cycles (lanes 2k, 2k+1 in cycle k) into the 2 chunk chains (slot = 8 x word + k, <= 2 words per round at
    // NCH 16), the pair adder forms each 2-chunk node, a BF16 sub-block is 1 unit.  BP = 1: option iii (4 mults).
    localparam integer BPH = BP == 2 ? 8 : 4;      // cycles a BF16 word is held
    localparam integer BPN = 16 / BPH;             // multipliers per macro
    localparam integer KW = BP == 2 ? 3 : 2;       // hold counter width
    localparam [2:0] HOLDM1 = BPH - 1;
    localparam [KW-1:0] KLAST = BPH - 1;

    // ---------------- inputs: registered at the element boundary when FAST (the column spine drives them from
    // its own registers; one more cycle keeps the input delay out of the capture and walker loops).  go_e and the
    // configuration are registered on the free clock, the x beats on the gated clock (the gate opens at go_e).
    wire         cfg_v_e, go_e, go_bf_e, xs_v_e, xb_v_e;
    wire [4:0]   cfg_a_e;
    wire [47:0]  cfg_d_e;
    wire [7:0]   xs_p_e;
    wire [2:0]   xs_b_e, xs_pos_e, xb_pos_e, xb_b_e;
    wire [1:0]   xs_sv_e;
    wire [255:0] xs_q0_e, xs_q1_e;
    wire [9:0]   xs_e0_e, xs_e1_e;
    wire [3:0]   xb_sv_e;
    wire [31:0]  xb_u_e;
    wire [1023:0] xb_d_e;
    wire go_en, go_ew, go_em;
    wire [1:0]   go_tag_e;            // QX = 7: kept copies of go_e for the nA / nB, wA / wB / fF and walker loads
    if (FAST != 0) begin : g_ir
        reg r_cfg_v, r_go, r_go_bf, r_xs_v, r_xb_v;
        reg [1:0] r_go_tag;
        reg [4:0] r_cfg_a; reg [47:0] r_cfg_d; reg [7:0] r_xs_p; reg [2:0] r_xs_b, r_xs_pos, r_xb_pos, r_xb_b;
        reg [1:0] r_xs_sv; reg [255:0] r_xs_q0, r_xs_q1; reg [9:0] r_xs_e0, r_xs_e1; reg [3:0] r_xb_sv;
        reg [31:0] r_xb_u; reg [1023:0] r_xb_d;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin r_cfg_v <= 1'b0; r_go <= 1'b0; end
            else begin r_cfg_v <= cfg_v; r_go <= go; end
        always @(posedge clk) begin r_cfg_a <= cfg_a; r_cfg_d <= cfg_d; r_go_bf <= go_bf; r_go_tag <= go_tag; end
        assign go_tag_e = r_go_tag;
        always @(posedge gclk or negedge rst_n)
            if (!rst_n) begin r_xs_v <= 1'b0; r_xb_v <= 1'b0; end
            else begin r_xs_v <= xs_v; r_xb_v <= xb_v; end
        always @(posedge gclk) begin
            r_xs_p <= xs_p; r_xs_b <= xs_b; r_xs_sv <= xs_sv; r_xs_q0 <= xs_q0; r_xs_e0 <= xs_e0;
            r_xs_q1 <= xs_q1; r_xs_e1 <= xs_e1; r_xs_pos <= xs_pos; r_xb_pos <= xb_pos; r_xb_b <= xb_b;
            r_xb_sv <= xb_sv; r_xb_u <= xb_u; r_xb_d <= xb_d;
        end
        // configuration writes are not registered: the class registers must be final one cycle before go_e so the
        // registered sub-block facts below are current when go_e starts the walkers
        assign cfg_v_e = cfg_v; assign cfg_a_e = cfg_a; assign cfg_d_e = cfg_d; assign go_e = r_go; assign go_bf_e = r_go_bf;
        if (QX >= 7) begin : g_gok
            // Z11d: r_go -> nB[31] -3.8 ps through a 7 / 22 / 15 / 21-load buffer tree (slews 110-150 ps)
            ot_v41_kreg #(.W(1), .AR(1)) u_gn (.clk(clk), .arst_n(rst_n), .d(go), .q(go_en));
            ot_v41_kreg #(.W(1), .AR(1)) u_gw (.clk(clk), .arst_n(rst_n), .d(go), .q(go_ew));
            ot_v41_kreg #(.W(1), .AR(1)) u_gm (.clk(clk), .arst_n(rst_n), .d(go), .q(go_em));
        end else begin : g_ngok
            assign go_en = r_go; assign go_ew = r_go; assign go_em = r_go;
        end
        assign xs_v_e = r_xs_v; assign xs_p_e = r_xs_p; assign xs_b_e = r_xs_b; assign xs_sv_e = r_xs_sv;
        assign xs_q0_e = r_xs_q0; assign xs_e0_e = r_xs_e0; assign xs_q1_e = r_xs_q1; assign xs_e1_e = r_xs_e1;
        assign xs_pos_e = r_xs_pos; assign xb_pos_e = r_xb_pos; assign xb_v_e = r_xb_v; assign xb_b_e = r_xb_b;
        assign xb_sv_e = r_xb_sv; assign xb_u_e = r_xb_u; assign xb_d_e = r_xb_d;
    end else begin : g_nir
        assign cfg_v_e = cfg_v; assign cfg_a_e = cfg_a; assign cfg_d_e = cfg_d; assign go_e = go; assign go_bf_e = go_bf;
        assign go_tag_e = go_tag;
        assign go_en = go; assign go_ew = go; assign go_em = go;
        assign xs_v_e = xs_v; assign xs_p_e = xs_p; assign xs_b_e = xs_b; assign xs_sv_e = xs_sv;
        assign xs_q0_e = xs_q0; assign xs_e0_e = xs_e0; assign xs_q1_e = xs_q1; assign xs_e1_e = xs_e1;
        assign xs_pos_e = xs_pos; assign xb_pos_e = xb_pos; assign xb_v_e = xb_v; assign xb_b_e = xb_b;
        assign xb_sv_e = xb_sv; assign xb_u_e = xb_u; assign xb_d_e = xb_d;
    end

    // ---------------- clock gate: the element runs only while it has an op in flight --------------------------
    // Configuration registers stay on clk.  Everything else is clocked from `go_e` until DRAIN cycles after the
    // walkers stop (DRAIN covers the longest issue-to-partial latency: capture, block dot, chain, pair, segment
    // tree, BF16 tree), so the last partial has left and pv is low again before the clock stops.
    wire walk_busy;

    // ---------------- PQ: banked output tags, op parity, configuration shadow + replay (see the PQ header) ------
    localparam integer CW = 3 * NSEG + 1;       // configuration words per load
    localparam integer RPW = 2 * NSEG + 1;      // replayed words: segments, classes, sub-blocks / positions
    wire              pq_tp, pq_fault, pq_swap, pq_walking, pq_bank_free, pq_sh_free;
    wire [NB*TRW-1:0] pq_tree;
    wire [NB*3-1:0]   pq_pos;
    wire [NB-1:0]     pq_idle;
    wire [NB*16-1:0]  pq_row;
    wire [NB*5-1:0]   pq_idx, pq_n;
    if (PQ != 0) begin : g_pq
        reg [47:0] sh_w [0:RPW-1];
        always @(posedge clk) if (cfg_v_x && {27'd0, cfg_a_x} < RPW) sh_w[cfg_a_x] <= cfg_d_x;
        // replay: rk walks 0 .. RPW-1 after the swap; the boundary registers' timing is kept (word -> register)
        reg        rp_run;
        reg [4:0]  rk;
        reg [3:0]  rp_tail;
        reg        rp_v;
        reg [4:0]  rp_a;
        reg [47:0] rp_d;
        reg [NSEG-1:0] rp_cdec;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin rp_run <= 1'b0; rk <= 5'd0; rp_tail <= 4'd0; rp_v <= 1'b0; rp_cdec <= '0; end
            else begin
                if (pq_swap) begin rp_run <= 1'b1; rk <= 5'd0; end
                else if (rp_run) begin rk <= rk + 5'd1; if (rk == 5'(RPW - 1)) rp_run <= 1'b0; end
                rp_tail <= (rp_run && rk == 5'(RPW - 1)) ? 4'(RT) : (rp_tail != 4'd0 ? rp_tail - 4'd1 : 4'd0);
                rp_v <= rp_run;
                for (int c = 0; c < NSEG; c++) rp_cdec[c] <= rp_run && rk == 5'(NSEG + c);
            end
        end
        always @(posedge clk) begin rp_a <= rk; rp_d <= sh_w[rk]; end
        assign cfg_v = rp_v; assign cfg_a = rp_a; assign cfg_d = rp_d;
        assign qy_cdec = (QPIPE != 0) ? rp_cdec : '0;
        assign pq_walking = walk_busy | rp_run | rp_v | (rp_tail != 4'd0);
        if (QPIPE == 0 || FAST == 0 || MTP == 0) begin : g_pq_bad
            initial begin $display("ot_v41_rom_elem_qx_pq_w10: PQ requires QPIPE = FAST = MTP = 1"); $finish; end
        end
    end else begin : g_npq
        assign cfg_v = cfg_v_x; assign cfg_a = cfg_a_x; assign cfg_d = cfg_d_x; assign qy_cdec = qy_cdec_x;
        assign pq_walking = walk_busy;
    end
    ot_v41_elem_pq_tags #(.NSEG(NSEG), .NB(NB), .MTP(MTP), .PQ(PQ), .DRAIN(DRAIN)) u_pq (.clk(clk), .rst_n(rst_n),
        .cfg_v(cfg_v_x), .cfg_a(cfg_a_x), .cfg_d(cfg_d_x[25:0]), .go_e(go_e), .go_tag(go_tag_e), .walk_busy(walk_busy),
        .walking(pq_walking), .tp(pq_tp), .bank_free(pq_bank_free), .sh_free(pq_sh_free), .swap(pq_swap), .fault(pq_fault),
        .t_tree(pq_tree), .t_pos(pq_pos), .q_idle(pq_idle), .q_row(pq_row), .q_idx(pq_idx), .q_n(pq_n));
    // status outputs from registers (element boundary; Z21 post-CTS: the combinational outputs missed the output
    // budget by 23-39 ps).  The tags module judges the load bank against go_e; a go still in the boundary / input
    // registers (go_pin, go) switches the bank before the load's words arrive, so bank_free is low from the go_pin
    // cycle on (registered: from the cycle after go_pin, when the loader can first start after that go's cfg_go).
    // PQ = 0: the tags module's constants (1, 1) and walk_busy, registered alike.
    reg st_walking, st_bank_free, st_sh_free;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin st_walking <= 1'b0; st_bank_free <= 1'b1; st_sh_free <= 1'b1; end
        else begin
            st_walking <= pq_walking;
            st_bank_free <= pq_bank_free && (PQ == 0 || (!go_pin && !go));
            st_sh_free <= pq_sh_free;
        end
    assign walking = st_walking; assign bank_free = st_bank_free; assign sh_free = st_sh_free;
    reg [7:0] drain;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) drain <= 8'd0;
        else if (go_e || walk_busy) drain <= DRAIN[7:0];
        else if (drain != 8'd0) drain <= drain - 8'd1;
    wire cg_en0 = !rst_n || go || go_e || walk_busy || drain != 8'd0;
    wire cg_en;
    wire qz_en_r;                       // QZ: en_r (QTIMING_FIX) and the low QK - 1 gate extension bits
    wire qz_ext_lo;
    if (QTIMING_FIX != 0) begin : g_qt_cg
        // en_r(t) == go_e(t) || drain(t) != 0 (go_e = r_go = go delayed when FAST, else go itself)
        (* keep *) reg en_r;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) en_r <= 1'b0;
`ifdef QT_MUTANT_CG
            else en_r <= ((FAST != 0) ? go : 1'b0) || go_e || walk_busy || drain > 8'd2;   // negative control
`else
            else en_r <= ((FAST != 0) ? go : 1'b0) || go_e || walk_busy || drain > 8'd1;
`endif
        assign cg_en = !rst_n || go || en_r;
        assign qz_en_r = en_r;
`ifdef QT_CHECK
        always @(negedge clk) if (rst_n && cg_en !== cg_en0) begin
            $display("QT_CHECK FAIL: cg_en %b != original %b at %t", cg_en, cg_en0, $time); $fatal(1);
        end
`endif
    end else begin : g_qt_nocg
        assign cg_en = cg_en0;
        assign qz_en_r = 1'b0;
    end
    // QPIPE: the gate stays open QK cycles longer, for the QK added datapath stages
    wire cg_en_q;
    if (QK != 0) begin : g_qext
        reg [QK:0] ext;                 // ext[QK] is unused (keeps the shift legal at QK = 1)
        always @(posedge clk or negedge rst_n)
            if (!rst_n) ext <= '0;
            else ext <= {ext[QK-1:0], cg_en};
        assign cg_en_q = cg_en || (|ext[QK-1:0]);
        if (QK > 1) begin : g_xl
            assign qz_ext_lo = |ext[QK-2:0];
        end else begin : g_nxl
            assign qz_ext_lo = 1'b0;
        end
    end else begin : g_nqext
        assign cg_en_q = cg_en;
        assign qz_ext_lo = 1'b0;
    end
    wire cg_en_g;                       // the ICG enable
    if (QZ != 0) begin : g_qz_cg
        wire en_r_d = ((FAST != 0) ? go : 1'b0) || go_e || walk_busy || drain > 8'd1;   // g_qt_cg.en_r's next state
        // z(t+1) = cg_en_q(t+1): rst_n(t+1) = 1 and go(t+1) = go_pin(t) once rst_n_pin is high; en_r and ext load
        // only while rst_n(t) is high (both reset on rst_n)
`ifdef QZ_MUTANT_Z
        // negative control: the drain term lost, so the gate closes as soon as the walkers stop (in-flight words never
        // reach the outputs).  (Dropping go_pin alone only removes the gated edge right after a go into a closed gate,
        // whose beat capture is never used: invisible at the outputs, caught by the QP_CHECK assertion instead.)
        wire z_d = go_pin || (rst_n && (((FAST != 0) ? go : 1'b0) || go_e || walk_busy));
`else
        wire z_d = go_pin || (rst_n && (en_r_d || (QK != 0 ? (go || qz_en_r || qz_ext_lo) : 1'b0)));
`endif
        wire z_q;
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b1)) u_z (.clk(clk), .arst_n(rst_n_pin), .d(z_d), .q(z_q));
        assign cg_en_g = z_q;
`ifdef QP_CHECK
        always @(negedge clk) if (rst_n_pin && z_q !== cg_en_q) begin
            $display("QZ_CHECK FAIL: registered gate enable %b != cg_en_q %b at %t", z_q, cg_en_q, $time); $fatal(1);
        end
`endif
        if (QTIMING_FIX == 0 || QPIPE == 0 || FAST == 0 || PP == 0 || QP_CAP != 0 || BF16 != 0 || BP != 0) begin : g_qz_bad
            initial begin $display("ot_v41_rom_elem_qz_w10: QZ requires QTIMING_FIX = QPIPE = FAST = PP = 1, QP_CAP = BF16 = BP = 0"); $finish; end
        end
    end else begin : g_nqz_cg
        assign cg_en_g = cg_en_q;
    end
    if (CG != 0) begin : g_cg
        ot_hdc_cg u_cg (.clk(clk), .en(cg_en_g), .gclk(gclk));
    end else begin : g_nocg
        assign gclk = clk;
    end

    // ---------------- configuration ----------------------------------------------------------------
    reg [15:0] s_row [0:NB*NSEG-1];      // row of segment s on macro m at [m * NSEG + s]
    reg [4:0]  s_idx [0:NSEG-1];
    reg [4:0]  s_n   [0:NSEG-1];
    reg        s_fp4 [0:NSEG-1];
    reg        s_lo  [0:NSEG-1];
    reg        s_hi  [0:NSEG-1];
    reg        s_bf  [0:NSEG-1];
    reg        c_bf  [0:NSEG-1];
    reg        fam;
    reg [12:0] s_base [0:NSEG-1];
    reg        c_v   [0:NSEG-1];
    reg [7:0]  c_u0  [0:NSEG-1];
    reg [6:0]  c_nu  [0:NSEG-1];
    reg [SW-1:0] c_s0 [0:NSEG-1];
    reg [SW-1:0] c_s1 [0:NSEG-1];
    reg [2:0]  qlast;               // sub-blocks - 1
    reg [2:0]  plast;               // positions - 1 (MTP)
    reg [13:0] pbase;               // PP: the phase's first word in issue order (even); bank = index[0]
    always @(posedge clk) if (cfg_v_e) begin
        if ({27'd0, cfg_a_e} < NSEG) begin
            s_row[cfg_a_e[SW-1:0]]  <= cfg_d_e[15:0];
            s_idx[cfg_a_e[SW-1:0]]  <= cfg_d_e[20:16];
            s_n[cfg_a_e[SW-1:0]]    <= cfg_d_e[25:21];
            s_fp4[cfg_a_e[SW-1:0]]  <= cfg_d_e[26];
            s_lo[cfg_a_e[SW-1:0]]   <= cfg_d_e[27];
            s_hi[cfg_a_e[SW-1:0]]   <= cfg_d_e[28];
            s_base[cfg_a_e[SW-1:0]] <= cfg_d_e[41:29];
            s_bf[cfg_a_e[SW-1:0]]   <= cfg_d_e[42];
        end else if ({27'd0, cfg_a_e} < 2 * NSEG) begin
            c_v[cfg_a_e[SW-1:0]]  <= cfg_d_e[0];
            c_u0[cfg_a_e[SW-1:0]] <= cfg_d_e[8:1];
            c_nu[cfg_a_e[SW-1:0]] <= cfg_d_e[15:9];
            c_s0[cfg_a_e[SW-1:0]] <= cfg_d_e[16 +: SW];
            c_s1[cfg_a_e[SW-1:0]] <= cfg_d_e[19 +: SW];
            c_bf[cfg_a_e[SW-1:0]] <= cfg_d_e[22];
        end else if ({27'd0, cfg_a_e} == 2 * NSEG) begin
            qlast <= cfg_d_e[2:0];
            plast <= (MTP != 0) ? cfg_d_e[5:3] : 3'd0;
            pbase <= cfg_d_e[19:6];
        end else begin                          // 2NSEG+1+s: the row of segment s on the pair's second macro
            // 2NSEG+1+s -> NSEG+s for every s, including s = NSEG-1 (the low-bit decode wrapped it to NSEG-1; main b9e873649)
            if (NB > 1 && {27'd0, cfg_a_e} <= 3 * NSEG) s_row[{27'd0, cfg_a_e} - (NSEG + 1)] <= cfg_d_e[15:0];
        end
    end

    // QPIPE: the output stage's row / segment tables (o_row, o_seg, o_n and the idle-half test) as the configuration
    // held them QK cycles earlier: a partial leaves QK cycles later than in the qt element, so it must see the
    // configuration it would have seen then, whenever the parent rewrites it
    reg [15:0] so_row [0:NB*NSEG-1];
    reg [4:0]  so_idx [0:NSEG-1];
    reg [4:0]  so_n   [0:NSEG-1];
    if (QK != 0) begin : g_cso
        reg [QK:0]     dcv;
        reg [5*QK+4:0] dca;
        reg [48*QK+47:0] dcd;
        // no reset, like the configuration registers themselves (a write during reset still lands)
        always @(posedge clk) begin dcv <= {dcv[QK-1:0], cfg_v_e}; dca <= {dca[5*QK-1:0], cfg_a_e}; dcd <= {dcd[48*QK-1:0], cfg_d_e}; end
        wire        qv_ = dcv[QK-1];
        wire [4:0]  qa_ = dca[5*QK-1 -: 5];
        wire [47:0] qd_ = dcd[48*QK-1 -: 48];
        always @(posedge clk) if (qv_) begin
            if ({27'd0, qa_} < NSEG) begin
                so_row[qa_[SW-1:0]] <= qd_[15:0]; so_idx[qa_[SW-1:0]] <= qd_[20:16]; so_n[qa_[SW-1:0]] <= qd_[25:21];
            end else if ({27'd0, qa_} > 2 * NSEG)
                // 2NSEG+1+s -> NSEG+s for every s, including s = NSEG-1 (main b9e873649)
                if (NB > 1 && {27'd0, qa_} <= 3 * NSEG) so_row[{27'd0, qa_} - (NSEG + 1)] <= qd_[15:0];
        end
    end
    // per class: unit count and whether it belongs to the running family, packed for the walkers
    reg [7*NSEG-1:0] nu_p;
    reg [NSEG-1:0] base_live, base_go;
    integer ci;
    always @* begin
        for (ci = 0; ci < NSEG; ci = ci + 1) begin
            nu_p[7*ci +: 7] = c_nu[ci];
            base_live[ci] = c_v[ci] && c_bf[ci] == fam;
            base_go[ci] = c_v[ci] && c_bf[ci] == go_bf_e;
        end
    end
    localparam integer UW = 1 + 3 + 3 + SW + 3;     // {run, q, b, c, j}
    wire [SW-1:0] c_first;
    wire          c_first_ok;
    ot_v41_first_w10 #(.N(NSEG)) u_first (.live(base_go), .c(c_first), .ok(c_first_ok));
    wire [SW-1:0] c_live;             // first class of the running family (a new MTP position restarts here)
    wire          c_live_ok;
    ot_v41_first_w10 #(.N(NSEG)) u_flive (.live(base_live), .c(c_live), .ok(c_live_ok));

    // units per sub-block: 8 (shift 3); BF16_PAIR BF16 family 2 (shift 1)
    wire [1:0] sbs = (BP != 0 && fam) ? (BP == 2 ? 2'd0 : 2'd1) : 2'd3;
    wire [1:0] sbs_go = (BP != 0 && go_bf_e) ? (BP == 2 ? 2'd0 : 2'd1) : 2'd3;
    wire [8:0] sbn = 9'd1 << sbs;
    wire [8:0] sbn_go = 9'd1 << sbs_go;
    // FAST walkers: the per-class sub-block facts (class live in sub-block q, its units there) depend only on q and
    // the op, so they are held in registers for q and q + 1 (A, B) instead of being recomputed inside the walk
    // loop; A <= B and B <= f(q + 2) when q advances, both <= f(0), f(1) at go_e and at an MTP restart.
    function automatic [6*NSEG-1:0] sbf(input [3:0] q, input [1:0] sh, input [7*NSEG-1:0] nu, input [NSEG-1:0] base);
        integer k;
        reg [6:0] q8, rem;
        begin
            q8 = {3'd0, q} << sh;
            for (k = 0; k < NSEG; k = k + 1) begin
                rem = (nu[7*k +: 7] > q8) ? nu[7*k +: 7] - q8 : 7'd0;
                sbf[k] = base[k] && rem != 7'd0;                                  // live
                sbf[NSEG + 4*k +: 4] = (rem > (7'd1 << sh)) ? (4'd1 << sh) : rem[3:0];   // units in sub-block
                sbf[5*NSEG + k] = rem != 7'd0 && rem <= (7'd1 << sh);              // the class ends here
            end
        end
    endfunction
    wire [6*NSEG-1:0] f0_go = sbf(4'd0, sbs_go, nu_p, base_go);
    wire [6*NSEG-1:0] f1_go = sbf(4'd1, sbs_go, nu_p, base_go);
    // QX helpers (one-hot class selects)
    function automatic [NSEG-1:0] qx_low(input [NSEG-1:0] v);     // lowest set bit, one-hot; bit 0 if v == 0
        reg seen;
        qx_low = '0; seen = 1'b0;
        for (int k = 0; k < NSEG; k++) begin qx_low[k] = v[k] && !seen; seen = seen || v[k]; end
        if (!seen) qx_low[0] = 1'b1;
    endfunction
    function automatic [NSEG-1:0] qx_gt(input [NSEG-1:0] oh);     // mask k > c for one-hot c
        reg seen;
        qx_gt = '0; seen = 1'b0;
        for (int k = 0; k < NSEG; k++) begin qx_gt[k] = seen; seen = seen || oh[k]; end
    endfunction
    function automatic ca_f(input [6*NSEG-1:0] fa, input [SW-1:0] fc, input [2:0] fj);   // j + 1 < cur[c]
        ca_f = {1'b0, fj} + 4'd1 < fa[NSEG + 4*fc +: 4];
    endfunction
    // ---------------- x-need walker: one (pair, b) per class unit per round ------------------------------
    reg        n_run;
    reg [2:0]  n_q, n_pos, bn_pos, w_pos;
    reg [2:0]  n_b, n_j;
    reg [SW-1:0] n_c;
    wire [7:0] n_pair = c_u0[n_c] + {2'd0, n_q, n_j};
    wire [UW-1:0] n_nx, n_nx0;          // n_nx0: the encoded walk2 step; n_nx = n_nx0, or the one-hot step (QX = 3)
    reg [6*NSEG-1:0] nA, nB, wA, wB, fF0, fF1, nQ2, wQ2;     // xQ2: f(q + 2), registered every cycle
    if (FAST != 0) begin : g_nw2
        ot_v41_walk2_w10 #(.N(NSEG)) u_nw (.q(n_q), .b(n_b), .c(n_c), .j(n_j), .live(nA[NSEG-1:0]),
            .livq1(nB[NSEG-1:0]), .cur(nA[5*NSEG-1:NSEG]), .qlast(qlast), .nx(n_nx0));
    end else begin : g_nw1
        ot_v41_walk_w10 #(.N(NSEG)) u_nw (.q(n_q), .b(n_b), .c(n_c), .j(n_j), .nu(nu_p), .base(base_live),
                                       .qlast(qlast), .sbs(2'd3), .nx(n_nx0));
    end
    // QX = 2: the x-need walker's round end (no next unit: MTP restart / stop) and sub-block advance from a decoded
    // n_c and per-class vectors of nA (= !n_nx[UW-1] and n_nx[UW-1] && n_nx q != n_q of walk2)
    wire [NSEG-1:0] qx_ndec = NSEG'(1) << n_c;
    reg  [NSEG-1:0] qx_ncmp, qx_ngt;
    always @* begin
        for (int k = 0; k < NSEG; k++) qx_ncmp[k] = {1'b0, n_j} + 4'd1 < nA[NSEG + 4*k +: 4];
        for (int k = 0; k < NSEG; k++) qx_ngt[k] = k > n_c;
    end
    wire qx_n_same = |(qx_ndec & qx_ncmp) || |(nA[NSEG-1:0] & qx_ngt);
    wire qx_n_endq = n_b == 3'd7 && n_q == qlast;
    // QX = 3: the x-need walker's step in one-hot form, as the word walker's (QX = 1, 2): n_coh / n_cgt mirror n_c,
    // n_ca_r holds its "next unit of the same class" decision, the next class stays one-hot
    reg  [NSEG-1:0] n_coh, n_cgt;
    reg  n_ca_r;
    reg  [NSEG-1:0] qn_cmpA, qn_cmpA1, qn_c0A, qn_c0B;
    wire [2:0] qn_j1 = n_j + 3'd1;
    always @* for (int k = 0; k < NSEG; k++) begin
        qn_cmpA[k]  = {1'b0, n_j} + 4'd1 < nA[NSEG + 4*k +: 4];
        qn_cmpA1[k] = {1'b0, qn_j1} + 4'd1 < nA[NSEG + 4*k +: 4];
        qn_c0A[k]   = 4'd1 < nA[NSEG + 4*k +: 4];
        qn_c0B[k]   = 4'd1 < nB[NSEG + 4*k +: 4];
    end
    wire qn_b7 = n_b == 3'd7;
    wire qn_case_a = n_ca_r;
    wire [NSEG-1:0] qn_above = nA[NSEG-1:0] & n_cgt;
    wire qn_nf = |qn_above;
    wire [NSEG-1:0] qn_onc = qx_low(qn_above);
    wire [NSEG-1:0] qn_ofc = qx_low(qn_b7 ? nB[NSEG-1:0] : nA[NSEG-1:0]);
    wire qn_endq = qn_b7 && n_q == qlast;
    wire qn_same = qn_case_a || qn_nf;
    wire [NSEG-1:0] qn_nxoh = qn_case_a ? n_coh : qn_nf ? qn_onc : qn_endq ? NSEG'(1) : qn_ofc;
    reg  [SW-1:0] qn_c_nx;
    always @* begin
        qn_c_nx = '0;
        for (int k = 0; k < NSEG; k++) qn_c_nx = qn_c_nx | ({SW{qn_nxoh[k]}} & SW'(k));
    end
    wire [UW-1:0] qn_nx = {qn_same || !qn_endq, qn_same ? n_q : qn_endq ? 3'd0 : qn_b7 ? n_q + 3'd1 : n_q,
                           qn_same ? n_b : qn_endq ? 3'd0 : n_b + 3'd1, qn_c_nx, qn_case_a ? qn_j1 : 3'd0};
    wire qn_ca_nx = qn_case_a ? |(n_coh & qn_cmpA1) : qn_nf ? |(qn_onc & qn_c0A) : qn_endq ? qn_c0A[0] :
`ifdef QX_MUTANT_NCA
                    |(qn_ofc & qn_c0A);                           // negative control: sub-block advance ignored
`else
                    qn_b7 ? |(qn_ofc & qn_c0B) : |(qn_ofc & qn_c0A);
`endif
    assign n_nx = (QX >= 3) ? qn_nx : n_nx0;
    wire qx_n_end = (QX >= 3) ? !qn_same && qn_endq : (QX >= 2) ? !qx_n_same && qx_n_endq : !n_nx0[UW-1];
    wire qx_n_adv = (QX >= 3) ? !qn_same && !qn_endq && qn_b7 :
                    (QX >= 2) ? !qx_n_same && !qx_n_endq && n_b == 3'd7 : n_nx0[UW-1] && n_nx0[UW-2 -: 3] != n_q;
`ifdef QP_CHECK
    always @(negedge clk) if (QX >= 2 && rst_n && n_run && (qx_n_end !== !n_nx0[UW-1]
            || qx_n_adv !== (n_nx0[UW-1] && n_nx0[UW-2 -: 3] != n_q) || (QX >= 3 && qn_nx !== n_nx0))) begin
        $display("QX_CHECK FAIL: x-need walker end/advance %b%b at %t", qx_n_end, qx_n_adv, $time); $fatal(1);
    end
`endif
    wire pair_match;
    if (FRONT_PAR != 0) begin : g_front_par
        wire [NSEG-1:0] class_match;
        for (genvar fc = 0; fc < NSEG; fc = fc + 1) begin : g_class
            // The assignment truncates BEFORE equality, just like n_pair.
            // Keep the independent cones so mapping cannot pull a base mux
            // back ahead of the adder on the n_c -> hit -> nB enable path.
            (* keep *) wire [7:0] expected_pair;
`ifdef W10_MUTANT_FRONT_PAIR
            assign expected_pair = c_u0[fc] + {2'd0, n_q, n_j} + 8'd1;
`else
            assign expected_pair = c_u0[fc] + {2'd0, n_q, n_j};
`endif
            assign class_match[fc] = (n_c == SW'(fc)) && (xs_p_e == expected_pair);
        end
        assign pair_match = |class_match;
    end else begin : g_front_serial
        assign pair_match = xs_p_e == n_pair;
    end
    wire hit_q0 = n_run && !fam && xs_v_e && pair_match && xs_b_e == n_b && xs_pos_e == n_pos;
    // QTIMING_FIX: HC duplicated copies of the need-walker state, each updated exactly as the original (on its own
    // match, which equals the original match by induction), each with a per-class parallel pair compare
    wire [HC-1:0] hit_k;
    wire          hit_q;
    if (QTIMING_FIX != 0) begin : g_qt_hit
        // QPIPE (with the x boundary register and FAST): the pair offset xs_p - c_u0[c] (mod 256) of every class is
        // formed from the boundary register and registered with the beat, against the class base the configuration
        // holds in the match cycle; c_u0 + {q, j} == xs_p  <=>  xs_p - c_u0 == {q, j} (mod 256)
        localparam integer QPD = (QPIPE != 0 && QP_XS != 0 && FAST != 0) ? 1 : 0;
        reg [7:0] r_dp [0:NSEG-1];
        if (QPD != 0) begin : g_dp
            integer dc;
            always @(posedge gclk)
                for (dc = 0; dc < NSEG; dc = dc + 1)
`ifdef QP_MUTANT_DP
                    if (QX < 10) r_dp[dc] <= xs_p - ((cfg_v_e && cfg_a_e == 5'(NSEG + dc)) ? cfg_d_e[8:1] : c_u0[dc]) + ((dc == 5) ? 8'd1 : 8'd0);
`else
                    if (QX < 10) r_dp[dc] <= xs_p - (((QY != 0) ? qy_cdec[dc] : (cfg_v_e && cfg_a_e == 5'(NSEG + dc))) ? cfg_d_e[8:1] : c_u0[dc]);
`endif
            // QX = 10: both differences by prefix adders in parallel, then the select (route Z15b: b_cfg_d -> select ->
            // rippled 8-bit subtract -> r_dp -56.8 ps)
            if (QX >= 10) begin : g_dpk
                wire [7:0] dpc;
                ot_v41_ksadd #(.W(8)) u_dpc (.a(xs_p), .b(~cfg_d_e[8:1]), .cin(1'b1), .s(dpc), .cout());
                for (genvar dk = 0; dk < NSEG; dk = dk + 1) begin : g_k
                    wire [7:0] dpu;
                    ot_v41_ksadd #(.W(8)) u_dpu (.a(xs_p), .b(~c_u0[dk]), .cin(1'b1), .s(dpu), .cout());
                    always @(posedge gclk)
`ifdef QP_MUTANT_DP
                        r_dp[dk] <= (((QY != 0) ? qy_cdec[dk] : (cfg_v_e && cfg_a_e == 5'(NSEG + dk))) ? dpc : dpu) + ((dk == 5) ? 8'd1 : 8'd0);
`else
                        r_dp[dk] <= ((QY != 0) ? qy_cdec[dk] : (cfg_v_e && cfg_a_e == 5'(NSEG + dk))) ? dpc : dpu;
`endif
                end
            end
        end
        for (genvar hc = 0; hc < HC; hc = hc + 1) begin : g_hc
            (* keep, dont_touch = "true" *) reg d_run;
            (* keep, dont_touch = "true" *) reg d_fam;
            (* keep, dont_touch = "true" *) reg [SW-1:0] d_c;
            (* keep, dont_touch = "true" *) reg [2:0] d_q, d_j, d_b, d_pos;
            wire [NSEG-1:0] cm;
            for (genvar fc = 0; fc < NSEG; fc = fc + 1) begin : g_cls
                (* keep *) wire [7:0] ep;
`ifdef QT_MUTANT_HIT
                assign ep = c_u0[fc] + {2'd0, d_q, d_j} + ((hc == 2 && fc == 3) ? 8'd1 : 8'd0);   // negative control
`else
                assign ep = c_u0[fc] + {2'd0, d_q, d_j};
`endif
                if (QPD != 0) begin : g_pd
                    assign cm[fc] = (d_c == SW'(fc)) && (r_dp[fc] == {2'd0, d_q, d_j});
                end else begin : g_pe
                    assign cm[fc] = (d_c == SW'(fc)) && (xs_p_e == ep);
                end
            end
            assign hit_k[hc] = d_run && !d_fam && xs_v_e && (|cm) && xs_b_e == d_b && xs_pos_e == d_pos;
            always @(posedge gclk or negedge rst_n)
                if (!rst_n) begin d_run <= 1'b0; d_fam <= 1'b0; end
                else if (go_e) begin
`ifdef W10_MUTANT_EMPTY_GO
                    d_run <= !go_bf_e;
`else
                    d_run <= !go_bf_e && c_first_ok;
`endif
                    d_fam <= go_bf_e;
                end else if (hit_k[hc] && !(!n_nx[UW-1] && n_more)) d_run <= n_nx[UW-1];
            always @(posedge gclk)
                if (go_e) begin d_q <= 3'd0; d_b <= 3'd0; d_c <= c_first; d_j <= 3'd0; d_pos <= 3'd0; end
                else if (hit_k[hc]) begin
                    if (!n_nx[UW-1] && n_more) begin
                        d_q <= 3'd0; d_b <= 3'd0; d_c <= c_live; d_j <= 3'd0; d_pos <= d_pos + 3'd1;
                    end else {d_q, d_b, d_c, d_j} <= n_nx[UW-2:0];
                end
        end
        assign hit_q = hit_k[0];
`ifdef QT_CHECK
        always @(negedge gclk) if (rst_n) for (int hc = 0; hc < HC; hc++) if (hit_k[hc] !== hit_q0) begin
            $display("QT_CHECK FAIL: hit copy %0d %b != original %b at %t", hc, hit_k[hc], hit_q0, $time); $fatal(1);
        end
`endif
    end else begin : g_qt_nohit
        assign hit_k = {HC{hit_q0}};
        assign hit_q = hit_q0;
    end
    // BF16: capture, in slot order, every slice of this round (b) whose unit lies in a live class's sub-block
    reg        bn_run;
    reg [2:0]  bn_q;
    reg [2:0]  bn_b;
    reg [6:0]  bn_cnt, bn_tot;
    reg [3:0]  bm;
    // per-class unit bounds [b_lo, b_hi) of the current sub-block, held in registers so the capture match is a
    // compare only; they (and the round's slice total bn_tot) advance with the sub-block
    reg [8:0]  b_lo [0:NSEG-1];
    reg [8:0]  b_hi [0:NSEG-1];
    reg [8:0]  nlo [0:NSEG-1];
    reg [8:0]  nhi [0:NSEG-1];
    reg [6:0]  ntot, gtot, ltot;
    reg [8:0]  lo0 [0:NSEG-1];
    reg [8:0]  hi0 [0:NSEG-1];
    reg [8:0]  cend, glo, ghi;
    integer bk, bc;
    always @* begin
        ntot = 7'd0; gtot = 7'd0; ltot = 7'd0;
        for (bc = 0; bc < NSEG; bc = bc + 1) begin
            cend = (FAST != 0) ? cend_r[bc] : {1'b0, c_u0[bc]} + {2'd0, c_nu[bc]};
            // next sub-block
            nlo[bc] = b_lo[bc] + sbn;
            nhi[bc] = (cend < nlo[bc] + sbn) ? cend : nlo[bc] + sbn;
            if (base_live[bc] && nhi[bc] > nlo[bc]) ntot = ntot + (nhi[bc] - nlo[bc]);
            // sub-block 0 at go_e
            glo = {1'b0, c_u0[bc]};
            ghi = (cend < glo + sbn_go) ? cend : glo + sbn_go;
            lo0[bc] = glo; hi0[bc] = ghi;
            if (base_go[bc]) gtot = gtot + (ghi - glo);
            if (base_live[bc]) ltot = ltot + (ghi - glo);
        end
        for (bk = 0; bk < 4; bk = bk + 1) begin
            bm[bk] = 1'b0;
            for (bc = 0; bc < NSEG; bc = bc + 1)
                if (base_live[bc] && {1'b0, xb_u_e[8*bk +: 8]} >= b_lo[bc] && {1'b0, xb_u_e[8*bk +: 8]} < b_hi[bc])
                    bm[bk] = 1'b1;
            bm[bk] = bm[bk] && (BF16 != 0 || BP != 0) && bn_run && fam && xb_v_e && xb_sv_e[bk] && xb_b_e == bn_b && xb_pos_e == bn_pos;
        end
    end
    // FAST: the sub-block bounds and slice totals come from registers (the sums over classes are off the go and
    // advance paths): per class the first-sub-block end for each family (from the class registers, on clk), the
    // live family's first-sub-block total, and the next sub-block's bounds and total (from b_lo, on gclk)
    reg [8:0] hi0q_r [0:NSEG-1];
    reg [8:0] hi0b_r [0:NSEG-1];
    reg [3:0] glq_r [0:NSEG-1];
    reg [3:0] glb_r [0:NSEG-1];
    reg [8:0] nlo_r [0:NSEG-1];
    reg [8:0] nhi_r [0:NSEG-1];
    reg [6:0] ntot_r, ltot_r;
    reg [6:0] gtot_f;
    reg [8:0] ce_, hq_, hb_;
    integer bf;
    reg [8:0] cend_r [0:NSEG-1];
    always @(posedge clk) for (bf = 0; bf < NSEG; bf = bf + 1) cend_r[bf] <= {1'b0, c_u0[bf]} + {2'd0, c_nu[bf]};
    always @(posedge clk) begin
        for (bf = 0; bf < NSEG; bf = bf + 1) begin
            ce_ = cend_r[bf];
            hq_ = (ce_ < {1'b0, c_u0[bf]} + 9'd8) ? ce_ : {1'b0, c_u0[bf]} + 9'd8;
            hb_ = (ce_ < {1'b0, c_u0[bf]} + ((BP == 2) ? 9'd1 : (BP != 0) ? 9'd2 : 9'd8)) ? ce_
                : {1'b0, c_u0[bf]} + ((BP == 2) ? 9'd1 : (BP != 0) ? 9'd2 : 9'd8);
            hi0q_r[bf] <= hq_; hi0b_r[bf] <= hb_;
            glq_r[bf] <= hq_[3:0] - c_u0[bf][3:0]; glb_r[bf] <= hb_[3:0] - c_u0[bf][3:0];
        end
    end
    // sub-block-0 slice totals of each family (configuration only; the configuration ends >= 2 cycles before go)
    reg [6:0] tot0_r, tot1_r;
    reg [4:0] tq_r [0:3];
    reg [4:0] tb_r [0:3];
    always @(posedge clk) begin
        for (bf = 0; bf < 4; bf = bf + 1) begin
            tq_r[bf] <= ((c_v[2*bf] && !c_bf[2*bf]) ? {1'b0, glq_r[2*bf]} : 5'd0)
                      + ((c_v[2*bf+1] && !c_bf[2*bf+1]) ? {1'b0, glq_r[2*bf+1]} : 5'd0);
            tb_r[bf] <= ((c_v[2*bf] && c_bf[2*bf]) ? {1'b0, glb_r[2*bf]} : 5'd0)
                      + ((c_v[2*bf+1] && c_bf[2*bf+1]) ? {1'b0, glb_r[2*bf+1]} : 5'd0);
        end
        tot0_r <= {2'd0, tq_r[0]} + {2'd0, tq_r[1]} + {2'd0, tq_r[2]} + {2'd0, tq_r[3]};
        tot1_r <= {2'd0, tb_r[0]} + {2'd0, tb_r[1]} + {2'd0, tb_r[2]} + {2'd0, tb_r[3]};
    end
    always @* gtot_f = go_bf_e ? tot1_r : tot0_r;
    // next-sub-block total: 3 registered stages from b_lo (a sub-block lasts >= 8 rounds)
    reg [3:0] dk_r [0:NSEG-1];
    reg [5:0] ps_r [0:3];
    always @(posedge gclk) begin
        for (bf = 0; bf < NSEG; bf = bf + 1) begin
            nlo_r[bf] <= nlo[bf]; nhi_r[bf] <= nhi[bf];
            dk_r[bf] <= (base_live[bf] && nhi_r[bf] > nlo_r[bf]) ? nhi_r[bf][3:0] - nlo_r[bf][3:0] : 4'd0;
        end
        for (bf = 0; bf < 4; bf = bf + 1) ps_r[bf] <= {2'd0, dk_r[2*bf]} + {2'd0, dk_r[2*bf+1]};
        ntot_r <= {1'b0, ps_r[0]} + {1'b0, ps_r[1]} + {1'b0, ps_r[2]} + {1'b0, ps_r[3]};
        ltot_r <= fam ? tot1_r : tot0_r;
    end
    // bound registers: sub-block 0 at go_e and at each new position, the next sub-block at a sub-block end
    wire bn_adv = bnum != 0 && bn_cnt + {4'd0, bnum} == bn_tot && bn_b == 3'd7;
    wire bn_newpos = bn_adv && bn_q == qlast;
    always @(posedge gclk) begin
        for (bc = 0; bc < NSEG; bc = bc + 1)
            if (FAST != 0) begin
                if (go_e || bn_newpos) begin
                    b_lo[bc] <= {1'b0, c_u0[bc]};
                    b_hi[bc] <= (go_e ? go_bf_e : fam) ? hi0b_r[bc] : hi0q_r[bc];
                end else if (bn_adv) begin b_lo[bc] <= nlo_r[bc]; b_hi[bc] <= nhi_r[bc]; end
            end else begin
                if (go_e || bn_newpos) begin b_lo[bc] <= lo0[bc]; b_hi[bc] <= hi0[bc]; end
                else if (bn_adv) begin b_lo[bc] <= nlo[bc]; b_hi[bc] <= nhi[bc]; end
            end
    end
    // FAST: the slice match is registered (stage A) and counted / pushed a cycle later (stage B).  The spine keeps
    // one idle cycle between the last beat of a round and the first beat of the next, so stage A never matches
    // against a round state that stage B is about to advance.
    reg [3:0]    bm_r;
    reg [1023:0] xbd_r;
    always @(posedge gclk or negedge rst_n) if (!rst_n) bm_r <= 4'd0; else bm_r <= (go_e || FAST == 0) ? 4'd0 : bm;
    always @(posedge gclk) xbd_r <= xb_d_e;
    wire [3:0]    bmu = (FAST != 0) ? bm_r : bm;
    wire [1023:0] xbd = (FAST != 0) ? xbd_r : xb_d_e;
    wire [2:0] bnum = {2'd0, bmu[0]} + {2'd0, bmu[1]} + {2'd0, bmu[2]} + {2'd0, bmu[3]};
    wire hit = hit_q;

    // ---------------- x FIFO (pair slices) ------------------------------------------------------------------
    localparam integer XW = $clog2(XF);
    reg [255:0] f_q0 [0:XF-1];
    reg [9:0]   f_e0 [0:XF-1];
    reg [255:0] f_q1 [0:XF-1];
    reg [9:0]   f_e1 [0:XF-1];
    reg [XW-1:0] f_wr, f_rd;
    reg [XW:0]  f_cnt;
    // FAST: a captured FP8/FP4 beat is written into the FIFO one cycle after the match (the walker loop and the
    // 532-bit FIFO write enables are not in one cycle)
    reg          fw_v;
    reg [255:0]  fw_q0, fw_q1;
    reg [9:0]    fw_e0, fw_e1;
    always @(posedge gclk or negedge rst_n) if (!rst_n) fw_v <= 1'b0; else fw_v <= (FAST != 0) && hit_q && !go_e;
    always @(posedge gclk) if (QTIMING_FIX != 0 || hit_q) begin fw_q0 <= xs_q0_e; fw_q1 <= xs_q1_e; fw_e0 <= xs_e0_e; fw_e1 <= xs_e1_e; end
    wire         qpush = (FAST != 0) ? fw_v : hit_q;
    wire [2:0] npush = qpush ? 3'd1 : bnum;
    reg [XW-1:0] bpre [0:3];
    always @* begin
        bpre[0] = '0;
        bpre[1] = {{(XW-1){1'b0}}, bmu[0]};
        bpre[2] = bpre[1] + {{(XW-1){1'b0}}, bmu[1]};
        bpre[3] = bpre[2] + {{(XW-1){1'b0}}, bmu[2]};
    end

    // ---------------- word walker -------------------------------------------------------------------------------
    reg        w_run, w_h;
    reg [2:0]  w_q;
    reg [2:0]  w_b, w_j;
    reg [SW-1:0] w_c, w_s;
    reg [HW-1:0] w_cnt;
    reg [12:0] w_ptr [0:NSEG-1];
    wire [6:0] w_uabs = ({4'd0, w_q} << sbs) + {4'd0, w_j};
    wire [3:0] w_curc = wA[NSEG + 4*w_c +: 4];
    wire w_firstu = (FAST != 0) ? (w_q == 3'd0 && w_j == 3'd0) : w_uabs == 7'd0;
    wire w_lastu0 = (FAST != 0) ? (wA[5*NSEG + w_c] && {1'b0, w_j} + 4'd1 == w_curc) : w_uabs + 7'd1 == c_nu[w_c];
    // QPIPE: w_lastu is a function of walker state only (w_c, w_j, wA), so it is held in a register loaded with its
    // value for the walker's next state, case by case exactly as the walker loads that state (below)
    reg  w_lu_r;
    wire w_lastu  = (QPIPE != 0 && FAST != 0) ? w_lu_r : w_lastu0;
    // QX = 6: w_s's segment flags {fp4, bf, hi, lo} held in w_sf_r, loaded wherever w_s is (below)
    reg  [3:0] w_sf_r;
    wire [3:0] w_sf = (QX >= 6) ? w_sf_r : {s_fp4[w_s], s_bf[w_s], s_hi[w_s], s_lo[w_s]};
    wire [1:0] hv = {!(w_lastu && !w_sf[1]), !(w_firstu && !w_sf[0])};
    wire w_fp4 = w_sf[3];
    wire w_bf = w_sf[2];
    wire w_seg_last = w_fp4 || w_bf || w_h || !hv[1];          // the segment's last word for this unit
    wire w_cl0 = w_s == c_s1[w_c];
    reg  w_cl_r;                        // QY: w_cl0 held in a register (see the header)
    wire w_cl = (QY != 0) ? w_cl_r : w_cl0;
    wire w_cls_last = w_seg_last && w_cl;
    wire [UW-1:0] w_nx0;                // the walker's next {run, q, b, c, j} (encoded)
    if (FAST != 0) begin : g_ww2
        ot_v41_walk2_w10 #(.N(NSEG)) u_ww (.q(w_q), .b(w_b), .c(w_c), .j(w_j), .live(wA[NSEG-1:0]),
            .livq1(wB[NSEG-1:0]), .cur(wA[5*NSEG-1:NSEG]), .qlast(qlast), .nx(w_nx0));
    end else begin : g_ww1
        ot_v41_walk_w10 #(.N(NSEG)) u_ww (.q(w_q), .b(w_b), .c(w_c), .j(w_j), .nu(nu_p), .base(base_live),
                                       .qlast(qlast), .sbs(sbs), .nx(w_nx0));
    end
    // QX: the walker's step decided in one-hot form (see the header).  w_coh / w_cgt mirror w_c (one-hot, k > w_c),
    // every per-class quantity the step needs is formed for all classes in parallel from registers, and the next
    // class stays one-hot (qx_nxoh) so each consequence is an AND-OR select instead of an encode then a decode.
    reg  [NSEG-1:0] w_coh, w_cgt;
    reg  [NSEG-1:0] qx_cmpA, qx_luA1, qx_l0A, qx_l0B, qx_h0, qx_s1n;
    reg  [SW-1:0]   qx_s0_nx, qx_c_nx;
    wire [2:0]      qx_j1 = w_j + 3'd1;
    wire [SW-1:0]   qx_snx = w_s + 1'b1;
    always @* for (int k = 0; k < NSEG; k++) begin
        qx_cmpA[k] = {1'b0, w_j} + 4'd1 < wA[NSEG + 4*k +: 4];                         // j + 1 < cur[k]
        qx_luA1[k] = wA[5*NSEG + k] && ({1'b0, qx_j1} + 4'd1 == wA[NSEG + 4*k +: 4]);  // lu_f(wA, k, j + 1)
        qx_l0A[k]  = wA[5*NSEG + k] && (4'd1 == wA[NSEG + 4*k +: 4]);                   // lu_f(wA, k, 0)
        qx_l0B[k]  = wB[5*NSEG + k] && (4'd1 == wB[NSEG + 4*k +: 4]);                   // lu_f(wB, k, 0)
        qx_h0[k]   = !s_fp4[c_s0[k]] && !s_bf[c_s0[k]] && !s_lo[c_s0[k]];
        qx_s1n[k]  = qx_snx == c_s1[k];
    end
    wire qx_b7   = w_b == 3'd7;
    reg  w_ca_r;                                                  // QX = 2: qx_case_a held in a register
    wire qx_case_a = (QX >= 2) ? w_ca_r : |(w_coh & qx_cmpA);     // next unit of the same class
    wire [NSEG-1:0] qx_above = wA[NSEG-1:0] & w_cgt;
    wire qx_nf   = |qx_above;                                     // a later live class in this round
    wire [NSEG-1:0] qx_onc = qx_low(qx_above);
    wire [NSEG-1:0] qx_ofc = qx_low(qx_b7 ? wB[NSEG-1:0] : wA[NSEG-1:0]);   // first class of the next round
    wire qx_endq = qx_b7 && w_q == qlast;                         // last round of the last sub-block
    wire qx_same = qx_case_a || qx_nf;                            // round (q, b) unchanged
    wire [NSEG-1:0] qx_nxoh = qx_case_a ? w_coh : qx_nf ? qx_onc : qx_endq ? NSEG'(1) : qx_ofc;
    wire [NSEG-1:0] qx_nxgt = qx_gt(qx_nxoh);
    always @* begin
        qx_s0_nx = '0; qx_c_nx = '0;
        for (int k = 0; k < NSEG; k++) begin
            qx_s0_nx = qx_s0_nx | ({SW{qx_nxoh[k]}} & c_s0[k]);
            qx_c_nx  = qx_c_nx  | ({SW{qx_nxoh[k]}} & SW'(k));
        end
    end
    wire [2:0] qx_q_nx = qx_same ? w_q : qx_endq ? 3'd0 : qx_b7 ? w_q + 3'd1 : w_q;
    wire [UW-1:0] qx_nx = {qx_same || !qx_endq, qx_q_nx, qx_same ? w_b : qx_endq ? 3'd0 : w_b + 3'd1, qx_c_nx,
                           qx_case_a ? qx_j1 : 3'd0};
    wire qx_lu_nx = qx_case_a ? |(w_coh & qx_luA1) : qx_nf ? |(qx_onc & qx_l0A) : qx_endq ? qx_l0A[0] :
`ifdef QX_MUTANT_LU
                    |(qx_ofc & qx_l0A);                           // negative control: sub-block advance ignored
`else
                    qx_b7 ? |(qx_ofc & qx_l0B) : |(qx_ofc & qx_l0A);
`endif
    wire qx_first = qx_case_a ? (w_q == 3'd0 && qx_j1 == 3'd0) : qx_nf ? w_q == 3'd0 : qx_endq ? 1'b1 :
                    qx_b7 ? w_q == 3'd7 : w_q == 3'd0;
    wire qx_h_nx = qx_first && |(qx_nxoh & qx_h0);
    wire qx_adv  = !qx_same && !qx_endq && qx_b7;                 // the step advances the sub-block (wA <= wB)
    // QX = 2: w_ca_r's value for the walker's next state, case by case as w_lu_r (lu_f with < in place of ==)
    reg  [NSEG-1:0] qx_cmpA1, qx_c0A, qx_c0B;
    always @* for (int k = 0; k < NSEG; k++) begin
        qx_cmpA1[k] = {1'b0, qx_j1} + 4'd1 < wA[NSEG + 4*k +: 4];  // ca_f(wA, k, j + 1)
        qx_c0A[k]   = 4'd1 < wA[NSEG + 4*k +: 4];                    // ca_f(wA, k, 0)
        qx_c0B[k]   = 4'd1 < wB[NSEG + 4*k +: 4];                    // ca_f(wB, k, 0)
    end
    wire qx_ca_nx = qx_case_a ? |(w_coh & qx_cmpA1) : qx_nf ? |(qx_onc & qx_c0A) : qx_endq ? qx_c0A[0] :
`ifdef QX_MUTANT_CA
                    |(qx_ofc & qx_c0A);                           // negative control: sub-block advance ignored
`else
                    qx_b7 ? |(qx_ofc & qx_c0B) : |(qx_ofc & qx_c0A);
`endif
    wire [UW-1:0] w_nx = (QX != 0) ? qx_nx : w_nx0;
    wire w_round_end = (QX != 0) ? !qx_same : !w_nx[UW-1] || w_nx[UW-5 -: 3] != w_b;
    wire [SW-1:0] w_nx_c = w_nx[3 +: SW];
    wire [SW-1:0] s_next = w_s + 1'b1;
    wire [6:0] nx_uabs = ({4'd0, w_nx[UW-2 -: 3]} << sbs) + {4'd0, w_nx[2:0]};

    reg [LAT-1:0] hz_v;
    reg [HW-1:0] hz_s [0:LAT-1];
    reg hazard;
    integer k;
    always @* begin
        hazard = 1'b0;
        for (k = 0; k < LAT - 1; k = k + 1) if (hz_v[k] && hz_s[k] == w_cnt) hazard = 1'b1;   // LAT-cycle recurrence
    end
    // QX = 5: the hazard held in a register loaded with its next-cycle value.  hz_s[0] takes w_cnt and hz_v[0] takes
    // issue every cycle, so next cycle's hazard is H(c') || (issue && w_cnt == c') with H(c) the match of c against
    // entries 0 .. LAT-3 now and c' the next w_cnt (0 at go, w_cnt + 1 or 0 on an issue, else w_cnt): three
    // register-only candidates, with issue only the final select.
    function automatic qx_hz(input [HW-1:0] c);
        qx_hz = 1'b0;
        for (int j = 0; j < LAT - 2; j++) if (hz_v[j] && hz_s[j] == c) qx_hz = 1'b1;
    endfunction
    reg  hazard_r;
    // PP: word i is in bank i[0]; a bank is read at most every other cycle (only an MTP restart to an even base
    // right after an even word can collide: one stall)
    reg [13:0] a_ctr;
    reg        pp_last_v, pp_last_b;
    wire       pp_block = (PP != 0) && pp_last_v && pp_last_b == a_ctr[0];
    reg [2:0] bp_hold;                      // BF16_PAIR: cycles left of the word being multiplied
    wire issue = w_run && f_cnt != 0 && !((QX >= 5) ? hazard_r : hazard) && !pp_block && !(BP != 0 && bp_hold != 3'd0);
    wire pop = issue && w_cls_last;
    reg ffault;
    wire [NB-1:0] bk_fault;
    wire [NB-1:0] qy_bkf;               // QY: each half's fault OR, registered
    // QPIPE: busy and the front-end fault are delayed with the datapath (registered outputs); the datapath faults
    // already carry its QK added cycles
    wire busy_c;
    if (QK != 0) begin : g_qo
        reg [QK:0] busy_d, ff_d;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin busy_d <= '0; ff_d <= '0; end
            else begin busy_d <= {busy_d[QK-1:0], busy_c}; ff_d <= {ff_d[QK-1:0], ffault}; end
        assign busy = busy_d[QK-1];
        if (QY != 0) begin : g_qyf
            // fault port from a register: ff_d one more stage, the halves' registered ORs (bk_fault_r), then the OR
            reg ffq, fq;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin ffq <= 1'b0; fq <= 1'b0; end
                else begin ffq <= ff_d[QK-1]; fq <= ffq | (|qy_bkf); end
            assign fault = fq | (PQ != 0 ? pq_fault : 1'b0);
        end else begin : g_nqyf
            assign fault = ff_d[QK-1] | (|bk_fault) | (PQ != 0 ? pq_fault : 1'b0);
        end
    end else begin : g_nqo
        assign busy = busy_c;
        assign fault = ffault | (|bk_fault) | (PQ != 0 ? pq_fault : 1'b0);
    end

    // an FP8 segment whose first unit lacks the low chunk starts at half 1
    wire [SW-1:0] s0_first = c_s0[c_first];
    wire [SW-1:0] s0_nx = (QX != 0) ? qx_s0_nx : c_s0[w_nx_c];
    wire h_go   = !s_fp4[s0_first] && !s_bf[s0_first] && !s_lo[s0_first];
    wire h_next = !s_fp4[s_next] && !s_bf[s_next] && w_firstu && !s_lo[s_next];
    wire nx_first = (FAST != 0) ? (w_nx[UW-2 -: 3] == 3'd0 && w_nx[2:0] == 3'd0) : nx_uabs == 7'd0;
    wire h_nx   = (QX != 0) ? qx_h_nx : !s_fp4[s0_nx] && !s_bf[s0_nx] && nx_first && !s_lo[s0_nx];
    wire [SW-1:0] s0_live = c_s0[c_live];
    wire h_live = !s_fp4[s0_live] && !s_bf[s0_live] && !s_lo[s0_live];
    // MTP: a walker that finishes a position's rounds restarts for the next position
    wire n_more = n_pos != plast;
    wire w_more = w_pos != plast;
    wire w_restart = issue && w_cls_last && ((QX != 0) ? !qx_same && qx_endq : !w_nx[UW-1]) && w_more;
    // QX = 5: hazard_r's next value (above).  On an issue w_cnt restarts at 0 exactly when the class's last word
    // ends the round (an MTP restart implies the round end: !qx_same), else it counts up.
    wire qx_hz_zero = w_cls_last && w_round_end;
    wire qx_hz_h0 = qx_hz({HW{1'b0}}), qx_hz_hp = qx_hz(w_cnt + 1'b1), qx_hz_hs = qx_hz(w_cnt);
    wire qx_hz_is = qx_hz_zero ? (w_cnt == {HW{1'b0}}) || qx_hz_h0 : qx_hz_hp;
`ifdef QX_MUTANT_HZ
    wire qx_hz_nx = go_e ? (issue && w_cnt == {HW{1'b0}}) || qx_hz_h0 : qx_hz_hs;   // negative control: count advance ignored
`else
    wire qx_hz_nx = go_e ? (issue && w_cnt == {HW{1'b0}}) || qx_hz_h0 : issue ? qx_hz_is : qx_hz_hs;
`endif
    always @(posedge gclk or negedge rst_n)
        if (!rst_n) hazard_r <= 1'b0;
        else hazard_r <= qx_hz_nx;
`ifdef QP_CHECK
    always @(negedge clk) if (QX >= 5 && rst_n && hazard_r !== hazard) begin
        $display("QX_CHECK FAIL: hazard register %b != %b at %t", hazard_r, hazard, $time); $fatal(1);
    end
`endif
    function automatic lu_f(input [6*NSEG-1:0] fa, input [SW-1:0] fc, input [2:0] fj);
        lu_f = fa[5*NSEG + fc] && ({1'b0, fj} + 4'd1 == fa[NSEG + 4*fc +: 4]);
    endfunction
    wire lu_go = lu_f(f0_go, c_first, 3'd0);                     // go_e: (c_first, 0, f0_go)
    wire lu_rs = lu_f(fF0, c_live, 3'd0);                        // MTP restart: (c_live, 0, fF0)
    wire lu_xa = lu_f(wA, w_nx_c, w_nx[2:0]);                    // next (c, j) of the walk, sub-block unchanged
    wire lu_xb = lu_f(wB, w_nx_c, w_nx[2:0]);                    //   ... or advanced (wA <= wB)
    wire lu_nx = (QX != 0) ? qx_lu_nx : (w_nx[UW-1] && w_nx[UW-2 -: 3] != w_q) ? lu_xb : lu_xa;
    always @(posedge gclk)
        if (go_e) w_ca_r <= ca_f(f0_go, c_first, 3'd0);
        else if (issue && w_seg_last && w_cl) w_ca_r <= w_restart ? ca_f(fF0, c_live, 3'd0) : qx_ca_nx;
    always @(posedge gclk)
        if (go_e) w_lu_r <= lu_go;
`ifdef QP_MUTANT_LU
        else if (issue && w_seg_last && w_cl) w_lu_r <= w_restart ? lu_rs : lu_xa;   // negative control
`else
        else if (issue && w_seg_last && w_cl) w_lu_r <= w_restart ? lu_rs : lu_nx;
`endif
`ifdef QP_CHECK
    // after the first go, the register equals the original expression in every cycle the walker can issue
    reg qp_lu_seen = 1'b0;
    always @(posedge gclk) if (go_e) qp_lu_seen <= 1'b1;
    always @(negedge clk) if (QPIPE != 0 && FAST != 0 && rst_n && qp_lu_seen && w_run && w_lu_r !== w_lastu0) begin
        $display("QP_CHECK FAIL: w_lastu register %b != %b at %t", w_lu_r, w_lastu0, $time); $fatal(1);
    end
`endif


    always @(posedge gclk or negedge rst_n) begin
        if (!rst_n) begin
            n_run <= 1'b0; bn_run <= 1'b0; fam <= 1'b0; w_run <= 1'b0; f_cnt <= 0; f_wr <= 0; f_rd <= 0; hz_v <= '0; ffault <= 1'b0;
            pp_last_v <= 1'b0; bp_hold <= 3'd0;
        end else begin
            hz_v <= {hz_v[LAT-2:0], issue};
            pp_last_v <= issue; pp_last_b <= a_ctr[0];
            if (BP != 0) bp_hold <= (issue && w_bf) ? HOLDM1 : (bp_hold != 3'd0 ? bp_hold - 3'd1 : 3'd0);
            if (go_em) begin
                // go_e with no valid class of the phase's family is legal and a no-op (the spine broadcasts go_e to
                // every element): no walker starts, so no x beat is captured and no word is issued.  Before this,
                // the walkers started on the stale class 0 and could leave held operands in the segment tree that
                // corrupted the next op (W17 field-composition finding, 2026-09-30).
`ifdef W10_MUTANT_EMPTY_GO
                n_run <= !go_bf_e; bn_run <= go_bf_e; w_run <= 1'b1;
`else
                n_run <= !go_bf_e && c_first_ok; bn_run <= go_bf_e && c_first_ok; w_run <= c_first_ok;
`endif
                n_q <= 3'd0; n_b <= 3'd0; n_c <= c_first; n_j <= 3'd0;
                n_pos <= 3'd0; bn_pos <= 3'd0; w_pos <= 3'd0;
                bn_q <= 3'd0; bn_b <= 3'd0; bn_cnt <= 7'd0; fam <= go_bf_e; bn_tot <= (FAST != 0) ? gtot_f : gtot; w_q <= 3'd0; w_b <= 3'd0; w_c <= c_first; w_j <= 3'd0;
                w_s <= s0_first; w_h <= h_go; w_cnt <= 0;
                f_cnt <= 0; f_wr <= 0; f_rd <= 0;
            end else begin
                if (hit) begin
                    if (!n_nx[UW-1] && n_more) begin
                        n_q <= 3'd0; n_b <= 3'd0; n_c <= c_live; n_j <= 3'd0; n_pos <= n_pos + 3'd1;
                    end else {n_run, n_q, n_b, n_c, n_j} <= n_nx;
                end
                if (issue) begin
                    if (!w_seg_last) begin
                        w_h <= 1'b1;
                        w_cnt <= w_cnt + 1'b1;
                    end else if (!w_cl) begin
                        w_s <= s_next;
                        w_h <= h_next;
                        w_cnt <= w_cnt + 1'b1;
                    end else if (w_restart) begin
                        w_q <= 3'd0; w_b <= 3'd0; w_c <= c_live; w_j <= 3'd0;
                        w_s <= s0_live; w_h <= h_live; w_cnt <= {HW{1'b0}};
                        w_pos <= w_pos + 3'd1;
                    end else begin
                        {w_run, w_q, w_b, w_c, w_j} <= w_nx;
                        w_s <= s0_nx;
                        w_h <= h_nx;
                        w_cnt <= w_round_end ? {HW{1'b0}} : w_cnt + 1'b1;
                    end
                end
                f_cnt <= f_cnt + npush - (pop ? 1'b1 : 1'b0);
                f_wr <= f_wr + npush[XW-1:0];
                if (bnum != 0) begin
                    if (bn_cnt + {4'd0, bnum} == bn_tot) begin
                        bn_cnt <= 7'd0;
                        if (bn_b == 3'd7 && bn_q == qlast) begin
                            if (bn_pos != plast) begin bn_b <= 3'd0; bn_q <= 3'd0; bn_pos <= bn_pos + 3'd1; bn_tot <= (FAST != 0) ? ltot_r : ltot; end
                            else bn_run <= 1'b0;
                        end
                        else begin
                            bn_b <= bn_b + 3'd1;
                            if (bn_b == 3'd7) begin bn_q <= bn_q + 3'd1; bn_tot <= (FAST != 0) ? ntot_r : ntot; end
                        end
                    end else bn_cnt <= bn_cnt + {4'd0, bnum};
                end
                if (pop) f_rd <= f_rd + 1'b1;
                if ({1'b0, f_cnt} + {2'b0, npush} > XF + (pop ? 1 : 0)) ffault <= 1'b1;
                // BF16_PAIR: a round may hold at most NCH / 4 BF16 words (4 chain slots each)
                if (BP != 0 && issue && w_bf && {27'd0, w_cnt} >= NCH / BPH) ffault <= 1'b1;
            end
        end
    end
    // walker sub-block registers (FAST): see sbf above
    always @(posedge gclk) begin
        nQ2 <= sbf({1'b0, n_q} + 4'd2, 2'd3, nu_p, base_live);
        wQ2 <= sbf({1'b0, w_q} + 4'd2, sbs, nu_p, base_live);
    end
    wire n_step = hit;
    wire n_rst = n_step && !n_nx[UW-1] && n_more;
    wire w_step = issue && w_seg_last && w_cl;
    // QY: w_cl_r loaded with (w_s == c_s1[w_c]) for the walker's next (w_s, w_c), mirroring the walker's update
    reg [NSEG-1:0] qy_ceq;              // per class: c_s0[c] == c_s1[c] (a step lands on its class's first segment)
    always @* for (int c = 0; c < NSEG; c++) qy_ceq[c] = c_s0[c] == c_s1[c];
    always @(posedge gclk)
        if (go_e) w_cl_r <= s0_first == c_s1[c_first];
        else if (issue && w_seg_last) begin
            if (!w_cl) w_cl_r <= (QX != 0) ? |(w_coh & qx_s1n) : s_next == c_s1[w_c];
            else if (w_restart) w_cl_r <= s0_live == c_s1[c_live];
`ifdef QY_MUTANT_CL
            else w_cl_r <= !qy_ceq[w_nx_c];            // negative control: the step decision inverted
`else
            else w_cl_r <= (QX != 0) ? |(qx_nxoh & qy_ceq) : qy_ceq[w_nx_c];
`endif
        end
`ifdef QP_CHECK
    reg qy_seen = 1'b0;
    always @(posedge gclk) if (go_e) qy_seen <= 1'b1;
    always @(negedge clk) if (QY != 0 && rst_n && qy_seen && w_run && w_cl_r !== w_cl0) begin
        $display("QY_CHECK FAIL: w_cl register %b != %b at %t", w_cl_r, w_cl0, $time); $fatal(1);
    end
`endif
    // QX = 6: w_sf_r holds s_x[w_s] for the w_s after each edge.  It is on the gated clock with the walker registers
    // (on the free clock it captured ~68 ps early against them, route Z10d).  The configuration is written on the free
    // clock, also while a walk runs, so besides the walker's loads (go: s0_first; on an issue
    // with the segment's last word: s + 1 within the class, s0_live at an MTP restart, else the next class's first
    // segment, an AND-OR select by the one-hot next class) a segment write to the index w_s holds next overrides it
    // with the written flags.  The walker loads only on gclk edges (go_e and issue both hold the gate open).  A write
    // while the gate is closed is missed, but then the walker is idle (walk_busy holds the gate open while w_run) and
    // reloads at go_e; the flags reach an output only through an issue (i1_v), so the outputs are unchanged.
    function automatic [3:0] qx_sfl(input [SW-1:0] i);
        qx_sfl = {s_fp4[i], s_bf[i], s_hi[i], s_lo[i]};
    endfunction
    wire       qx_swr = cfg_v_e && {27'd0, cfg_a_e} < NSEG;               // a segment configuration write
    wire [SW-1:0] qx_sa = cfg_a_e[SW-1:0];
    wire [3:0] qx_swd = {cfg_d_e[26], cfg_d_e[42], cfg_d_e[28], cfg_d_e[27]};
    // per class: the flags of its first segment c_s0[k] and whether the write hits it; the go / restart / step
    // candidates are AND-OR selects of these by the one-hot first class of the go / running family or the one-hot
    // next class (Z10e: c_bf -> base_live -> encode -> c_s0[c_live] -> s_x[] -11.9 ps)
    wire [NSEG-1:0] qx_sf_ohf = qx_low(base_go), qx_sf_ohl = qx_low(base_live);
    reg  [3:0] qx_sf_nx, qx_sf_f, qx_sf_l;
    reg        qx_sw_nx, qx_sw_f, qx_sw_l;                                  // the write hits that class's s0
    always @* begin
        qx_sf_nx = 4'd0; qx_sw_nx = 1'b0; qx_sf_f = 4'd0; qx_sw_f = 1'b0; qx_sf_l = 4'd0; qx_sw_l = 1'b0;
        for (int k = 0; k < NSEG; k++) begin
            qx_sf_nx = qx_sf_nx | ({4{qx_nxoh[k]}} & qx_sfl(c_s0[k]));
            qx_sw_nx = qx_sw_nx | (qx_nxoh[k] && qx_sa == c_s0[k]);
            qx_sf_f  = qx_sf_f  | ({4{qx_sf_ohf[k]}} & qx_sfl(c_s0[k]));
            qx_sw_f  = qx_sw_f  | (qx_sf_ohf[k] && qx_sa == c_s0[k]);
            qx_sf_l  = qx_sf_l  | ({4{qx_sf_ohl[k]}} & qx_sfl(c_s0[k]));
            qx_sw_l  = qx_sw_l  | (qx_sf_ohl[k] && qx_sa == c_s0[k]);
        end
    end
    // QX = 10: the go / restart candidates from free-clock registers formed a cycle earlier (route Z15b: c_v ->
    // base_live -> first class -> flags -> w_sf_r -20.1 ps).  The go candidate is formed against the go_bf PIN (go_e's
    // family a cycle ahead) and the restart candidate against the running family; under the spine contract the
    // configuration is final a cycle before go_e and unchanged while a walk runs (QP_CHECK asserts both at use).
    reg  [3:0] qx_sf_fr, qx_sf_lr, qx_sf_fp;
    reg  [NSEG-1:0] qx_bgp;
    always @* for (int k = 0; k < NSEG; k++) qx_bgp[k] = c_v[k] && c_bf[k] == go_bf;
    wire [NSEG-1:0] qx_ohfp = qx_low(qx_bgp);
    always @* begin
        qx_sf_fp = 4'd0;
        for (int k = 0; k < NSEG; k++) qx_sf_fp = qx_sf_fp | ({4{qx_ohfp[k]}} & qx_sfl(c_s0[k]));
    end
    always @(posedge clk) begin qx_sf_fr <= qx_sf_fp; qx_sf_lr <= qx_sf_l; end
`ifdef QP_CHECK
    always @(negedge clk) if (QX >= 10 && rst_n && ((go_e && qx_sf_fr !== qx_sf_f) || (w_restart && qx_sf_lr !== qx_sf_l))) begin
        $display("QX_CHECK FAIL: registered go / restart flag candidates %b/%b != %b/%b at %t", qx_sf_fr, qx_sf_lr,
                 qx_sf_f, qx_sf_l, $time); $fatal(1);
    end
`endif
    wire qx_sld = go_e || issue && w_seg_last;                              // the walker loads w_s
    wire [3:0] qx_sf_ld = go_e ? ((QX >= 10) ? qx_sf_fr : qx_sf_f) : !w_cl ? qx_sfl(s_next) :
                          w_restart ? ((QX >= 10) ? qx_sf_lr : qx_sf_l) :
`ifdef QX_MUTANT_SF
                          qx_sfl(s_next);                                   // negative control: next class as s + 1
`else
                          qx_sf_nx;
`endif
    wire qx_sw_ld = go_e ? qx_sw_f : !w_cl ? qx_sa == s_next : w_restart ? qx_sw_l : qx_sw_nx;
    wire qx_sw_hit = qx_swr && (qx_sld ? qx_sw_ld : qx_sa == w_s);
    // in reset w_s holds (the walker does not load) but the configuration may still be written
    always @(posedge gclk)
        if (rst_n) w_sf_r <= qx_sw_hit ? qx_swd : qx_sld ? qx_sf_ld : w_sf_r;
        else if (qx_swr && qx_sa == w_s) w_sf_r <= qx_swd;
`ifdef QP_CHECK
    always @(negedge clk) if (QX >= 7 && (go_en !== go_e || go_ew !== go_e || go_em !== go_e)) begin
        $display("QX_CHECK FAIL: go copies %b%b%b != %b at %t", go_en, go_ew, go_em, go_e, $time); $fatal(1);
    end
    always @(negedge clk) if (QX >= 6 && rst_n && qy_seen && w_run && w_sf_r !== {s_fp4[w_s], s_bf[w_s], s_hi[w_s], s_lo[w_s]}) begin
        $display("QX_CHECK FAIL: segment flags %b for w_s %0d at %t", w_sf_r, w_s, $time); $fatal(1);
    end
`endif
    // QX = 3: n_coh / n_cgt / n_ca_r loaded exactly where n_c is (go; on a hit: MTP restart or step), the restart /
    // go values formed from the nA each loads (sbf(0) of the go / running family)
    wire [6*NSEG-1:0] qn_a_go = sbf(4'd0, 2'd3, nu_p, base_go), qn_a_rs = sbf(4'd0, 2'd3, nu_p, base_live);
    wire [NSEG-1:0] qn_ohf = qx_low(base_go), qn_ohl = qx_low(base_live);
    always @(posedge gclk) if (rst_n) begin
        if (go_e) begin n_coh <= qn_ohf; n_cgt <= qx_gt(qn_ohf); n_ca_r <= ca_f(qn_a_go, c_first, 3'd0); end
        else if (hit) begin
            if (qx_n_end && n_more) begin n_coh <= qn_ohl; n_cgt <= qx_gt(qn_ohl); n_ca_r <= ca_f(qn_a_rs, c_live, 3'd0); end
            else begin n_coh <= qn_nxoh; n_cgt <= qx_gt(qn_nxoh); n_ca_r <= qn_ca_nx; end
        end
    end
`ifdef QP_CHECK
    always @(negedge clk) if (QX >= 3 && rst_n && qy_seen) begin
        if (n_coh !== NSEG'(1) << n_c || n_cgt !== qx_gt(NSEG'(1) << n_c) || (n_run && n_ca_r !== |(n_coh & qn_cmpA))) begin
            $display("QX_CHECK FAIL: x-need class mirror %b/%b ca %b for n_c %0d at %t", n_coh, n_cgt, n_ca_r, n_c, $time);
            $fatal(1);
        end
    end
`endif
    // QX: w_coh / w_cgt loaded exactly where w_c is (go, MTP restart, class step)
    wire [NSEG-1:0] qx_ohf = qx_low(base_go), qx_ohl = qx_low(base_live);   // = ot_v41_first_w10 (bit 0 if none)
    always @(posedge gclk) if (rst_n) begin
        if (go_e) begin w_coh <= qx_ohf; w_cgt <= qx_gt(qx_ohf); end
        else if (issue && w_seg_last && w_cl) begin
            if (w_restart) begin w_coh <= qx_ohl; w_cgt <= qx_gt(qx_ohl); end
            else begin w_coh <= qx_nxoh; w_cgt <= qx_nxgt; end
        end
    end
`ifdef QP_CHECK
    // the mirrors equal the one-hot / mask of w_c, and every QX consequence equals the encoded walker's
    always @(negedge clk) if (QX != 0 && FAST != 0 && rst_n && qy_seen) begin
        if (QX >= 2 && w_run && w_ca_r !== |(w_coh & qx_cmpA)) begin
            $display("QX_CHECK FAIL: case-A register %b at %t", w_ca_r, $time); $fatal(1);
        end
        if (w_coh !== NSEG'(1) << w_c || w_cgt !== qx_gt(NSEG'(1) << w_c)) begin
            $display("QX_CHECK FAIL: class mirror %b/%b for w_c %0d at %t", w_coh, w_cgt, w_c, $time); $fatal(1);
        end
        if (w_run && (qx_nx !== w_nx0 || qx_s0_nx !== c_s0[w_nx0[3 +: SW]]
                || qx_lu_nx !== ((w_nx0[UW-1] && w_nx0[UW-2 -: 3] != w_q) ? lu_f(wB, w_nx0[3 +: SW], w_nx0[2:0])
                                                                           : lu_f(wA, w_nx0[3 +: SW], w_nx0[2:0]))
                || qx_h_nx !== (!s_fp4[c_s0[w_nx0[3 +: SW]]] && !s_bf[c_s0[w_nx0[3 +: SW]]] && !s_lo[c_s0[w_nx0[3 +: SW]]]
                                && w_nx0[UW-2 -: 3] == 3'd0 && w_nx0[2:0] == 3'd0)
                || qx_adv !== (w_nx0[UW-1] && w_nx0[UW-2 -: 3] != w_q)
                || |(qx_nxoh & qy_ceq) !== qy_ceq[w_nx0[3 +: SW]] || |(w_coh & qx_s1n) !== (s_next == c_s1[w_c]))) begin
            $display("QX_CHECK FAIL: one-hot step %h != walker %h at %t", qx_nx, w_nx0, $time); $fatal(1);
        end
    end
`endif
    // go_en / go_ew equal go_e (QX = 7 copies); the go loads are split by register group, unchanged in function
    always @(posedge gclk) begin
        if (go_en) begin
            nA <= sbf(4'd0, 2'd3, nu_p, base_go); nB <= sbf(4'd1, 2'd3, nu_p, base_go);
        end else begin
            // QTIMING_FIX: nA and nB take their enables from match copies 1 and 2 (equal to hit)
            if (hit_k[1 % HC] && qx_n_end && n_more) nA <= sbf(4'd0, 2'd3, nu_p, base_live);
            else if (hit_k[1 % HC] && qx_n_adv) nA <= nB;
            if (hit_k[2 % HC] && qx_n_end && n_more) nB <= sbf(4'd1, 2'd3, nu_p, base_live);
            else if (hit_k[2 % HC] && qx_n_adv) nB <= nQ2;
        end
        if (go_ew) begin
            fF0 <= f0_go; fF1 <= f1_go; wA <= f0_go; wB <= f1_go;
        end else begin
            if (w_restart) begin wA <= fF0; wB <= fF1; end
            else if (w_step && ((QX != 0) ? qx_adv : w_nx[UW-1] && w_nx[UW-2 -: 3] != w_q)) begin
                wA <= wB; wB <= wQ2;
            end
        end
    end
    integer si;
    always @(posedge gclk) begin
        if (go_e || w_restart) for (si = 0; si < NSEG; si = si + 1) w_ptr[si] <= s_base[si];
        else if (issue) w_ptr[w_s] <= w_ptr[w_s] + 13'd1;
        if (go_e || w_restart) a_ctr <= pbase;
        else if (issue) a_ctr <= a_ctr + 14'd1;
        if (FAST != 0 ? fw_v : hit) begin
            f_q0[f_wr] <= FAST != 0 ? fw_q0 : xs_q0_e; f_e0[f_wr] <= FAST != 0 ? fw_e0 : xs_e0_e;
            f_q1[f_wr] <= FAST != 0 ? fw_q1 : xs_q1_e; f_e1[f_wr] <= FAST != 0 ? fw_e1 : xs_e1_e;
        end
        for (bk = 0; bk < 4; bk = bk + 1)
            if (bmu[bk]) f_q0[f_wr + bpre[bk]] <= xbd[256*bk +: 256];
        hz_s[0] <= w_cnt;
        for (k = 1; k < LAT; k = k + 1) hz_s[k] <= hz_s[k-1];
    end

    // ---------------- x alignment with the ROM read (issue -> ROM -> capture: 2 cycles) ---------------------
    reg         i1_v;
    wire        i2_v;
    reg [255:0] i1_q0, i1_q1, i2_q0, i2_q1;
    reg [9:0]   i1_e0, i1_e1, i2_e0, i2_e1;
    localparam integer TW = HW + 3 + TRW + 6;  // {slot, position, tree, first, last, final, ok0, ok1, fp4}
    localparam integer TG = 3 + TRW;           // {position, tree}: follows a term to its segment tree
    wire [TRW-1:0] w_tree;
    if (MTP != 0) begin : g_tpos
        assign w_tree = {w_pos[0] ^ (PQ != 0 ? pq_tp : 1'b0), w_s};
    end else begin : g_tnopos
        assign w_tree = w_s;
    end
    reg [TW-1:0] i1_t, i2_t;
    reg i1_bf, i2_bf;
    reg i2x_bf, i2x_bk;
    reg [255:0] i2x_q0, i2x_q1;
    reg [9:0]   i2x_e0, i2x_e1;
    reg [TW-1:0] i2x_t;
    reg i1_bk;                              // PP: bank of the word
    reg i2_bk;
    reg         i2x_v;
    always @(posedge gclk or negedge rst_n) begin
        if (!rst_n) begin i1_v <= 1'b0; i2x_v <= 1'b0; end
        else begin i1_v <= issue; i2x_v <= i1_v; end
    end
    // FP8 word of half h uses slice h on lane 0; FP4 uses slice 0 on lane 0 and slice 1 on lane 1
    wire use_hi = !w_fp4 && !w_bf && w_h;
    // QPIPE: the FP8 half select is applied one stage later (i1 holds both slices and the select)
    reg i1_uh;
    always @(posedge gclk) begin
        i1_q0 <= (use_hi && QPIPE == 0) ? f_q1[f_rd] : f_q0[f_rd];
        i1_e0 <= (use_hi && QPIPE == 0) ? f_e1[f_rd] : f_e0[f_rd];
        i1_uh <= use_hi;
        i1_q1 <= f_q1[f_rd]; i1_e1 <= f_e1[f_rd];
        i1_t <= {w_cnt, w_pos, w_tree, w_b == 3'd0, w_b == 3'd7, w_b == 3'd7 && w_lastu && w_seg_last,
                 !w_bf && (w_fp4 ? hv[0] : 1'b1), !w_bf && w_fp4 && hv[1], w_fp4};
        i1_bf <= w_bf; i1_bk <= a_ctr[0];
        i2x_bf <= i1_bf; i2x_bk <= i1_bk;
`ifdef QP_MUTANT_HALF
        i2x_q0 <= (QPIPE != 0 && i1_uh) ? i1_q1 : i1_q0; i2x_e0 <= i1_e0;      // negative control: exponent half lost
`else
        i2x_q0 <= (QPIPE != 0 && i1_uh) ? i1_q1 : i1_q0; i2x_e0 <= (QPIPE != 0 && i1_uh) ? i1_e1 : i1_e0;
`endif
        i2x_q1 <= i1_q1; i2x_e1 <= i1_e1; i2x_t <= i1_t;
    end
    // PP: one more stage (the ROM word is captured 2 cycles after its read starts)
    if (PP != 0) begin : g_i3
        reg i3_v;
        always @(posedge gclk or negedge rst_n) if (!rst_n) i3_v <= 1'b0; else i3_v <= i2x_v;
        always @(posedge gclk) begin
            i2_bf <= i2x_bf; i2_bk <= i2x_bk; i2_q0 <= i2x_q0; i2_e0 <= i2x_e0; i2_q1 <= i2x_q1; i2_e1 <= i2x_e1;
            i2_t <= i2x_t;
        end
        assign i2_v = i3_v;
    end else begin : g_i2
        always @* begin
            i2_bf = i2x_bf; i2_bk = i2x_bk; i2_q0 = i2x_q0; i2_e0 = i2x_e0; i2_q1 = i2x_q1; i2_e1 = i2x_e1;
            i2_t = i2x_t;
        end
        assign i2_v = i2x_v;
    end
    wire t_fp4 = i2_t[0];
    function automatic [255:0] nib(input [127:0] c);
        integer i;
        begin
            nib = 256'd0;
            for (i = 0; i < 32; i = i + 1) nib[8*i +: 4] = c[4*i +: 4];
        end
    endfunction
    wire [12:0] rom_addr = PP != 0 ? {1'b0, a_ctr[12:1]} : w_ptr[w_s];

    // BF16_PAIR: the x slice of the word being multiplied, held once for both macros of the pair
    reg [255:0] hx_sh;
    always @(posedge gclk) if (BP != 0 && i2_v && i2_bf) hx_sh <= i2_q0;
    // ---------------- per macro: ROM, capture at its pins, lanes, chains, pair adder, segment tree ------------
    // QPIPE QP_CAP: the x slices delayed with the registered capture select (shared by the macros)
    reg [255:0] c3_q0, c3_q1;
    reg [9:0]   c3_e0, c3_e1;
    always @(posedge gclk) if (QPIPE != 0 && QP_CAP != 0) begin c3_q0 <= i2_q0; c3_e0 <= i2_e0; c3_q1 <= i2_q1; c3_e1 <= i2_e1; end
    if (QPIPE != 0 && (BF16 != 0 || BP != 0 || FAST == 0)) begin : g_qp_unsupported
        initial begin $display("ot_v41_rom_elem_qp_w10: QPIPE requires FAST = 1, BF16 = 0, BP = 0"); $finish; end
    end
    genvar mb;
    generate for (mb = 0; mb < NB; mb = mb + 1) begin : g_mac
    // QPIPE: this macro's own copy of the issue pipeline's control (the x slices stay shared), so nothing
    // synthesised from it is merged with the other macro's half across the die
    wire          mi2x_v, mi2x_bk, mi2_v, mi2_bk, mi2_bf;
    wire [TW-1:0] mi2_t;
    // QZ: this macro's reset synchroniser copy, select / enable copies and x slices (kept registers, see the header)
    wire              rst_m;            // lanes, issue control, capture, BF16 paths
    wire              rst_mc, rst_mp, rst_mt;   // chains; pair adder and its delays; segment tree and outputs
    wire [QZ_NS-1:0]  mz_bk, mz_fp4;
    wire [QZ_NE-1:0]  mz_c0, mz_c1;
    wire [255:0]      mz_q0, mz_q1;
    wire [9:0]        mz_e0, mz_e1;
    if (QZ != 0) begin : g_mz
        // four copies of the reset synchroniser (each = g_qb.rst_q), one per unit group, so no single register
        // drives every asynchronous reset of the macro half (R_cap0: rst_q -> fadd y recovery -52 ps at SS)
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_rs (.clk(clk), .arst_n(rst_n_pin), .d(1'b1), .q(rst_m));
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_rsc (.clk(clk), .arst_n(rst_n_pin), .d(1'b1), .q(rst_mc));
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_rsp (.clk(clk), .arst_n(rst_n_pin), .d(1'b1), .q(rst_mp));
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_rst (.clk(clk), .arst_n(rst_n_pin), .d(1'b1), .q(rst_mt));
        ot_v41_kreg #(.W(532)) u_x (.clk(gclk), .arst_n(1'b1), .d({i2x_q0, i2x_e0, i2x_q1, i2x_e1}),
                                    .q({mz_q0, mz_e0, mz_q1, mz_e1}));
    end else begin : g_nmz
        assign rst_m = rst_n; assign rst_mc = rst_n; assign rst_mp = rst_n; assign rst_mt = rst_n;
        assign mz_q0 = i2_q0; assign mz_e0 = i2_e0; assign mz_q1 = i2_q1; assign mz_e1 = i2_e1;
    end
    if (QPIPE != 0 && QZ != 0) begin : g_mi
        wire          z2x_bf, z2_bk;
        wire [TW-1:0] z2x_t;
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_v2x (.clk(gclk), .arst_n(rst_m), .d(i1_v), .q(mi2x_v));
        ot_v41_kreg #(.W(TW + 2)) u_c2x (.clk(gclk), .arst_n(1'b1), .d({i1_bk, i1_bf, i1_t}), .q({mi2x_bk, z2x_bf, z2x_t}));
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_v3 (.clk(gclk), .arst_n(rst_m), .d(mi2x_v), .q(mi2_v));
        ot_v41_kreg #(.W(TW + 2)) u_c2 (.clk(gclk), .arst_n(1'b1), .d({mi2x_bk, z2x_bf, z2x_t}), .q({z2_bk, mi2_bf, mi2_t}));
        assign mi2_bk = z2_bk;
        genvar zk;
        for (zk = 0; zk < QZ_NS; zk = zk + 1) begin : g_ns     // bank select and FP4 select copies (= mi2_bk, mi2_t[0])
`ifdef QZ_MUTANT_BK
            ot_v41_kreg #(.W(2)) u_s (.clk(gclk), .arst_n(1'b1), .d({mi2x_bk ^ (zk == 3), z2x_t[0]}), .q({mz_bk[zk], mz_fp4[zk]}));  // negative control
`else
            ot_v41_kreg #(.W(2)) u_s (.clk(gclk), .arst_n(1'b1), .d({mi2x_bk, z2x_t[0]}), .q({mz_bk[zk], mz_fp4[zk]}));
`endif
        end
        for (zk = 0; zk < QZ_NE; zk = zk + 1) begin : g_ne     // capture enables (= mi2x_v && !mi2x_bk, && mi2x_bk)
            ot_v41_kreg #(.W(2), .AR(1), .RV(2'b00)) u_e (.clk(gclk), .arst_n(rst_m), .d({i1_v && i1_bk, i1_v && !i1_bk}),
                                                          .q({mz_c1[zk], mz_c0[zk]}));
        end
    end else if (QPIPE != 0) begin : g_mi
        (* keep, dont_touch = "true" *) reg r_i2x_v;
        (* keep, dont_touch = "true" *) reg r_i2x_bk;
        (* keep, dont_touch = "true" *) reg r_i2x_bf;
        (* keep, dont_touch = "true" *) reg [TW-1:0] r_i2x_t;
        always @(posedge gclk or negedge rst_m) if (!rst_m) r_i2x_v <= 1'b0; else r_i2x_v <= i1_v;
        always @(posedge gclk) begin r_i2x_bk <= i1_bk; r_i2x_t <= i1_t; r_i2x_bf <= i1_bf; end
        if (PP != 0) begin : g_m3
            (* keep, dont_touch = "true" *) reg r_i3_v;
            (* keep, dont_touch = "true" *) reg r_i2_bk;
            (* keep, dont_touch = "true" *) reg r_i2_bf;
            (* keep, dont_touch = "true" *) reg [TW-1:0] r_i2_t;
            always @(posedge gclk or negedge rst_m) if (!rst_m) r_i3_v <= 1'b0; else r_i3_v <= r_i2x_v;
            always @(posedge gclk) begin r_i2_bk <= r_i2x_bk; r_i2_t <= r_i2x_t; r_i2_bf <= r_i2x_bf; end
            assign mi2_v = r_i3_v; assign mi2_bk = r_i2_bk; assign mi2_t = r_i2_t; assign mi2_bf = r_i2_bf;
        end else begin : g_m2
            assign mi2_v = r_i2x_v; assign mi2_bk = r_i2x_bk; assign mi2_t = r_i2x_t; assign mi2_bf = r_i2x_bf;
        end
        assign mi2x_v = r_i2x_v; assign mi2x_bk = r_i2x_bk;
    end else begin : g_nmi
        assign mi2x_v = i2x_v; assign mi2x_bk = i2x_bk; assign mi2_v = i2_v; assign mi2_bk = i2_bk;
        assign mi2_t = i2_t; assign mi2_bf = i2_bf;
    end
    if (QZ == 0) begin : g_nzs
        assign mz_bk = {QZ_NS{mi2_bk}}; assign mz_fp4 = {QZ_NS{mi2_t[0]}};
        assign mz_c0 = {QZ_NE{mi2x_v && !mi2x_bk}}; assign mz_c1 = {QZ_NE{mi2x_v && mi2x_bk}};
    end
    wire m_fp4 = mi2_t[0];

    wire [273:0] rd;
    wire [273:0] cap;
    wire [273:0] cap_hold;        // PP: the captured word of the last issued word's bank (stable over a BF16 hold)
    if (PP != 0) begin : g_pp
        // two 4096-word macros read alternately.  Each read is a 2-cycle path: the bank's own capture register
        // (placed at its pins) loads only in the cycle its word arrives (set_multicycle_path -setup 2 from the
        // macro to it), and the bank select sits after the capture registers.
        wire [273:0] rd0, rd1;
        reg  [273:0] cap0, cap1;
        ot_rom_4096x274_m8
`ifndef SYNTHESIS
            #(.INSTANCE(mb == 0 ? $sformatf("%s_0", INSTANCE) : $sformatf("%sb_0", INSTANCE)))
`endif
            u_rom0 (.clk(gclk), .ce_in(issue && !a_ctr[0]), .addr_in(a_ctr[12:1]), .rd_out(rd0));
        ot_rom_4096x274_m8
`ifndef SYNTHESIS
            #(.INSTANCE(mb == 0 ? $sformatf("%s_1", INSTANCE) : $sformatf("%sb_1", INSTANCE)))
`endif
            u_rom1 (.clk(gclk), .ce_in(issue && a_ctr[0]), .addr_in(a_ctr[12:1]), .rd_out(rd1));
        if (QZ != 0) begin : g_cz
            genvar ck;
            for (ck = 0; ck < QZ_NE; ck = ck + 1) begin : g_e
                localparam integer LO = (274 * ck) / QZ_NE, HI = (274 * (ck + 1)) / QZ_NE;
                always @(posedge gclk) begin
                    if (mz_c0[ck]) cap0[HI-1:LO] <= rd0[HI-1:LO];
                    if (mz_c1[ck]) cap1[HI-1:LO] <= rd1[HI-1:LO];
                end
            end
            for (ck = 0; ck < QZ_NS; ck = ck + 1) begin : g_s
                localparam integer LO = (274 * ck) / QZ_NS, HI = (274 * (ck + 1)) / QZ_NS;
                assign cap[HI-1:LO] = mz_bk[ck] ? cap1[HI-1:LO] : cap0[HI-1:LO];
            end
        end else begin : g_ncz
            always @(posedge gclk) begin
                if (mi2x_v && !mi2x_bk) cap0 <= rd0;
                if (mi2x_v && mi2x_bk) cap1 <= rd1;
            end
            assign cap = mi2_bk ? cap1 : cap0;
        end
        reg bk_h;
        always @(posedge gclk) if (mi2_v) bk_h <= mi2_bk;
        assign cap_hold = bk_h ? cap1 : cap0;
        assign rd = 274'd0;
    end else begin : g_one
        reg [273:0] cap_r;
        ot_rom_8192x274_m8
`ifndef SYNTHESIS
            #(.INSTANCE(mb == 0 ? INSTANCE : $sformatf("%sb", INSTANCE)))
`endif
            u_rom (.clk(gclk), .ce_in(issue), .addr_in(rom_addr), .rd_out(rd));
        always @(posedge gclk) cap_r <= rd;
        assign cap = cap_r;
        assign cap_hold = 274'd0;
    end
    // lane inputs; QPIPE QP_CAP: registered after the capture select (+1 cycle)
    wire [273:0]  lcap;
    wire          l_v0, l_v1;
    wire [TW-1:0] l_t;
    wire [255:0]  l_xq0, l_xq1;
    wire [9:0]    l_xe0, l_xe1;
    if (QPIPE != 0 && QP_CAP != 0) begin : g_lc
        (* keep, dont_touch = "true" *) reg lc_v0;
        (* keep, dont_touch = "true" *) reg lc_v1;
        (* keep, dont_touch = "true" *) reg [TW-1:0] lc_t;
        reg [273:0] lc_cap;
        always @(posedge gclk or negedge rst_m)
            if (!rst_m) begin lc_v0 <= 1'b0; lc_v1 <= 1'b0; end
            else begin lc_v0 <= mi2_v && mi2_t[2]; lc_v1 <= mi2_v && mi2_t[1]; end
        always @(posedge gclk) begin lc_t <= mi2_t; lc_cap <= cap; end
        assign lcap = lc_cap; assign l_v0 = lc_v0; assign l_v1 = lc_v1; assign l_t = lc_t;
        assign l_xq0 = c3_q0; assign l_xe0 = c3_e0; assign l_xq1 = c3_q1; assign l_xe1 = c3_e1;
    end else begin : g_nlc
        assign lcap = cap; assign l_v0 = mi2_v && mi2_t[2]; assign l_v1 = mi2_v && mi2_t[1]; assign l_t = mi2_t;
        assign l_xq0 = mz_q0; assign l_xe0 = mz_e0; assign l_xq1 = mz_q1; assign l_xe1 = mz_e1;
    end
    wire         l_fp4 = l_t[0];
    wire [255:0] w0q;
    wire [7:0]   w0e;
    if (QZ != 0) begin : g_wz
        wire [255:0] w0n = nib(lcap[127:0]);
        genvar wk;
        for (wk = 0; wk < QZ_NS; wk = wk + 1) begin : g_s
            localparam integer LO = (256 * wk) / QZ_NS, HI = (256 * (wk + 1)) / QZ_NS;
            assign w0q[HI-1:LO] = mz_fp4[wk] ? w0n[HI-1:LO] : lcap[HI-1:LO];
        end
        assign w0e = mz_fp4[0] ? lcap[135:128] : lcap[263:256];
    end else begin : g_nwz
        assign w0q = l_fp4 ? nib(lcap[127:0]) : lcap[255:0];
        assign w0e = l_fp4 ? lcap[135:128] : lcap[263:256];
    end
    wire [255:0] w1q = nib(lcap[263:136]);
    wire [7:0]   w1e = lcap[271:264];
    wire signed [9:0] we0 = $signed({2'b00, w0e}) - 10'sd127;
    wire signed [9:0] we1 = $signed({2'b00, w1e}) - 10'sd127;

    // ---------------- lanes --------------------------------------------------------------------------------------
    wire l0_v, l1_v, l0_f, l1_f;
    wire [31:0] l0_y, l1_y;
    wire [TW-1:0] l0_t, l1_t;
    if (FAST != 0 && QPIPE != 0) begin : g_l3
        ot_v41_bterm4_w10 #(.TW(TW), .P1S(QP_P1), .CSAM(QP_CSAM), .P2S(QX >= 4 ? 1 : 0), .NS(QX >= 10 ? 1 : 0)) u_l0 (.clk(gclk), .rst_n(rst_m), .v(l_v0), .fp4(l_fp4),
            .xq(l_xq0), .xe(l_xe0), .wq(w0q), .we(we0), .tag(l_t), .ov(l0_v), .y(l0_y), .f(l0_f), .otag(l0_t));
        ot_v41_bterm4_w10 #(.TW(TW), .P1S(QP_P1), .CSAM(QP_CSAM), .P2S(QX >= 4 ? 1 : 0), .NS(QX >= 10 ? 1 : 0)) u_l1 (.clk(gclk), .rst_n(rst_m), .v(l_v1), .fp4(1'b1),
            .xq(l_xq1), .xe(l_xe1), .wq(w1q), .we(we1), .tag(l_t), .ov(l1_v), .y(l1_y), .f(l1_f), .otag(l1_t));
    end else if (FAST != 0) begin : g_l2
        ot_v41_bterm2_w10 #(.TW(TW)) u_l0 (.clk(gclk), .rst_n(rst_m), .v(mi2_v && mi2_t[2]), .fp4(m_fp4),
            .xq(i2_q0), .xe(i2_e0), .wq(w0q), .we(we0), .tag(mi2_t), .ov(l0_v), .y(l0_y), .f(l0_f), .otag(l0_t));
        ot_v41_bterm2_w10 #(.TW(TW)) u_l1 (.clk(gclk), .rst_n(rst_m), .v(mi2_v && mi2_t[1]), .fp4(1'b1),
            .xq(i2_q1), .xe(i2_e1), .wq(w1q), .we(we1), .tag(mi2_t), .ov(l1_v), .y(l1_y), .f(l1_f), .otag(l1_t));
    end else begin : g_l1
        ot_v41_bterm #(.TW(TW)) u_l0 (.clk(gclk), .rst_n(rst_m), .v(mi2_v && mi2_t[2]), .fp4(m_fp4),
            .xq(i2_q0), .xe(i2_e0), .wq(w0q), .we(we0), .tag(mi2_t), .ov(l0_v), .y(l0_y), .f(l0_f), .otag(l0_t));
        ot_v41_bterm #(.TW(TW)) u_l1 (.clk(gclk), .rst_n(rst_m), .v(mi2_v && mi2_t[1]), .fp4(1'b1),
            .xq(i2_q1), .xe(i2_e1), .wq(w1q), .we(we1), .tag(mi2_t), .ov(l1_v), .y(l1_y), .f(l1_f), .otag(l1_t));
    end
    wire c0_v, c1_v, c0_f, c1_f, c0_fault, c1_fault, t_fault, b_fault;
    wire [31:0] c0_s, c1_s;
    wire [TG:0] c0_t, c1_t;   // {position, tree, final}
    // chain inputs: the block-dot lanes (FP8/FP4) or, in a BF16_PAIR BF16 phase, multipliers 0 and 1
    wire          ci0_v, ci1_v, ci0_f, ci1_f, ci_first, ci_last;
    wire [31:0]   ci0_y, ci1_y;
    wire [HW-1:0] ci_slot;
    wire [TG:0]   ci_tag;
    wire          m_v;                      // BF16_PAIR products valid (all four multipliers together)
    wire [31:0]   m_y [0:3];
    wire [3:0]    m_f;
    wire [HW-1:0] m_slot;
    wire          m_first, m_last;
    wire [TG:0]   m_tag;
    if (BP != 0) begin : g_bpm
        // hold the captured word and x slice for BPH cycles; cycle k multiplies lanes 4k .. 4k+3
        // the word: PP's per-bank capture register holds it (the next BF16 word arrives >= BPH cycles later);
        // without PP a copy is held.  The x slice is the pair's shared hx_sh.
        reg [255:0] hw_;
        wire [255:0] hwv = PP != 0 ? cap_hold[255:0] : hw_;
        reg [TW-1:0] ht;
        reg [KW-1:0] hk;
        reg hv;
        always @(posedge gclk or negedge rst_m) begin
            if (!rst_m) begin hv <= 1'b0; hk <= '0; end
            else if (mi2_v && mi2_bf) begin hv <= 1'b1; hk <= '0; end
            else if (hv) begin hk <= hk + 1'b1; if (hk == KLAST) hv <= 1'b0; end
        end
        always @(posedge gclk) if (mi2_v && mi2_bf) begin if (PP == 0) hw_ <= cap[255:0]; ht <= mi2_t; end
        // product pipe tag: {slot, first, last, position, tree, final}
        localparam integer PW_ = HW + 2 + TG + 1;
        // chain slot = 4 x (word in round) + k (the word index is the tag's slot field, < NCH / 4)
        wire [HW-1:0] pslot = {ht[TW-1-KW -: HW-KW], hk};
        // the segment's final base node is the LAST 4-chunk node of its last unit (k = 3)
        wire [PW_-1:0] pt_in = {pslot, ht[5], ht[4], ht[TW-HW-1 -: TG], ht[3] && hk == KLAST};
        wire [PW_-1:0] pt;
        // the lane select is registered (hv_r, wl_r, xl_r) before the multipliers
        ot_hdc_delay #(.W(PW_), .D(6)) u_mt (.clk(gclk), .rst_n(rst_m), .d(pt_in), .q(pt));
        reg [5:0] mvp;
        reg hv_r;
        always @(posedge gclk or negedge rst_m) if (!rst_m) begin mvp <= 6'd0; hv_r <= 1'b0; end
            else begin mvp <= {mvp[4:0], hv}; hv_r <= hv; end
        assign m_v = mvp[5];
        assign {m_slot, m_first, m_last, m_tag} = pt;
        genvar mm;
        for (mm = 0; mm < BPN; mm = mm + 1) begin : g_mul
            reg [15:0] wl, xl;
            always @(posedge gclk) begin wl <= hwv[16 * (BPN * hk + mm) +: 16]; xl <= hx_sh[16 * (BPN * hk + mm) +: 16]; end
            ot_hdc_bmul u_m (.clk(gclk), .rst_n(rst_m), .v(hv_r), .a({wl, 16'd0}), .b({xl, 16'd0}),
                             .y(m_y[mm]), .fault(m_f[mm]));
        end
        assign ci0_v = fam ? m_v : l0_v;           assign ci1_v = fam ? m_v : l1_v;
        assign ci0_y = fam ? m_y[0] : l0_y;        assign ci1_y = fam ? m_y[1] : l1_y;
        assign ci0_f = fam ? m_f[0] : l0_f;        assign ci1_f = fam ? m_f[1] : l1_f;
        assign ci_slot = fam ? m_slot : l0_t[TW-1 -: HW];
        assign ci_first = fam ? m_first : l0_t[5];
        assign ci_last = fam ? m_last : l0_t[4];
        assign ci_tag = fam ? m_tag : {l0_t[TW-HW-1 -: TG], l0_t[3]};
    end else begin : g_nobpm
        assign m_v = 1'b0; assign m_slot = '0; assign m_first = 1'b0; assign m_last = 1'b0; assign m_tag = '0;
        assign m_f = 4'd0;
        assign m_y[0] = 32'd0; assign m_y[1] = 32'd0; assign m_y[2] = 32'd0; assign m_y[3] = 32'd0;
        assign ci0_v = l0_v; assign ci1_v = l1_v; assign ci0_y = l0_y; assign ci1_y = l1_y;
        assign ci0_f = l0_f; assign ci1_f = l1_f; assign ci_slot = l0_t[TW-1 -: HW];
        assign ci_first = l0_t[5]; assign ci_last = l0_t[4]; assign ci_tag = {l0_t[TW-HW-1 -: TG], l0_t[3]};
    end
    // lane 1's slot/first/last/tag equal lane 0's whenever both run (same word); alone it carries its own
    wire [HW-1:0] ci1_slot = (BP != 0 && fam) ? m_slot : l1_t[TW-1 -: HW];
    wire          ci1_first = (BP != 0 && fam) ? m_first : l1_t[5];
    wire          ci1_last = (BP != 0 && fam) ? m_last : l1_t[4];
    wire [TG:0]   ci1_tag = (BP != 0 && fam) ? m_tag : {l1_t[TW-HW-1 -: TG], l1_t[3]};
    if (FAST != 0 && QZ != 0) begin : g_ch3
    ot_v41_chain4 #(.PD(QX >= 10 ? 1 : 0), .ND(QZ_NS / 2), .NCH(NCH), .TW(TG + 1), .CUT(CUT)) u_c0 (.clk(gclk), .rst_n(rst_mc), .v(ci0_v),
        .slot(ci_slot), .first(ci_first), .last(ci_last), .term(ci0_y), .term_f(ci0_f),
        .tag(ci_tag), .ov(c0_v), .osum(c0_s), .of(c0_f), .otag(c0_t), .fault(c0_fault));
    ot_v41_chain4 #(.PD(QX >= 10 ? 1 : 0), .ND(QZ_NS / 2), .NCH(NCH), .TW(TG + 1), .CUT(CUT)) u_c1 (.clk(gclk), .rst_n(rst_mc), .v(ci1_v),
        .slot(ci1_slot), .first(ci1_first), .last(ci1_last), .term(ci1_y), .term_f(ci1_f),
        .tag(ci1_tag), .ov(c1_v), .osum(c1_s), .of(c1_f), .otag(c1_t), .fault(c1_fault));
    end else if (FAST != 0) begin : g_ch2
    ot_v41_chain2 #(.NCH(NCH), .TW(TG + 1), .CUT(CUT)) u_c0 (.clk(gclk), .rst_n(rst_mc), .v(ci0_v),
        .slot(ci_slot), .first(ci_first), .last(ci_last), .term(ci0_y), .term_f(ci0_f),
        .tag(ci_tag), .ov(c0_v), .osum(c0_s), .of(c0_f), .otag(c0_t), .fault(c0_fault));
    ot_v41_chain2 #(.NCH(NCH), .TW(TG + 1), .CUT(CUT)) u_c1 (.clk(gclk), .rst_n(rst_mc), .v(ci1_v),
        .slot(ci1_slot), .first(ci1_first), .last(ci1_last), .term(ci1_y), .term_f(ci1_f),
        .tag(ci1_tag), .ov(c1_v), .osum(c1_s), .of(c1_f), .otag(c1_t), .fault(c1_fault));
    end else begin : g_ch1
    ot_v41_chain #(.NCH(NCH), .TW(TG + 1)) u_c0 (.clk(gclk), .rst_n(rst_mc), .v(ci0_v),
        .slot(ci_slot), .first(ci_first), .last(ci_last), .term(ci0_y), .term_f(ci0_f),
        .tag(ci_tag), .ov(c0_v), .osum(c0_s), .of(c0_f), .otag(c0_t), .fault(c0_fault));
    ot_v41_chain #(.NCH(NCH), .TW(TG + 1)) u_c1 (.clk(gclk), .rst_n(rst_mc), .v(ci1_v),
        .slot(ci1_slot), .first(ci1_first), .last(ci1_last), .term(ci1_y), .term_f(ci1_f),
        .tag(ci1_tag), .ov(c1_v), .osum(c1_s), .of(c1_f), .otag(c1_t), .fault(c1_fault));
    end
    // BF16_PAIR: chains 2 and 3 (multipliers 2 and 3) and the 4-chunk combine
    wire        c2_v, c3_v, c2_f, c3_f, c2_fault, c3_fault;
    wire [31:0] c2_s, c3_s;
    wire [TG:0] c2_t, c3_t;
    wire        q4_v, q4_err;
    wire [31:0] q4_val;
    wire [TG:0] q4_t;
    if (BP == 1) begin : g_bpc
        ot_v41_chain2 #(.NCH(NCH), .TW(TG + 1), .CUT(CUT)) u_c2 (.clk(gclk), .rst_n(rst_mc), .v(m_v),
            .slot(m_slot), .first(m_first), .last(m_last), .term(m_y[2]), .term_f(m_f[2]),
            .tag(m_tag), .ov(c2_v), .osum(c2_s), .of(c2_f), .otag(c2_t), .fault(c2_fault));
        ot_v41_chain2 #(.NCH(NCH), .TW(TG + 1), .CUT(CUT)) u_c3 (.clk(gclk), .rst_n(rst_mc), .v(m_v),
            .slot(m_slot), .first(m_first), .last(m_last), .term(m_y[3]), .term_f(m_f[3]),
            .tag(m_tag), .ov(c3_v), .osum(c3_s), .of(c3_f), .otag(c3_t), .fault(c3_fault));
    end else begin : g_nobpc
        assign c2_v = 1'b0; assign c3_v = 1'b0; assign c2_s = 32'd0; assign c3_s = 32'd0; assign c2_f = 1'b0;
        assign c3_f = 1'b0; assign c2_t = '0; assign c3_t = '0; assign c2_fault = 1'b0; assign c3_fault = 1'b0;
    end

    // ---------------- sibling-chunk pair (FP4): chunk 2p + chunk 2p+1, or the one present ------------------
    wire both = c0_v && c1_v;
    wire any = c0_v || c1_v;
    wire [TG:0] ct = c0_v ? c0_t : c1_t;
    wire [31:0] one = c0_v ? c0_s : c1_s;
    wire one_f = c0_v ? c0_f : c1_f;
    wire [31:0] pr_sum, pr_pass;
    wire [1:0] pr_err;
    wire pr_vo;
    if (FAST != 0) begin : g_pa2
        ot_v41_fadd #(.CUT(CUT)) u_pair (.clk(gclk), .rst_n(rst_mp), .valid_in(both), .a(c0_s), .b(c1_s),
            .y(pr_sum), .err(pr_err), .valid_out(pr_vo));
    end else begin : g_pa1
        ot_fp32_add_rne_pipe u_pair (.clk(gclk), .rst_n(rst_mp), .valid_in(both), .a(c0_s), .b(c1_s),
            .y(pr_sum), .err(pr_err), .valid_out(pr_vo));
    end
    ot_hdc_delay #(.W(32), .D(LAT)) u_pp (.clk(gclk), .rst_n(rst_mp), .d(one), .q(pr_pass));
    wire [TG+2:0] pr_t;   // {position, tree, final, both, err}
    ot_hdc_delay #(.W(TG + 3), .D(LAT)) u_pt (.clk(gclk), .rst_n(rst_mp),
        .d({ct, both, both ? (c0_f | c1_f) : one_f}), .q(pr_t));
    reg [LAT-1:0] pr_vp;
    always @(posedge gclk or negedge rst_mp)
        if (!rst_mp) pr_vp <= '0; else pr_vp <= {pr_vp[LAT-2:0], any};
    wire        q_v = pr_vp[LAT-1];
    wire [31:0] q_val = pr_t[1] ? pr_sum : pr_pass;
    wire        q_err = pr_t[0] | (pr_t[1] && pr_err != 2'd0);
    if (BP == 1) begin : g_bp4
        // chunks 4k+2 + 4k+3 (golden level 1), then (4k + 4k+1) + (4k+2 + 4k+3) (level 2)
        wire [31:0] pb_sum, l2_sum;
        wire [1:0]  pb_err, l2_err;
        wire        pb_vo, l2_vo;
        ot_v41_fadd #(.CUT(CUT)) u_pairb (.clk(gclk), .rst_n(rst_m), .valid_in(c2_v && c3_v), .a(c2_s), .b(c3_s),
            .y(pb_sum), .err(pb_err), .valid_out(pb_vo));
        wire pbe;
        ot_hdc_delay #(.W(1), .D(LAT)) u_pbe (.clk(gclk), .rst_n(rst_m), .d(c2_f | c3_f), .q(pbe));
        wire l2_in = fam && q_v;
        ot_v41_fadd #(.CUT(CUT)) u_l2 (.clk(gclk), .rst_n(rst_m), .valid_in(l2_in), .a(q_val), .b(pb_sum),
            .y(l2_sum), .err(l2_err), .valid_out(l2_vo));
        wire [TG+1:0] l2t;
        ot_hdc_delay #(.W(TG + 2), .D(LAT)) u_l2t (.clk(gclk), .rst_n(rst_m),
            .d({pr_t[TG+2:2], q_err | pbe | (pb_err != 2'd0)}), .q(l2t));
        assign q4_v = l2_vo; assign q4_val = l2_sum; assign q4_err = l2t[0] | (l2_err != 2'd0);
        assign q4_t = l2t[TG+1:1];
    end else begin : g_nobp4
        assign q4_v = 1'b0; assign q4_val = 32'd0; assign q4_err = 1'b0; assign q4_t = '0;
    end

    // ---------------- optional BF16 lanes -------------------------------------------------------------------
    wire bf_v, bf_err, bf_final;
    wire [31:0] bf_val;
    wire [TG-1:0] bf_tree;
    if (BF16 != 0) begin : g_bf
        if (FAST != 0) begin : g_f
        ot_v41_bf16_lanes2 #(.NCHB(NCHB), .TRW(TG), .CUT(CUT)) u_bf (.clk(gclk), .rst_n(rst_m), .v(mi2_v && mi2_bf),
            .w(cap[255:0]), .x(i2_q0), .slot(mi2_t[TW-HW +: $clog2(NCHB)]), .first(mi2_t[5]), .last(mi2_t[4]),
            .tree(mi2_t[TW-HW-1 -: TG]), .final_i(mi2_t[3]), .ov(bf_v), .oval(bf_val), .otree(bf_tree),
            .ofinal(bf_final), .oerr(bf_err), .fault(b_fault));
        end else begin : g_s
        ot_v41_bf16_lanes #(.NCHB(NCHB), .TRW(TG)) u_bf (.clk(gclk), .rst_n(rst_m), .v(mi2_v && mi2_bf),
            .w(cap[255:0]), .x(i2_q0), .slot(mi2_t[TW-HW +: $clog2(NCHB)]), .first(mi2_t[5]), .last(mi2_t[4]),
            .tree(mi2_t[TW-HW-1 -: TG]), .final_i(mi2_t[3]), .ov(bf_v), .oval(bf_val), .otree(bf_tree),
            .ofinal(bf_final), .oerr(bf_err), .fault(b_fault));
        end
    end else begin : g_nobf
        assign bf_v = 1'b0; assign bf_val = 32'd0; assign bf_tree = '0; assign bf_final = 1'b0;
        assign bf_err = 1'b0; assign b_fault = 1'b0;
    end
    wire        qq_v = (BP == 1 && fam) ? q4_v : q_v;       // BP 1 BF16 phase: the 4-chunk node (BP 2: the pair's)
    wire [31:0] qq_val = (BP == 1 && fam) ? q4_val : q_val;
    wire        qq_err = (BP == 1 && fam) ? q4_err : q_err;
    wire [TG:0] qq_t = (BP == 1 && fam) ? q4_t : pr_t[TG+2:2];
    wire        b_v = qq_v | bf_v;
    wire [31:0] b_val = bf_v ? bf_val : qq_val;
    wire        b_err = bf_v ? bf_err : qq_err;
    wire [TG-1:0] b_tag = bf_v ? bf_tree : qq_t[TG:1];
    wire [TRW-1:0] b_tree = b_tag[TRW-1:0];
    wire [2:0]     b_pos = b_tag[TG-1 -: 3];
    wire        b_final = bf_v ? bf_final : qq_t[0];

    // ---------------- segment tree -> partial ---------------------------------------------------------------------
    wire t_v, t_err;
    wire [TRW-1:0] t_tree;
    wire [2:0]     t_pos;
    wire [31:0] t_val;
    if (FAST != 0 && QPIPE != 0 && QX >= 9) begin : g_tr5
    // QX = 9: the decide stage split in two (one more cycle per tree level; see ot_v41_segtree5.sv)
    ot_v41_segtree5 #(.CUT(CUT), .NT(NSEG << (MTP != 0 ? 1 : 0)), .LV(LV), .EARLY(EARLY), .QD(BP != 0 ? 16 : 8)) u_tree (.clk(gclk), .rst_n(rst_mt), .in_v(b_v),
        .in_tree(b_tree), .in_pos(b_pos), .in_val(b_val), .in_final(b_final), .in_err(b_err),
        .ov(t_v), .otree(t_tree), .opos(t_pos), .oval(t_val), .oerr(t_err), .fault(t_fault));
    end else if (FAST != 0 && QPIPE != 0) begin : g_tr3
    ot_v41_segtree4 #(.XR(0), .XC(QX >= 8 ? 4 : 1), .CUT(CUT), .NT(NSEG << (MTP != 0 ? 1 : 0)), .LV(LV), .EARLY(EARLY), .QD(BP != 0 ? 16 : 8)) u_tree (.clk(gclk), .rst_n(rst_mt), .in_v(b_v),
        .in_tree(b_tree), .in_pos(b_pos), .in_val(b_val), .in_final(b_final), .in_err(b_err),
        .ov(t_v), .otree(t_tree), .opos(t_pos), .oval(t_val), .oerr(t_err), .fault(t_fault));
    end else if (FAST != 0) begin : g_tr2
    ot_v41_segtree2 #(.CUT(CUT), .NT(NSEG << (MTP != 0 ? 1 : 0)), .LV(LV), .EARLY(EARLY), .QD(BP != 0 ? 16 : 8)) u_tree (.clk(gclk), .rst_n(rst_mt), .in_v(b_v),
        .in_tree(b_tree), .in_pos(b_pos), .in_val(b_val), .in_final(b_final), .in_err(b_err),
        .ov(t_v), .otree(t_tree), .opos(t_pos), .oval(t_val), .oerr(t_err), .fault(t_fault));
    end else begin : g_tr1
    ot_v41_segtree #(.NT(NSEG << (MTP != 0 ? 1 : 0)), .LV(LV), .EARLY(EARLY)) u_tree (.clk(gclk), .rst_n(rst_mt), .in_v(b_v),
        .in_tree(b_tree), .in_pos(b_pos), .in_val(b_val), .in_final(b_final), .in_err(b_err),
        .ov(t_v), .otree(t_tree), .opos(t_pos), .oval(t_val), .oerr(t_err), .fault(t_fault));
    end
    reg o_v, o_err;
    reg [31:0] o_val;
    reg [15:0] o_row;
    reg [4:0] o_seg, o_n;
    reg [2:0] o_pos;
    wire [SW-1:0] t_seg = t_tree[SW-1:0];
    assign pq_tree[TRW*mb +: TRW] = t_tree;
    assign pq_pos[3*mb +: 3] = t_pos;
    always @(posedge gclk or negedge rst_mt) begin
        if (!rst_mt) o_v <= 1'b0;
        else o_v <= t_v && !(PQ != 0 ? pq_idle[mb] : (QK != 0 ? so_row[mb * NSEG + t_seg][15] : s_row[mb * NSEG + t_seg][15]));   // row bit 15: an idle half of a pair emits nothing
    end
    always @(posedge gclk) begin
        o_val <= t_val; o_err <= t_err;
`ifdef QP_MUTANT_SHADOW
        if (0) begin                                                           // negative control: live tables
`else
        if (QK != 0) begin
`endif
            o_row <= so_row[mb * NSEG + t_seg]; o_seg <= so_idx[t_seg]; o_n <= so_n[t_seg]; end
        else begin o_row <= s_row[mb * NSEG + t_seg]; o_seg <= s_idx[t_seg]; o_n <= s_n[t_seg]; end
        if (PQ != 0) begin o_row <= pq_row[16*mb +: 16]; o_seg <= pq_idx[5*mb +: 5]; o_n <= pq_n[5*mb +: 5]; end
        o_pos <= (MTP != 0) ? t_pos : 3'd0;
    end
    assign pv[mb] = o_v; assign pval[32*mb +: 32] = o_val; assign prow[16*mb +: 16] = o_row;
    assign pseg[5*mb +: 5] = o_seg; assign pnseg[5*mb +: 5] = o_n; assign perr[mb] = o_err;
    assign ppos[3*mb +: 3] = o_pos;
    assign bk_fault[mb] = c0_fault | c1_fault | c2_fault | c3_fault | t_fault | b_fault;
    if (QY != 0) begin : g_qyb
        reg bkf_r;
        always @(posedge clk or negedge rst_mt) if (!rst_mt) bkf_r <= 1'b0; else bkf_r <= bk_fault[mb];
        assign qy_bkf[mb] = bkf_r;
    end else begin : g_nqyb
        assign qy_bkf[mb] = bk_fault[mb];
    end
    end endgenerate
    assign busy_c = w_run | i1_v | i2_v | drain != 8'd0;
    assign walk_busy = w_run | n_run | bn_run | i1_v | i2_v | (BP != 0 && bp_hold != 3'd0);
    // slot field of the tag is HW bits; BF16 chains use its low log2(NCHB) bits (words per round <= NCHB)
`ifdef QXPQ_DBG
    reg dbg_pf, dbg_ff, dbg_bk;
    always @(posedge clk) if (rst_n) begin
        dbg_pf <= pq_fault; dbg_ff <= ffault; dbg_bk <= |bk_fault;
        if (pq_fault && !dbg_pf) $display("QXPQ_DBG %m pq_fault t=%0t go_e=%b walking=%b sh_free=%b cfg_v_x=%b a=%0d", $time, go_e, pq_walking, sh_free, cfg_v_x, cfg_a_x);
        if (ffault && !dbg_ff) $display("QXPQ_DBG %m ffault t=%0t", $time);
        if ((|bk_fault) && !dbg_bk) $display("QXPQ_DBG %m bk_fault=%b t=%0t", bk_fault, $time);
        if (go_e) $display("QXPQ_DBG %m go_e t=%0t tag=%0d walking=%b", $time, go_tag_e, pq_walking);
        if (pq_swap) $display("QXPQ_DBG %m swap t=%0t", $time);
    end
`endif
endmodule
