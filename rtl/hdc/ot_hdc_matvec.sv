`timescale 1ns/1ps
// ---------------------------------------------------------------------------
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
// Timing from an issue cycle c: memories return at c+1, operands are captured
// at c+2 and conditioned at c+3, products leave at c+8, sums at c+13, the
// split tree adds 6 per level (5 in the adder, 1 output register), and a result
// is written one cycle later.
// ---------------------------------------------------------------------------
module ot_hdc_matvec #(
    parameter integer W  = 16,
    parameter integer G  = 4,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16
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
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase,
    input  wire [AW-1:0]     i_ots,
    input  wire [AW-1:0]     i_ojs,
    input  wire              i_mmode,
    input  wire              i_oen,
    input  wire              i_amax,
    // weight ROM: G*W bf16 lanes per word
    output reg               wrom_re,
    output reg  [AW-1:0]     wrom_addr,
    input  wire [G*W*16-1:0] wrom_q,
    // KV SRAM: one port per group, W lanes (BF16 values in 32-bit words) per word
    output reg               kv_re,
    output reg  [G*AW-1:0]   kv_addr,
    input  wire [G*W*32-1:0] kv_q,
    // x reads (vector memory, element), one port per group
    output reg  [G-1:0]      x_re,
    output reg  [G*AW-1:0]   x_addr,
    input  wire [G*32-1:0]   x_q,
    // result words, one port per group
    output reg               ov,          // a result round-slot (whether or not written)
    output reg  [G-1:0]      o_we,
    output reg  [G*AW-1:0]   o_addr,
    output reg  [G*W-1:0]    o_mask,
    output reg  [G*W*32-1:0] o_data,
    // argmax
    output reg  [NW-1:0]     am_idx,
    output reg  [31:0]       am_val,
    output reg               am_any,
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
    reg [1:0]        split_r;
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
    // tiles one round covers: G/S for ROM ops, 1 for KV ops
    wire [LG:0]      per_round = G >> (i_wsrc ? 2'd0 : i_split);

    assign ready = !active;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0;
            wrom_re <= 1'b0; kv_re <= 1'b0; x_re <= 0;
        end else if (!active) begin
            wrom_re <= 1'b0; kv_re <= 1'b0; x_re <= 0;
            if (go) begin
                active <= 1'b1;
                nout_r <= i_nout; tiles_r <= i_tiles; k_r <= i_k;
                wsrc_r <= i_wsrc; round_r <= i_round; oen_r <= i_oen; amax_r <= i_amax;
                mmode_r <= i_mmode; split_r <= i_wsrc ? 2'd0 : i_split;
                ts_r <= i_ts; tstep_r <= i_wsrc ? (i_ts << LG) : i_ts; ks_r <= i_ks; js_r <= i_js; jsh_r <= i_jsh;
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
            //: KV ops: group g takes tile r*G + g, its own word
            for (gi = 0; gi < G; gi = gi + 1) kv_addr[gi*AW +: AW] <= cur + gi * ts_r;
            x_re <= {G{1'b1}};
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
    // x address per group: chunk c = g mod S
    always @(posedge clk) begin
        for (gi = 0; gi < G; gi = gi + 1)
            x_addr[gi*AW +: AW] <= xc + (gi & ((1 << split_r) - 1)) * xcs_r;
    end

    // Tag of the element issued this cycle (registered alongside the address).
    reg          e_v, e_first, e_last, e_oen, e_amax, e_wsrc, e_round, e_mmode;
    reg [1:0]    e_split;
    reg [AW-1:0] e_oa, e_ots;
    reg [NW:0]   e_nb, e_lb, e_rem;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) e_v <= 1'b0;
        else e_v <= active;
    end
    always @(posedge clk) begin
        e_first <= (k == 0); e_last <= k_last;
        e_oen <= oen_r; e_amax <= amax_r; e_wsrc <= wsrc_r; e_round <= round_r; e_mmode <= mmode_r;
        e_split <= split_r; e_oa <= oa; e_ots <= ots_r; e_nb <= nb; e_lb <= lb;
        e_rem <= {1'b0, nout_r};
    end

    // -- S1 (memories answer) -> S2 (capture) -> S3 (condition) -----------------
    localparam integer TW = 1 + 1 + 1 + 1 + 1 + 2 + AW + AW + 3 * (NW + 1);
    wire [TW-1:0] e_tag = {e_last, e_oen, e_amax, e_wsrc, e_mmode, e_split, e_oa, e_ots, e_nb, e_lb, e_rem};
    reg  [TW-1:0] s1_tag, s1b_tag, s2_tag, s3_tag;
    reg          s1_v, s1b_v, s2_v, s3_v, s1_first, s1b_first, s2_first, s3_first;
    reg          s1b_wsrc, s1b_round;
    //: Memory read data is registered once as it arrives (MEM_PIPE): the
    //: weight word is 2,048 bits wide and its lanes span the whole engine, so a
    //: pin-to-lane wire gets a cycle of its own.
    reg [G*W*16-1:0] mq_wrom;
    reg [G*W*32-1:0] mq_kv;
    reg [G*32-1:0]   mq_x;
    reg          s1_wsrc, s1_round, s2_round, s3_wsrc;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 0; s1b_v <= 0; s2_v <= 0; s3_v <= 0; end
        else begin s1_v <= e_v; s1b_v <= s1_v; s2_v <= s1b_v; s3_v <= s2_v; end
    end
    reg [G*W*32-1:0] s2_w, s3_w;
    reg [G*32-1:0]   s2_x, s3_x;
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
        for (l = 0; l < G; l = l + 1)
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

    // -- lanes -------------------------------------------------------------------
    wire [G*W*32-1:0] sum;
    wire [G*W-1:0]    lfault;
    genvar g, gl;
    generate
        for (g = 0; g < G; g = g + 1) begin : g_grp
            for (gl = 0; gl < W; gl = gl + 1) begin : g_lane
                localparam integer LI = g * W + gl;
                wire [31:0] prod, fb_pre, acc_in;
                reg  [31:0] acc_q;
                wire f0, f1;
                //: every product is BF16 x BF16 (weights, x rounded; BF16 KV, q and
                //: probabilities rounded), so every lane has the small exact multiplier
                ot_hdc_bmul u_mul (.clk(clk), .rst_n(rst_n), .v(s3_v),
                                   .a(s3_w[32*LI +: 32]), .b(s3_x[32*g +: 32]), .y(prod), .fault(f0));
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
    endgenerate

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
    generate
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
    endgenerate
    wire [G*W*32-1:0] res = lvl[LG];
    //: A status bit: registered in two levels (see ot_hdc_stream).
    reg [G:0] fault_q;
    integer fg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault_q <= 0; fault <= 1'b0; end
        else begin
            for (fg = 0; fg < G; fg = fg + 1) fault_q[fg] <= |lfault[fg*W +: W];
            fault_q[G] <= |tfault;
            fault <= |fault_q;
        end
    end

    // -- results -------------------------------------------------------------------
    reg           ov1;
    reg  [G-1:0]  o_we1;
    reg  [G*AW-1:0] o_addr1;
    reg  [G*W-1:0]  o_mask1;
    reg  [G*W*32-1:0] o_data1;
    wire          r_v = vline[10 + OD];
    wire          r_last, r_oen, r_amax, r_wsrc, r_mmode;
    wire [1:0]    r_split;
    wire [AW-1:0] r_oa, r_ots;
    wire [NW:0]   r_nb, r_lb, r_nout;
    assign {r_last, r_oen, r_amax, r_wsrc, r_mmode, r_split, r_oa, r_ots, r_nb, r_lb, r_nout} = a_tag;
    wire [LG:0]   r_ports = G >> r_split;
    reg  [G*W-1:0] r_mask;
    integer q, ql;
    always @(*) begin
        for (q = 0; q < G; q = q + 1)
            for (ql = 0; ql < W; ql = ql + 1)
                r_mask[q*W + ql] = (q < r_ports) &&
                    (r_mmode ? (r_lb + q * W + ql < r_nout) : (r_nb + q * (W * IL) + ql < r_nout));
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ov1 <= 1'b0; o_we1 <= 0;
        end else begin
            ov1 <= r_v && r_last;
            for (q = 0; q < G; q = q + 1)
                o_we1[q] <= r_v && r_last && r_oen && (q < r_ports);
        end
    end
    always @(posedge clk) begin
        for (q = 0; q < G; q = q + 1)
            o_addr1[q*AW +: AW] <= r_oa + q * r_ots;
        o_mask1 <= r_mask; o_data1 <= res;
    end
    //: A second output register: the result bus is 2,048 bits wide and its
    //: flops sit by the lanes, so the pins get flops of their own.  ov, and the
    //: chaining progress counted from it, move with the data.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ov <= 1'b0; o_we <= 0; end
        else begin ov <= ov1; o_we <= o_we1; end
    end
    always @(posedge clk) begin
        o_addr <= o_addr1; o_mask <= o_mask1; o_data <= o_data1;
    end

    // -- argmax: a registered compare tree over the round-slot, then a running best --
    // Keys order binary32 values as unsigned integers (zeros are canonical +0);
    // on equal keys the lower row wins, in the tree and across cycles.
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    localparam integer NL = G * W;
    localparam integer LV = $clog2(NL);
    //: The key is an invertible function of the value, so the tree carries only
    //: the key and recovers the value at the end (half the tree's wiring).
    localparam integer CW = 1 + 32 + NW;            // {valid, key, row}
    wire [CW*NL-1:0] alv [0:LV];
    reg  [LV:0] tv;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) tv <= 0;
        else tv <= {tv[LV-1:0], r_v && r_last && r_amax};
    end
    genvar e;
    generate
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
    endgenerate
    wire [CW-1:0] top = alv[LV][CW-1:0];
    wire          top_v = top[CW-1];
    wire [31:0]   top_key = top[CW-2 -: 32];
    wire [31:0]   top_val = top_key[31] ? {1'b0, top_key[30:0]} : ~top_key;   // okey inverted
    wire [NW-1:0] top_idx = top[NW-1:0];
    reg [31:0] best_key;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            am_any <= 1'b0; am_idx <= 0; am_val <= 0; best_key <= 0;
        end else begin
            if (go && ready && i_amax) am_any <= 1'b0;
            else if (tv[LV] && top_v && (!am_any || top_key > best_key ||
                                         (top_key == best_key && top_idx < am_idx))) begin
                am_any <= 1'b1; best_key <= top_key; am_idx <= top_idx; am_val <= top_val;
            end
        end
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
    wire idle_c = !active && !e_v && !s1_v && !s1b_v && !s2_v && !s3_v && !(|vline) && !(|tv) && !ov1 && !ov;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) idle <= 1'b1;
        else idle <= idle_c && !(go && ready);
    end
endmodule
