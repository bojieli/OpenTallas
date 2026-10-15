`timescale 1ns/1ps
module ot_qwen_tt_core_spctl #(
    parameter integer W  = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer INT8_SCALE_WCS_BASE = 1,
    parameter integer GT = 80,
    parameter integer TG = 4,
    parameter integer SMIN = 3,
    parameter integer SMAX = 5,
    parameter integer TCUT = 3,
    parameter integer XD = 0,
    parameter integer XVM = 0,
    parameter integer ORD = 0,
    parameter integer SCALE_LOCAL = 0,
    parameter integer PQ = 4,
    parameter integer ACC_LAT = 5,
    parameter integer TREE_LAT = 3,
    parameter integer FAST_ISSUE = 0,
    parameter integer KV_PREP = 0,
    parameter integer MUL_LAT = 5,
    parameter integer SCALE_LAT = 5,
    parameter integer LANDED = 0,      // qwen-vm-me: progress / idle count LANDED result bursts (land_cnt), 0 = base
    // qwen-band-integrate 2026-10-08 (default 0 = base):
    //   RX    extra edges between the tree lanes' level-(LG-1) words and the port elements (the band-lane blocks'
    //         +5 + 2 LNK): the element tags (p_v_e2 / p_f_e2), the scale requests, the result valid, the argmax top
    //         and the argmax-accumulator clear move RX edges later, so every result-side output is the base's
    //         delayed RX edges (the per-level tree selects t_sel_e / t_tv_e are unchanged: the bands are lane-timed).
    //   BANDF 1: the result-port positions are BAND-LOCAL (ot_qfd_band_lanes frame): position p = 8b + k holds group
    //         g = b * 2^(TCUT+3-s) + k (k < 2^(TCUT+3-s)) at split s <= TCUT+3, else g = k on band 0 (k < GT >> s);
    //         the scale requests use g (rows, scale address, in-range test).  Needs GT = 48 << TCUT, SMIN >= TCUT.
    parameter integer RX = 0,
    //   RXA   the argmax-accumulator clear's delay (default RX): the result shift relative to the op's ISSUE, which is
    //         RX minus any reduction of XD (a caller that makes the tree selects early by lowering XD passes RXA itself)
    parameter integer RXA = RX,
    parameter integer BANDF = 0,
    // AMR = 1 (safe-qwen S-D1, 2026-10-08; 0 = unchanged): the argmax tree's top word {top_v, key, idx} and its valid /
    // rmax tag are registered AT the accumulator, and the accumulator clear moves with them, so the top-vs-best compare
    // (u_bgt) and the am_idx / best_key / am_val update are local (routed qfd_sp_tree_top_b: am_idx -> u_bgt -> am_idx
    // 2,228 ps, 6 logic + ~40 wire buffers).  The argmax result (am_any / am_idx / am_val) settles one edge later.
    parameter integer AMR = 0,
    // SPRE (redesign-qwen 2026-10-09; 0 = unchanged): the post-scale request path (pretag ring read -> per-group in-range
    // compare / multiply -> scale_active -> scale_addr add, tree-top TT -1,584 / -1,592) is cut by one register stage:
    // the tags are delayed PD - 1 (balanced-OR ring read), the per-group request is registered, and scale_re / gre / addr
    // are formed from it on the edge the base forms them.  0 cycles, same outputs every edge.
    parameter integer SPRE = 0,
    parameter integer XADDR = 1,         // el1011-q-seq: 0 = no per-port x_re / x_addr (callers on the descriptor form x_dv/x_dc/x_dcs;
                                         //   62.7 k flops + shared CSA rows of fan-out 2-4 k in ctlm_i, all unobserved)
    parameter integer RDMEM = 0,         // el1011-q-seq: 1 = the long tag delay lines (u_tag / u_pretag) in SRAM (rdelay MEM)
    parameter integer SC = 0,            // el1011-q-seq setup cuts (exact, 0 cycles; bit 0 on, bits 1-3 negative controls): fpapk-4e9afc303 classes
                                         //   (a) pre-scale compare from flops: u_pretag one edge shorter + a register, the two differences
                                         //   (nout - nb / nout - lb) as kept KS in that stage, the per-group test a kept compare against
                                         //   pgi*K (BANDF only; bit 2 mutant: >= for >); (b) mx write: lane rotate / slot select
                                         //   pre-decoded from the ring output and the slot maximum rk[t_j] / rseen[t_j] registered with
                                         //   write forwarding (bit 1 mutant: no forwarding); (c) scale_addr = b_sbase + b_off, the
                                         //   offset added one stage earlier (bit 3 mutant: offset without nbs)
    parameter integer AMI = 0,           // el1011-q-seq (coordinator 10-11 decision, +1 argmax-loop cycle): 1 = p_am pin register (the die
                                         //   word lands in a flop at the ctlm pin; textbook class 3, routed p_am -> argmax -58 ps), and every
                                         //   result-side argmax / mx timing (tree valid line tv, tag line u_ttag, accumulator clear RXA) one
                                         //   edge later to match: am_* / mx_* / idle settle one edge later, the result sequence is unchanged;
                                         //   2 = negative control (the register without the +1 compensation: MUST FAIL)
    parameter integer PK = 0             // el1011-q-seq (exact, 0 cycles): 1 = progress subtract as a kept Kogge-Stone (was a 16-b MAJ ripple behind the
                                         //   land_cnt pin flop) and the u_ttag line read from a register (ring D-1 + output flop: t_* straight from flops); 2 = negative control (KS carry-in dropped: progress one low)
) (
    input  wire              clk,
    input  wire              rst_n,
    output wire [(1+1+1+1+1+4+AW+AW+3*(NW+1)+1+3+1+AW+AW)-1:0] scale_tag,
    output wire scale_v,
    output wire [NW-1:0] scale_t,

    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [15:0]       land_cnt,  // LANDED: result bursts written into the vector memory since reset (ot_qfd_res_merge)
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
    output reg               kv_re,
    // scale requests (ONE CYCLE EARLIER than ot_qwen_me_spine_w12's)
    // x reads and the x network's first (select) stage
    output reg  [(1<<SMAX)-1:0]    x_re,
    output reg  [(1<<SMAX)*AW-1:0] x_addr,
    input  wire [(1<<SMAX)*32-1:0] x_q,
    output reg  [(1<<SMAX)*32-1:0] xl0,
    // the x read as a descriptor (qwen-rtl-finish 2026-10-07, die master qfd_sp_tree_top): x_re[c] = x_dv for every
    // enabled port, x_addr[c] = x_dc + (c mod 2^x_dsp) * x_dcs (mod 2^AW), the x network select stage's split = x_dsp
    // (op_split, before its 2 + XVM delay).  Equivalent to x_re / x_addr; a caller uses one or the other.
    output reg               x_dv,
    output reg  [AW-1:0]     x_dc,
    output reg  [AW-1:0]     x_dcs,
    output wire [3:0]        x_dsp,
    // tree elements: per level (index = level) the hold/sum select and the adder valid, one cycle early
    output wire [$clog2(GT):0] t_sel_e,
    output wire [$clog2(GT):0] t_tv_e,
    input  wire [W-1:0]        tr_fault,       // the tree elements' registered faults
    // port elements: the element tag fields and valid two cycles early; their argmax nodes and faults
    output wire              p_v_e2,
    output wire [1+1+1+1+4+AW+AW+3*(NW+1)-1:0] p_f_e2,
    input  wire [((GT >> SMIN) / PQ)*(1+32+NW)-1:0] p_am,
    input  wire [((GT >> SMIN) / PQ)-1:0]   p_fault,
    input  wire              fab_fault,
    output wire              ov,
    output reg  [NW-1:0]     am_idx,
    output reg  [31:0]       am_val,
    output reg               am_any,
    output reg               mx_we,
    output reg  [AW-1:0]     mx_addr,
    output reg  [W-1:0]      mx_mask,
    output reg  [W*32-1:0]   mx_data,
    output reg  [15:0]       progress,
    output wire              fault
);
    // the PART 2 engine top of ot_qwen_w12_matvec_part, fixed here
    localparam integer G = GT;
    localparam integer PART = 2;
    localparam integer GBASE = 0;
    localparam integer GBASE_PORT = 0;
    localparam integer INT8_WEIGHT = 1;
    localparam integer NX = 1 << SMAX;
    localparam integer MEM_EXTRA = 0;
    localparam integer GOUT = GT >> SMIN;
    wire [31:0] i_gbase = 32'd0;
    wire        active_o;
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

    // -- x reads -------------------------------------------------------------------------------------------
    //: accepted go: the edge that latches split_r / xcs_r (pend is never set on the FAST_ISSUE = 0 loop)
    wire go_acc = go && !active && !pend;
    //: x_re: the per-port enable (port < GT/S tiles of chunks) is a function of the op's split only -> latched at the go
    reg [NPX-1:0] xre_en;
    always @(posedge clk)
        if (go_acc)
            for (gi = 0; gi < NPX; gi = gi + 1)
                xre_en[gi] <= (((gb + gi) >> i_split) < (GT >> i_split));
    generate if (XADDR != 0) begin : g_xre
    always @(posedge clk or negedge rst_n) begin
            if (!rst_n) x_re <= 0;
            else if (!active) x_re <= 0;
            else
                for (gi = 0; gi < NX; gi = gi + 1)
                    x_re[gi] <= (gi < NPX) && xre_en[gi];
        end
    end else begin : g_noxre
        always @(*) x_re = '0;
    end endgenerate
    //: descriptor form of the same read (registered on the same edges as x_re / x_addr)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) x_dv <= 1'b0;
        else x_dv <= active;
    end
    always @(posedge clk) begin
        x_dc <= xc;
        if (go_acc) x_dcs <= i_xcs;
    end
    //: x_addr = xc + c * xcs (c = port mod S): c * xcs is constant through the op, latched at the go as the
    //: carry-save pair of its shifted rows (one row per set bit b of the port number, kept when b < split)
    function automatic integer pc_below(input integer v, input integer b);
        integer i;
        begin pc_below = 0; for (i = 0; i < b; i = i + 1) pc_below = pc_below + ((v >> i) & 1); end
    endfunction
    genvar xg, xb;
    generate if (XADDR == 0) begin : g_noxa
        always @(*) x_addr = '0;
    end else begin : g_xaddr
        for (xg = 0; xg < NX; xg = xg + 1) begin : g_xa
            localparam integer NB = pc_below(xg, 16);
            if (xg >= NPX) begin : g_none
                always @(posedge clk) x_addr[xg*AW +: AW] <= {AW{1'b0}};
            end else if (NB == 0) begin : g_zero
                always @(posedge clk) x_addr[xg*AW +: AW] <= xc;
            end else begin : g_off
                wire [NB*AW-1:0] rows;
                for (xb = 0; xb < 16; xb = xb + 1) begin : g_r
                    if ((xg >> xb) & 1) begin : g_set
                        assign rows[pc_below(xg, xb)*AW +: AW] = (xb < i_split) ? (i_xcs << xb) : {AW{1'b0}};
                    end
                end
                wire [AW-1:0] r_s, r_c;
                ot_qwen_w12_csa_tree #(.W(AW), .N(NB)) u_cs (.rows(rows), .s(r_s), .c(r_c));
                reg  [AW-1:0] o_s, o_c;
                always @(posedge clk) if (go_acc) begin o_s <= r_s; o_c <= r_c; end
                wire [AW-1:0] a_s = xc ^ o_s ^ o_c;
                wire [AW-1:0] a_c = ((xc & o_s) | (xc & o_c) | (o_s & o_c)) << 1;
                wire [AW-1:0] a_y;
                ot_qwen_w12_kadd #(.W(AW)) u_ka (.a(a_s), .b(a_c), .s(a_y));
                always @(posedge clk) x_addr[xg*AW +: AW] <= a_y;
            end
        end
    end endgenerate

    // -- element tags (as ot_qwen_w12_matvec_part; no lanes here) -----------------------------------------
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
        e_opend <= t_last && k_last && j_last;
    end
    localparam integer TW = 1 + 1 + 1 + 1 + 1 + 4 + AW + AW + 3 * (NW + 1) + 1 + 3 + 1 + AW + AW;
    wire [TW-1:0] e_tag = {e_last, e_oen, e_amax, e_wsrc, e_mmode, e_split, e_oa, e_ots, e_nb, e_lb, e_rem,
                           e_rmax, e_j, e_opend, e_mbase, scale_base_r};
    reg  [TW-1:0] s1_tag, s1b_tag, s2_tag, s3_tag;
    wire [TW-1:0] m_tag;
    wire          m_first, m_wsrc, m_round;
    wire [MEM_EXTRA+2:0] m_vl;
    ot_hdc_vline #(.D(MEM_EXTRA + 2)) u_mv (.clk(clk), .rst_n(rst_n), .v(e_v), .vd(m_vl));
    wire          m_v = m_vl[MEM_EXTRA];
    ot_hdc_delay #(.W(TW + 3), .D(MEM_EXTRA)) u_mt (.clk(clk), .rst_n(rst_n),
        .d({e_tag, e_first, e_wsrc, e_round}), .q({m_tag, m_first, m_wsrc, m_round}));
    reg          s1_v, s1b_v, s2_v, s3_v;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 0; s1b_v <= 0; s2_v <= 0; s3_v <= 0; end
        else begin s1_v <= m_v; s1b_v <= s1_v; s2_v <= s1b_v; s3_v <= s2_v; end
    end
    always @(posedge clk) begin
        s1_tag <= m_tag; s1b_tag <= s1_tag; s2_tag <= s1b_tag; s3_tag <= s2_tag;
    end
    //: a_tag = s3_tag + (SD + OD + XDD); the port elements take it TWO cycles early (a_tag_e2) and register it twice
    localparam integer AD = SD + OD + XDD + RX;
    wire [TW-1:0] a_tag_e2;
    reg  [TW-1:0] a_tag_e1, a_tag;
    ot_qwen_me_rdelay_w12 #(.W(TW), .D(AD - 2), .MEM(RDMEM)) u_tag (.clk(clk), .rst_n(rst_n), .d(s3_tag), .q(a_tag_e2));
    always @(posedge clk) begin a_tag_e1 <= a_tag_e2; a_tag <= a_tag_e1; end
    wire [AD:0] vline;
    ot_hdc_vline #(.D(AD)) u_v (.clk(clk), .rst_n(rst_n), .v(s3_v), .vd(vline));
    assign p_v_e2 = vline[AD - 2];
    wire          pf_last, pf_oen, pf_amax, pf_wsrc, pf_mmode, pf_rmax, pf_opend;
    wire [3:0]    pf_split;
    wire [AW-1:0] pf_oa, pf_ots, pf_mbase, pf_sbase;
    wire [NW:0]   pf_nb, pf_lb, pf_nout;
    wire [2:0]    pf_j;
    assign {pf_last, pf_oen, pf_amax, pf_wsrc, pf_mmode, pf_split, pf_oa, pf_ots, pf_nb, pf_lb, pf_nout,
            pf_rmax, pf_j, pf_opend, pf_mbase, pf_sbase} = a_tag_e2;
    assign p_f_e2 = {pf_last, pf_oen, pf_wsrc, pf_mmode, pf_split, pf_oa, pf_ots, pf_nb, pf_lb, pf_nout};

    // -- split tree control: level lv's input split (split_at), its select and adder valid ----------------
    //: split_at[lv] at level lv+1's input; sat_e[lv] the same value one cycle earlier
    wire [LG*4+3:0] split_at, sat_e;
    wire [3:0] t_split, t_split_e;
    localparam integer D0 = SD + TL * LV0 + XDD;
    ot_qwen_me_rdelay_w12 #(.W(4), .D(D0 - 1)) u_ts (.clk(clk), .rst_n(rst_n), .d(s3_tag[TW-6 -: 4]), .q(t_split_e));
    reg [3:0] t_split_r;
    always @(posedge clk) t_split_r <= t_split_e;
    assign t_split = t_split_r;
    assign split_at[4*LV0+3 -: 4] = t_split;
    assign sat_e[4*LV0+3 -: 4] = t_split_e;
    genvar lv;
    generate
        for (lv = 0; lv <= LG; lv = lv + 1) begin : g_lctl
            if (lv <= LV0) begin : g_none
                assign t_sel_e[lv] = 1'b0;
                assign t_tv_e[lv] = 1'b0;
            end else begin : g_lvl
                //: sp_sel = split_at[lv-1] + TA (the select when the level's sums emerge); sp_e one cycle earlier
                wire [3:0] sp_e;
                reg  [3:0] sp_sel, sp_out;
                ot_hdc_delay #(.W(4), .D(TA - 1)) u_sd (.clk(clk), .rst_n(rst_n), .d(split_at[4*lv-1 -: 4]), .q(sp_e));
                always @(posedge clk) begin sp_sel <= sp_e; sp_out <= sp_sel; end
                assign split_at[4*lv+3 -: 4] = sp_out;
                assign sat_e[4*lv+3 -: 4] = sp_sel;
                assign t_sel_e[lv] = (sp_e >= lv);
                assign t_tv_e[lv] = vline[SD + TL*(lv-1) + XDD - 1] && (sat_e[4*lv-1 -: 4] >= lv);
            end
        end
    endgenerate

    assign scale_tag=s3_tag;
    assign scale_v=s3_v;
    assign scale_t=s3_t;

    // -- result tag (a_tag + SCALE_LAT, the post-scale multiply) and the result valid ---------------------------------
    wire [TW-1:0] result_tag;
    wire [SCALE_LAT:0] vd;
    ot_qwen_me_rdelay_w12 #(.W(TW), .D(SCALE_LAT)) u_rtag (.clk(clk), .rst_n(rst_n), .d(a_tag), .q(result_tag));
    ot_hdc_vline #(.D(SCALE_LAT)) u_rv (.clk(clk), .rst_n(rst_n), .v(vline[AD]), .vd(vd));
    wire [SCALE_LAT:0] post_pending = vd;
    wire          r_v = vd[SCALE_LAT];
    wire          r_last, r_oen, r_amax, r_wsrc, r_mmode;
    wire [3:0]    r_split;
    wire [AW-1:0] r_oa, r_ots;
    wire [NW:0]   r_nb, r_lb, r_nout;
    wire          r_rmax, r_opend;
    wire [2:0]    r_j;
    wire [AW-1:0] r_mbase, r_sbase;
    assign {r_last, r_oen, r_amax, r_wsrc, r_mmode, r_split, r_oa, r_ots, r_nb, r_lb, r_nout,
            r_rmax, r_j, r_opend, r_mbase, r_sbase} = result_tag;

    // -- fault: the tree elements register their adders' faults (as fault_q[G] here); the port elements
    //: register their multipliers' faults (seen one cycle later than the monolithic engine's)
    reg  fq_t;
    reg  [3:0] range_q;
    reg  range_fault;
    reg  fault_in;
    reg  fault_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fq_t <= 1'b0; fault_r <= 1'b0; fault_in <= 1'b0; range_fault <= 1'b0; end
        else begin
            fault_in <= fab_fault;
            fq_t <= fault_in;
            fault_r <= fq_t | (|tr_fault) | (|p_fault) | split_fault;
            if (go && ready && (i_split > SMAX)) range_fault <= 1'b1;
        end
    end
    assign fault = fault_r | range_fault;

    // -- results: the valid line (the data are the port elements') ---------------------------------------------
    reg ov1, ov2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ov1 <= 1'b0; ov2 <= 1'b0; end
        else begin ov1 <= r_v && r_last; ov2 <= ov1; end
    end
    wire [ORD+2:0] ov_line;
    ot_hdc_vline #(.D(ORD + 2)) u_ovl (.clk(clk), .rst_n(rst_n), .v(ov2), .vd(ov_line));
    generate if (ORD > 0) begin : g_ord
        assign ov = ov_line[ORD];
    end else begin : g_no_ord
        assign ov = ov2;
    end endgenerate

    // -- argmax: levels LPT+1 .. LV over the port elements' level-LPT nodes ---------------------------------
    localparam integer NL = NPG * W;
    localparam integer LV = $clog2(NL);
    localparam integer AN = 1 << LV;
    localparam integer LPT = $clog2(PQ * W);
    localparam integer NPT = NPG / PQ;
    localparam integer CW = 1 + 32 + NW;
    wire [CW*AN-1:0] alv [LPT:LV];
    //: AMI: AMC = the +1 compensation (AMI 1 only; AMI 2 registers p_am without it); LVT = the tree-top valid tap
    localparam integer AMC = (AMI == 1) ? 1 : 0;
    localparam integer LVT = LV + AMC;
    reg  [LVT:0] tv;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) tv <= 0;
        else tv <= {tv[LVT-1:0], r_v && r_last && (r_amax || r_rmax)};
    end
    wire [1+3+1+AW-1:0] ttag;
    wire [1+3+1+AW-1:0] ttag_ew;     // SC (b): the ring output one edge before ttag (PK)
    wire [31:0] rk_jx;              // SC (b): rk[t_j] (registered under SCB)
    wire        rseen_jx;
    generate if (PK != 0 && LV >= 2) begin : g_ttreg
        // PK: the same LV + 1 edges as a ring of LV and a register, so the mx write stage starts from flops
        wire [1+3+1+AW-1:0] ttag_e;
        ot_qwen_me_rdelay_w12 #(.W(1 + 3 + 1 + AW), .D(LV + AMC), .TREE(((SC & 1) != 0) ? 1 : 0)) u_ttag (.clk(clk), .rst_n(rst_n),
            .d({r_rmax, r_j, r_opend && r_last, r_mbase}), .q(ttag_e));
        reg [1+3+1+AW-1:0] ttag_q;
        always @(posedge clk) ttag_q <= ttag_e;
        assign ttag = ttag_q;
        assign ttag_ew = ttag_e;
    end else begin : g_ttline
        assign ttag_ew = '0;
        ot_qwen_me_rdelay_w12 #(.W(1 + 3 + 1 + AW), .D(LV + 1 + AMC)) u_ttag (.clk(clk), .rst_n(rst_n),
            .d({r_rmax, r_j, r_opend && r_last, r_mbase}), .q(ttag));
    end endgenerate
    wire          t_rmax, t_opend;
    wire [2:0]    t_j;
    wire [AW-1:0] t_mbase;
    assign {t_rmax, t_j, t_opend, t_mbase} = ttag;
    genvar e, al;
    generate
        if (AMI != 0) begin : g_ami
            reg [CW*NPT-1:0] pam_pin;     // AMI: the p_am pin register (datapath, no reset; qualified by tv)
            always @(posedge clk) pam_pin <= p_am;
            assign alv[LPT][CW*NPT-1:0] = pam_pin;
        end else begin : g_amd
            assign alv[LPT][CW*NPT-1:0] = p_am;
        end
        if ((AN >> LPT) > NPT) begin : g_ppad
            assign alv[LPT][CW*AN-1:CW*NPT] = 0;
        end else if (AN > (AN >> LPT)) begin : g_ppad2
            assign alv[LPT][CW*AN-1:CW*(AN >> LPT)] = 0;
        end
        for (al = LPT + 1; al <= LV; al = al + 1) begin : g_alvl
            for (e = 0; e < (AN >> al); e = e + 1) begin : g_node
                wire [CW-1:0] x0 = alv[al-1][CW*(2*e) +: CW];
                wire [CW-1:0] x1 = alv[al-1][CW*(2*e+1) +: CW];
                //: key0 > key1, or equal keys and row0 < row1  <=>  {key0, ~row0} > {key1, ~row1}: one kept
                //: prefix carry (A > B <=> carry out of A + ~B), not Yosys's rippled > / == / <
                wire          gt, gt_c;
                wire [32+NW-1:0] gt_s;
                ot_qwen_w12_ksa #(.W(32 + NW)) u_gt (.a({x0[CW-2 -: 32], ~x0[NW-1:0]}), .b(~{x1[CW-2 -: 32], ~x1[NW-1:0]}),
                    .cin(1'b0), .s(gt_s), .cout(gt_c));
                assign gt = gt_c;
                wire          x0_wins = x0[CW-1] && (!x1[CW-1] || gt);
                reg  [CW-1:0] c;
                always @(posedge clk) c <= x0_wins ? x0 : x1;
                assign alv[al][CW*e +: CW] = c;
            end
            assign alv[al][CW*AN-1 : CW*(AN >> al)] = 0;
        end
    endgenerate
    wire [CW-1:0] top = alv[LV][CW-1:0];
    wire          top_v = top[CW-1];
    wire [31:0]   top_key = top[CW-2 -: 32];
    wire [31:0]   top_val = top_key[31] ? {1'b0, top_key[30:0]} : ~top_key;
    wire [NW-1:0] top_idx = top[NW-1:0];
    reg [31:0] best_key;
    //: AMR: the accumulator's own copy of the tree top (and its tag / clear), one edge after the tree
    wire [CW-1:0] atop;
    wire          a_tv, a_rmax, a_clr;
    //: the accumulator clear of an amax op at its issue (RXA > 0: RXA edges later, with the results)
    wire am_clr;
    generate if (RXA + AMC > 0) begin : g_amc
        ot_hdc_delay #(.W(1), .D(RXA + AMC), .RESET(1)) u_amc (.clk(clk), .rst_n(rst_n), .d(go && ready && i_amax), .q(am_clr));
    end else begin : g_amc0
        assign am_clr = go && ready && i_amax;
    end endgenerate
    //: top > best (key, then the lower index): the same kept carry as the tree nodes
    wire best_gt;
    wire [32+NW-1:0] best_s;
    generate if (AMR != 0) begin : g_amr
        reg [CW-1:0] atop_q;
        reg          a_tv_q, a_rmax_q, a_clr_q;
        always @(posedge clk) atop_q <= top;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin a_tv_q <= 1'b0; a_rmax_q <= 1'b0; a_clr_q <= 1'b0; end
            else begin a_tv_q <= tv[LVT]; a_rmax_q <= t_rmax; a_clr_q <= am_clr; end
        assign atop = atop_q; assign a_tv = a_tv_q; assign a_rmax = a_rmax_q; assign a_clr = a_clr_q;
    end else begin : g_amw
        assign atop = top; assign a_tv = tv[LVT]; assign a_rmax = t_rmax; assign a_clr = am_clr;
    end endgenerate
    wire          atop_v = atop[CW-1];
    wire [31:0]   atop_key = atop[CW-2 -: 32];
    wire [NW-1:0] atop_idx = atop[NW-1:0];
    wire [31:0]   atop_val = atop_key[31] ? {1'b0, atop_key[30:0]} : ~atop_key;
`ifdef OT_MUT_AMR
    // bench mutant (AMR path only, so the AMR = 0 reference is untouched): the accumulator stores a wrong row index
    wire [NW-1:0] atop_idx_w = atop_idx ^ {{(NW-1){1'b0}}, (AMR != 0) ? 1'b1 : 1'b0};
`else
    wire [NW-1:0] atop_idx_w = atop_idx;
`endif
    ot_qwen_w12_ksa #(.W(32 + NW)) u_bgt (.a({atop_key, ~atop_idx}), .b(~{best_key, ~am_idx}), .cin(1'b0), .s(best_s),
        .cout(best_gt));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            am_any <= 1'b0; am_idx <= 0; am_val <= 0; best_key <= 0;
        end else begin
            if (a_clr) am_any <= 1'b0;
            else if (a_tv && !a_rmax && atop_v && (!am_any || best_gt)) begin
                am_any <= 1'b1; best_key <= atop_key; am_idx <= atop_idx_w; am_val <= atop_val;
            end
        end
    end
    reg [31:0] rk [0:IL-1];
    reg [IL-1:0] rseen;
    integer rj;
    wire [31:0] rk_j = rk_jx;
    wire        rk_ge, rk_c;
    wire [31:0] rk_s;
    //: rk_j >= top_key (carry out of rk_j + ~top_key + 1), kept prefix
    ot_qwen_w12_ksa #(.W(32)) u_rge (.a(rk_j), .b(~top_key), .cin(1'b1), .s(rk_s), .cout(rk_c));
    assign rk_ge = rk_c;
    wire [31:0] nk = (!top_v || (rseen_jx && rk_ge)) ? rk_j : top_key;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rseen <= 0; mx_we <= 1'b0;
`ifdef OT_TB_RK_RST
            // bench diagnostic only (el1011-q-seq TXN): clear the per-slot maxima in reset, so an mx write after a reset
            // cannot carry slot values left by an operation the reset aborted
            for (rj = 0; rj < IL; rj = rj + 1) rk[rj] <= 32'd0;
`endif
        end
        else begin
            mx_we <= 1'b0;
            if (tv[LVT] && t_rmax) begin
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
    //: SC (b): the mx write from flops.  The lane rotate ((t_mbase + rj) % W) and the slot test (rj == t_j) are decoded
    //: from the ring output one edge early (registered beside ttag_q); the slot maximum rk[t_j] / rseen[t_j] are
    //: registered one edge early with forwarding of this edge's slot write, so nk no longer waits for a t_j mux.
    localparam integer SCB = ((SC & 1) != 0 && PK != 0 && LV >= 2 && IL <= W) ? 1 : 0;
    generate if (SCB != 0) begin : g_scb
        wire [2:0]    e_j = ttag_ew[AW+1 +: 3];
        wire [LW-1:0] e_mb = ttag_ew[LW-1:0];
        reg  [W*IL-1:0] l_sel;      // lane l holds slot rj
        reg  [W-1:0]    l_j;        // lane l holds slot t_j
        reg  [31:0]     rk_jr;
        reg             rs_jr;
        wire rk_wr = tv[LVT] && t_rmax && !t_opend && top_v;    // this edge's slot write (rk[t_j] <= nk)
        integer ll, jj;
        always @(posedge clk) begin
            for (ll = 0; ll < W; ll = ll + 1) begin
                l_j[ll] <= 1'b0;
                for (jj = 0; jj < IL; jj = jj + 1) begin
                    l_sel[ll*IL + jj] <= (((e_mb + jj) % W) == ll);
                    if ((((e_mb + jj) % W) == ll) && (jj == e_j)) l_j[ll] <= 1'b1;
                end
            end
        end
`ifdef OT_TB_RK_RST
        always @(posedge clk or negedge rst_n) if (!rst_n) rk_jr <= 32'd0; else
`else
        always @(posedge clk)
`endif
            rk_jr <= (rk_wr && (t_j == e_j) && ((SC & 2) == 0)) ? nk : rk[e_j];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) rs_jr <= 1'b0;
            else if (tv[LVT] && t_rmax && t_opend) rs_jr <= 1'b0;
            else rs_jr <= (rk_wr && (t_j == e_j) && ((SC & 2) == 0)) ? 1'b1 : rseen[e_j];
        assign rk_jx = rk_jr; assign rseen_jx = rs_jr;
`ifdef OT_SC_COV
        // bench-only coverage (el1011-q-seq SC): slot writes forwarded into the registered slot maximum, mx writes
        integer cov_fwd = 0, cov_mxw = 0, cov_rkw = 0;
        always @(posedge clk) begin
            if (rk_wr && (t_j == e_j)) cov_fwd = cov_fwd + 1;
            if (rk_wr) cov_rkw = cov_rkw + 1;
            if (tv[LVT] && t_rmax && t_opend) cov_mxw = cov_mxw + 1;
        end
        final $display("SC_COV b: rk_writes=%0d fwd=%0d mx_writes=%0d", cov_rkw, cov_fwd, cov_mxw);
`endif
        always @(posedge clk) begin
            if (tv[LVT] && t_rmax && t_opend) begin
                mx_addr <= t_mbase >> LW;
                for (ll = 0; ll < W; ll = ll + 1) begin
                    mx_mask[ll] <= |l_sel[ll*IL +: IL];
                    mx_data[32*ll +: 32] <= 32'd0;
                    for (jj = 0; jj < IL; jj = jj + 1)
                        if (l_sel[ll*IL + jj] && !l_j[ll]) mx_data[32*ll +: 32] <= rk[jj][31] ? {1'b0, rk[jj][30:0]} : ~rk[jj];
                    if (l_j[ll]) mx_data[32*ll +: 32] <= nk[31] ? {1'b0, nk[30:0]} : ~nk;
                end
            end
        end
    end else begin : g_nscb
        assign rk_jx = rk[t_j]; assign rseen_jx = rseen[t_j];
    always @(posedge clk) begin
        if (tv[LVT] && t_rmax && t_opend) begin
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
    end endgenerate

    // -- progress, idle (as ot_qwen_w12_matvec_part) ----------------------------------------------------------
    reg [15:0] n_last_issued, n_ov, ov_mark;
    //: LANDED (qwen-vm-me): the result rows reach the banked vector memory through the band serializers and the merge
    //: at a variable time; progress counts the bursts LANDED there (in order, ot_qfd_res_merge land_cnt) and the
    //: element is idle only when every burst it emitted has landed.  0: the base (bursts counted at the ports).
    wire [15:0] ov_done;
    generate if (PK != 0) begin : g_pks
        // a - b = a + ~b + 1 with kept log-depth prefix levels (ABC re-ripples a behavioural subtract)
        wire pk_co;
        ot_hdc_ksadd_k #(.W(16)) u_pks (.a((LANDED != 0) ? land_cnt : n_ov), .b(~ov_mark), .cin((PK == 2) ? 1'b0 : 1'b1),
            .s(ov_done), .cout(pk_co));
    end else begin : g_pkb
        assign ov_done = ((LANDED != 0) ? land_cnt : n_ov) - ov_mark;
    end endgenerate
    wire        land_wait = (LANDED != 0) && (land_cnt != n_ov);
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
    localparam [ORD+2:0] OMASK = (1 << (ORD + 1)) - 2;
    wire ord_busy = |(ov_line & OMASK);
    wire idle_c = !active && !pend && !e_v && !(|m_vl) && !s1_v && !s1b_v && !s2_v && !s3_v && !(|vline) && !(|post_pending) && !(|tv) && !ov1
                  && !ov2 && !ord_busy && !mx_we && !land_wait && !((AMR != 0) && a_tv);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) idle <= 1'b1;
        else idle <= idle_c && !(go && ready);
    end

    // -- x network select stage: the split of the element whose x arrives now (ot_qwen_me_spine_w12) -------
    localparam integer NXL = NX / TG;
    reg  [3:0] op_split;
    always @(posedge clk) if (go && ready) op_split <= i_split;
    assign x_dsp = op_split;
    wire [3:0] x_split;
    ot_hdc_delay #(.W(4), .D(2 + XVM)) u_xs (.clk(clk), .rst_n(rst_n), .d(op_split), .q(x_split));
    genvar r, i;
    generate
        for (r = 0; r < NXL; r = r + 1) begin : g_line
            wire [SMAX:0] quads = (1 << x_split) / TG;
            wire [SMAX:0] src = r & (quads - 1);
            for (i = 0; i < TG; i = i + 1) begin : g_e
                always @(posedge clk) xl0[(r*TG + i)*32 +: 32] <= x_q[(src*TG + i)*32 +: 32];
            end
        end
    endgenerate
endmodule
