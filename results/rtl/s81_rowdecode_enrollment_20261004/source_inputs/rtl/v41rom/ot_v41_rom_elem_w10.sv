`timescale 1ns/1ps
// ---------------------------------------------------------------------------
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
module ot_v41_rom_elem_w10 #(
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
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire         go_bf,        // the phase's family: 0 = FP8/FP4 (shared FP8 x stream), 1 = BF16
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,       // MTP position of the beat
    input  wire [2:0]   xb_pos,
    // BF16 x stream beat: 4 lane-group slices {unit, 16 BF16} for block b
    input  wire         xb_v,
    input  wire [2:0]   xb_b,
    input  wire [3:0]   xb_sv,
    input  wire [31:0]  xb_u,
    input  wire [1023:0] xb_d,
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
    wire gclk;
    if (FAST != 0) begin : g_ir
        reg r_cfg_v, r_go, r_go_bf, r_xs_v, r_xb_v;
        reg [4:0] r_cfg_a; reg [47:0] r_cfg_d; reg [7:0] r_xs_p; reg [2:0] r_xs_b, r_xs_pos, r_xb_pos, r_xb_b;
        reg [1:0] r_xs_sv; reg [255:0] r_xs_q0, r_xs_q1; reg [9:0] r_xs_e0, r_xs_e1; reg [3:0] r_xb_sv;
        reg [31:0] r_xb_u; reg [1023:0] r_xb_d;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin r_cfg_v <= 1'b0; r_go <= 1'b0; end
            else begin r_cfg_v <= cfg_v; r_go <= go; end
        always @(posedge clk) begin r_cfg_a <= cfg_a; r_cfg_d <= cfg_d; r_go_bf <= go_bf; end
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
        assign xs_v_e = r_xs_v; assign xs_p_e = r_xs_p; assign xs_b_e = r_xs_b; assign xs_sv_e = r_xs_sv;
        assign xs_q0_e = r_xs_q0; assign xs_e0_e = r_xs_e0; assign xs_q1_e = r_xs_q1; assign xs_e1_e = r_xs_e1;
        assign xs_pos_e = r_xs_pos; assign xb_pos_e = r_xb_pos; assign xb_v_e = r_xb_v; assign xb_b_e = r_xb_b;
        assign xb_sv_e = r_xb_sv; assign xb_u_e = r_xb_u; assign xb_d_e = r_xb_d;
    end else begin : g_nir
        assign cfg_v_e = cfg_v; assign cfg_a_e = cfg_a; assign cfg_d_e = cfg_d; assign go_e = go; assign go_bf_e = go_bf;
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
    reg [7:0] drain;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) drain <= 8'd0;
        else if (go_e || walk_busy) drain <= DRAIN[7:0];
        else if (drain != 8'd0) drain <= drain - 8'd1;
    wire cg_en = !rst_n || go || go_e || walk_busy || drain != 8'd0;
    if (CG != 0) begin : g_cg
        ot_hdc_cg u_cg (.clk(clk), .en(cg_en), .gclk(gclk));
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
            // 2NSEG+1+s -> NSEG+s for every s, including s = NSEG-1 (the low-bit decode wrapped it to NSEG-1)
            if (NB > 1 && {27'd0, cfg_a_e} <= 3 * NSEG) s_row[{27'd0, cfg_a_e} - (NSEG + 1)] <= cfg_d_e[15:0];
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
    // ---------------- x-need walker: one (pair, b) per class unit per round ------------------------------
    reg        n_run;
    reg [2:0]  n_q, n_pos, bn_pos, w_pos;
    reg [2:0]  n_b, n_j;
    reg [SW-1:0] n_c;
    wire [7:0] n_pair = c_u0[n_c] + {2'd0, n_q, n_j};
    wire [UW-1:0] n_nx;
    reg [6*NSEG-1:0] nA, nB, wA, wB, fF0, fF1, nQ2, wQ2;     // xQ2: f(q + 2), registered every cycle
    if (FAST != 0) begin : g_nw2
        ot_v41_walk2_w10 #(.N(NSEG)) u_nw (.q(n_q), .b(n_b), .c(n_c), .j(n_j), .live(nA[NSEG-1:0]),
            .livq1(nB[NSEG-1:0]), .cur(nA[5*NSEG-1:NSEG]), .qlast(qlast), .nx(n_nx));
    end else begin : g_nw1
        ot_v41_walk_w10 #(.N(NSEG)) u_nw (.q(n_q), .b(n_b), .c(n_c), .j(n_j), .nu(nu_p), .base(base_live),
                                       .qlast(qlast), .sbs(2'd3), .nx(n_nx));
    end
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
    wire hit_q = n_run && !fam && xs_v_e && pair_match && xs_b_e == n_b && xs_pos_e == n_pos;
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
    always @(posedge gclk) if (hit_q) begin fw_q0 <= xs_q0_e; fw_q1 <= xs_q1_e; fw_e0 <= xs_e0_e; fw_e1 <= xs_e1_e; end
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
    wire w_lastu  = (FAST != 0) ? (wA[5*NSEG + w_c] && {1'b0, w_j} + 4'd1 == w_curc) : w_uabs + 7'd1 == c_nu[w_c];
    wire [1:0] hv = {!(w_lastu && !s_hi[w_s]), !(w_firstu && !s_lo[w_s])};
    wire w_fp4 = s_fp4[w_s];
    wire w_bf = s_bf[w_s];
    wire w_seg_last = w_fp4 || w_bf || w_h || !hv[1];          // the segment's last word for this unit
    wire w_cls_last = w_seg_last && w_s == c_s1[w_c];
    wire [UW-1:0] w_nx;
    if (FAST != 0) begin : g_ww2
        ot_v41_walk2_w10 #(.N(NSEG)) u_ww (.q(w_q), .b(w_b), .c(w_c), .j(w_j), .live(wA[NSEG-1:0]),
            .livq1(wB[NSEG-1:0]), .cur(wA[5*NSEG-1:NSEG]), .qlast(qlast), .nx(w_nx));
    end else begin : g_ww1
        ot_v41_walk_w10 #(.N(NSEG)) u_ww (.q(w_q), .b(w_b), .c(w_c), .j(w_j), .nu(nu_p), .base(base_live),
                                       .qlast(qlast), .sbs(sbs), .nx(w_nx));
    end
    wire w_round_end = !w_nx[UW-1] || w_nx[UW-5 -: 3] != w_b;
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
    // PP: word i is in bank i[0]; a bank is read at most every other cycle (only an MTP restart to an even base
    // right after an even word can collide: one stall)
    reg [13:0] a_ctr;
    reg        pp_last_v, pp_last_b;
    wire       pp_block = (PP != 0) && pp_last_v && pp_last_b == a_ctr[0];
    reg [2:0] bp_hold;                      // BF16_PAIR: cycles left of the word being multiplied
    wire issue = w_run && f_cnt != 0 && !hazard && !pp_block && !(BP != 0 && bp_hold != 3'd0);
    wire pop = issue && w_cls_last;
    reg ffault;
    wire [NB-1:0] bk_fault;
    assign fault = ffault | (|bk_fault);

    // an FP8 segment whose first unit lacks the low chunk starts at half 1
    wire [SW-1:0] s0_first = c_s0[c_first];
    wire [SW-1:0] s0_nx = c_s0[w_nx_c];
    wire h_go   = !s_fp4[s0_first] && !s_bf[s0_first] && !s_lo[s0_first];
    wire h_next = !s_fp4[s_next] && !s_bf[s_next] && w_firstu && !s_lo[s_next];
    wire nx_first = (FAST != 0) ? (w_nx[UW-2 -: 3] == 3'd0 && w_nx[2:0] == 3'd0) : nx_uabs == 7'd0;
    wire h_nx   = !s_fp4[s0_nx] && !s_bf[s0_nx] && nx_first && !s_lo[s0_nx];
    wire [SW-1:0] s0_live = c_s0[c_live];
    wire h_live = !s_fp4[s0_live] && !s_bf[s0_live] && !s_lo[s0_live];
    // MTP: a walker that finishes a position's rounds restarts for the next position
    wire n_more = n_pos != plast;
    wire w_more = w_pos != plast;
    wire w_restart = issue && w_cls_last && !w_nx[UW-1] && w_more;


    always @(posedge gclk or negedge rst_n) begin
        if (!rst_n) begin
            n_run <= 1'b0; bn_run <= 1'b0; fam <= 1'b0; w_run <= 1'b0; f_cnt <= 0; f_wr <= 0; f_rd <= 0; hz_v <= '0; ffault <= 1'b0;
            pp_last_v <= 1'b0; bp_hold <= 3'd0;
        end else begin
            hz_v <= {hz_v[LAT-2:0], issue};
            pp_last_v <= issue; pp_last_b <= a_ctr[0];
            if (BP != 0) bp_hold <= (issue && w_bf) ? HOLDM1 : (bp_hold != 3'd0 ? bp_hold - 3'd1 : 3'd0);
            if (go_e) begin
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
                    end else if (w_s != c_s1[w_c]) begin
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
    wire w_step = issue && w_seg_last && w_s == c_s1[w_c];
    always @(posedge gclk) begin
        if (go_e) begin
            fF0 <= f0_go; fF1 <= f1_go; nA <= sbf(4'd0, 2'd3, nu_p, base_go); nB <= sbf(4'd1, 2'd3, nu_p, base_go);
            wA <= f0_go; wB <= f1_go;
        end else begin
            if (n_rst) begin nA <= sbf(4'd0, 2'd3, nu_p, base_live); nB <= sbf(4'd1, 2'd3, nu_p, base_live); end
            else if (n_step && n_nx[UW-1] && n_nx[UW-2 -: 3] != n_q) begin
                nA <= nB; nB <= nQ2;
            end
            if (w_restart) begin wA <= fF0; wB <= fF1; end
            else if (w_step && w_nx[UW-1] && w_nx[UW-2 -: 3] != w_q) begin
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
        assign w_tree = {w_pos[0], w_s};
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
    always @(posedge gclk) begin
        i1_q0 <= use_hi ? f_q1[f_rd] : f_q0[f_rd];
        i1_e0 <= use_hi ? f_e1[f_rd] : f_e0[f_rd];
        i1_q1 <= f_q1[f_rd]; i1_e1 <= f_e1[f_rd];
        i1_t <= {w_cnt, w_pos, w_tree, w_b == 3'd0, w_b == 3'd7, w_b == 3'd7 && w_lastu && w_seg_last,
                 !w_bf && (w_fp4 ? hv[0] : 1'b1), !w_bf && w_fp4 && hv[1], w_fp4};
        i1_bf <= w_bf; i1_bk <= a_ctr[0];
        i2x_bf <= i1_bf; i2x_bk <= i1_bk;
        i2x_q0 <= i1_q0; i2x_e0 <= i1_e0; i2x_q1 <= i1_q1; i2x_e1 <= i1_e1; i2x_t <= i1_t;
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
    genvar mb;
    generate for (mb = 0; mb < NB; mb = mb + 1) begin : g_mac
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
        always @(posedge gclk) begin
            if (i2x_v && !i2x_bk) cap0 <= rd0;
            if (i2x_v && i2x_bk) cap1 <= rd1;
        end
        assign cap = i2_bk ? cap1 : cap0;
        reg bk_h;
        always @(posedge gclk) if (i2_v) bk_h <= i2_bk;
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
    wire [255:0] w0q = t_fp4 ? nib(cap[127:0]) : cap[255:0];
    wire [7:0]   w0e = t_fp4 ? cap[135:128] : cap[263:256];
    wire [255:0] w1q = nib(cap[263:136]);
    wire [7:0]   w1e = cap[271:264];
    wire signed [9:0] we0 = $signed({2'b00, w0e}) - 10'sd127;
    wire signed [9:0] we1 = $signed({2'b00, w1e}) - 10'sd127;

    // ---------------- lanes --------------------------------------------------------------------------------------
    wire l0_v, l1_v, l0_f, l1_f;
    wire [31:0] l0_y, l1_y;
    wire [TW-1:0] l0_t, l1_t;
    if (FAST != 0) begin : g_l2
        ot_v41_bterm2_w10 #(.TW(TW)) u_l0 (.clk(gclk), .rst_n(rst_n), .v(i2_v && i2_t[2]), .fp4(t_fp4),
            .xq(i2_q0), .xe(i2_e0), .wq(w0q), .we(we0), .tag(i2_t), .ov(l0_v), .y(l0_y), .f(l0_f), .otag(l0_t));
        ot_v41_bterm2_w10 #(.TW(TW)) u_l1 (.clk(gclk), .rst_n(rst_n), .v(i2_v && i2_t[1]), .fp4(1'b1),
            .xq(i2_q1), .xe(i2_e1), .wq(w1q), .we(we1), .tag(i2_t), .ov(l1_v), .y(l1_y), .f(l1_f), .otag(l1_t));
    end else begin : g_l1
        ot_v41_bterm #(.TW(TW)) u_l0 (.clk(gclk), .rst_n(rst_n), .v(i2_v && i2_t[2]), .fp4(t_fp4),
            .xq(i2_q0), .xe(i2_e0), .wq(w0q), .we(we0), .tag(i2_t), .ov(l0_v), .y(l0_y), .f(l0_f), .otag(l0_t));
        ot_v41_bterm #(.TW(TW)) u_l1 (.clk(gclk), .rst_n(rst_n), .v(i2_v && i2_t[1]), .fp4(1'b1),
            .xq(i2_q1), .xe(i2_e1), .wq(w1q), .we(we1), .tag(i2_t), .ov(l1_v), .y(l1_y), .f(l1_f), .otag(l1_t));
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
        always @(posedge gclk or negedge rst_n) begin
            if (!rst_n) begin hv <= 1'b0; hk <= '0; end
            else if (i2_v && i2_bf) begin hv <= 1'b1; hk <= '0; end
            else if (hv) begin hk <= hk + 1'b1; if (hk == KLAST) hv <= 1'b0; end
        end
        always @(posedge gclk) if (i2_v && i2_bf) begin if (PP == 0) hw_ <= cap[255:0]; ht <= i2_t; end
        // product pipe tag: {slot, first, last, position, tree, final}
        localparam integer PW_ = HW + 2 + TG + 1;
        // chain slot = 4 x (word in round) + k (the word index is the tag's slot field, < NCH / 4)
        wire [HW-1:0] pslot = {ht[TW-1-KW -: HW-KW], hk};
        // the segment's final base node is the LAST 4-chunk node of its last unit (k = 3)
        wire [PW_-1:0] pt_in = {pslot, ht[5], ht[4], ht[TW-HW-1 -: TG], ht[3] && hk == KLAST};
        wire [PW_-1:0] pt;
        // the lane select is registered (hv_r, wl_r, xl_r) before the multipliers
        ot_hdc_delay #(.W(PW_), .D(6)) u_mt (.clk(gclk), .rst_n(rst_n), .d(pt_in), .q(pt));
        reg [5:0] mvp;
        reg hv_r;
        always @(posedge gclk or negedge rst_n) if (!rst_n) begin mvp <= 6'd0; hv_r <= 1'b0; end
            else begin mvp <= {mvp[4:0], hv}; hv_r <= hv; end
        assign m_v = mvp[5];
        assign {m_slot, m_first, m_last, m_tag} = pt;
        genvar mm;
        for (mm = 0; mm < BPN; mm = mm + 1) begin : g_mul
            reg [15:0] wl, xl;
            always @(posedge gclk) begin wl <= hwv[16 * (BPN * hk + mm) +: 16]; xl <= hx_sh[16 * (BPN * hk + mm) +: 16]; end
            ot_hdc_bmul u_m (.clk(gclk), .rst_n(rst_n), .v(hv_r), .a({wl, 16'd0}), .b({xl, 16'd0}),
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
    if (FAST != 0) begin : g_ch2
    ot_v41_chain2 #(.NCH(NCH), .TW(TG + 1), .CUT(CUT)) u_c0 (.clk(gclk), .rst_n(rst_n), .v(ci0_v),
        .slot(ci_slot), .first(ci_first), .last(ci_last), .term(ci0_y), .term_f(ci0_f),
        .tag(ci_tag), .ov(c0_v), .osum(c0_s), .of(c0_f), .otag(c0_t), .fault(c0_fault));
    ot_v41_chain2 #(.NCH(NCH), .TW(TG + 1), .CUT(CUT)) u_c1 (.clk(gclk), .rst_n(rst_n), .v(ci1_v),
        .slot(ci1_slot), .first(ci1_first), .last(ci1_last), .term(ci1_y), .term_f(ci1_f),
        .tag(ci1_tag), .ov(c1_v), .osum(c1_s), .of(c1_f), .otag(c1_t), .fault(c1_fault));
    end else begin : g_ch1
    ot_v41_chain #(.NCH(NCH), .TW(TG + 1)) u_c0 (.clk(gclk), .rst_n(rst_n), .v(ci0_v),
        .slot(ci_slot), .first(ci_first), .last(ci_last), .term(ci0_y), .term_f(ci0_f),
        .tag(ci_tag), .ov(c0_v), .osum(c0_s), .of(c0_f), .otag(c0_t), .fault(c0_fault));
    ot_v41_chain #(.NCH(NCH), .TW(TG + 1)) u_c1 (.clk(gclk), .rst_n(rst_n), .v(ci1_v),
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
        ot_v41_chain2 #(.NCH(NCH), .TW(TG + 1), .CUT(CUT)) u_c2 (.clk(gclk), .rst_n(rst_n), .v(m_v),
            .slot(m_slot), .first(m_first), .last(m_last), .term(m_y[2]), .term_f(m_f[2]),
            .tag(m_tag), .ov(c2_v), .osum(c2_s), .of(c2_f), .otag(c2_t), .fault(c2_fault));
        ot_v41_chain2 #(.NCH(NCH), .TW(TG + 1), .CUT(CUT)) u_c3 (.clk(gclk), .rst_n(rst_n), .v(m_v),
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
        ot_v41_fadd #(.CUT(CUT)) u_pair (.clk(gclk), .rst_n(rst_n), .valid_in(both), .a(c0_s), .b(c1_s),
            .y(pr_sum), .err(pr_err), .valid_out(pr_vo));
    end else begin : g_pa1
        ot_fp32_add_rne_pipe u_pair (.clk(gclk), .rst_n(rst_n), .valid_in(both), .a(c0_s), .b(c1_s),
            .y(pr_sum), .err(pr_err), .valid_out(pr_vo));
    end
    ot_hdc_delay #(.W(32), .D(LAT)) u_pp (.clk(gclk), .rst_n(rst_n), .d(one), .q(pr_pass));
    wire [TG+2:0] pr_t;   // {position, tree, final, both, err}
    ot_hdc_delay #(.W(TG + 3), .D(LAT)) u_pt (.clk(gclk), .rst_n(rst_n),
        .d({ct, both, both ? (c0_f | c1_f) : one_f}), .q(pr_t));
    reg [LAT-1:0] pr_vp;
    always @(posedge gclk or negedge rst_n)
        if (!rst_n) pr_vp <= '0; else pr_vp <= {pr_vp[LAT-2:0], any};
    wire        q_v = pr_vp[LAT-1];
    wire [31:0] q_val = pr_t[1] ? pr_sum : pr_pass;
    wire        q_err = pr_t[0] | (pr_t[1] && pr_err != 2'd0);
    if (BP == 1) begin : g_bp4
        // chunks 4k+2 + 4k+3 (golden level 1), then (4k + 4k+1) + (4k+2 + 4k+3) (level 2)
        wire [31:0] pb_sum, l2_sum;
        wire [1:0]  pb_err, l2_err;
        wire        pb_vo, l2_vo;
        ot_v41_fadd #(.CUT(CUT)) u_pairb (.clk(gclk), .rst_n(rst_n), .valid_in(c2_v && c3_v), .a(c2_s), .b(c3_s),
            .y(pb_sum), .err(pb_err), .valid_out(pb_vo));
        wire pbe;
        ot_hdc_delay #(.W(1), .D(LAT)) u_pbe (.clk(gclk), .rst_n(rst_n), .d(c2_f | c3_f), .q(pbe));
        wire l2_in = fam && q_v;
        ot_v41_fadd #(.CUT(CUT)) u_l2 (.clk(gclk), .rst_n(rst_n), .valid_in(l2_in), .a(q_val), .b(pb_sum),
            .y(l2_sum), .err(l2_err), .valid_out(l2_vo));
        wire [TG+1:0] l2t;
        ot_hdc_delay #(.W(TG + 2), .D(LAT)) u_l2t (.clk(gclk), .rst_n(rst_n),
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
        ot_v41_bf16_lanes2 #(.NCHB(NCHB), .TRW(TG), .CUT(CUT)) u_bf (.clk(gclk), .rst_n(rst_n), .v(i2_v && i2_bf),
            .w(cap[255:0]), .x(i2_q0), .slot(i2_t[TW-HW +: $clog2(NCHB)]), .first(i2_t[5]), .last(i2_t[4]),
            .tree(i2_t[TW-HW-1 -: TG]), .final_i(i2_t[3]), .ov(bf_v), .oval(bf_val), .otree(bf_tree),
            .ofinal(bf_final), .oerr(bf_err), .fault(b_fault));
        end else begin : g_s
        ot_v41_bf16_lanes #(.NCHB(NCHB), .TRW(TG)) u_bf (.clk(gclk), .rst_n(rst_n), .v(i2_v && i2_bf),
            .w(cap[255:0]), .x(i2_q0), .slot(i2_t[TW-HW +: $clog2(NCHB)]), .first(i2_t[5]), .last(i2_t[4]),
            .tree(i2_t[TW-HW-1 -: TG]), .final_i(i2_t[3]), .ov(bf_v), .oval(bf_val), .otree(bf_tree),
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
    if (FAST != 0) begin : g_tr2
    ot_v41_segtree2 #(.CUT(CUT), .NT(NSEG << (MTP != 0 ? 1 : 0)), .LV(LV), .EARLY(EARLY), .QD(BP != 0 ? 16 : 8)) u_tree (.clk(gclk), .rst_n(rst_n), .in_v(b_v),
        .in_tree(b_tree), .in_pos(b_pos), .in_val(b_val), .in_final(b_final), .in_err(b_err),
        .ov(t_v), .otree(t_tree), .opos(t_pos), .oval(t_val), .oerr(t_err), .fault(t_fault));
    end else begin : g_tr1
    ot_v41_segtree #(.NT(NSEG << (MTP != 0 ? 1 : 0)), .LV(LV), .EARLY(EARLY)) u_tree (.clk(gclk), .rst_n(rst_n), .in_v(b_v),
        .in_tree(b_tree), .in_pos(b_pos), .in_val(b_val), .in_final(b_final), .in_err(b_err),
        .ov(t_v), .otree(t_tree), .opos(t_pos), .oval(t_val), .oerr(t_err), .fault(t_fault));
    end
    reg o_v, o_err;
    reg [31:0] o_val;
    reg [15:0] o_row;
    reg [4:0] o_seg, o_n;
    reg [2:0] o_pos;
    wire [SW-1:0] t_seg = t_tree[SW-1:0];
    always @(posedge gclk or negedge rst_n) begin
        if (!rst_n) o_v <= 1'b0;
        else o_v <= t_v && !s_row[mb * NSEG + t_seg][15];   // row bit 15: an idle half of a pair emits nothing
    end
    always @(posedge gclk) begin
        o_val <= t_val; o_row <= s_row[mb * NSEG + t_seg]; o_seg <= s_idx[t_seg]; o_n <= s_n[t_seg]; o_err <= t_err;
        o_pos <= (MTP != 0) ? t_pos : 3'd0;
    end
    assign pv[mb] = o_v; assign pval[32*mb +: 32] = o_val; assign prow[16*mb +: 16] = o_row;
    assign pseg[5*mb +: 5] = o_seg; assign pnseg[5*mb +: 5] = o_n; assign perr[mb] = o_err;
    assign ppos[3*mb +: 3] = o_pos;
    assign bk_fault[mb] = c0_fault | c1_fault | c2_fault | c3_fault | t_fault | b_fault;
    end endgenerate
    assign busy = w_run | i1_v | i2_v | drain != 8'd0;
    assign walk_busy = w_run | n_run | bn_run | i1_v | i2_v | (BP != 0 && bp_hold != 3'd0);
    // slot field of the tag is HW bits; BF16 chains use its low log2(NCHB) bits (words per round <= NCHB)
endmodule


// ot_v41_walk_w10 with the sub-block facts precomputed (FAST): live (classes with units in sub-block q), livq1 (in
// sub-block q + 1) and cur (units of each class in sub-block q) come from registers.
module ot_v41_walk2_w10 #(parameter integer N = 4) (
    input  wire [2:0] q,
    input  wire [2:0] b,
    input  wire [$clog2(N)-1:0] c,
    input  wire [2:0] j,
    input  wire [N-1:0] live,
    input  wire [N-1:0] livq1,
    input  wire [4*N-1:0] cur,
    input  wire [2:0] qlast,
    output reg  [1+3+3+$clog2(N)+3-1:0] nx
);
    localparam integer SW = $clog2(N);
    reg [SW-1:0] nc, fc;
    reg nf, ff;
    reg [N-1:0] livn;
    reg [3:0] curc;
    integer k;
    always @* begin
        curc = cur[4*c +: 4];
        livn = (b == 3'd7) ? livq1 : live;
        nf = 1'b0; nc = '0;
        for (k = N - 1; k >= 0; k = k - 1) if (live[k] && k > c) begin nc = k[SW-1:0]; nf = 1'b1; end
        ff = 1'b0; fc = '0;
        for (k = N - 1; k >= 0; k = k - 1) if (livn[k]) begin fc = k[SW-1:0]; ff = 1'b1; end
        if ({1'b0, j} + 4'd1 < curc)             nx = {1'b1, q, b, c, j + 3'd1};
        else if (nf)                             nx = {1'b1, q, b, nc, 3'd0};
        else if (b == 3'd7 && q == qlast)        nx = '0;
        else                                     nx = {1'b1, (b == 3'd7) ? q + 3'd1 : q, b + 3'd1, fc, 3'd0};
    end
endmodule


// first live class
module ot_v41_first_w10 #(parameter integer N = 4) (
    input  wire [N-1:0] live,
    output reg  [$clog2(N)-1:0] c,
    output reg  ok
);
    integer k;
    always @* begin
        c = '0; ok = 1'b0;
        for (k = N - 1; k >= 0; k = k - 1) if (live[k]) begin c = k[$clog2(N)-1:0]; ok = 1'b1; end
    end
endmodule

// next (q, b, class, unit) of the element's round walk: next unit of the class, else the next live class of
// the sub-block, else the next round (b, then sub-block q), else done (run = 0).  A class of nu units has
// min(8, nu - 8q) units in sub-block q.
module ot_v41_walk_w10 #(parameter integer N = 4) (
    input  wire [2:0] q,
    input  wire [2:0] b,
    input  wire [$clog2(N)-1:0] c,
    input  wire [2:0] j,
    input  wire [7*N-1:0] nu,
    input  wire [N-1:0] base,
    input  wire [2:0] qlast,
    input  wire [1:0] sbs,              // log2 units per sub-block (3: 8 units; 1: 2 units)
    output reg  [1+3+3+$clog2(N)+3-1:0] nx
);
    localparam integer SW = $clog2(N);
    reg [SW-1:0] nc, fc;
    reg nf, ff;
    reg [2:0] nq;
    reg [6:0] rem, q8, nq8;
    reg [3:0] cur;
    reg [N-1:0] live, livn;
    integer k;
    always @* begin
        q8 = {4'd0, q} << sbs;
        nq = (b == 3'd7) ? q + 3'd1 : q;
        nq8 = {4'd0, nq} << sbs;
        cur = 4'd0;
        for (k = 0; k < N; k = k + 1) begin
            rem = (nu[7*k +: 7] > q8) ? nu[7*k +: 7] - q8 : 7'd0;
            live[k] = base[k] && rem != 7'd0;
            if (k == c) cur = (rem > (7'd1 << sbs)) ? (4'd1 << sbs) : rem[3:0];
            livn[k] = base[k] && nu[7*k +: 7] > nq8;
        end
        nf = 1'b0; nc = '0;
        for (k = N - 1; k >= 0; k = k - 1) if (live[k] && k > c) begin nc = k[SW-1:0]; nf = 1'b1; end
        ff = 1'b0; fc = '0;
        for (k = N - 1; k >= 0; k = k - 1) if (livn[k]) begin fc = k[SW-1:0]; ff = 1'b1; end
        if ({1'b0, j} + 4'd1 < cur)              nx = {1'b1, q, b, c, j + 3'd1};
        else if (nf)                             nx = {1'b1, q, b, nc, 3'd0};
        else if (b == 3'd7 && q == qlast)        nx = '0;
        else                                     nx = {1'b1, nq, b + 3'd1, fc, 3'd0};
    end
endmodule
