`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Matrix-vector engine of the DeepSeek-V4.1 hardwired decode core: the reduced
// Qwen3 core's ot_hdc_matvec (rtl/hdc/ot_hdc_matvec.sv, whose header follows)
// plus HEAD GROUPS for KV-sourced ops, which the Qwen3 core does not use.  With
// i_hg = 0 every address, mask and step below is ot_hdc_matvec's.
//
// HEAD GROUPS (wsrc = 1, i_hg = hg, H = 2^hg).  The G groups form H head groups
// of G/H groups each: group g = h*(G/H) + q is tile q of the round in head
// group h.  Every head group reads the SAME KV words (tile t = r*(G/H) + q)
// and its own x (x element + h*xcs), and writes its own results (word
// + h*ogs).  A round covers G/H tiles of W rows, not G.  Attention at a short
// context (W rows or fewer) thus keeps every group busy on its own heads
// instead of leaving G-1 groups masked.  The arithmetic of every output is
// unchanged: the same products, in the same order.
//
// Matrix-vector engine of the hardwired decode core.
//
// G groups of W lanes.  Each lane is a pipelined multiply feeding a pipelined
// FP32 add, and holds IL outputs in flight: the sum circulates back after
// exactly IL cycles (adder latency 5 plus IL-5 delay), so each output
// accumulates its products strictly in order -- (((0 + w0 x0) + w1 x1) + ...)
// -- while the lane retires one multiply-accumulate per cycle.  No accumulator
// file and no stall: the issue loop never waits, because weights come from a
// ROM (or the KV SRAM) at a fixed latency.
//
// K-SPLIT.  A matrix with few rows cannot fill G*W*IL output slots.  With
// split S = 2^split, group g = q*S + c takes contiguous K chunk c (length
// kc = i_k) of tile t = r*(G/S) + q, and a pipelined pairwise tree adds the S
// chunk sums, ((c0 + c1) + (c2 + c3)).  The order is fixed by the program and
// specified in tools/hdc_golden.py (matvec, split_for).
//
// Element order: round r, then k, then slot j.  Lane l of group g multiplies
// lane g*W+l of weight word  wbase + r*ts + k*ks + (j >> jsh)*js  by x element
// xbase + c*xcs + k*xks + j*xjs  (BF16-rounded, RNE, when `round`), and after
// the last k output port q writes lane l of word  obase + t*ots + j*ojs.  A lane
// is valid when (t*IL + j)*W + l < nout (mmode 0: rows) or t*W + l < nout
// (mmode 1: every slot its own vector -- one attention head per slot).
//
// MULTIPLIERS.  Every product is BF16 x BF16: ROM weights times BF16-rounded
// x, and (KV-sourced ops) the BF16 KV cache times BF16-rounded q or
// probabilities.  Every lane therefore has the exact BF16 multiplier
// (ot_hdc_bmul), and KV-sourced ops spread over all groups: group g takes
// tile r*G + g through its own KV port.
//
// LANE MULTIPLIER (MP, multi-token prediction).  Every lane, its split tree,
// its result port and the argmax are replicated MP times; copy p serves
// position slot p of an op with i_m > p: it reads its x at + p*i_xps
// (elements) and writes at + p*i_ops (words).  The weight (or KV) word is read
// ONCE per element and broadcast to the copies, so one ROM read serves i_m
// positions.  Each copy's arithmetic is the one-position engine's.  MP = 1 is
// the one-position engine, port for port.
//
// Timing from an issue cycle c: memories return at c+1, operands are captured
// at c+2 and conditioned at c+3, products leave at c+8, sums at c+13, the
// split tree adds 6 per level (5 in the adder, 1 output register), and a result
// is written one cycle later.
//
// FUSED DRAFT HEAD (successor, tools/dsrom_fused_draft_head.py; selected only with --fused-head, the as-built
// file is unchanged).  An op with i_oacc set adds, to every result, the vector-memory word at the result's OWN
// output address (read through the ra port when the result leaves the split tree), sum = fadd(addend, result),
// one RNE binary32 add exactly as the stream unit's AD_C add it replaces; the sum, not the result, feeds the
// argmax tree and the (optional) write.  The DSpark draft step uses it for logits = lm_head(h) + Markov(e):
// the lm_head op writes LG, the Markov op (oacc, amax) adds LG and takes the argmax on its own output
// stream -- no vocab-length stream-unit add, no vocab-length XU SELECT.  With i_iwe the argmax index of copy p
// is written (as a uint32 element) at element i_iaddr + p once the op has drained, which is where the next
// draft row's Markov gather reads it.  A fused op's results leave DF = 7 cycles later (addend read 2 + add 5);
// the engine takes no other op until a fused op has drained (ready), so results never overlap.  Every
// non-fused op is cycle- and bit-identical to the as-built engine.  Copy p of a multi-position op (i_m) adds
// its own output word (+ p*ops) and writes its own index, so a batched head (L2) composes unchanged.
// ---------------------------------------------------------------------------
module ot_hdc_v41_matvec #(
    parameter integer W  = 16,
    parameter integer G  = 4,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer MP = 1            // lane multiplier: positions per weight read
) (
    input  wire              clk,
    input  wire              rst_n,
    // instruction
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_tiles,     // rounds
    input  wire [NW-1:0]     i_k,         // k per chunk
    input  wire              i_wsrc,      // 0 weight ROM, 1 KV SRAM (both BF16 values)
    input  wire [AW-1:0]     i_wbase,
    input  wire [AW-1:0]     i_ts,
    input  wire [AW-1:0]     i_ks,
    input  wire [AW-1:0]     i_js,
    input  wire [AW-1:0]     i_xbase,
    input  wire [AW-1:0]     i_xks,
    input  wire [AW-1:0]     i_xjs,
    input  wire [AW-1:0]     i_xcs,
    input  wire [2:0]        i_jsh,
    input  wire [1:0]        i_split,
    input  wire [1:0]        i_hg,        // head groups 2^hg (KV-sourced ops)
    input  wire [AW-1:0]     i_ogs,       // result word stride per head group
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase,
    input  wire [AW-1:0]     i_ots,
    input  wire [AW-1:0]     i_ojs,
    input  wire              i_mmode,
    input  wire              i_oen,
    input  wire              i_amax,
    input  wire              i_oacc,      // FUSED: result += vector-memory word at its own output address
    input  wire              i_iwe,       // FUSED: write the argmax index (copy p at i_iaddr + p)
    input  wire [AW-1:0]     i_iaddr,
    input  wire [2:0]        i_m,         // positions served (0 = 1)
    input  wire [AW-1:0]     i_xps,       // x element stride per position
    input  wire [AW-1:0]     i_ops,       // result word stride per position
    // weight ROM: G*W bf16 lanes per word
    output reg               wrom_re,
    output reg  [AW-1:0]     wrom_addr,
    input  wire [G*W*16-1:0] wrom_q,
    // KV SRAM: one port per group, W lanes (BF16 values in 32-bit words) per word
    output reg               kv_re,
    output reg  [G*AW-1:0]   kv_addr,
    input  wire [G*W*32-1:0] kv_q,
    // x reads (vector memory, element), one port per group and position copy
    output reg  [MP*G-1:0]      x_re,
    output reg  [MP*G*AW-1:0]   x_addr,
    input  wire [MP*G*32-1:0]   x_q,
    // result words, one port per group and position copy
    output reg                  ov,          // a result round-slot (whether or not written)
    output reg  [MP*G-1:0]      o_we,
    output reg  [MP*G*AW-1:0]   o_addr,
    output reg  [MP*G*W-1:0]    o_mask,
    output reg  [MP*G*W*32-1:0] o_data,
    // FUSED: addend word reads, one port per group and position copy (the result ports' twin)
    output reg  [MP*G-1:0]      ra_re,
    output reg  [MP*G*AW-1:0]   ra_addr,
    input  wire [MP*G*W*32-1:0] ra_q,
    // argmax, per position copy
    output reg  [MP*NW-1:0]     am_idx,
    output reg  [MP*32-1:0]     am_val,
    output reg  [MP-1:0]        am_any,
    // result slots the latest accepted instruction has produced
    output reg  [15:0]       progress,
    output reg               fault
);
    localparam integer LW = $clog2(W);
    localparam integer LG = $clog2(G);
    localparam integer FB = IL - 5;       // circulation delay after the adder
    localparam integer TL = 6;            // split-tree cycles per level: 5 in the adder + 1 output register
    localparam integer OD = TL * LG;      // split tree

    // -- issue loop -----------------------------------------------------------
    integer gi;
    reg              active;
    reg [NW-1:0]     nout_r, tiles_r, k_r;
    reg              wsrc_r, round_r, oen_r, amax_r, mmode_r;
    reg [1:0]        split_r, hg_r;
    reg [AW-1:0]     ogs_r;
    reg [2:0]        m_r;
    reg [AW-1:0]     xps_r, ops_r;
    reg [AW-1:0]     tstep_r;          // weight step per round: ts, or G*ts for KV ops (tile r*G + g)
    reg [AW-1:0]     ts_r, ks_r, js_r, xks_r, xjs_r, xcs_r, ots_r, ojs_r;
    reg [2:0]        jsh_r;
    reg [NW-1:0]     t, k;
    reg [$clog2(IL)-1:0] j;
    reg [AW-1:0]     cur, base_k, base_t, xk, xc, xk_base, oa, ot, ot_step;
    reg [NW:0]       nb, nb_t, nb_step;    // first row of the current slot / round (port 0)
    reg [NW:0]       lb, lb_step;          // first lane-vector index of the round (mmode 1)
    reg              t_last, k_last;
    wire             j_last = (j == IL - 1);
    // tiles one round covers: G/S for ROM ops, G/H for KV ops
    wire [LG:0]      per_round = G >> (i_wsrc ? i_hg : i_split);

    reg              fus_busy;         // a fused op is in flight: no other op until it drains
    reg              oacc_r, iwe_r;
    reg [AW-1:0]     iaddr_r;
    reg              iw_pend;
    wire             drained, iw_go;
    assign ready = !active && !fus_busy;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0;
            wrom_re <= 1'b0; kv_re <= 1'b0; x_re <= 0;
        end else if (!active) begin
            wrom_re <= 1'b0; kv_re <= 1'b0; x_re <= 0;
            if (go) begin
                active <= 1'b1;
                nout_r <= i_nout; tiles_r <= i_tiles; k_r <= i_k;
                wsrc_r <= i_wsrc; round_r <= i_round; oen_r <= i_oen; amax_r <= i_amax; oacc_r <= i_oacc;
                mmode_r <= i_mmode; split_r <= i_wsrc ? 2'd0 : i_split;
                hg_r <= i_wsrc ? i_hg : 2'd0; ogs_r <= i_ogs;
                ts_r <= i_ts; tstep_r <= i_wsrc ? (i_ts << (LG - i_hg)) : i_ts; ks_r <= i_ks; js_r <= i_js; jsh_r <= i_jsh;
                m_r <= (i_m == 3'd0) ? 3'd1 : i_m; xps_r <= i_xps; ops_r <= i_ops;
                xks_r <= i_xks; xjs_r <= i_xjs; xcs_r <= i_xcs; ots_r <= i_ots; ojs_r <= i_ojs;
                t <= 0; k <= 0; j <= 0;
                t_last <= (i_tiles == 1); k_last <= (i_k == 1);
                cur <= i_wbase; base_k <= i_wbase; base_t <= i_wbase;
                xk <= i_xbase; xc <= i_xbase; xk_base <= i_xbase;
                oa <= i_obase; ot <= i_obase; ot_step <= i_ots * per_round;
                nb <= 0; nb_t <= 0; nb_step <= per_round * (W * IL);
                lb <= 0; lb_step <= per_round * W;
            end
        end else begin
            // this cycle's element: (r, k, j) at `cur`
            wrom_re <= !wsrc_r; kv_re <= wsrc_r;
            wrom_addr <= cur;
            //: KV ops: group g = h*(G/H) + q takes tile r*(G/H) + q, its own word
            for (gi = 0; gi < G; gi = gi + 1) kv_addr[gi*AW +: AW] <= cur + (gi & ((G >> hg_r) - 1)) * ts_r;
            for (gi = 0; gi < MP; gi = gi + 1) x_re[gi*G +: G] <= {G{gi < m_r}};
            if (!j_last) begin
                j <= j + 1'b1; oa <= oa + ojs_r; nb <= nb + W; xc <= xc + xjs_r;
                //: the weight word advances once per 2^jsh slots
                if ((((j + 1'b1) >> jsh_r) << jsh_r) == (j + 1'b1)) cur <= cur + js_r;
            end else begin
                j <= 0; nb <= nb_t; oa <= ot;
                if (!k_last) begin
                    k <= k + 1'b1; k_last <= (k + 2 == k_r);
                    base_k <= base_k + ks_r; cur <= base_k + ks_r;
                    xk <= xk + xks_r; xc <= xk + xks_r;
                end else begin
                    k <= 0; k_last <= (k_r == 1);
                    xk <= xk_base; xc <= xk_base;
                    if (!t_last) begin
                        t <= t + 1'b1; t_last <= (t + 2 == tiles_r);
                        base_t <= base_t + tstep_r; base_k <= base_t + tstep_r; cur <= base_t + tstep_r;
                        ot <= ot + ot_step; oa <= ot + ot_step;
                        nb_t <= nb_t + nb_step; nb <= nb_t + nb_step; lb <= lb + lb_step;
                    end else begin
                        active <= 1'b0;
                    end
                end
            end
        end
    end
    // x address per group: chunk c = g mod S (ROM ops), head group h = g div (G/H) (KV ops)
    integer pi;
    always @(posedge clk) begin
        for (pi = 0; pi < MP; pi = pi + 1)
            for (gi = 0; gi < G; gi = gi + 1)
                x_addr[(pi*G + gi)*AW +: AW] <= xc + ((gi & ((1 << split_r) - 1)) + (gi >> (LG - hg_r))) * xcs_r +
                                                pi * xps_r;
    end

    // Tag of the element issued this cycle (registered alongside the address).
    reg          e_v, e_first, e_last, e_oen, e_amax, e_wsrc, e_round, e_mmode, e_fus;
    reg [1:0]    e_split, e_hg;
    reg [AW-1:0] e_ogs;
    reg [AW-1:0] e_oa, e_ots, e_ops;
    reg [2:0]    e_m;
    reg [NW:0]   e_nb, e_lb, e_rem;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) e_v <= 1'b0;
        else e_v <= active;
    end
    always @(posedge clk) begin
        e_first <= (k == 0); e_last <= k_last;
        e_oen <= oen_r; e_amax <= amax_r; e_wsrc <= wsrc_r; e_round <= round_r; e_mmode <= mmode_r;
        e_fus <= oacc_r;
        e_split <= split_r; e_hg <= hg_r; e_ogs <= ogs_r; e_oa <= oa; e_ots <= ots_r; e_nb <= nb; e_lb <= lb;
        e_rem <= {1'b0, nout_r};
        e_m <= m_r; e_ops <= ops_r;
    end

    // -- S1 (memories answer) -> S2 (capture) -> S3 (condition) -----------------
    localparam integer TW = 1 + 1 + 1 + 1 + 1 + 2 + AW + AW + 3 * (NW + 1) + 2 + AW + 3 + AW + 1;
    wire [TW-1:0] e_tag = {e_last, e_oen, e_amax, e_wsrc, e_mmode, e_split, e_oa, e_ots, e_nb, e_lb, e_rem,
                           e_hg, e_ogs, e_m, e_ops, e_fus};
    reg  [TW-1:0] s1_tag, s1b_tag, s2_tag, s3_tag;
    reg          s1_v, s1b_v, s2_v, s3_v, s1_first, s1b_first, s2_first, s3_first;
    reg          s1b_wsrc, s1b_round;
    //: Memory read data is registered once as it arrives (MEM_PIPE): the
    //: weight word is 2,048 bits wide and its lanes span the whole engine, so a
    //: pin-to-lane wire gets a cycle of its own.
    reg [G*W*16-1:0] mq_wrom;
    reg [G*W*32-1:0] mq_kv;
    reg [MP*G*32-1:0] mq_x;
    reg          s1_wsrc, s1_round, s2_round, s3_wsrc;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 0; s1b_v <= 0; s2_v <= 0; s3_v <= 0; end
        else begin s1_v <= e_v; s1b_v <= s1_v; s2_v <= s1b_v; s3_v <= s2_v; end
    end
    reg [G*W*32-1:0] s2_w, s3_w;
    reg [MP*G*32-1:0] s2_x, s3_x;
    integer l;
    always @(posedge clk) begin
        s1_tag <= e_tag; s1b_tag <= s1_tag; s2_tag <= s1b_tag; s3_tag <= s2_tag;
        s1_first <= e_first; s1b_first <= s1_first; s2_first <= s1b_first; s3_first <= s2_first;
        s1_wsrc <= e_wsrc; s1_round <= e_round; s1b_wsrc <= s1_wsrc; s1b_round <= s1_round;
        s2_round <= s1b_round;
        mq_wrom <= wrom_q; mq_kv <= kv_q; mq_x <= x_q;
        s3_wsrc <= s2_tag[TW-4];
        for (l = 0; l < G * W; l = l + 1)
            s2_w[32*l +: 32] <= s1b_wsrc ? mq_kv[32*l +: 32] : {mq_wrom[16*l +: 16], 16'h0000};
        s2_x <= mq_x;
        s3_w <= s2_w;
        for (l = 0; l < MP * G; l = l + 1)
            s3_x[32*l +: 32] <= s2_round ? ((s2_x[32*l +: 32] + 32'h7FFF + {31'd0, s2_x[32*l + 16]}) & 32'hFFFF0000)
                                         : s2_x[32*l +: 32];
    end
    wire [TW-1:0] a_tag;
    ot_hdc_delay #(.W(TW), .D(10 + OD)) u_tag (.clk(clk), .rst_n(rst_n), .d(s3_tag), .q(a_tag));
    wire [10+OD:0] vline;
    ot_hdc_vline #(.D(10 + OD)) u_v (.clk(clk), .rst_n(rst_n), .v(s3_v), .vd(vline));
    wire [5:0] fl_first;
    ot_hdc_vline #(.D(5)) u_first (.clk(clk), .rst_n(rst_n), .v(s3_first && s3_v), .vd(fl_first));
    // split and KV flag reach the tree 10 cycles after S3
    wire [1:0] t_split;
    ot_hdc_delay #(.W(2), .D(10)) u_ts (.clk(clk), .rst_n(rst_n), .d(s3_tag[TW-6 -: 2]), .q(t_split));

    // result tag fields as the split tree delivers them (u_: the result's own cycle)
    wire          t_v = vline[10 + OD];
    wire          u_last, u_oen, u_amax, u_wsrc, u_mmode, u_fus;
    wire [1:0]    u_split, u_hg;
    wire [AW-1:0] u_ogs;
    wire [AW-1:0] u_oa, u_ots, u_ops;
    wire [2:0]    u_m;
    wire [NW:0]   u_nb, u_lb, u_nout;
    assign {u_last, u_oen, u_amax, u_wsrc, u_mmode, u_split, u_oa, u_ots, u_nb, u_lb, u_nout, u_hg, u_ogs, u_m,
            u_ops, u_fus} = a_tag;
    wire [LG:0]   u_tq = (G >> u_hg) - 1;
    wire [LG:0]   u_ports = G >> u_split;
    //: FUSED: a fused op's tag and valid wait DF cycles (addend read 2 + add 5); its results never share a
    //: cycle with another op's (ready holds the engine until it drains), so r_* select by the delayed valid
    localparam integer DF = 7;
    wire [TW-1:0] f_tag;
    ot_hdc_delay #(.W(TW), .D(DF)) u_ftag (.clk(clk), .rst_n(rst_n), .d(a_tag), .q(f_tag));
    wire [DF:0] fline;
    ot_hdc_vline #(.D(DF)) u_fv (.clk(clk), .rst_n(rst_n), .v(t_v && u_fus), .vd(fline));
    wire          f_v = fline[DF];
    wire          r_v = f_v || (t_v && !u_fus);
    wire          r_last, r_oen, r_amax, r_wsrc, r_mmode, r_fus;
    wire [1:0]    r_split, r_hg;
    wire [AW-1:0] r_ogs;
    wire [AW-1:0] r_oa, r_ots, r_ops;
    wire [2:0]    r_m;
    wire [NW:0]   r_nb, r_lb, r_nout;
    assign {r_last, r_oen, r_amax, r_wsrc, r_mmode, r_split, r_oa, r_ots, r_nb, r_lb, r_nout, r_hg, r_ogs, r_m,
            r_ops, r_fus} = f_v ? f_tag : a_tag;
    wire [LG:0]   r_tq = (G >> r_hg) - 1;         // tile-in-round mask of a port
    wire [LG:0]   r_ports = G >> r_split;
    reg  [G*W-1:0] r_mask;
    integer q, ql;
    always @(*) begin
        for (q = 0; q < G; q = q + 1)
            for (ql = 0; ql < W; ql = ql + 1)
                r_mask[q*W + ql] = (q < r_ports) &&
                    (r_mmode ? (r_lb + (q & r_tq) * W + ql < r_nout) : (r_nb + q * (W * IL) + ql < r_nout));
    end
    localparam integer LV = $clog2(G * W);
    reg  [LV:0] tv;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) tv <= 0;
        else tv <= {tv[LV-1:0], r_v && r_last && r_amax};
    end
    reg ov1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ov1 <= 1'b0;
        else ov1 <= r_v && r_last;
    end
    //: A second output register: the result bus is 2,048 bits wide per copy and its
    //: flops sit by the lanes, so the pins get flops of their own.  ov, and the
    //: chaining progress counted from it, move with the data.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ov <= 1'b0;
        else ov <= ov1;
    end
    wire [MP-1:0] mp_fault;
    genvar mp;
    generate for (mp = 0; mp < MP; mp = mp + 1) begin : g_mp
    // -- lanes -------------------------------------------------------------------
    wire [G*W*32-1:0] sum;
    wire [G*W-1:0]    lfault;
    genvar g, gl;
        for (g = 0; g < G; g = g + 1) begin : g_grp
            for (gl = 0; gl < W; gl = gl + 1) begin : g_lane
                localparam integer LI = g * W + gl;
                wire [31:0] prod, fb_pre, acc_in;
                reg  [31:0] acc_q;
                wire f0, f1;
                //: every product is BF16 x BF16 (weights, x rounded; BF16 KV, q and
                //: probabilities rounded), so every lane has the small exact multiplier
                ot_hdc_bmul u_mul (.clk(clk), .rst_n(rst_n), .v(s3_v),
                                   .a(s3_w[32*LI +: 32]), .b(s3_x[32*(mp*G + g) +: 32]), .y(prod), .fault(f0));
                // add input at c+8; the circulating sum from IL cycles earlier.
                //: The first-element select is made one cycle early into acc_q: the
                //: flag fans out to every lane bit (G*W*32 loads), and registering the
                //: mux gives its buffer tree a whole cycle instead of sharing one with
                //: the adder's alignment logic (me_iter11: -98 ps on this path).
                always @(posedge clk) acc_q <= fl_first[4] ? 32'd0 : fb_pre;
                assign acc_in = acc_q;
                ot_hdc_fadd u_add (clk, rst_n, vline[5], acc_in, prod,
                                   sum[32*LI +: 32], f1);
                ot_hdc_delay #(.W(32), .D(FB - 1)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum[32*LI +: 32]), .q(fb_pre));
                assign lfault[LI] = f0 | f1;
            end
        end

    // -- split tree: level L adds word pairs when split >= L, else delays ----------
    //: Each level ends in a register: the sum-or-held select fans out to every
    //: word bit, and unregistered it shared a cycle with the next level's
    //: exponent alignment (me_iter12: -91 ps on that path).
    wire [G*W*32-1:0] lvl [0:LG];
    wire [LG:0]       tfault;
    assign lvl[0] = sum;
    assign tfault[0] = 1'b0;
    wire [LG*2+1:0] split_at;                       // split at each level's input
    assign split_at[1:0] = t_split;
    genvar lv, p;
        for (lv = 1; lv <= LG; lv = lv + 1) begin : g_lvl
            wire [1:0] sp_sel;                      // split when the level's sums emerge
            ot_hdc_delay #(.W(2), .D(5)) u_sd (.clk(clk), .rst_n(rst_n), .d(split_at[2*lv-1 -: 2]), .q(sp_sel));
            reg  [1:0] sp_out;
            always @(posedge clk) sp_out <= sp_sel;
            assign split_at[2*lv+1 -: 2] = sp_out;
            wire [G*W*32-1:0] held;
            ot_hdc_delay #(.W(G*W*32), .D(5)) u_hold (.clk(clk), .rst_n(rst_n), .d(lvl[lv-1]), .q(held));
            wire [(G >> lv)*W-1:0] pf;
            reg  [G*W*32-1:0] lq;
            for (p = 0; p < (G >> lv) * W; p = p + 1) begin : g_add
                localparam integer PW = p / W, PL = p % W;
                wire [31:0] s_out;
                ot_hdc_fadd u_add (clk, rst_n, vline[10 + TL*(lv-1)] && (split_at[2*lv-1 -: 2] >= lv),
                                   lvl[lv-1][32*((2*PW)*W + PL) +: 32], lvl[lv-1][32*((2*PW+1)*W + PL) +: 32],
                                   s_out, pf[p]);
                always @(posedge clk) lq[32*p +: 32] <= (sp_sel >= lv) ? s_out : held[32*p +: 32];
            end
            if ((G >> lv) < G) begin : g_rest
                always @(posedge clk) lq[G*W*32-1 : (G >> lv)*W*32] <= held[G*W*32-1 : (G >> lv)*W*32];
            end
            assign lvl[lv] = lq;
            assign tfault[lv] = |pf;
        end
    wire [G*W*32-1:0] res_u = lvl[LG];
    //: FUSED: read the addend words at the result's own output address as it leaves the tree, hold the
    //: result 2 cycles to meet them, add (addend + result, the golden add's operand order), 5 cycles
    integer rq;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ra_re[mp*G +: G] <= 0;
        else
            for (rq = 0; rq < G; rq = rq + 1)
                ra_re[mp*G + rq] <= t_v && u_fus && u_last && (rq < u_ports) && (mp < u_m);
    end
    always @(posedge clk)
        for (rq = 0; rq < G; rq = rq + 1)
            ra_addr[(mp*G + rq)*AW +: AW] <= u_oa + (rq & u_tq) * u_ots + (rq >> (LG - u_hg)) * u_ogs + mp * u_ops;
    wire [G*W*32-1:0] res_h;
    ot_hdc_delay #(.W(G*W*32), .D(2)) u_rh (.clk(clk), .rst_n(rst_n), .d(res_u), .q(res_h));
    wire [1:0] hline;
    ot_hdc_vline #(.D(1)) u_hv (.clk(clk), .rst_n(rst_n), .v(t_v && u_fus && u_last), .vd(hline));
    reg ah_v;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ah_v <= 1'b0;
        else ah_v <= hline[1];
    end
    wire [G*W*32-1:0] fsum;
    wire [G*W-1:0]    ffault;
    for (g = 0; g < G * W; g = g + 1) begin : g_fadd
        ot_hdc_fadd u_add (clk, rst_n, ah_v, ra_q[(mp*G*W + g)*32 +: 32], res_h[32*g +: 32], fsum[32*g +: 32],
                           ffault[g]);
    end
    wire [G*W*32-1:0] res = f_v ? fsum : res_u;
    //: A status bit: registered in two levels (see ot_hdc_stream).
    reg [G:0] fault_q;
    integer fg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault_q <= 0;
        else begin
            for (fg = 0; fg < G; fg = fg + 1) fault_q[fg] <= |lfault[fg*W +: W];
            fault_q[G] <= |tfault || (|ffault);
        end
    end
    assign mp_fault[mp] = |fault_q;

    // -- results -------------------------------------------------------------------
    reg  [G-1:0]  o_we1;
    reg  [G*AW-1:0] o_addr1;
    reg  [G*W-1:0]  o_mask1;
    reg  [G*W*32-1:0] o_data1;
    integer qq;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) o_we1 <= 0;
        else
            for (qq = 0; qq < G; qq = qq + 1)
                o_we1[qq] <= r_v && r_last && r_oen && (qq < r_ports) && (mp < r_m);
    end
    always @(posedge clk) begin
        for (qq = 0; qq < G; qq = qq + 1)
            o_addr1[qq*AW +: AW] <= r_oa + (qq & r_tq) * r_ots + (qq >> (LG - r_hg)) * r_ogs + mp * r_ops;
        o_mask1 <= r_mask; o_data1 <= res;
    end
    //: FUSED: the argmax index write takes port 0 once the op has drained (no result write is in flight)
    wire [AW-1:0] iw_e = iaddr_r + mp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) o_we[mp*G +: G] <= 0;
        else if (iw_go) o_we[mp*G +: G] <= {{(G-1){1'b0}}, mp < m_r};
        else o_we[mp*G +: G] <= o_we1;
    end
    always @(posedge clk) begin
        if (iw_go) begin
            o_addr[mp*G*AW +: G*AW] <= {{((G-1)*AW){1'b0}}, iw_e >> LW};
            o_mask[mp*G*W +: G*W] <= {{(G*W-1){1'b0}}, 1'b1} << iw_e[LW-1:0];
            o_data[mp*G*W*32 +: G*W*32] <= {{(G*W-1){32'd0}}, {{(32-NW){1'b0}}, am_idx[mp*NW +: NW]}}
                                           << (32 * iw_e[LW-1:0]);
        end else begin
            o_addr[mp*G*AW +: G*AW] <= o_addr1; o_mask[mp*G*W +: G*W] <= o_mask1;
            o_data[mp*G*W*32 +: G*W*32] <= o_data1;
        end
    end

    // -- argmax: a registered compare tree over the round-slot, then a running best --
    // Keys order binary32 values as unsigned integers (zeros are canonical +0);
    // on equal keys the lower row wins, in the tree and across cycles.
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    localparam integer NL = G * W;
    //: The key is an invertible function of the value, so the tree carries only
    //: the key and recovers the value at the end (half the tree's wiring).
    localparam integer CW = 1 + 32 + NW;            // {valid, key, row}
    wire [CW*NL-1:0] alv [0:LV];
    genvar e;
        for (e = 0; e < NL; e = e + 1) begin : g_leaf
            localparam integer EQ = e / W, EL = e % W;
            reg [CW-1:0] c;
            //: sized on its own: an integer term would widen a concatenated sum
            wire [NW-1:0] row = r_nb[NW-1:0] + EQ * (W * IL) + EL;
            always @(posedge clk)
                c <= {r_mask[e], okey(res[32*e +: 32]), row};
            assign alv[0][CW*e +: CW] = c;
        end
        for (lv = 1; lv <= LV; lv = lv + 1) begin : g_alvl
            for (e = 0; e < (NL >> lv); e = e + 1) begin : g_node
                wire [CW-1:0] x0 = alv[lv-1][CW*(2*e) +: CW];
                wire [CW-1:0] x1 = alv[lv-1][CW*(2*e+1) +: CW];
                wire          x0_wins = x0[CW-1] && (!x1[CW-1] || x0[CW-2 -: 32] > x1[CW-2 -: 32] ||
                                        (x0[CW-2 -: 32] == x1[CW-2 -: 32] && x0[NW-1:0] < x1[NW-1:0]));
                reg  [CW-1:0] c;
                always @(posedge clk) c <= x0_wins ? x0 : x1;
                assign alv[lv][CW*e +: CW] = c;
            end
            if ((NL >> lv) < NL) begin : g_pad
                assign alv[lv][CW*NL-1 : CW*(NL >> lv)] = 0;
            end
        end
    wire [CW-1:0] top = alv[LV][CW-1:0];
    wire          top_v = top[CW-1];
    wire [31:0]   top_key = top[CW-2 -: 32];
    wire [31:0]   top_val = top_key[31] ? {1'b0, top_key[30:0]} : ~top_key;   // okey inverted
    wire [NW-1:0] top_idx = top[NW-1:0];
    reg [31:0] best_key;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            am_any[mp] <= 1'b0; am_idx[mp*NW +: NW] <= 0; am_val[mp*32 +: 32] <= 0; best_key <= 0;
        end else begin
            if (go && ready && i_amax) am_any[mp] <= 1'b0;
            else if (tv[LV] && top_v && (!am_any[mp] || top_key > best_key ||
                                         (top_key == best_key && top_idx < am_idx[mp*NW +: NW]))) begin
                am_any[mp] <= 1'b1; best_key <= top_key; am_idx[mp*NW +: NW] <= top_idx;
                am_val[mp*32 +: 32] <= top_val;
            end
        end
    end
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else fault <= |mp_fault;
    end

    // Chaining progress: each issued last-k element becomes one result slot,
    // in order, so the latest instruction has produced (slots out - slots
    // issued before its acceptance).
    reg [15:0] n_last_issued, n_ov, ov_mark;
    wire [15:0] ov_done = n_ov - ov_mark;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n_last_issued <= 0; n_ov <= 0; ov_mark <= 0; progress <= 0;
        end else begin
            n_last_issued <= n_last_issued + ((active && k_last) ? 16'd1 : 16'd0);
            n_ov <= n_ov + (ov ? 16'd1 : 16'd0);
            if (go && ready) begin
                ov_mark <= n_last_issued; progress <= 0;
            end else begin
                progress <= ov_done[15] ? 16'd0 : ov_done;
            end
        end
    end

    //: Registered: the OR of every valid bit is wide.  Cleared on the
    //: accepting edge so a just-issued op never reads as drained.
    assign drained = !active && !e_v && !s1_v && !s1b_v && !s2_v && !s3_v && !(|vline) && !(|tv) && !ov1 && !ov &&
                   !(|fline);
    // FUSED: hold the engine while a fused op drains; then write its argmax index (i_iwe)
    assign iw_go = iw_pend && drained;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fus_busy <= 1'b0; iw_pend <= 1'b0; iwe_r <= 1'b0; iaddr_r <= 0;
        end else if (go && ready) begin
            fus_busy <= i_oacc; iw_pend <= i_oacc && i_iwe; iwe_r <= i_iwe; iaddr_r <= i_iaddr;
        end else if (iw_go) begin
            iw_pend <= 1'b0;
        end else if (fus_busy && drained && !iw_pend && !(|o_we)) begin
            fus_busy <= 1'b0;
        end
    end
    wire idle_c = drained && !iw_pend && !(|o_we);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) idle <= 1'b1;
        else idle <= idle_c && !(go && ready);
    end
endmodule
