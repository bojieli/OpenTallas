// NK/NL S1 control partition, step 1 (Q-COMPUTE-ELEM r2, 2026-10-15; plan 64d5fd9d2, audit dbeb0e06c):
// the FAST_ISSUE issue loop of ot_qwen_w12_matvec_part_banked_v1 moved VERBATIM into its own module so it can be
// hardened as the control leaf (state + local decode; every output below is a register, no logic between flop and pin).
// Exact hierarchy move: same statements, same edges, 0 cycles (ISSUE_LEAF=1 in the parent; bench = the NK benches).
module ot_qwen_w12_issue_banked_v1 #(
    parameter integer W = 16, parameter integer G = 4, parameter integer IL = 8, parameter integer AW = 24,
    parameter integer NW = 16, parameter integer GT = G, parameter integer SMIN = 0, parameter integer KV_PREP = 0,
    parameter integer INT8_WEIGHT = 0, parameter integer INT8_SCALE_WCS_BASE = 0, parameter integer TMUT = 0
) (
    input  wire clk, rst_n, go,
    input  wire [NW-1:0] i_nout, i_tiles, i_k,
    input  wire i_wsrc, i_round, i_mmode, i_oen, i_amax, i_rmax,
    input  wire [AW-1:0] i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs, i_wcs, i_obase, i_ots, i_ojs, i_mbase,
    input  wire [2:0] i_jsh,
    input  wire [3:0] i_split,
    output reg wrom_re, kv_re,
    output reg [AW-1:0] wrom_addr,
    output wire  o_active,
    output wire [NW-1:0] o_nout_r,
    output wire [NW-1:0] o_tiles_r,
    output wire [NW-1:0] o_k_r,
    output wire  o_wsrc_r,
    output wire  o_round_r,
    output wire  o_oen_r,
    output wire  o_amax_r,
    output wire  o_mmode_r,
    output wire  o_rmax_r,
    output wire [AW-1:0] o_mbase_r,
    output wire [AW-1:0] o_scale_base_r,
    output wire [3:0] o_split_r,
    output wire [AW-1:0] o_wcs_r,
    output wire [NW-1:0] o_ktot_r,
    output wire [AW-1:0] o_ts_r,
    output wire [AW-1:0] o_ots_r,
    output wire [AW-1:0] o_xcs_r,
    output wire [NW-1:0] o_t,
    output wire [NW-1:0] o_k,
    output wire [$clog2(IL)-1:0] o_j,
    output wire [AW-1:0] o_cur,
    output wire [AW-1:0] o_oa,
    output wire [NW:0] o_nb,
    output wire [NW:0] o_lb,
    output wire [AW-1:0] o_xc,
    output wire  o_t_last,
    output wire  o_k_last,
    output wire  o_split_fault,
    output wire  o_pend
);
    localparam integer PRUNE = (SMIN > 0);
    reg              active;
    reg [NW-1:0]     nout_r, tiles_r, k_r;
    reg              wsrc_r, round_r, oen_r, amax_r, mmode_r, rmax_r;
    reg [AW-1:0]     mbase_r;
    reg [AW-1:0]     scale_base_r;
    reg [3:0]        split_r;
    reg [AW-1:0]     tstep_r;          // weight step per round: ts, or (G/S)*ts for KV ops
    reg [AW-1:0]     wcs_r;
    reg [NW-1:0]     ktot_r;           // KV ops: the whole K (elements past it multiply +0)
    reg [AW-1:0]     ts_r, ks_r, js_r, xks_r, xjs_r, xcs_r, ots_r, ojs_r;
    reg [2:0]        jsh_r;
    reg [NW-1:0]     t, k;
    reg [$clog2(IL)-1:0] j;
    reg [AW-1:0]     cur, base_k, base_t, xk, xc, xk_base, oa, ot, ot_step;
    reg [NW:0]       nb, nb_t, nb_step;    // first row of the current slot / round (port 0)
    reg [NW:0]       lb, lb_step;          // first lane-vector index of the round (mmode 1)
    reg              t_last, k_last;
    wire             j_last = (j == IL - 1);
    //: pruning: an op below the smallest split the pruned tree supports
    reg              split_fault;
    //: KV_PREP > 0: a KV-sourced op waits KV_PREP cycles after its go (ready low) for its per-group KV
    //: offsets, which leave the issue path as a pipelined multiply (see g_kv_addr)
    reg              pend;
    reg [3:0]        pcnt;

    //: FAST_ISSUE (1.2 GHz @ SS): the same schedule, cycle for cycle (plus KV_PREP on KV ops).
    //: (1) The per-op products (the round steps ts*(GT/S), ots*(GT/S), (GT/S)*W*IL, (GT/S)*W and the KV
    //:     K-step count ceil(K/S)) are first needed at the first K or round boundary, IL >= 3 cycles after
    //:     the go: they are two register stages computed from the latched fields, not an input-to-register
    //:     multiply; ts*(GT/S) is shifted adds of ts (GT's set bits), not a multiplier.
    //: (2) Every loop add is ot_qwen_w12_kadd: a Kogge-Stone prefix adder whose levels are kept netlist
    //:     boundaries (ABC re-maps a flattened `+` as a MAJ ripple: 22 cells, -656 ps at SS on `cur`).
    localparam integer PRW = $clog2(GT) + 1;
    //: x * (GT >> s), exactly, as the sum of x shifted to each set bit b >= s of the constant GT (two terms at
    //: 6,144): no multiplier
    function automatic [AW+PRW-1:0] mul_gt_shr(input [AW-1:0] x, input [3:0] sh);
        integer b;
        reg [AW+PRW-1:0] acc;
        begin
            acc = 0;
            for (b = 0; b < PRW; b = b + 1)
                if (((GT >> b) & 1) != 0 && b >= sh) acc = acc + ({{PRW{1'b0}}, x} << (b - sh));
            mul_gt_shr = acc;
        end
    endfunction
    reg [PRW-1:0]    pr_a;                 // GT >> split
    reg [AW+PRW-1:0] tsg_a, otsg_a;        // ts*(GT>>S), ots*(GT>>S)
    reg [NW-1:0]     kc_a;
    localparam [NW:0]   WNB = W;
    localparam [NW-1:0] ONE = 1, TWO = 2;
    //: three stages (the first use is IL >= 3 cycles after the go): the shifted terms, their kept sum, the result
    localparam integer NB_GT = PRW;
    //: TP-setting bench mutants (qwen-tp8 2026-10-12; TMUT 0 = the real constants, synthesis-identical): 4 = the
    //: round-step products ts*(GT>>S) / ots*(GT>>S) built from a stale 2*GT (a TP4 constant on a TP8 tile).
    //: (a stale-2*GT pr_a or e_gm bound was tried as TMUT 5: unobservable -- it only touches groups no result port reads)
    localparam integer GT_TS = (TMUT == 4) ? (GT << 1) : GT;
    reg [AW+PRW-1:0] tsh [0:NB_GT-1];
    reg [AW+PRW-1:0] osh [0:NB_GT-1];
    reg [NW:0]       kpad_a;
    always @(posedge clk) begin : p_terms
        integer b;
        for (b = 0; b < NB_GT; b = b + 1) begin
            tsh[b] <= (((GT_TS >> b) & 1) != 0 && b >= split_r) ? ({{PRW{1'b0}}, ts_r} << (b - split_r)) : {(AW+PRW){1'b0}};
            osh[b] <= (((GT_TS >> b) & 1) != 0 && b >= split_r) ? ({{PRW{1'b0}}, ots_r} << (b - split_r)) : {(AW+PRW){1'b0}};
        end
        pr_a <= GT >> split_r;
        kpad_a <= {1'b0, ktot_r} + ((1 << split_r) - 1);
    end
    wire [AW+PRW-1:0] tsum, osum;
    wire [NB_GT*(AW+PRW)-1:0] tsh_flat, osh_flat;
    ot_qwen_w12_ksum #(.W(AW+PRW), .N(NB_GT)) u_ts (.rows(tsh_flat), .s(tsum));
    ot_qwen_w12_ksum #(.W(AW+PRW), .N(NB_GT)) u_os (.rows(osh_flat), .s(osum));
    genvar tb;
    for (tb = 0; tb < NB_GT; tb = tb + 1) begin : g_fl
        assign tsh_flat[tb*(AW+PRW) +: AW+PRW] = tsh[tb];
        assign osh_flat[tb*(AW+PRW) +: AW+PRW] = osh[tb];
    end
    always @(posedge clk) begin
        tsg_a <= tsum; otsg_a <= osum;
        kc_a <= wsrc_r ? kpad_a[NW-1:0] >> split_r : ktot_r;       // ceil(K/S) (K + S - 1 < 2^NW)
        tstep_r <= !wsrc_r ? ts_r : tsg_a[AW-1:0];
        ot_step <= otsg_a[AW-1:0];
        nb_step <= pr_a * (W * IL);
        lb_step <= pr_a * W;
        k_r <= kc_a;
    end
    //: loop adds
    wire [AW-1:0] cur_js, oa_j, xc_j, bk_k, xk_k, bt_t, ot_t;
    wire [NW:0]   nb_j, nbt_t, lb_t;
    wire [NW-1:0] k_1, k_2, t_1, t_2;
    ot_qwen_w12_kadd #(.W(AW)) u_a0 (.a(cur), .b(js_r), .s(cur_js));
    ot_qwen_w12_kadd #(.W(AW)) u_a1 (.a(oa), .b(ojs_r), .s(oa_j));
    ot_qwen_w12_kadd #(.W(AW)) u_a2 (.a(xc), .b(xjs_r), .s(xc_j));
    ot_qwen_w12_kadd #(.W(AW)) u_a3 (.a(base_k), .b(ks_r), .s(bk_k));
    ot_qwen_w12_kadd #(.W(AW)) u_a4 (.a(xk), .b(xks_r), .s(xk_k));
    ot_qwen_w12_kadd #(.W(AW)) u_a5 (.a(base_t), .b(tstep_r), .s(bt_t));
    ot_qwen_w12_kadd #(.W(AW)) u_a6 (.a(ot), .b(ot_step), .s(ot_t));
    ot_qwen_w12_kadd #(.W(NW+1)) u_a7 (.a(nb), .b(WNB), .s(nb_j));
    ot_qwen_w12_kadd #(.W(NW+1)) u_a8 (.a(nb_t), .b(nb_step), .s(nbt_t));
    ot_qwen_w12_kadd #(.W(NW+1)) u_a9 (.a(lb), .b(lb_step), .s(lb_t));
    ot_qwen_w12_kadd #(.W(NW)) u_a10 (.a(k), .b(ONE), .s(k_1));
    ot_qwen_w12_kadd #(.W(NW)) u_a11 (.a(k), .b(TWO), .s(k_2));
    ot_qwen_w12_kadd #(.W(NW)) u_a12 (.a(t), .b(ONE), .s(t_1));
    ot_qwen_w12_kadd #(.W(NW)) u_a13 (.a(t), .b(TWO), .s(t_2));
    //: the go's own first-boundary flags, without the K-step divide: ceil(K/S) == 1 <=> K <= S
    wire kc_is_1 = i_wsrc ? ({{(32-NW){1'b0}}, i_k} <= (32'd1 << i_split)) : (i_k == 1);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; pend <= 1'b0; pcnt <= 4'd0;
            wrom_re <= 1'b0; kv_re <= 1'b0;
            split_fault <= 1'b0;
        end else if (pend) begin
            wrom_re <= 1'b0; kv_re <= 1'b0;
            if (pcnt == 0) begin pend <= 1'b0; active <= 1'b1; end
            else pcnt <= pcnt - 1'b1;
        end else if (!active) begin
            wrom_re <= 1'b0; kv_re <= 1'b0;
            if (go) begin
                if (KV_PREP > 0 && i_wsrc) begin pend <= 1'b1; pcnt <= KV_PREP - 1; end
                else active <= 1'b1;
                if (PRUNE && i_split < SMIN) split_fault <= 1'b1;
                nout_r <= i_nout; tiles_r <= i_tiles; ktot_r <= i_k;
                wsrc_r <= i_wsrc; round_r <= i_round; oen_r <= i_oen; amax_r <= i_amax;
                rmax_r <= i_rmax; mbase_r <= i_mbase;
                scale_base_r <= (INT8_WEIGHT != 0 && INT8_SCALE_WCS_BASE != 0) ? i_wcs : i_wbase;
                mmode_r <= i_mmode; split_r <= i_split; wcs_r <= i_wcs;
                ts_r <= i_ts; ks_r <= i_ks; js_r <= i_js; jsh_r <= i_jsh;
                xks_r <= i_xks; xjs_r <= i_xjs; xcs_r <= i_xcs; ots_r <= i_ots; ojs_r <= i_ojs;
                t <= 0; k <= 0; j <= 0;
                t_last <= (i_tiles == 1); k_last <= kc_is_1;
                cur <= i_wbase; base_k <= i_wbase; base_t <= i_wbase;
                xk <= i_xbase; xc <= i_xbase; xk_base <= i_xbase;
                oa <= i_obase; ot <= i_obase;
                nb <= 0; nb_t <= 0;
                lb <= 0;
            end
        end else begin
            wrom_re <= !wsrc_r; kv_re <= wsrc_r;
            wrom_addr <= cur;
            if (!j_last) begin
                j <= j + 1'b1; oa <= oa_j; nb <= nb_j; xc <= xc_j;
                if ((((j + 1'b1) >> jsh_r) << jsh_r) == (j + 1'b1)) cur <= cur_js;
            end else begin
                j <= 0; nb <= nb_t; oa <= ot;
                if (!k_last) begin
                    k <= k_1; k_last <= (k_2 == k_r);
                    base_k <= bk_k; cur <= bk_k;
                    xk <= xk_k; xc <= xk_k;
                end else begin
                    k <= 0; k_last <= (k_r == 1);
                    xk <= xk_base; xc <= xk_base;
                    if (!t_last) begin
                        t <= t_1; t_last <= (t_2 == tiles_r);
                        base_t <= bt_t; base_k <= bt_t; cur <= bt_t;
                        ot <= ot_t; oa <= ot_t;
                        nb_t <= nbt_t; nb <= nbt_t; lb <= lb_t;
                    end else begin
                        active <= 1'b0;
                    end
                end
            end
        end
    end
    assign o_active = active;
    assign o_nout_r = nout_r;
    assign o_tiles_r = tiles_r;
    assign o_k_r = k_r;
    assign o_wsrc_r = wsrc_r;
    assign o_round_r = round_r;
    assign o_oen_r = oen_r;
    assign o_amax_r = amax_r;
    assign o_mmode_r = mmode_r;
    assign o_rmax_r = rmax_r;
    assign o_mbase_r = mbase_r;
    assign o_scale_base_r = scale_base_r;
    assign o_split_r = split_r;
    assign o_wcs_r = wcs_r;
    assign o_ktot_r = ktot_r;
    assign o_ts_r = ts_r;
    assign o_ots_r = ots_r;
    assign o_xcs_r = xcs_r;
    assign o_t = t;
    assign o_k = k;
    assign o_j = j;
    assign o_cur = cur;
    assign o_oa = oa;
    assign o_nb = nb;
    assign o_lb = lb;
    assign o_xc = xc;
    assign o_t_last = t_last;
    assign o_k_last = k_last;
    assign o_split_fault = split_fault;
    assign o_pend = pend;
endmodule
