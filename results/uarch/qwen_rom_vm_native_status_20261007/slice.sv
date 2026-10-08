module native_me_address_slice #(
    parameter integer W  = 16,
    parameter integer G  = 4,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer INT8_WEIGHT = 0,
    parameter integer INT8_SCALE_WCS_BASE = 0,
    parameter integer PART = 0,          // 0 monolithic, 1 tile, 2 top
    parameter integer GT = G,            // groups of the whole engine
    parameter integer GBASE = 0,         // global index of local group 0
    parameter integer GBASE_PORT = 0,    // 1: take it from i_gbase (a strap)
    parameter integer SMIN = 0,          // pruning: smallest split any op uses
    parameter integer TCUT = 0,          // PART 2: t_in is split-tree level TCUT
    parameter integer XD = 0,            // PART 2: t_in's extra cycles over the monolithic timing
    parameter integer NX = G,            // x ports generated (PART 2: the chunk stream)
    parameter integer ORD = 0,           // extra result-write register stages
    // SCALE_LOCAL = 1: each result-port group holds only its own row scales
    // (port-local scale ROM): word  wcs + round*IL + slot, where the program's
    // wcs is the matrix's port-local base (sum of the earlier matrices'
    // rounds*IL).  0: the dense image  wcs + round*(GT/S)*IL + q*IL + slot.
    parameter integer SCALE_LOCAL = 0,
    // GOUT: result and scale ports provided (the result-port groups a pruned top has; default G)
    parameter integer GOUT = G,
    // MEM_EXTRA: memory data (ROM, KV, x) returns MEM_EXTRA cycles later than c+1 (a capture register at
    // the macro pins, e.g. the ROM tile at 0.833 ns SS); the element tags wait the same cycles
    parameter integer MEM_EXTRA = 0,
    // Adder depths (1.2 GHz @ SS, AGENTS.md clock target).  ACC_LAT: the lane accumulator's FP32 add latency
    // (5: ot_hdc_fadd, the qualified five-stage pipe; else ot_hdc_fp32_add_lat #(ACC_LAT), bit-identical, 3..7).
    // The IL-slot ring is acc register + adder + (FB - 1) delay = IL, so ACC_LAT <= IL - 1.  TREE_LAT: the
    // split-tree pair adder (3: ot_hdc_qadd; else ot_hdc_fp32_add_lat #(TREE_LAT)).  Values do not change;
    // results emerge ACC_LAT - 5 + LG * (TREE_LAT - 3) cycles later.
    parameter integer ACC_LAT = 5,
    parameter integer TREE_LAT = 3,
    // FAST_ISSUE: the 1.2 GHz issue loop (pipelined per-op products, keep-prefix loop adds); 0: the original
    parameter integer FAST_ISSUE = 0,
    // KV_PREP: cycles a KV-sourced op waits after its go for the pipelined per-group KV offsets (3), 0: none
    parameter integer KV_PREP = 0,
    // MUL_LAT: the lane's BF16 product latency (5: ot_qwen_w12_bmul; 6: its product cut after the carry-save rows;
    // 7: + a kept per-lane input register; 8: + the decoded operands registered)
    parameter integer MUL_LAT = 5
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_tiles,     // rounds
    input  wire [NW-1:0]     i_k,         // k per chunk (KV ops: the whole K)
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
    input  wire [3:0]        i_split,
    input  wire [AW-1:0]     i_wcs,       // KV ops: word stride between chunks
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase,
    input  wire [AW-1:0]     i_ots,
    input  wire [AW-1:0]     i_ojs,
    input  wire              i_mmode,
    input  wire              i_oen,
    input  wire              i_amax,
    input  wire              i_rmax,      // per-slot maxima of the results -> word mbase / W, lanes mbase % W + j
    input  wire [AW-1:0]     i_mbase,
    // Matrix weight ROM: G*W BF16 lanes, or G*W signed INT8 codes.
    output reg               wrom_re,
    output reg  [AW-1:0]     wrom_addr,
    input  wire [G*W*((INT8_WEIGHT != 0) ? 8 : 16)-1:0] wrom_q,
    // One independent scale read per group. Row-word address is the matrix's
    // weight base plus output-row-word offset. Non-INT8 mode ties requests low.
    output reg               scale_re,
    output reg  [GOUT-1:0]   scale_gre,  // active group read enables; scale_re is their OR
    output reg  [GOUT*AW-1:0] scale_addr,
    input  wire [GOUT*W*16-1:0] scale_q,
    // KV SRAM: one port per group, W lanes (BF16 values in 32-bit words) per word
    output reg               kv_re,
    output reg  [G*AW-1:0]   kv_addr,
    input  wire [G*W*32-1:0] kv_q,
    // x reads (vector memory, element), one port per group
    output reg  [G-1:0]      x_re,
    output reg  [G*AW-1:0]   x_addr,
    input  wire [G*32-1:0]   x_q,
    // result words, one port per group
    output wire              ov,          // a result round-slot (whether or not written)
    output wire [GOUT-1:0]   o_we,
    output wire [GOUT*AW-1:0] o_addr,
    output wire [GOUT*W-1:0] o_mask,
    output wire [GOUT*W*32-1:0] o_data,
    // argmax
    output reg  [NW-1:0]     am_idx,
    output reg  [31:0]       am_val,
    output reg               am_any,
    // the per-slot maxima word (one masked word write after the op's last result)
    output reg               mx_we,
    output reg  [AW-1:0]     mx_addr,
    output reg  [W-1:0]      mx_mask,
    output reg  [W*32-1:0]   mx_data,
    // result slots the latest accepted instruction has produced
    output reg  [15:0]       progress,
    output reg               fault,
    // -- physical partition ---------------------------------------------------
    input  wire [31:0]       i_gbase,
    input  wire [((PART == 2) ? ((G >> TCUT) > 0 ? (G >> TCUT) : 1) : 1)*W*32-1:0] t_in,
    input  wire              t_fault_in,  // PART 2: OR of the tiles' and tree nodes' faults
    output wire [W*32-1:0]   t_out,
    output wire              t_vout,
    output wire              t_fault,
    output wire              active_o
);
    localparam integer LW = $clog2(W);
    localparam integer LG = $clog2(G);
    localparam integer FB = IL - ACC_LAT; // circulation delay after the adder
    localparam integer SD = MUL_LAT + ACC_LAT;  // S3 -> the lane sums (products at +MUL_LAT, the accumulator add)
    localparam integer TA = TREE_LAT;     // split-tree adder: ot_hdc_qadd (rtl/hdc/ot_hdc_fastfp.sv), LATENCY 3, or ot_qwen_w12_ladd
    localparam integer TL = TA + 1;       // split-tree cycles per level: the adder + 1 output register
    localparam integer OD = TL * LG;      // split tree
    localparam integer XDD = (PART == 2) ? XD : 0;
    localparam integer LV0 = (PART == 2) ? TCUT : 0;   // tree levels LV0+1..LG live here
    localparam integer PRUNE = (SMIN > 0);
    // result-port groups: the only groups a K-split tree can deliver to
    localparam integer NPG = PRUNE ? (((GT >> SMIN) < G) ? (GT >> SMIN) : G) : G;
    localparam integer NPX = (NX < G) ? NX : G;
    localparam integer LANES = (PART != 2);
    localparam integer PORTS = (PART != 1);
    //: internal widths: the lanes' (GL), the split tree's (GI: the top holds only the positions of
    //: its input level) and the result path's (GR: the result-port groups when pruned)
    localparam integer GL = LANES ? G : 1;
    localparam integer GI = (PART == 2) ? (G >> TCUT) : G;
    localparam integer GR = PRUNE ? NPG : G;
    function automatic [15:0] int8_bf16(input [7:0] code);
        reg [7:0] mag, norm;
        reg [2:0] msb;
        integer bit_index;
        begin
            mag = code[7] ? (~code + 8'd1) : code;
            msb = 0;
            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1)
                if (mag[bit_index]) msb = bit_index[2:0];
            norm = mag << (3'd7 - msb);
            int8_bf16 = (mag == 0) ? 16'd0 :
                        {code[7], (8'd127 + {5'd0, msb}), norm[6:0]};
        end
    endfunction
    //: the global index of local group 0
    wire [31:0] gb = (GBASE_PORT != 0) ? i_gbase : GBASE;

    // -- issue loop -----------------------------------------------------------
    integer gi;
    reg              active;
    assign active_o = active;
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

    assign ready = !active && !pend;

generate if (FAST_ISSUE == 0) begin : g_issue_legacy
    // tiles one round covers: GT/S (the whole engine's groups)
    wire [$clog2(GT):0] per_round = GT >> i_split;
    //: KV ops cut their whole K interleaved: ceil(K/S) steps
    wire [NW-1:0]    kc_in = i_wsrc ? ((i_k + ((16'd1 << i_split) - 16'd1)) >> i_split) : i_k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; pend <= 1'b0; pcnt <= 4'd0;
            wrom_re <= 1'b0; kv_re <= 1'b0;
            split_fault <= 1'b0;
        end else if (!active) begin
            wrom_re <= 1'b0; kv_re <= 1'b0;
            if (go) begin
                active <= 1'b1;
                if (PRUNE && i_split < SMIN) split_fault <= 1'b1;
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
            // this cycle's element: (r, k, j) at `cur`
            wrom_re <= !wsrc_r; kv_re <= wsrc_r;
            wrom_addr <= cur;
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
end else begin : g_issue_fast
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
    reg [AW+PRW-1:0] tsh [0:NB_GT-1];
    reg [AW+PRW-1:0] osh [0:NB_GT-1];
    reg [NW:0]       kpad_a;
    always @(posedge clk) begin : p_terms
        integer b;
        for (b = 0; b < NB_GT; b = b + 1) begin
            tsh[b] <= (((GT >> b) & 1) != 0 && b >= split_r) ? ({{PRW{1'b0}}, ts_r} << (b - split_r)) : {(AW+PRW){1'b0}};
            osh[b] <= (((GT >> b) & 1) != 0 && b >= split_r) ? ({{PRW{1'b0}}, ots_r} << (b - split_r)) : {(AW+PRW){1'b0}};
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
end endgenerate
    // x reads (group g = GBASE + local: chunk c = g mod S).  With a
    // non-power-of-two GT, the final GT % S groups have no complete K-split
    // tile.  The O4 drafter FC uses G=6144, S=4096; only groups 0..4095 belong
    // to its one output tile per round.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) x_re <= 0;
        else if (!active) x_re <= 0;
        else
            for (gi = 0; gi < G; gi = gi + 1)
                x_re[gi] <= (gi < NPX) && (((gb + gi) >> split_r) < (GT >> split_r));
    end
    always @(posedge clk) begin
        for (gi = 0; gi < NPX; gi = gi + 1)
            x_addr[gi*AW +: AW] <= xc + ((gb + gi) & ((1 << split_r) - 1)) * xcs_r;
    end
    // Tag of the element issued this cycle (registered alongside the address).
    reg          e_v, e_first, e_last, e_oen, e_amax, e_wsrc, e_round, e_mmode;
    reg [3:0]    e_split;
    //: KV ops: group g's element k*S + c lies past K -> its operands are zeroed
    //: (a +0 product; the sum is unchanged, so a ragged last chunk is exact)
    reg [G-1:0]  e_gm;
    reg          e_rmax, e_opend;
    reg [2:0]    e_j;
    reg [AW-1:0] e_mbase;
    reg [AW-1:0] e_oa, e_ots;
    reg [NW:0]   e_nb, e_lb, e_rem;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) e_v <= 1'b0;
        else e_v <= active;
    end
    //: the element's round (SCALE_LOCAL scale addressing), beside the tag
    reg [NW-1:0] e_t, s1_t, s1b_t, s2_t, s3_t;
    wire [NW-1:0] m_t;
    ot_hdc_delay #(.W(NW), .D(MEM_EXTRA)) u_mtt (.clk(clk), .rst_n(rst_n), .d(e_t), .q(m_t));
    always @(posedge clk) begin e_t <= t; s1_t <= m_t; s1b_t <= s1_t; s2_t <= s1b_t; s3_t <= s2_t; end
    always @(posedge clk) begin
        e_first <= (k == 0); e_last <= k_last;
        e_oen <= oen_r; e_amax <= amax_r; e_wsrc <= wsrc_r; e_round <= round_r; e_mmode <= mmode_r;
        e_split <= split_r; e_oa <= oa; e_ots <= ots_r; e_nb <= nb; e_lb <= lb;
        e_rem <= {1'b0, nout_r};
        e_rmax <= rmax_r; e_j <= j; e_mbase <= mbase_r;
        e_opend <= t_last && k_last && j_last;           // the op's last element
    end
    // -- S1 (memories answer) -> S2 (capture) -> S3 (condition) -----------------
    localparam integer TW = 1 + 1 + 1 + 1 + 1 + 4 + AW + AW + 3 * (NW + 1) + 1 + 3 + 1 + AW + AW;
    wire [TW-1:0] e_tag = {e_last, e_oen, e_amax, e_wsrc, e_mmode, e_split, e_oa, e_ots, e_nb, e_lb, e_rem,
                           e_rmax, e_j, e_opend, e_mbase, scale_base_r};
    reg  [TW-1:0] s1_tag, s1b_tag, s2_tag, s3_tag;
    //: MEM_EXTRA: the element's tags wait for its later memory data
    wire [TW-1:0] m_tag;
    wire [G-1:0]  m_gm;
    wire          m_first, m_wsrc, m_round;
    //: (D >= 2 for ot_hdc_vline; the bits past MEM_EXTRA duplicate s1_v / s1b_v)
    wire [MEM_EXTRA+2:0] m_vl;
    ot_hdc_vline #(.D(MEM_EXTRA + 2)) u_mv (.clk(clk), .rst_n(rst_n), .v(e_v), .vd(m_vl));
    wire          m_v = m_vl[MEM_EXTRA];
    ot_hdc_delay #(.W(TW + G + 3), .D(MEM_EXTRA)) u_mt (.clk(clk), .rst_n(rst_n),
        .d({e_tag, e_gm, e_first, e_wsrc, e_round}), .q({m_tag, m_gm, m_first, m_wsrc, m_round}));
    reg          s1_v, s1b_v, s2_v, s3_v, s1_first, s1b_first, s2_first, s3_first;
    reg          s1b_wsrc, s1b_round;
    reg          s1_wsrc, s1_round, s2_round, s3_wsrc;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 0; s1b_v <= 0; s2_v <= 0; s3_v <= 0; end
        else begin s1_v <= m_v; s1b_v <= s1_v; s2_v <= s1b_v; s3_v <= s2_v; end
    end
    always @(posedge clk) begin
        s1_tag <= m_tag; s1b_tag <= s1_tag; s2_tag <= s1b_tag; s3_tag <= s2_tag;
        s1_first <= m_first; s1b_first <= s1_first; s2_first <= s1b_first; s3_first <= s2_first;
        s1_wsrc <= m_wsrc; s1_round <= m_round; s1b_wsrc <= s1_wsrc; s1b_round <= s1_round;
        s2_round <= s1b_round;
        s3_wsrc <= s2_tag[TW-4];
    end
    wire [TW-1:0] a_tag;
    generate if (PORTS) begin : g_atag
        ot_hdc_delay #(.W(TW), .D(SD + OD + XDD)) u_tag (.clk(clk), .rst_n(rst_n), .d(s3_tag), .q(a_tag));
    end else begin : g_no_atag
        assign a_tag = {TW{1'b0}};
    end endgenerate
    wire [SD+OD+XDD:0] vline;
    ot_hdc_vline #(.D(SD + OD + XDD)) u_v (.clk(clk), .rst_n(rst_n), .v(s3_v), .vd(vline));
    wire [MUL_LAT:0] fl_first;
    ot_hdc_vline #(.D(MUL_LAT)) u_first (.clk(clk), .rst_n(rst_n), .v(s3_first && s3_v), .vd(fl_first));
    // split and KV flag reach the tree's first level here 10 cycles after S3
    // (PART 2: its first level, LV0 + 1, TL*LV0 + XD cycles later)
    wire [3:0] t_split;
    ot_hdc_delay #(.W(4), .D(SD + TL * LV0 + XDD)) u_ts (.clk(clk), .rst_n(rst_n), .d(s3_tag[TW-6 -: 4]), .q(t_split));

    wire [GI*W*32-1:0] raw_res; // unobserved datapath, deliberately undriven
    wire raw_v = vline[SD + OD + XDD];
    wire raw_last, raw_oen, raw_amax, raw_wsrc, raw_mmode;
    wire [3:0] raw_split;
    wire [AW-1:0] raw_oa, raw_ots, raw_mbase, raw_sbase;
    wire [NW:0] raw_nb, raw_lb, raw_nout;
    wire raw_rmax, raw_opend;
    wire [2:0] raw_j;
    assign {raw_last, raw_oen, raw_amax, raw_wsrc, raw_mmode, raw_split,
            raw_oa, raw_ots, raw_nb, raw_lb, raw_nout,
            raw_rmax, raw_j, raw_opend, raw_mbase, raw_sbase} = a_tag;
    wire [GR*W*32-1:0] res;
    wire [TW-1:0] result_tag;
    wire result_v;
    wire [GR*W-1:0] scale_faults;
    wire [7:0] post_pending;
    generate if (INT8_WEIGHT != 0 && PORTS) begin : g_post_scale
        wire [TW-1:0] tag_d5, pre_tag;
        wire [5:0] vd;
        wire [SD-2+OD+XDD:0] pre_vline;
        wire pre_last, pre_oen, pre_amax, pre_wsrc, pre_mmode;
        wire [3:0] pre_split;
        wire [AW-1:0] pre_oa, pre_ots, pre_mbase, pre_sbase;
        wire [NW:0] pre_nb, pre_lb, pre_nout;
        wire pre_rmax, pre_opend;
        wire [2:0] pre_j;
        wire [GR*W*32-1:0] scaled;
        ot_hdc_delay #(.W(TW), .D(5)) u_tag (.clk(clk), .rst_n(rst_n), .d(a_tag), .q(tag_d5));
        ot_hdc_vline #(.D(5)) u_v (.clk(clk), .rst_n(rst_n), .v(raw_v), .vd(vd));
        ot_hdc_delay #(.W(TW), .D(SD-2+OD+XDD)) u_pretag (.clk(clk), .rst_n(rst_n),
            .d(s3_tag), .q(pre_tag));
        wire [NW-1:0] pre_t;
        if (SCALE_LOCAL != 0) begin : g_pret
            ot_hdc_delay #(.W(NW), .D(SD-2+OD+XDD)) u_pret (.clk(clk), .rst_n(rst_n), .d(s3_t), .q(pre_t));
        end else begin : g_nopret
            assign pre_t = {NW{1'b0}};
        end
        ot_hdc_vline #(.D(SD-2+OD+XDD)) u_prev (.clk(clk), .rst_n(rst_n),
            .v(s3_v), .vd(pre_vline));
        assign {pre_last, pre_oen, pre_amax, pre_wsrc, pre_mmode, pre_split,
                pre_oa, pre_ots, pre_nb, pre_lb, pre_nout,
                pre_rmax, pre_j, pre_opend, pre_mbase, pre_sbase} = pre_tag;
        wire [GOUT-1:0] pre_scale_active;
        genvar pg;
        for (pg = 0; pg < NPG; pg = pg + 1) begin : g_scale_request_mask
            // A group with no output rows cannot need a scale word. This also
            // drops the incomplete G % S tail in a K-split operation.
            assign pre_scale_active[pg] = pre_vline[SD-2+OD+XDD] && pre_last && !pre_wsrc &&
                ((gb + pg) < (GT >> pre_split)) &&
                (pre_mmode ? (pre_lb + (gb + pg)*W < pre_nout) :
                             (pre_nb + (gb + pg)*(W*IL) < pre_nout));
        end
        if (NPG < GOUT) begin : g_scale_request_pruned
            assign pre_scale_active[GOUT-1:NPG] = 0;
        end
        // pre_tag precedes a_tag by two cycles. The registered request becomes
        // visible to the synchronous ROM at the next edge, and scale_q is
        // stable when raw_res enters the FP32 multiplier at the following edge.
        integer sg;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin scale_re <= 1'b0; scale_gre <= 0; end
            else begin scale_re <= |pre_scale_active; scale_gre <= pre_scale_active; end
        end
        always @(posedge clk) begin
            for (sg = 0; sg < NPG; sg = sg + 1)
                scale_addr[sg*AW +: AW] <= !pre_scale_active[sg] ? pre_sbase :
                    (SCALE_LOCAL != 0) ? pre_sbase + pre_t * IL + pre_j :
                                         pre_sbase + (pre_nb >> LW) + (gb + sg) * IL;
        end
        assign res = scaled;
        assign result_tag = tag_d5;
        assign result_v = vd[5];
        assign post_pending = {2'b00, vd};
    end else begin : g_no_post_scale
        assign scale_re = 1'b0;
        assign scale_gre = 0;
        assign scale_addr = 0;
        assign scale_faults = 0;
        assign res = raw_res[GR*W*32-1:0];
        assign result_tag = a_tag;
        assign result_v = PORTS ? raw_v : 1'b0;
        assign post_pending = 0;
    end endgenerate
    // -- results -------------------------------------------------------------------
    reg           ov1, ov2;
    reg  [GR-1:0]  o_we1, o_we2;
    reg  [GR*AW-1:0] o_addr1, o_addr2;
    reg  [GR*W-1:0]  o_mask1, o_mask2;
    reg  [GR*W*32-1:0] o_data1, o_data2;
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
    wire [$clog2(GT):0] r_ports = GT >> r_split;
    reg  [GR*W-1:0] r_mask;
    integer q, ql;
    always @(*) begin
        r_mask = {GR*W{1'b0}};
        for (q = 0; q < NPG; q = q + 1)
            for (ql = 0; ql < W; ql = ql + 1)
                r_mask[q*W + ql] = (gb + q < r_ports) &&
                    (r_mmode ? (r_lb + (gb + q) * W + ql < r_nout) : (r_nb + (gb + q) * (W * IL) + ql < r_nout));
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ov1 <= 1'b0; o_we1 <= 0;
        end else begin
            ov1 <= r_v && r_last;
            for (q = 0; q < GR; q = q + 1)
                o_we1[q] <= (q < NPG) && r_v && r_last && r_oen && (gb + q < r_ports);
        end
    end
    always @(posedge clk) begin
        for (q = 0; q < NPG; q = q + 1)
            o_addr1[q*AW +: AW] <= r_oa + (gb + q) * r_ots;
        o_mask1 <= r_mask; o_data1 <= res;
    end
    //: A second output register: the result bus is 2,048 bits wide and its
    //: flops sit by the lanes, so the pins get flops of their own.  ov, and the
    //: chaining progress counted from it, move with the data.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ov2 <= 1'b0; o_we2 <= 0; end
        else begin ov2 <= ov1; o_we2 <= o_we1; end
    end
    always @(posedge clk) begin
        o_addr2 <= o_addr1; o_mask2 <= o_mask1; o_data2 <= o_data1;
    end
    //: ORD further stages carry the result write to the vector memory (the
    //: spine wire from the port groups); ov and progress move with the data.
    //: (a line of ORD + 2 >= 2 stages: ot_hdc_vline needs D >= 2; stages above ORD are unused)
    wire [ORD+2:0] ov_line;
    ot_hdc_vline #(.D(ORD + 2)) u_ovl (.clk(clk), .rst_n(rst_n), .v(ov2), .vd(ov_line));
    wire [GR-1:0]      o_we_r;
    wire [GR*AW-1:0]   o_addr_r;
    wire [GR*W-1:0]    o_mask_r;
    wire [GR*W*32-1:0] o_data_r;
    generate if (ORD > 0) begin : g_ord
        ot_hdc_delay #(.W(GR), .D(ORD), .RESET(1)) u_owe (.clk(clk), .rst_n(rst_n), .d(o_we2), .q(o_we_r));
        ot_hdc_delay #(.W(GR*AW + GR*W + GR*W*32), .D(ORD)) u_od (.clk(clk), .rst_n(rst_n),
            .d({o_addr2, o_mask2, o_data2}), .q({o_addr_r, o_mask_r, o_data_r}));
        assign ov = ov_line[ORD];
    end else begin : g_no_ord
        assign ov = ov2; assign o_we_r = o_we2;
        assign o_addr_r = o_addr2; assign o_mask_r = o_mask2; assign o_data_r = o_data2;
    end endgenerate
    //: groups above the result ports never write (their ports are constant)
    generate if (GR < GOUT) begin : g_ozx
        assign o_we = {{(GOUT - GR){1'b0}}, o_we_r};
        assign o_addr = {{((GOUT - GR) * AW){1'b0}}, o_addr_r};
        assign o_mask = {{((GOUT - GR) * W){1'b0}}, o_mask_r};
        assign o_data = {{((GOUT - GR) * W * 32){1'b0}}, o_data_r};
    end else begin : g_ofull
        assign o_we = o_we_r; assign o_addr = o_addr_r; assign o_mask = o_mask_r; assign o_data = o_data_r;
    end endgenerate

    genvar lv;
    // -- argmax: a registered compare tree over the round-slot, then a running best --
    // Keys order binary32 values as unsigned integers (zeros are canonical +0);
    // on equal keys the lower row wins, in the tree and across cycles.
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    localparam integer NL = NPG * W;                 // leaves: the result-port lanes
    localparam integer LV = $clog2(NL);
    localparam integer AN = 1 << LV;             // pad non-power-of-two lane counts with invalid leaves
    //: The key is an invertible function of the value, so the tree carries only
    //: the key and recovers the value at the end (half the tree's wiring).
    localparam integer CW = 1 + 32 + NW;            // {valid, key, row}
    wire [CW*AN-1:0] alv [0:LV];
    reg  [LV:0] tv;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) tv <= 0;
        else tv <= {tv[LV-1:0], r_v && r_last && (r_amax || r_rmax)};
    end
    //: the result's op kind, slot and the op's end travel beside the tree
    wire [1+3+1+AW-1:0] ttag;
    ot_hdc_delay #(.W(1 + 3 + 1 + AW), .D(LV + 1)) u_ttag (.clk(clk), .rst_n(rst_n),
        .d({r_rmax, r_j, r_opend && r_last, r_mbase}), .q(ttag));
    wire          t_rmax, t_opend;
    wire [2:0]    t_j;
    wire [AW-1:0] t_mbase;
    assign {t_rmax, t_j, t_opend, t_mbase} = ttag;
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
            else if (tv[LV] && !t_rmax && top_v && (!am_any || top_key > best_key ||
                                         (top_key == best_key && top_idx < am_idx))) begin
                am_any <= 1'b1; best_key <= top_key; am_idx <= top_idx; am_val <= top_val;
            end
        end
    end

    // -- per-slot maxima (RMAX: the attention rows' max, taken as the scores
    // emerge): slot j's key is the max over the op's rounds of the tree's top;
    // after the op's last result the IL maxima are written as one masked word.
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
    localparam [ORD+2:0] OMASK = (1 << (ORD + 1)) - 2;     // result-write stages 1..ORD
    wire ord_busy = |(ov_line & OMASK);
    wire idle_c = !active && !pend && !e_v && !(|m_vl) && !s1_v && !s1b_v && !s2_v && !s3_v && !(|vline) && !(|post_pending) && !(|tv) && !ov1
                  && !ov2 && !ord_busy && !mx_we;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) idle <= 1'b1;
        else idle <= idle_c && !(go && ready);
    end
endmodule
module ot_qwen_w12_kadd #(parameter integer W = 24) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    output wire [W-1:0] s
);
    wire c;
    ot_qwen_w12_ksa #(.W(W)) u (.a(a), .b(b), .cin(1'b0), .s(s), .cout(c));
endmodule

// N rows of W bits reduced carry-save (3:2 per level) to two, kept-level boundaries
module ot_qwen_w12_csa_tree #(parameter integer W = 24, parameter integer N = 8) (
    input  wire [N*W-1:0] rows,
    output wire [W-1:0]   s,
    output wire [W-1:0]   c
);
    function automatic integer nxt(input integer n);
        nxt = (n <= 2) ? n : 2 * (n / 3) + (n % 3);
    endfunction
    function automatic integer cnt(input integer l);
        integer i, n;
        begin n = N; for (i = 0; i < l; i = i + 1) n = nxt(n); cnt = n; end
    endfunction
    function automatic integer depth(input integer d);
        integer n, l;
        begin n = N; l = 0; while (n > 2) begin n = nxt(n); l = l + 1; end depth = l; end
    endfunction
    localparam integer L = depth(0);
    genvar l, i;
    generate
        for (l = 0; l <= L; l = l + 1) begin : g_l
            localparam integer NL = cnt(l);
            (* keep *) wire [((NL > 0) ? NL : 1)*W-1:0] r;
            if (l == 0) begin : g0
                assign r = rows;
            end else begin : gn
                localparam integer NP = cnt(l - 1);
                for (i = 0; i < NP / 3; i = i + 1) begin : g_c
                    wire [W-1:0] x = g_l[l-1].r[(3*i)*W +: W], y = g_l[l-1].r[(3*i+1)*W +: W],
                                 z = g_l[l-1].r[(3*i+2)*W +: W];
                    assign r[(2*i)*W +: W] = x ^ y ^ z;
                    assign r[(2*i+1)*W +: W] = ((x & y) | (x & z) | (y & z)) << 1;
                end
                for (i = 0; i < NP % 3; i = i + 1) begin : g_p
                    assign r[(2*(NP/3)+i)*W +: W] = g_l[l-1].r[(3*(NP/3)+i)*W +: W];
                end
            end
        end
    endgenerate
    assign s = g_l[L].r[0 +: W];
    assign c = (cnt(L) > 1) ? g_l[L].r[W +: W] : {W{1'b0}};
endmodule

// the sum (mod 2^W) of N rows: carry-save tree, then a kept prefix add
module ot_qwen_w12_ksum #(parameter integer W = 24, parameter integer N = 8) (
    input  wire [N*W-1:0] rows,
    output wire [W-1:0]   s
);
    wire [W-1:0] a, b;
    ot_qwen_w12_csa_tree #(.W(W), .N(N)) u_t (.rows(rows), .s(a), .c(b));
    ot_qwen_w12_kadd #(.W(W)) u_a (.a(a), .b(b), .s(s));
endmodule
