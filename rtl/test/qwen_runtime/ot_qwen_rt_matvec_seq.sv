`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SIMULATION-ONLY runtime decomposition of rtl/hdc/ot_hdc_matvec.sv, part 1:
// every G-independent register of the engine (issue loop, element tags,
// operand-stage valids/tags, split-tree timing, post-scale timing, argmax
// running best, per-slot maxima, progress, idle, fault).
//
// This module is not hardware. It exists so that a G6144 engine can be
// simulated without elaborating 98,304 lanes in one Verilator model: the
// per-group state lives in ot_qwen_rt_matvec_slice (compiled once and
// instantiated G times by a C++ host), the split tree in ot_qwen_rt_tree_cell
// and the argmax tree above one group in ot_qwen_rt_amax_tree.  The host
// copies wire values between models; it never adds a register, queue or
// cycle.  Every statement below is copied from ot_hdc_matvec with the
// per-group loops removed; the removed per-group values travel on the b_*
// broadcast outputs (current register values, i.e. exactly what the original
// per-group logic read) and the x_* reduction inputs (ORs over the groups that
// the original computed inside the module).
//
// Equivalence is a test, not an assumption: tools/qwen_rt_matvec_gate.py
// compares every public port of the composition against the unmodified
// ot_hdc_matvec on every cycle.
// ---------------------------------------------------------------------------
module ot_qwen_rt_matvec_seq #(
    parameter integer W  = 16,
    parameter integer G  = 4,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer INT8_WEIGHT = 0,
    parameter integer INT8_SCALE_WCS_BASE = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_tiles,
    input  wire [NW-1:0]     i_k,
    input  wire              i_wsrc,
    input  wire [AW-1:0]     i_wbase,
    input  wire [AW-1:0]     i_ts,
    input  wire [AW-1:0]     i_ks,
    input  wire [AW-1:0]     i_js,
    input  wire [AW-1:0]     i_xbase,
    input  wire [AW-1:0]     i_xks,
    input  wire [AW-1:0]     i_xjs,
    input  wire [AW-1:0]     i_xcs,
    input  wire [2:0]        i_jsh,
    input  wire [3:0]        i_split,
    input  wire [AW-1:0]     i_wcs,
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase,
    input  wire [AW-1:0]     i_ots,
    input  wire [AW-1:0]     i_ojs,
    input  wire              i_mmode,
    input  wire              i_oen,
    input  wire              i_amax,
    input  wire              i_rmax,
    input  wire [AW-1:0]     i_mbase,
    output reg               wrom_re,
    output reg  [AW-1:0]     wrom_addr,
    output reg               scale_re,
    output reg               kv_re,
    output reg               ov,
    output reg  [NW-1:0]     am_idx,
    output reg  [31:0]       am_val,
    output reg               am_any,
    output reg               mx_we,
    output reg  [AW-1:0]     mx_addr,
    output reg  [W-1:0]      mx_mask,
    output reg  [W*32-1:0]   mx_data,
    output reg  [15:0]       progress,
    output reg               fault,
    // -- broadcast to the per-group slices (register values) ------------------
    output wire              b_active,
    output wire [AW-1:0]     b_cur,
    output wire [3:0]        b_split_r,
    output wire [AW-1:0]     b_ts_r,
    output wire [AW-1:0]     b_wcs_r,
    output wire [AW-1:0]     b_xc,
    output wire [AW-1:0]     b_xcs_r,
    output wire              b_wsrc_r,
    output wire [NW-1:0]     b_k,
    output wire [NW-1:0]     b_ktot_r,
    output wire              b_s1b_wsrc,
    output wire              b_s2_round,
    output wire              b_s3_v,
    output wire              b_fl_first4,
    output wire              b_vline5,
    output wire [$clog2(G)-1:0] b_reduce_valid,   // per split-tree level
    output wire [$clog2(G)-1:0] b_reduce_select,
    output wire              b_pre_v,             // pre_vline[8+OD]
    output wire [3*(NW+1)+AW+4+3-1:0] b_pre,      // {last, wsrc, mmode, split, nb, lb, nout, sbase}
    output wire              b_raw_v,
    output wire [2*(NW+1)+(NW+1)+4+3-1:0] b_raw,  // {last, wsrc, mmode, split, nb, lb, nout}
    output wire              b_r_v,
    output wire [3*(NW+1)+2*AW+4+3-1:0] b_r,      // {last, oen, mmode, split, oa, ots, nb, lb, nout}
    // -- reductions over the slices / cells (current wire values) -------------
    input  wire              x_scale_any,         // |pre_scale_active
    input  wire              x_group_fault_q,     // |fault_q[G-1:0]
    input  wire              x_scale_fault,       // |scale_faults
    input  wire              x_tfault,            // |tfault
    input  wire [1+32+NW-1:0] x_top               // alv[LV] (argmax tree root register)
);
    localparam integer LW = $clog2(W);
    localparam integer LG = $clog2(G);
    localparam integer FB = IL - 5;
    localparam integer TA = 3;
    localparam integer TL = TA + 1;
    localparam integer OD = TL * LG;

    // -- issue loop (ot_hdc_matvec, per-group kv_addr/x_re/x_addr removed) ----
    reg              active;
    reg [NW-1:0]     nout_r, tiles_r, k_r;
    reg              wsrc_r, round_r, oen_r, amax_r, mmode_r, rmax_r;
    reg [AW-1:0]     mbase_r;
    reg [AW-1:0]     scale_base_r;
    reg [3:0]        split_r;
    reg [AW-1:0]     tstep_r;
    reg [AW-1:0]     wcs_r;
    reg [NW-1:0]     ktot_r;
    reg [AW-1:0]     ts_r, ks_r, js_r, xks_r, xjs_r, xcs_r, ots_r, ojs_r;
    reg [2:0]        jsh_r;
    reg [NW-1:0]     t, k;
    reg [$clog2(IL)-1:0] j;
    reg [AW-1:0]     cur, base_k, base_t, xk, xc, xk_base, oa, ot, ot_step;
    reg [NW:0]       nb, nb_t, nb_step;
    reg [NW:0]       lb, lb_step;
    reg              t_last, k_last;
    wire             j_last = (j == IL - 1);
    wire [LG:0]      per_round = G >> i_split;
    wire [NW-1:0]    kc_in = i_wsrc ? ((i_k + ((16'd1 << i_split) - 16'd1)) >> i_split) : i_k;

    assign ready = !active;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0;
            wrom_re <= 1'b0; kv_re <= 1'b0;
        end else if (!active) begin
            wrom_re <= 1'b0; kv_re <= 1'b0;
            if (go) begin
                active <= 1'b1;
                nout_r <= i_nout; tiles_r <= i_tiles; k_r <= kc_in; ktot_r <= i_k;
                wsrc_r <= i_wsrc; round_r <= i_round; oen_r <= i_oen; amax_r <= i_amax;
                rmax_r <= i_rmax; mbase_r <= i_mbase;
                scale_base_r <= (INT8_WEIGHT != 0 && INT8_SCALE_WCS_BASE != 0) ? i_wcs : i_wbase;
                mmode_r <= i_mmode; split_r <= i_split; wcs_r <= i_wcs;
                ts_r <= i_ts; tstep_r <= i_wsrc ? (i_ts * per_round) : i_ts; ks_r <= i_ks; js_r <= i_js; jsh_r <= i_jsh;
                xks_r <= i_xks; xjs_r <= i_xjs; xcs_r <= i_xcs; ots_r <= i_ots; ojs_r <= i_ojs;
                t <= 0; k <= 0; j <= 0;
                t_last <= (i_tiles == 1); k_last <= (kc_in == 1);
                cur <= i_wbase; base_k <= i_wbase; base_t <= i_wbase;
                xk <= i_xbase; xc <= i_xbase; xk_base <= i_xbase;
                oa <= i_obase; ot <= i_obase; ot_step <= i_ots * per_round;
                nb <= 0; nb_t <= 0; nb_step <= per_round * (W * IL);
                lb <= 0; lb_step <= per_round * W;
            end
        end else begin
            wrom_re <= !wsrc_r; kv_re <= wsrc_r;
            wrom_addr <= cur;
            if (!j_last) begin
                j <= j + 1'b1; oa <= oa + ojs_r; nb <= nb + W; xc <= xc + xjs_r;
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
    assign b_active = active; assign b_cur = cur; assign b_split_r = split_r;
    assign b_ts_r = ts_r; assign b_wcs_r = wcs_r; assign b_xc = xc; assign b_xcs_r = xcs_r;
    assign b_wsrc_r = wsrc_r; assign b_k = k; assign b_ktot_r = ktot_r;

    // -- element tags (per-group e_gm removed) --------------------------------
    reg          e_v, e_first, e_last, e_oen, e_amax, e_wsrc, e_round, e_mmode;
    reg [3:0]    e_split;
    reg          e_rmax, e_opend;
    reg [2:0]    e_j;
    reg [AW-1:0] e_mbase;
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
        e_rmax <= rmax_r; e_j <= j; e_mbase <= mbase_r;
        e_opend <= t_last && k_last && j_last;
    end

    // -- S1 -> S2 -> S3 valids and tags (per-group data removed) --------------
    localparam integer TW = 1 + 1 + 1 + 1 + 1 + 4 + AW + AW + 3 * (NW + 1) + 1 + 3 + 1 + AW + AW;
    wire [TW-1:0] e_tag = {e_last, e_oen, e_amax, e_wsrc, e_mmode, e_split, e_oa, e_ots, e_nb, e_lb, e_rem,
                           e_rmax, e_j, e_opend, e_mbase, scale_base_r};
    reg  [TW-1:0] s1_tag, s1b_tag, s2_tag, s3_tag;
    reg          s1_v, s1b_v, s2_v, s3_v, s1_first, s1b_first, s2_first, s3_first;
    reg          s1b_wsrc, s1b_round;
    reg          s1_wsrc, s1_round, s2_round, s3_wsrc;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 0; s1b_v <= 0; s2_v <= 0; s3_v <= 0; end
        else begin s1_v <= e_v; s1b_v <= s1_v; s2_v <= s1b_v; s3_v <= s2_v; end
    end
    always @(posedge clk) begin
        s1_tag <= e_tag; s1b_tag <= s1_tag; s2_tag <= s1b_tag; s3_tag <= s2_tag;
        s1_first <= e_first; s1b_first <= s1_first; s2_first <= s1b_first; s3_first <= s2_first;
        s1_wsrc <= e_wsrc; s1_round <= e_round; s1b_wsrc <= s1_wsrc; s1b_round <= s1_round;
        s2_round <= s1b_round;
        s3_wsrc <= s2_tag[TW-4];
    end
    assign b_s1b_wsrc = s1b_wsrc; assign b_s2_round = s2_round; assign b_s3_v = s3_v;
    wire [TW-1:0] a_tag;
    ot_hdc_delay #(.W(TW), .D(10 + OD)) u_tag (.clk(clk), .rst_n(rst_n), .d(s3_tag), .q(a_tag));
    wire [10+OD:0] vline;
    ot_hdc_vline #(.D(10 + OD)) u_v (.clk(clk), .rst_n(rst_n), .v(s3_v), .vd(vline));
    wire [5:0] fl_first;
    ot_hdc_vline #(.D(5)) u_first (.clk(clk), .rst_n(rst_n), .v(s3_first && s3_v), .vd(fl_first));
    wire [3:0] t_split;
    ot_hdc_delay #(.W(4), .D(10)) u_ts (.clk(clk), .rst_n(rst_n), .d(s3_tag[TW-6 -: 4]), .q(t_split));
    assign b_fl_first4 = fl_first[4]; assign b_vline5 = vline[5];

    // -- split-tree timing (per-level data in ot_qwen_rt_tree_cell) -----------
    wire [LG*4+3:0] split_at;
    assign split_at[3:0] = t_split;
    genvar lv;
    generate
        for (lv = 1; lv <= LG; lv = lv + 1) begin : g_lvl
            wire [3:0] sp_sel;
            ot_hdc_delay #(.W(4), .D(TA)) u_sd (.clk(clk), .rst_n(rst_n), .d(split_at[4*lv-1 -: 4]), .q(sp_sel));
            reg  [3:0] sp_out;
            always @(posedge clk) sp_out <= sp_sel;
            assign split_at[4*lv+3 -: 4] = sp_out;
            assign b_reduce_valid[lv-1] = vline[10 + TL*(lv-1)] && (split_at[4*lv-1 -: 4] >= lv);
            assign b_reduce_select[lv-1] = sp_sel >= lv;
        end
    endgenerate
    wire raw_v = vline[10 + OD];
    wire raw_last, raw_oen, raw_amax, raw_wsrc, raw_mmode;
    wire [3:0] raw_split;
    wire [AW-1:0] raw_oa, raw_ots, raw_mbase, raw_sbase;
    wire [NW:0] raw_nb, raw_lb, raw_nout;
    wire raw_rmax, raw_opend;
    wire [2:0] raw_j;
    assign {raw_last, raw_oen, raw_amax, raw_wsrc, raw_mmode, raw_split,
            raw_oa, raw_ots, raw_nb, raw_lb, raw_nout,
            raw_rmax, raw_j, raw_opend, raw_mbase, raw_sbase} = a_tag;
    assign b_raw_v = raw_v;
    assign b_raw = {raw_last, raw_wsrc, raw_mmode, raw_split, raw_nb, raw_lb, raw_nout};
    wire [TW-1:0] result_tag;
    wire result_v;
    wire [7:0] post_pending;
    generate if (INT8_WEIGHT != 0) begin : g_post_scale
        wire [TW-1:0] tag_d5, pre_tag;
        wire [5:0] vd;
        wire [8+OD:0] pre_vline;
        wire pre_last, pre_oen, pre_amax, pre_wsrc, pre_mmode;
        wire [3:0] pre_split;
        wire [AW-1:0] pre_oa, pre_ots, pre_mbase, pre_sbase;
        wire [NW:0] pre_nb, pre_lb, pre_nout;
        wire pre_rmax, pre_opend;
        wire [2:0] pre_j;
        ot_hdc_delay #(.W(TW), .D(5)) u_tag (.clk(clk), .rst_n(rst_n), .d(a_tag), .q(tag_d5));
        ot_hdc_vline #(.D(5)) u_v (.clk(clk), .rst_n(rst_n), .v(raw_v), .vd(vd));
        ot_hdc_delay #(.W(TW), .D(8+OD)) u_pretag (.clk(clk), .rst_n(rst_n),
            .d(s3_tag), .q(pre_tag));
        ot_hdc_vline #(.D(8+OD)) u_prev (.clk(clk), .rst_n(rst_n),
            .v(s3_v), .vd(pre_vline));
        assign {pre_last, pre_oen, pre_amax, pre_wsrc, pre_mmode, pre_split,
                pre_oa, pre_ots, pre_nb, pre_lb, pre_nout,
                pre_rmax, pre_j, pre_opend, pre_mbase, pre_sbase} = pre_tag;
        assign b_pre_v = pre_vline[8+OD];
        assign b_pre = {pre_last, pre_wsrc, pre_mmode, pre_split, pre_nb, pre_lb, pre_nout, pre_sbase};
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) scale_re <= 1'b0;
            else scale_re <= x_scale_any;
        end
        assign result_tag = tag_d5;
        assign result_v = vd[5];
        assign post_pending = {2'b00, vd};
    end else begin : g_no_post_scale
        always @(*) scale_re = 1'b0;
        assign b_pre_v = 1'b0;
        assign b_pre = 0;
        assign result_tag = a_tag;
        assign result_v = raw_v;
        assign post_pending = 0;
    end endgenerate
    // fault: fault_q[G-1:0] lives in the slices, fault_q[G] here.
    reg fault_q_tree;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault_q_tree <= 1'b0; fault <= 1'b0; end
        else begin
            fault_q_tree <= x_tfault;
            fault <= x_group_fault_q | fault_q_tree | x_scale_fault;
        end
    end

    // -- results (per-group data in the slices) --------------------------------
    reg           ov1;
    wire          r_v = result_v;
    wire          r_last, r_oen, r_amax, r_wsrc, r_mmode;
    wire [3:0]    r_split;
    wire [AW-1:0] r_oa, r_ots;
    wire [NW:0]   r_nb, r_lb, r_nout;
    wire          r_rmax, r_opend;
    wire [2:0]    r_j;
    wire [AW-1:0] r_mbase, r_sbase;
    assign {r_last, r_oen, r_amax, r_wsrc, r_mmode, r_split, r_oa, r_ots, r_nb, r_lb, r_nout,
            r_rmax, r_j, r_opend, r_mbase, r_sbase} = result_tag;
    assign b_r_v = r_v;
    assign b_r = {r_last, r_oen, r_mmode, r_split, r_oa, r_ots, r_nb, r_lb, r_nout};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ov1 <= 1'b0;
        else ov1 <= r_v && r_last;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ov <= 1'b0;
        else ov <= ov1;
    end

    // -- argmax running best (tree in slices + ot_qwen_rt_amax_tree) ----------
    localparam integer NL = G * W;
    localparam integer LV = $clog2(NL);
    localparam integer CW = 1 + 32 + NW;
    reg  [LV:0] tv;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) tv <= 0;
        else tv <= {tv[LV-1:0], r_v && r_last && (r_amax || r_rmax)};
    end
    wire [1+3+1+AW-1:0] ttag;
    ot_hdc_delay #(.W(1 + 3 + 1 + AW), .D(LV + 1)) u_ttag (.clk(clk), .rst_n(rst_n),
        .d({r_rmax, r_j, r_opend && r_last, r_mbase}), .q(ttag));
    wire          t_rmax, t_opend;
    wire [2:0]    t_j;
    wire [AW-1:0] t_mbase;
    assign {t_rmax, t_j, t_opend, t_mbase} = ttag;
    wire [CW-1:0] top = x_top;
    wire          top_v = top[CW-1];
    wire [31:0]   top_key = top[CW-2 -: 32];
    wire [31:0]   top_val = top_key[31] ? {1'b0, top_key[30:0]} : ~top_key;
    wire [NW-1:0] top_idx = top[NW-1:0];
    reg [31:0] best_key;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            am_any <= 1'b0; am_idx <= 0; am_val <= 0; best_key <= 0;
        end else begin
            if (go && ready && i_amax) am_any <= 1'b0;
            else if (tv[LV] && !t_rmax && top_v && (!am_any || top_key > best_key ||
                                         (top_key == best_key && top_idx < am_idx))) begin
                am_any <= 1'b1; best_key <= top_key; am_idx <= top_idx; am_val <= top_val;
            end
        end
    end

    reg [31:0] rk [0:IL-1];
    reg [IL-1:0] rseen;
    integer rj;
    wire [31:0] nk = (!top_v || (rseen[t_j] && top_key <= rk[t_j])) ? rk[t_j] : top_key;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rseen <= 0; mx_we <= 1'b0; end
        else begin
            mx_we <= 1'b0;
            if (tv[LV] && t_rmax) begin
                if (t_opend) begin
                    mx_we <= 1'b1;
                    rseen <= 0;
                end else if (top_v) begin
                    rk[t_j] <= nk;
                    rseen[t_j] <= 1'b1;
                end
            end
        end
    end
    always @(posedge clk) begin
        if (tv[LV] && t_rmax && t_opend) begin
            mx_addr <= t_mbase >> LW;
            mx_mask <= {W{1'b0}};
            mx_data <= {(W*32){1'b0}};
            for (rj = 0; rj < IL; rj = rj + 1) begin
                mx_mask[(t_mbase[LW-1:0] + rj) % W] <= 1'b1;
                mx_data[32*((t_mbase[LW-1:0] + rj) % W) +: 32] <=
                    (rj == t_j) ? (nk[31] ? {1'b0, nk[30:0]} : ~nk) : (rk[rj][31] ? {1'b0, rk[rj][30:0]} : ~rk[rj]);
            end
        end
    end

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

    wire idle_c = !active && !e_v && !s1_v && !s1b_v && !s2_v && !s3_v && !(|vline) && !(|post_pending) && !(|tv) && !ov1 && !ov
                  && !mx_we;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) idle <= 1'b1;
        else idle <= idle_c && !(go && ready);
    end
endmodule
