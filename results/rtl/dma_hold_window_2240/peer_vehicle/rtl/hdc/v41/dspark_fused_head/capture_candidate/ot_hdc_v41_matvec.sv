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
// draft row's Markov gather reads it.  A fused op's results leave DF = 2 + 5 cycles later (addend read 2 + add 5; FH_ALAT);
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
    parameter integer MP = 1,           // lane multiplier: positions per weight read
    parameter integer FAULT_RETIRE = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input wire fh_retire_busy,fh_warm_ack,fh_ov_retired,
    input wire fh_leaf_v_retired,
    input wire [MP*G*W*(1+32+NW)-1:0] fh_leaf_retired,
    output wire [MP*G*W*(1+32+NW)-1:0] fh_leaf,
    output wire [5+2+2*AW+3*(NW+1)+2+AW+3+AW+1-1:0] fh_tag,
    output wire fh_tag_v,
    output reg fh_leaf_v,fh_warm_emit,
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
    output wire [MP*G-1:0]      ra_re,
    output wire [MP*G*AW-1:0]   ra_addr,
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
    reg              iw_issued;
    wire             drained;
    reg              iw_go;
    reg              iw_go2, iw_go3;
    //: FH_MARGIN: one more index-write stage (the 64-lane select travels centre -> group -> lane)
    wire iw_write_go = FH_CAPTURE ? (FH_MARGIN ? iw_go3 : iw_go2) : iw_go;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin iw_go2 <= 1'b0; iw_go3 <= 1'b0; end
        else begin iw_go2 <= iw_go; iw_go3 <= iw_go2; end
    wire             iw_go_n;
    assign ready = !active && !fus_busy && (!FAULT_RETIRE || !fh_retire_busy);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0;
            wrom_re <= 1'b0; kv_re <= 1'b0; x_re <= 0;
        end else if (!active) begin
            wrom_re <= 1'b0; kv_re <= 1'b0; x_re <= 0;
            if (go && (!FAULT_RETIRE || ready)) begin
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
    //: FUSED: the tag line ends in a register of its own (a_tag_p is the tag one cycle early), so the fused
    //: head's selects are made a cycle ahead and registered: zero added cycles, the r_* fields start at flops
    wire [TW-1:0] a_tag_p;
    reg  [TW-1:0] a_tag;
    ot_hdc_delay #(.W(TW), .D(10 + OD - 1)) u_tag (.clk(clk), .rst_n(rst_n), .d(s3_tag), .q(a_tag_p));
    always @(posedge clk) a_tag <= a_tag_p;
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
    // the same fields one cycle early (p_: a_tag_p, valid vline[9 + OD])
    wire          t_v_p = vline[10 + OD - 1];
    wire          p_last, p_oen, p_amax, p_wsrc, p_mmode, p_fus;
    wire [1:0]    p_split, p_hg;
    wire [AW-1:0] p_ogs, p_oa, p_ots, p_ops;
    wire [2:0]    p_m;
    wire [NW:0]   p_nb, p_lb, p_nout;
    assign {p_last, p_oen, p_amax, p_wsrc, p_mmode, p_split, p_oa, p_ots, p_nb, p_lb, p_nout, p_hg, p_ogs, p_m,
            p_ops, p_fus} = a_tag_p;
    wire [LG:0]   p_tq = (G >> p_hg) - 1;
    wire [LG:0]   p_ports = G >> p_split;
    //: FUSED: a fused op's tag and valid wait DF cycles (addend read 2 + add 5); its results never share a
    //: cycle with another op's (ready holds the engine until it drains), so r_* select by the delayed valid
    //: FH_ALAT (+define+OT_FH_ALAT=n, default 7): 0 is the as-built five-stage ot_hdc_fadd (DF 7, does not
    //: close 1.2 GHz at SS); n = 5..7 is the bit-identical keep-prefix ot_hdc_fp32_add_lat #(n), DF = 2 + n.
    //: 7 is the closed configuration (results/rtl/dsrom_fh_close_20261004)
`ifdef OT_FH_ALAT
    localparam integer FH_ALAT = `OT_FH_ALAT;
`else
    localparam integer FH_ALAT = 7;
`endif
`ifdef OT_FH_CAPTURE
    localparam integer FH_CAPTURE = `OT_FH_CAPTURE;
`else
    localparam integer FH_CAPTURE = 0;
`endif
`ifdef OT_FH_MARGIN
    localparam integer FH_MARGIN = `OT_FH_MARGIN;
`else
    localparam integer FH_MARGIN = 0;
`endif
`ifdef OT_FH_RETURN_EXTRA
    localparam integer FH_RETURN_EXTRA = `OT_FH_RETURN_EXTRA;
`else
    localparam integer FH_RETURN_EXTRA = 0;
`endif
    localparam integer DF = 2 + FH_RETURN_EXTRA + FH_CAPTURE + ((FH_ALAT == 0) ? 5 : FH_ALAT);
    //: f_tag_p is the fused tag one cycle early; r_tag / r_v are f_v ? f_tag : a_tag and f_v || (t_v && !u_fus),
    //: selected a cycle ahead from the early taps and registered
    wire [TW-1:0] f_tag_p;
    ot_hdc_delay #(.W(TW), .D(DF - 1)) u_ftag (.clk(clk), .rst_n(rst_n), .d(a_tag), .q(f_tag_p));
    wire [DF:0] fline;
    ot_hdc_vline #(.D(DF)) u_fv (.clk(clk), .rst_n(rst_n), .v(t_v && u_fus), .vd(fline));
    wire          f_v = fline[DF];
    reg  [TW-1:0] r_tag;
    assign fh_tag=r_tag;
    assign fh_tag_v=r_v;
    reg           r_v;
    always @(posedge clk) r_tag <= fline[DF - 1] ? f_tag_p : a_tag_p;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) r_v <= 1'b0;
        else r_v <= fline[DF - 1] || (t_v_p && !p_fus);
    end
    wire          r_last, r_oen, r_amax, r_wsrc, r_mmode, r_fus;
    wire [1:0]    r_split, r_hg;
    wire [AW-1:0] r_ogs;
    wire [AW-1:0] r_oa, r_ots, r_ops;
    wire [2:0]    r_m;
    wire [NW:0]   r_nb, r_lb, r_nout;
    assign {r_last, r_oen, r_amax, r_wsrc, r_mmode, r_split, r_oa, r_ots, r_nb, r_lb, r_nout, r_hg, r_ogs, r_m,
            r_ops, r_fus} = r_tag;
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
        else if(FAULT_RETIRE) tv <= {tv[LV-1:1],fh_leaf_v_retired,1'b0};
        else tv <= {tv[LV-1:0], r_v && r_last && r_amax};
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin fh_leaf_v<=0;fh_warm_emit<=0;end
        else begin fh_leaf_v<=r_v&&r_last&&r_amax;fh_warm_emit<=iw_write_go;end
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
    //: FUSED: the addend read and add (ot_hdc_v41_fh_add, below)
    wire [G*W*32-1:0] fsum;
    wire [G*W-1:0]    ffault;
    ot_hdc_v41_fh_add #(.W(W), .G(G), .AW(AW), .MPI(mp), .ALAT(FH_ALAT), .CAPTURE(FH_CAPTURE), .RETURN_EXTRA(FH_RETURN_EXTRA), .TREE(FH_MARGIN)) u_fh (
        .clk(clk), .rst_n(rst_n), .t_v_p(t_v_p), .p_fus(p_fus), .p_last(p_last), .p_ports(p_ports), .p_m(p_m),
        .p_tq(p_tq), .p_hg(p_hg), .p_oa(p_oa), .p_ots(p_ots), .p_ogs(p_ogs), .p_ops(p_ops), .res_u(res_u),
        .ra_re(ra_re[mp*G +: G]), .ra_addr(ra_addr[mp*G*AW +: G*AW]), .ra_q(ra_q[mp*G*W*32 +: G*W*32]),
        .fsum(fsum), .ffault(ffault));
    wire [G*W-1:0] fused_lane_v;
    for (genvar fl=0; fl<G*W; fl=fl+1) begin : g_fused_select
        if (FH_CAPTURE) begin : g_local
            ot_hdc_v41_fh_kreg u_sel (.clk(clk), .rst_n(rst_n), .d(fline[DF-1]), .q(fused_lane_v[fl]));
        end else assign fused_lane_v[fl] = f_v;
    end
    wire [G*W*32-1:0] res;
    for (genvar rl=0; rl<G*W; rl=rl+1) begin : g_result_local
        assign res[32*rl+:32] = fused_lane_v[rl] ? fsum[32*rl+:32] : res_u[32*rl+:32];
    end
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
        else if (iw_write_go) o_we[mp*G +: G] <= {{(G-1){1'b0}}, mp < m_r};
        else o_we[mp*G +: G] <= o_we1;
    end
    //: the iw_go select of the 2,048-bit result bus: NIW kept copies of the iw_go flop (one per 4 lanes),
    //: each the same register (same input, same reset), so its fan-out is not one net (C7h: -4.5 ps SS)
    localparam integer IWG_LANES = FH_CAPTURE ? 1 : 4;
    localparam integer NIW = (G * W + IWG_LANES - 1) / IWG_LANES;
    wire [NIW-1:0] iwg;
    genvar ic;
    for (ic = 0; ic < NIW; ic = ic + 1) begin : g_iwg
        ot_hdc_v41_fh_kreg u_iwg (.clk(clk), .rst_n(rst_n), .d(FH_CAPTURE ? (FH_MARGIN ? iw_go2 : iw_go) : iw_go_n), .q(iwg[ic]));
    end
    wire [NW-1:0] index_local [0:W-1];
    wire [W-1:0] index_mask_local;
    for (genvar ix=0; ix<W; ix=ix+1) begin : g_index_prepare
        ot_hdc_v41_fh_indexreg #(.NW(NW),.LW(LW),.LANE(ix)) u_index (
            .clk(clk), .index_in(am_idx[mp*NW+:NW]), .lane_in(iw_e[LW-1:0]),
            .index_q(index_local[ix]), .mask_q(index_mask_local[ix]));
    end
    wire [G*W*32-1:0] iw_data_old = {{(G*W-1){32'd0}}, {{(32-NW){1'b0}}, am_idx[mp*NW +: NW]}} << (32 * iw_e[LW-1:0]);
    wire [G*W-1:0]    iw_mask_old = {{(G*W-1){1'b0}}, 1'b1} << iw_e[LW-1:0];
    wire [G*W*32-1:0] iw_data;
    wire [G*W-1:0] iw_mask;
    for (genvar ix=0; ix<G*W; ix=ix+1) begin : g_index_word
        if (FH_CAPTURE && ix<W) begin
            assign iw_data[32*ix+:32] = index_mask_local[ix] ? {{(32-NW){1'b0}}, index_local[ix]} : 32'b0;
            assign iw_mask[ix] = index_mask_local[ix];
        end else if (FH_CAPTURE) begin
            assign iw_data[32*ix+:32] = 32'b0;
            assign iw_mask[ix] = 1'b0;
        end else begin
            assign iw_data[32*ix+:32] = iw_data_old[32*ix+:32];
            assign iw_mask[ix] = iw_mask_old[ix];
        end
    end
    integer il, ia;
    always @(posedge clk) begin
        for (il = 0; il < G * W; il = il + 1) begin
            o_data[mp*G*W*32 + 32*il +: 32] <= iwg[il / IWG_LANES] ? iw_data[32*il +: 32] : o_data1[32*il +: 32];
            o_mask[mp*G*W + il] <= iwg[il / IWG_LANES] ? iw_mask[il] : o_mask1[il];
        end
        for (ia = 0; ia < G; ia = ia + 1)
            o_addr[(mp*G + ia)*AW +: AW] <= iwg[ia * W / IWG_LANES] ? ((ia == 0) ? (iw_e >> LW) : {AW{1'b0}})
                                                            : o_addr1[ia*AW +: AW];
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
            assign fh_leaf[mp*CW*NL+CW*e+:CW]=c;
            assign alv[0][CW*e+:CW]=FAULT_RETIRE?fh_leaf_retired[mp*CW*NL+CW*e+:CW]:c;
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
            n_ov <= n_ov + ((FAULT_RETIRE?fh_ov_retired:ov) ? 16'd1 : 16'd0);
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
                   !(|fline) && (!FAULT_RETIRE || !fh_retire_busy);
    // FUSED: hold the engine while a fused op drains; then write its argmax index (i_iwe)
    //: iw_go is iw_pend && drained, registered: while a fused op is pending no op is accepted, so every
    //: in-flight bit is a shift of a bit that is in flight now, and the argmax valid tv[LV] (the last to clear)
    //: is tv[LV-1] a cycle earlier: drained next cycle == drained_nx now (the as-built OR without tv[LV])
    wire drained_nx = !active && !e_v && !s1_v && !s1b_v && !s2_v && !s3_v && !(|vline) && !(|tv[LV-1:0]) &&
                      !ov1 && !ov && !(|fline) && (!FAULT_RETIRE || !fh_retire_busy);
    assign iw_go_n = iw_pend && !iw_go && !(FH_CAPTURE && iw_go2) && !(FH_CAPTURE && FH_MARGIN && iw_go3) && drained_nx && (!FAULT_RETIRE || !iw_issued);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) iw_go <= 1'b0;
        else iw_go <= iw_go_n;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fus_busy <= 1'b0; iw_pend <= 1'b0; iw_issued<=0; iwe_r <= 1'b0; iaddr_r <= 0;
        end else if (go && ready) begin
            fus_busy <= i_oacc; iw_pend <= i_oacc && i_iwe; iw_issued<=0; iwe_r <= i_iwe; iaddr_r <= i_iaddr;
        end else if (FAULT_RETIRE && iw_write_go) begin
            iw_issued<=1;
        end else if (FAULT_RETIRE ? fh_warm_ack : iw_write_go) begin
            iw_pend <= 1'b0; iw_issued<=0;
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

// ---------------------------------------------------------------------------
// ot_hdc_v41_fh_add: the FUSED draft head's addend read and add for one position copy (MPI) of
// ot_hdc_v41_matvec, factored out so it hardens as a unit.  Read the addend words at the result's own output
// address as it leaves the split tree, hold the result 2 cycles to meet them, add (addend + result, the golden
// add's operand order).  ALAT 0: the as-built five-stage ot_hdc_fadd; 5..7: ot_hdc_fp32_add_lat #(ALAT), bit for
// bit the same sum and fault (rtl/test/tb_w11_fp32_add_lat.sv).  fsum leaves 2 + latency cycles after t_v.
// ---------------------------------------------------------------------------
module ot_hdc_v41_fh_add #(
    parameter integer W = 16,
    parameter integer G = 4,
    parameter integer AW = 24,
    parameter integer MPI = 0,
    parameter integer ALAT = 0,
    parameter integer CAPTURE = 0,
    parameter integer RETURN_EXTRA = 0,
    // TREE (default 0; margin-first 1, needs CAPTURE and RETURN_EXTRA >= 2): the protected return valid
    // reaches the 64 lane capture registers through two kept copies per group (centre-to-group, group),
    // tapped two cycles earlier. Same cycle.
    parameter integer TREE = 0
) (
    input  wire                  clk,
    input  wire                  rst_n,
    // the result tag one cycle before the result leaves the split tree (engine: a_tag_p, vline[9 + OD])
    input  wire                  t_v_p,
    input  wire                  p_fus,
    input  wire                  p_last,
    input  wire [$clog2(G):0]    p_ports,
    input  wire [2:0]            p_m,
    input  wire [$clog2(G):0]    p_tq,
    input  wire [1:0]            p_hg,
    input  wire [AW-1:0]         p_oa,
    input  wire [AW-1:0]         p_ots,
    input  wire [AW-1:0]         p_ogs,
    input  wire [AW-1:0]         p_ops,
    input  wire [G*W*32-1:0]     res_u,
    output reg  [G-1:0]          ra_re,
    output reg  [G*AW-1:0]       ra_addr,
    input  wire [G*W*32-1:0]     ra_q,
    output wire [G*W*32-1:0]     fsum,
    output wire [G*W-1:0]        ffault
);
    localparam integer LG = $clog2(G);
    generate if (G > 4) begin : g_bad_g
        ot_hdc_v41_fh_add_supports_G_up_to_4 u_trap ();   // the stride multiples are selects of 0..3 x
    end endgenerate
    //: ra_re / ra_addr are registered on the cycle after the result leaves the tree (t + 1), as the engine's
    //: result port; from the early tag (t - 1) the address takes two stages: the three terms, then their sum
    integer rq;
    reg [G-1:0]    re0;
    reg [G*AW-1:0] ta, tb, tc;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin re0 <= 0; ra_re <= 0; end
        else begin
            for (rq = 0; rq < G; rq = rq + 1)
                re0[rq] <= t_v_p && p_fus && p_last && (rq < p_ports) && (MPI < p_m);
            ra_re <= re0;
        end
    end
    //: every carry chain is a (* keep *) Kogge-Stone (ot_hdc_ksadd_k): the multiples k * stride (k < G) are a
    //: select of 0, x, 2x, 3x (3x by one prefix add); the sum is a 3:2 carry-save stage and one prefix add
    localparam [AW-1:0] MPI_W = MPI;
    wire [AW-1:0] ots3, ogs3, mops, ta_n;
    ot_hdc_ksadd_k #(.W(AW)) u_o3 (.a(p_ots), .b(p_ots << 1), .cin(1'b0), .s(ots3), .cout());
    ot_hdc_ksadd_k #(.W(AW)) u_g3 (.a(p_ogs), .b(p_ogs << 1), .cin(1'b0), .s(ogs3), .cout());
    assign mops = MPI_W * p_ops;                    // MPI is a constant (0 for copy 0)
    ot_hdc_ksadd_k #(.W(AW)) u_ta (.a(p_oa), .b(mops), .cin(1'b0), .s(ta_n), .cout());
    function automatic [AW-1:0] kx(input [1:0] k, input [AW-1:0] x, input [AW-1:0] x3);
        kx = (k == 2'd0) ? {AW{1'b0}} : (k == 2'd1) ? x : (k == 2'd2) ? (x << 1) : x3;
    endfunction
    genvar ga;
    generate for (ga = 0; ga < G; ga = ga + 1) begin : g_ra
        wire [AW-1:0] sa = ta[ga*AW +: AW], sb = tb[ga*AW +: AW], sc = tc[ga*AW +: AW];
        wire [AW-1:0] cs_s = sa ^ sb ^ sc;
        wire [AW-1:0] cs_c = ((sa & sb) | (sa & sc) | (sb & sc)) << 1;
        wire [AW-1:0] sum;
        ot_hdc_ksadd_k #(.W(AW)) u_sum (.a(cs_s), .b(cs_c), .cin(1'b0), .s(sum), .cout());
        always @(posedge clk) begin
            ta[ga*AW +: AW] <= ta_n;
            tb[ga*AW +: AW] <= kx(2'(ga & p_tq), p_ots, ots3);
            tc[ga*AW +: AW] <= kx(2'(ga >> (LG - p_hg)), p_ogs, ogs3);
            ra_addr[ga*AW +: AW] <= sum;
        end
    end endgenerate
    wire [G*W*32-1:0] res_h;
    ot_hdc_delay #(.W(G*W*32), .D(2 + RETURN_EXTRA)) u_rh (.clk(clk), .rst_n(rst_n), .d(res_u), .q(res_h));
    //: the addend valid: two cycles after the result leaves the tree (as ot_hdc_vline #(1) and a register)
    reg hv0, hv1, ah_v;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin hv0 <= 1'b0; hv1 <= 1'b0; ah_v <= 1'b0; end
        else begin hv0 <= t_v_p && p_fus && p_last; hv1 <= hv0; ah_v <= hv1; end
    end
    wire protected_v;
    wire [G-1:0] protected_vg;
    generate if (TREE) begin : g_rv_tree
`ifndef SYNTHESIS
        initial if (!CAPTURE || RETURN_EXTRA < 2) $fatal(1, "TREE needs CAPTURE and RETURN_EXTRA >= 2");
`endif
        wire rv_pre;
        wire [G-1:0] rv_mid;
        if (RETURN_EXTRA > 2) begin : g_d
            ot_hdc_delay #(.W(1), .D(RETURN_EXTRA - 2)) u_return_valid (.clk(clk), .rst_n(rst_n), .d(ah_v), .q(rv_pre));
        end else begin : g_n
            assign rv_pre = ah_v;
        end
        for (genvar gq = 0; gq < G; gq = gq + 1) begin : g_rvg
            ot_hdc_v41_fh_kreg u_rvm (.clk(clk), .rst_n(rst_n), .d(rv_pre), .q(rv_mid[gq]));
            ot_hdc_v41_fh_kreg u_rvg (.clk(clk), .rst_n(rst_n), .d(rv_mid[gq]), .q(protected_vg[gq]));
        end
        assign protected_v = protected_vg[0];
    end else begin : g_rv_line
        ot_hdc_delay #(.W(1), .D(RETURN_EXTRA)) u_return_valid (.clk(clk), .rst_n(rst_n), .d(ah_v), .q(protected_v));
        assign protected_vg = {G{protected_v}};
    end endgenerate
    genvar g;
    generate for (g = 0; g < G * W; g = g + 1) begin : g_fadd
        wire [31:0] addend_in, result_in;
        wire valid_in;
        if (CAPTURE) begin : g_capture
            reg [31:0] addend_r, result_r;
            always @(posedge clk) begin
                addend_r <= ra_q[32*g+:32];
                result_r <= res_h[32*g+:32];
            end
            ot_hdc_v41_fh_kreg u_v (.clk(clk), .rst_n(rst_n), .d(protected_vg[g / W]), .q(valid_in));
            assign addend_in=addend_r;
            assign result_in=result_r;
        end else begin
            assign addend_in=ra_q[32*g+:32];
            assign result_in=res_h[32*g+:32];
            assign valid_in=protected_v;
        end
        if (ALAT == 0) begin : g_asb
            ot_hdc_fadd u_add (clk, rst_n, valid_in, addend_in, result_in, fsum[32*g +: 32], ffault[g]);
        end else begin : g_lat
            wire [1:0] err;
            wire       vo;
            ot_hdc_fp32_add_lat #(.LAT(ALAT)) u_add (.clk(clk), .rst_n(rst_n), .valid_in(valid_in), .a(addend_in),
                                                     .b(result_in), .y(fsum[32*g +: 32]), .err(err),
                                                     .valid_out(vo));
            assign ffault[g] = vo && (err != 2'd0);
        end
    end endgenerate
endmodule

// a register the synthesis flow keeps as its own instance (no merge of equal flops): fan-out copies
(* keep_hierarchy *)
module ot_hdc_v41_fh_kreg (
    input  wire clk,
    input  wire rst_n,
    input  wire d,
    output reg  q
);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) q <= 1'b0;
        else q <= d;
endmodule

(* keep_hierarchy *)
module ot_hdc_v41_fh_indexreg #(parameter integer NW=16,LW=4,LANE=0)(
    input wire clk,input wire [NW-1:0] index_in,input wire [LW-1:0] lane_in,
    output reg [NW-1:0] index_q,output reg mask_q);
    always @(posedge clk) begin
        index_q<=index_in; mask_q<=lane_in==LANE;
    end
endmodule
