`timescale 1ns/1ps
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
// KV-SOURCED OPS (wsrc) are K-split the same way but INTERLEAVED: i_k is the
// op's whole K, chunk c takes k' = c, c+S, c+2S, ... (the loop runs
// ceil(K/S) steps; an element with k*S + c >= K has both operands zeroed, a
// +0 product, so a ragged last chunk sums exactly), group g = q*S + c reads
// KV word  wbase + t*ts + c*wcs + k*ks + (j >> jsh)*js  for tile
// t = r*(G/S) + q.  Scores split head_dim, the weighted sum positions
// (tools/hdc_golden.py matvec_il, attn_splits).
//
// Element order: round r, then k, then slot j.  Lane l of group g multiplies
// lane g*W+l of weight word  wbase + r*ts + k*ks + (j >> jsh)*js  by x element
// xbase + c*xcs + k*xks + j*xjs  (BF16-rounded, RNE, when `round`), and after
// the last k output port q writes lane l of word  obase + t*ots + j*ojs.  A lane
// is valid when (t*IL + j)*W + l < nout (mmode 0: rows) or t*W + l < nout
// (mmode 1: every slot its own vector -- one attention head per slot).
//
// MULTIPLIERS. BF16 mode reads BF16 ROM weights. INT8 mode reads signed codes
// packed from two four-bit select cells, converts them exactly to BF16, then
// uses the same exact BF16 multiplier. KV-sourced ops retain BF16 values.
// INT8 matrix results receive one BF16 row-scale multiply after the complete
// K-split tree, before writeback and argmax. Its one-cycle scale ROM request
// starts two cycles before the tree result; only the five-cycle FP32 multiply
// extends the result path, and the tags follow those five cycles.
//
// Timing from an issue cycle c: memories return at c+1, operands are captured
// at c+2 and conditioned at c+3, products leave at c+8, sums at c+13, the
// split tree adds 4 per level (3 in the low-latency adder, 1 output register), and a result
// is written one cycle later.
//
// PHYSICAL PARTITION (ot_qwen_w12_matvec_part; the ot_qwen_w12_matvec wrapper keeps the
// monolithic engine, PART = 0).  A die of GT groups is built as GT/G tile
// elements plus one spine top, all instances of the same RTL:
//   PART 1 (tile)  G local groups whose global indices are GBASE + g (GBASE a
//                  parameter, or the strap input i_gbase with GBASE_PORT = 1,
//                  so every tile is one netlist).  It runs its own copy of the
//                  issue loop from the broadcast instruction, reads its ROM and
//                  KV slice, takes x on x_q from the x network, and adds its
//                  groups through the first log2(G) split-tree levels.  t_out
//                  is its level-log2(G) word (valid t_vout), which the tree
//                  above adds with its neighbours'.  No post-scale, result or
//                  argmax logic.
//   PART 2 (top)   G = GT.  The issue loop (its x ports serve the chunk stream,
//                  NX of them), no lanes: t_in carries tree level TCUT for the
//                  G >> TCUT positions, arriving XD cycles after the monolithic
//                  timing (instruction broadcast, VM conflict register and
//                  tree wire stages); levels TCUT+1..log2(G), the post-scale,
//                  results, argmax and per-slot maxima follow, with ORD extra
//                  result-write register stages.
// PRUNING (SMIN > 0).  Every op issues with split >= SMIN (an op below it
// raises fault).  Tree levels <= SMIN therefore always add and carry no held
// registers; only the NP = GT >> SMIN result-port groups get the post-scale
// multipliers, result registers and argmax leaves (the argmax tree is
// log2(NP * W) levels deep, so its result is earlier than the unpruned one's).
// Default parameters reproduce the original engine port for port.
// ---------------------------------------------------------------------------
`timescale 1ns/1ps
module ot_qwen_w12_matvec #(
    parameter integer W  = 16,
    parameter integer G  = 4,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer INT8_WEIGHT = 0,
    // Full-shape INT8 programs put the scale image at ME_WCS. Reduced
    // programs keep the historical shared ME_WBASE address by default.
    parameter integer INT8_SCALE_WCS_BASE = 0,
    parameter integer SMIN = 0,          // pruning: smallest split any op uses (0 = none)
    parameter integer ORD = 0,           // extra result-write register stages
    parameter integer ACC_LAT = 5,       // lane accumulator / split-tree adder latencies (ot_qwen_w12_matvec_part)
    parameter integer TREE_LAT = 3,
    parameter integer FAST_ISSUE = 0,
    parameter integer KV_PREP = 0,
    parameter integer MUL_LAT = 5
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output wire              idle,
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
    output wire              wrom_re,
    output wire [AW-1:0]     wrom_addr,
    input  wire [G*W*((INT8_WEIGHT != 0) ? 8 : 16)-1:0] wrom_q,
    output wire              scale_re,
    output wire [G-1:0]      scale_gre,
    output wire [G*AW-1:0]   scale_addr,
    input  wire [G*W*16-1:0] scale_q,
    output wire              kv_re,
    output wire [G*AW-1:0]   kv_addr,
    input  wire [G*W*32-1:0] kv_q,
    output wire [G-1:0]      x_re,
    output wire [G*AW-1:0]   x_addr,
    input  wire [G*32-1:0]   x_q,
    output wire              ov,
    output wire [G-1:0]      o_we,
    output wire [G*AW-1:0]   o_addr,
    output wire [G*W-1:0]    o_mask,
    output wire [G*W*32-1:0] o_data,
    output wire [NW-1:0]     am_idx,
    output wire [31:0]       am_val,
    output wire              am_any,
    output wire              mx_we,
    output wire [AW-1:0]     mx_addr,
    output wire [W-1:0]      mx_mask,
    output wire [W*32-1:0]   mx_data,
    output wire [15:0]       progress,
    output wire              fault
);
    // The issue loop's state, named for the testbenches that observe it.
    wire active;
    ot_qwen_w12_matvec_part #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW), .INT8_WEIGHT(INT8_WEIGHT),
                         .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE), .SMIN(SMIN), .ORD(ORD),
                         .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT)) u_p (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc),
        .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js),
        .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs),
        .i_jsh(i_jsh), .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round),
        .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax), .i_mbase(i_mbase),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .scale_re(scale_re), .scale_gre(scale_gre), .scale_addr(scale_addr), .scale_q(scale_q),
        .kv_re(kv_re), .kv_addr(kv_addr), .kv_q(kv_q),
        .x_re(x_re), .x_addr(x_addr), .x_q(x_q),
        .ov(ov), .o_we(o_we), .o_addr(o_addr), .o_mask(o_mask), .o_data(o_data),
        .am_idx(am_idx), .am_val(am_val), .am_any(am_any),
        .mx_we(mx_we), .mx_addr(mx_addr), .mx_mask(mx_mask), .mx_data(mx_data),
        .progress(progress), .fault(fault),
        .i_gbase(32'd0), .t_in({W*32{1'b0}}), .t_fault_in(1'b0),
        .t_out(), .t_vout(), .t_fault(), .active_o(active));
endmodule

`timescale 1ns/1ps
module ot_qwen_w12_matvec_part #(
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
    // MUL_LAT: the lane's BF16 product latency (5: ot_qwen_w12_bmul; 6: its product cut after the carry-save rows)
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
    //: KV ops: group g = q*S + c takes tile r*(GT/S) + q, chunk c: its own word
    generate if (LANES && KV_PREP == 0) begin : g_kv_addr
        always @(posedge clk) begin
            if (active)
                for (gi = 0; gi < G; gi = gi + 1)
                    kv_addr[gi*AW +: AW] <= cur + ((gb + gi) >> split_r) * ts_r + ((gb + gi) & ((1 << split_r) - 1)) * wcs_r;
        end
    end else if (LANES) begin : g_kv_addr_prep
        //: the per-group offset q*ts + c*wcs is constant through the op: a free-running three-stage pipeline
        //: from the go's latched fields: (1) q, c; (2) the shifted rows of both products reduced carry-save to two;
        //: (3) their kept prefix sum -- ready after KV_PREP = 3
        localparam integer QW = $clog2(GT) + 1;       // q < GT
        localparam integer CW = 16;                   // c < 2^split
        reg [QW-1:0] q_p [0:G-1];
        reg [CW-1:0] c_p [0:G-1];
        reg [AW-1:0] off [0:G-1];
        genvar gq, rb;
        for (gq = 0; gq < G; gq = gq + 1) begin : g_off
            wire [AW-1:0] a_s, osum;
            wire [(QW+CW)*AW-1:0] rows;
            for (rb = 0; rb < QW; rb = rb + 1) begin : g_rq
                assign rows[rb*AW +: AW] = q_p[gq][rb] ? (ts_r << rb) : {AW{1'b0}};
            end
            for (rb = 0; rb < CW; rb = rb + 1) begin : g_rc
                assign rows[(QW+rb)*AW +: AW] = c_p[gq][rb] ? (wcs_r << rb) : {AW{1'b0}};
            end
            reg [AW-1:0] r_s, r_c;
            wire [31:0] qv = (gb + gq) >> split_r;
            wire [31:0] cv = (gb + gq) & ((1 << split_r) - 1);
            wire [AW-1:0] cs_s, cs_c;
            ot_qwen_w12_csa_tree #(.W(AW), .N(QW+CW)) u_cs (.rows(rows), .s(cs_s), .c(cs_c));
            ot_qwen_w12_kadd #(.W(AW)) u_sum (.a(r_s), .b(r_c), .s(osum));
            always @(posedge clk) begin
                q_p[gq] <= qv[QW-1:0];
                c_p[gq] <= cv[CW-1:0];
                r_s <= cs_s; r_c <= cs_c;
                off[gq] <= osum;
            end
            ot_qwen_w12_kadd #(.W(AW)) u_ka (.a(cur), .b(off[gq]), .s(a_s));
            always @(posedge clk)
                if (active) kv_addr[gq*AW +: AW] <= a_s;
        end
    end endgenerate

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
    generate if (LANES && FAST_ISSUE != 0 && KV_PREP >= 2) begin : g_gm_fast
        //: k*S + c < K  <=>  k < ceil((K - c) / S) (K > c): the per-group K-step limit is constant through the op, a
        //: two-stage pipeline from the latched fields, ready by the KV op's first element (KV_PREP >= 2)
        reg [NW:0] kdif [0:G-1];
        reg [NW:0] klim [0:G-1];
        genvar gk;
        for (gk = 0; gk < G; gk = gk + 1) begin : g_kl
            wire [31:0] c32 = (gb + gk) & ((1 << split_r) - 1);
            always @(posedge clk) begin
                kdif[gk] <= ({{(32-NW){1'b0}}, ktot_r} > c32) ? (ktot_r - c32[NW:0] + ((1 << split_r) - 1)) : {(NW+1){1'b0}};
                klim[gk] <= kdif[gk] >> split_r;
                e_gm[gk] <= (((gb + gk) >> split_r) < (GT >> split_r)) && (!wsrc_r || ({1'b0, k} < klim[gk]));
            end
        end
    end else if (LANES) begin : g_gm
        always @(posedge clk)
            for (gi = 0; gi < G; gi = gi + 1)
                e_gm[gi] <= (((gb + gi) >> split_r) < (GT >> split_r)) &&
                            (!wsrc_r || (({{(32-NW){1'b0}}, k} << split_r) + ((gb + gi) & ((1 << split_r) - 1))
                                          < {{(32-NW){1'b0}}, ktot_r}));
    end endgenerate

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
    //: Memory read data is registered once as it arrives (MEM_PIPE): the
    //: weight word is 2,048 bits wide and its lanes span the whole engine, so a
    //: pin-to-lane wire gets a cycle of its own.
    reg [GL*W*((INT8_WEIGHT != 0) ? 8 : 16)-1:0] mq_wrom;
    reg [GL*W*32-1:0] mq_kv;
    reg [GL*32-1:0]   mq_x;
    reg [GL*W*32-1:0] s2_w, s3_w;
    reg [GL*32-1:0]   s2_x, s3_x;
    reg [G-1:0]      s1_gm, s1b_gm, s2_gm;
    integer l;
    //: the BF16 round of x: x + 0x7FFF + x[16] as a kept prefix add (bit-identical to the flattened `+`)
    wire [GL*32-1:0] x_rnd;
    genvar xr;
    generate for (xr = 0; xr < GL; xr = xr + 1) begin : g_xrnd
        if (FAST_ISSUE != 0) begin : g_keep_round
            ot_qwen_w12_kadd #(.W(32)) u_r (.a(s2_x[32*xr +: 32]), .b(32'h7FFF + {31'd0, s2_x[32*xr + 16]}), .s(x_rnd[32*xr +: 32]));
        end else begin : g_legacy_round
            assign x_rnd[32*xr +: 32] = s2_x[32*xr +: 32] + 32'h7FFF + {31'd0, s2_x[32*xr + 16]};
        end
    end endgenerate
    generate if (LANES) begin : g_operand
        always @(posedge clk) begin
            s1_gm <= m_gm; s1b_gm <= s1_gm; s2_gm <= s1b_gm;
            mq_wrom <= wrom_q; mq_kv <= kv_q; mq_x <= x_q;
            for (l = 0; l < G * W; l = l + 1)
                if (INT8_WEIGHT != 0)
                    s2_w[32*l +: 32] <= !s1b_gm[l / W] ? 32'd0 : s1b_wsrc ? mq_kv[32*l +: 32] :
                                              {int8_bf16(mq_wrom[8*l +: 8]), 16'h0000};
                else
                    s2_w[32*l +: 32] <= !s1b_gm[l / W] ? 32'd0 : s1b_wsrc ? mq_kv[32*l +: 32] :
                                              {mq_wrom[16*l +: 16], 16'h0000};
            s2_x <= mq_x;
            s3_w <= s2_w;
            for (l = 0; l < G; l = l + 1)
                s3_x[32*l +: 32] <= !s2_gm[l] ? 32'd0 :
                                    s2_round ? (x_rnd[32*l +: 32] & 32'hFFFF0000) : s2_x[32*l +: 32];
        end
    end endgenerate
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

    // -- lanes -------------------------------------------------------------------
    wire [GL*W*32-1:0] sum;
    wire [G*W-1:0]    lfault;
    genvar g, gl;
    generate if (LANES) begin : g_lanes
        for (g = 0; g < G; g = g + 1) begin : g_grp
            for (gl = 0; gl < W; gl = gl + 1) begin : g_lane
                localparam integer LI = g * W + gl;
                wire [31:0] prod, fb_pre, acc_in;
                reg  [31:0] acc_q;
                wire f0, f1;
                //: every product is BF16 x BF16 (weights, x rounded; BF16 KV, q and
                //: probabilities rounded), so every lane has the small exact multiplier
                if (MUL_LAT == 5) begin : g_legacy_mul
                    ot_hdc_bmul u_mul (.clk(clk), .rst_n(rst_n), .v(s3_v),
                                     .a(s3_w[32*LI +: 32]), .b(s3_x[32*g +: 32]), .y(prod), .fault(f0));
                end else begin : g_candidate_mul
                    ot_qwen_w12_bmul #(.LAT(MUL_LAT)) u_mul (.clk(clk), .rst_n(rst_n), .v(s3_v),
                                     .a(s3_w[32*LI +: 32]), .b(s3_x[32*g +: 32]), .y(prod), .fault(f0));
                end
                // add input at c+8; the circulating sum from IL cycles earlier.
                //: The first-element select is made one cycle early into acc_q: the
                //: flag fans out to every lane bit (G*W*32 loads), and registering the
                //: mux gives its buffer tree a whole cycle instead of sharing one with
                //: the adder's alignment logic (me_iter11: -98 ps on this path).
                always @(posedge clk) acc_q <= fl_first[MUL_LAT-1] ? 32'd0 : fb_pre;
                assign acc_in = acc_q;
                if (ACC_LAT == 5) begin : g_fadd
                    ot_hdc_fadd u_add (clk, rst_n, vline[MUL_LAT], acc_in, prod,
                                       sum[32*LI +: 32], f1);
                end else begin : g_ladd
                    ot_qwen_w12_ladd #(.LAT(ACC_LAT)) u_add (clk, rst_n, vline[MUL_LAT], acc_in, prod,
                                                       sum[32*LI +: 32], f1);
                end
                ot_hdc_delay #(.W(32), .D(FB - 1)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum[32*LI +: 32]), .q(fb_pre));
                assign lfault[LI] = f0 | f1;
            end
        end
    end else begin : g_no_lanes
        assign sum = {GL*W*32{1'b0}};
        assign lfault = {G*W{1'b0}};
    end endgenerate

    // -- split tree: level L adds word pairs when split >= L, else delays ----------
    //: Each level ends in a register: the sum-or-held select fans out to every
    //: word bit, and unregistered it shared a cycle with the next level's
    //: exponent alignment (me_iter12: -91 ps on that path).
    //: Pruned (SMIN): a level <= SMIN always adds and holds nothing; above it,
    //: only positions below NPG are held.
    wire [GI*W*32-1:0] lvl [0:LG];
    wire [LG:0]       tfault;
    genvar lv, p;
    generate
        if (PART == 2) begin : g_tin
            assign lvl[LV0] = t_in[GI*W*32-1:0];
        end else begin : g_tsum
            assign lvl[0] = sum;
        end
    endgenerate
    assign tfault[LV0] = 1'b0;
    wire [LG*4+3:0] split_at;                       // split at each level's input
    assign split_at[4*LV0+3 -: 4] = t_split;
    generate
        for (lv = LV0 + 1; lv <= LG; lv = lv + 1) begin : g_lvl
            localparam integer ALWAYS = PRUNE && (SMIN >= lv);
            localparam integer HOLD_TO = PRUNE ? NPG : G;      // held positions [G >> lv, HOLD_TO)
            wire [3:0] sp_sel;                      // split when the level's sums emerge
            ot_hdc_delay #(.W(4), .D(TA)) u_sd (.clk(clk), .rst_n(rst_n), .d(split_at[4*lv-1 -: 4]), .q(sp_sel));
            reg  [3:0] sp_out;
            always @(posedge clk) sp_out <= sp_sel;
            assign split_at[4*lv+3 -: 4] = sp_out;
            localparam integer PAIRS = (G >> lv) * W;
            wire [(PAIRS > 0 ? PAIRS : 1)-1:0] pf;
            if (PAIRS == 0) assign pf = 1'b0;
            // registered positions [0, R1): pairs below R0 = G >> lv, held above
            localparam integer R0 = (G >> lv);
            localparam integer R1 = ALWAYS ? R0 : ((HOLD_TO > R0) ? HOLD_TO : R0);
            localparam integer RW = (R1 > 0) ? R1 : 1;
            reg  [RW*W*32-1:0] lq;
            wire [GI*W*32-1:0] held;
            if (!ALWAYS && HOLD_TO > 0) begin : g_hold
                ot_hdc_delay #(.W(HOLD_TO*W*32), .D(TA)) u_hold (.clk(clk), .rst_n(rst_n),
                    .d(lvl[lv-1][HOLD_TO*W*32-1:0]), .q(held[HOLD_TO*W*32-1:0]));
                if (HOLD_TO < GI) begin : g_hz
                    assign held[GI*W*32-1:HOLD_TO*W*32] = 0;
                end
            end else begin : g_nohold
                assign held = {GI*W*32{1'b0}};
            end
            for (p = 0; p < PAIRS; p = p + 1) begin : g_add
                localparam integer PW = p / W, PL = p % W;
                wire [31:0] s_out;
                ot_qwen_w12_tadd #(.LAT(TREE_LAT)) u_add (clk, rst_n, vline[SD + TL*(lv-1) + XDD] && (split_at[4*lv-1 -: 4] >= lv),
                                   lvl[lv-1][32*((2*PW)*W + PL) +: 32], lvl[lv-1][32*((2*PW+1)*W + PL) +: 32],
                                   s_out, pf[p]);
                if (ALWAYS) begin : g_a
                    always @(posedge clk) lq[32*p +: 32] <= s_out;
                end else begin : g_s
                    always @(posedge clk) lq[32*p +: 32] <= (sp_sel >= lv) ? s_out : held[32*p +: 32];
                end
            end
            if (R1 > R0) begin : g_rest
                always @(posedge clk) lq[R1*W*32-1 : R0*W*32] <= held[R1*W*32-1 : R0*W*32];
            end
            if (R1 == 0) begin : g_lz
                assign lvl[lv] = {GI*W*32{1'b0}};
            end else if (R1 < GI) begin : g_lp
                assign lvl[lv] = {{((GI - R1) * W * 32){1'b0}}, lq};
            end else begin : g_lf
                assign lvl[lv] = lq;
            end
            assign tfault[lv] = |pf;
        end
    endgenerate
    // PART 1: the tile's top level and its valid, towards the tree above
    assign t_out = lvl[LG][W*32-1:0];
    assign t_vout = vline[SD + OD];
    wire [GI*W*32-1:0] raw_res = lvl[LG];
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
        genvar si;
        for (si = 0; si < NPG*W; si = si + 1) begin : g_scale
            localparam integer GROUP = si / W;
            localparam integer LANE = si % W;
            wire active_lane = ((gb + GROUP) < (GT >> raw_split)) &&
                (raw_mmode ? (raw_lb + (gb + GROUP)*W + LANE < raw_nout) :
                             (raw_nb + (gb + GROUP)*(W*IL) + LANE < raw_nout));
            ot_hdc_fmul u_mul (
                .clk(clk), .rst_n(rst_n), .v(raw_v && raw_last && active_lane),
                .a(raw_res[32*si +: 32]),
                .b({raw_wsrc ? 16'h3F80 : scale_q[16*si +: 16], 16'd0}),
                .y(scaled[32*si +: 32]), .fault(scale_faults[si])
            );
        end
        if (NPG < GR) begin : g_scale_pruned
            assign scaled[GR*W*32-1:NPG*W*32] = 0;
            assign scale_faults[GR*W-1:NPG*W] = 0;
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
    //: A status bit: registered in two levels (see ot_hdc_stream).
    reg [G:0] fault_q;
    integer fg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault_q <= 0; fault <= 1'b0; end
        else begin
            for (fg = 0; fg < G; fg = fg + 1) fault_q[fg] <= |lfault[fg*W +: W];
            fault_q[G] <= |tfault | ((PART == 2) ? t_fault_in : 1'b0);
            fault <= |fault_q | (|scale_faults) | split_fault;
        end
    end
    assign t_fault = fault;

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
    genvar e;
    generate
        for (e = 0; e < NL; e = e + 1) begin : g_leaf
            localparam integer EQ = e / W, EL = e % W;
            reg [CW-1:0] c;
            //: sized on its own: an integer term would widen a concatenated sum
            wire [NW-1:0] row = r_nb[NW-1:0] + (gb + EQ) * (W * IL) + EL;
            always @(posedge clk)
                c <= {r_mask[e], okey(res[32*e +: 32]), row};
            assign alv[0][CW*e +: CW] = c;
        end
        for (e = NL; e < AN; e = e + 1) begin : g_leaf_pad
            assign alv[0][CW*e +: CW] = {CW{1'b0}};
        end
        for (lv = 1; lv <= LV; lv = lv + 1) begin : g_alvl
            for (e = 0; e < (AN >> lv); e = e + 1) begin : g_node
                wire [CW-1:0] x0 = alv[lv-1][CW*(2*e) +: CW];
                wire [CW-1:0] x1 = alv[lv-1][CW*(2*e+1) +: CW];
                wire          x0_wins = x0[CW-1] && (!x1[CW-1] || x0[CW-2 -: 32] > x1[CW-2 -: 32] ||
                                        (x0[CW-2 -: 32] == x1[CW-2 -: 32] && x0[NW-1:0] < x1[NW-1:0]));
                reg  [CW-1:0] c;
                always @(posedge clk) c <= x0_wins ? x0 : x1;
                assign alv[lv][CW*e +: CW] = c;
            end
            if ((AN >> lv) < AN) begin : g_pad
                assign alv[lv][CW*AN-1 : CW*(AN >> lv)] = 0;
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


// ot_qwen_w12_ladd #(LAT): ot_hdc_fp32_add_lat (bit-identical to ot_hdc_qadd / ot_hdc_fadd) with the qadd port
// shape: fault = a valid result's err.
`timescale 1ns/1ps
module ot_qwen_w12_ladd #(parameter integer LAT = 7) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    ot_hdc_fp32_add_lat #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                        .valid_out(vo));
    assign fault = vo && (err != 2'd0);
endmodule

// The split-tree pair adder: ot_hdc_qadd at LAT 3 (the legacy netlist), else ot_qwen_w12_ladd #(LAT).
`timescale 1ns/1ps
module ot_qwen_w12_tadd #(parameter integer LAT = 3) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    generate if (LAT == 3) begin : g_q
        ot_hdc_qadd u (clk, rst_n, v, a, b, y, fault);
    end else begin : g_l
        ot_qwen_w12_ladd #(.LAT(LAT)) u (clk, rst_n, v, a, b, y, fault);
    end endgenerate
endmodule

// ot_qwen_w12_kadd #(W): a + b (mod 2^W) through ot_qwen_w12_ksa, the keep-prefix Kogge-Stone adder
`timescale 1ns/1ps
module ot_qwen_w12_kadd #(parameter integer W = 24) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    output wire [W-1:0] s
);
    wire c;
    ot_qwen_w12_ksa #(.W(W)) u (.a(a), .b(b), .cin(1'b0), .s(s), .cout(c));
endmodule

// N rows of W bits reduced carry-save (3:2 per level) to two, kept-level boundaries
`timescale 1ns/1ps
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
`timescale 1ns/1ps
module ot_qwen_w12_ksum #(parameter integer W = 24, parameter integer N = 8) (
    input  wire [N*W-1:0] rows,
    output wire [W-1:0]   s
);
    wire [W-1:0] a, b;
    ot_qwen_w12_csa_tree #(.W(W), .N(N)) u_t (.rows(rows), .s(a), .c(b));
    ot_qwen_w12_kadd #(.W(W)) u_a (.a(a), .b(b), .s(s));
endmodule
