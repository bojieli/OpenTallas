// PRIVATE file-list alternative, original module/default source untouched.
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
        .clk(clk), .rst_n(rst_n), .go(go), .go_cp({32{go}}), .ready(ready), .idle(idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc),
        .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js),
        .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs),
        .i_jsh(i_jsh), .i_split(i_split), .i_split_copy(i_split), .i_wcs(i_wcs), .i_round(i_round),
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

module ot_qwen_w12_matvec_part #(
    parameter integer SPLIT_CP = 0,
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
    parameter integer MUL_LAT = 5,
    // WCONV = 1 (INT8_WEIGHT): the ROM port carries the weight codes already expanded to BF16 (G*W*16 bits) by
    // the tile's ROM pipeline (ot_qwen_rom_tile_logic_w12 ROM_PIPE); values identical, the expansion moves off the
    // capture->lane wire.  0: the original.
    parameter integer WCONV = 0,
    // LRST = 1: each lane group and each split-tree level takes its own kept reset copy (asserted with rst_n,
    // released one edge later); lanes see their first valid >= 4 edges after any go, so the later release is
    // invisible.  0: the original (rst_n everywhere).
    // LRST = 3 (qwen-1010/c 2026-10-10): LRST 2 plus a second kept copy per LANE and per TREE ADDER, fed by its group /
    // level copy (released two edges after rst_n, assert still asynchronous): the level copy drove every tree adder's
    // reset flops through 13 buffer levels (rp1pcl-hm0).  0 cycles.
    parameter integer LRST = 0,
    parameter integer TMUT = 0,          // 2: one tree adder's reset copy never released (bench mutant, LRST 3)
    // HIER = NPL > 0 (el1011-q-tile 2026-10-11, textbook class 1/2/4; PART != 2, LANES, every tree level always adds):
    // the lanes and the split tree as W / NPL hardened lane-slice leaves (ot_qwen_w12_lane_slice: NPL lane positions
    // of every group + their whole sub-tree; the tree only adds equal positions across groups).  The leaf's input pin
    // flops ARE the S3 registers, its output is the tree's last-level register: same edges, 0 cycles.  Each leaf
    // keeps its own valid line / first line / split delay / reset relay (one local clock tree per leaf).
    parameter integer HIER = 0,
    // HIER_HARD = 1 (round 2): each slice is the hardened leaf master ot_qwen_tile_lsl (fixed G 4 / NPL 2 / IL 8 / MUL 8 /
    // ACC 7 / TREE 7 / LRST 3 / ANR 1; rtl/physical/ot_qwen_tile_lsl.sv in simulation, its blackbox + views in the parent route)
    parameter integer HIER_HARD = 0,
    parameter integer LRR = 0,            // el1011-q-tile h3: one reset relay flop per hardened leaf (1-cycle later leaf release)
    parameter integer XTX = 0,            // el1011-q-tile r3 (HIER_HARD): XTX registered transmit rungs in front of every hardened
                                          // leaf (v/first/split/w and the ROUNDED x), one kept copy per leaf; +XTX cycles of latency
    parameter integer GLUE_HARD = 0, // existing mq_wrom/S2 stages owned per LSL (fixed ROM-only mode)
    parameter integer LOCAL_ROOTS = 0, // physical clock ownership only; no data edge change
    parameter integer CHILD_CLOCKS = 0,
    parameter integer REGROOT = 0,     // Q-ROMPARENT 10-16 (RPH 3 only): ck_reg = {data E, data W, gn W, gs W} regional roots; 0 = ck_reg unused
    parameter integer ANR = 0            // hardcore-1010 D: lane / tree adders as ot_hdc_fp32_add_lat_nr (0 = unchanged)
) (
    input wire [7:0] ck_lsl,
    input wire [7:0] ck_tx,
    input wire [3:0] ck_reg,
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    //: REGROOT 8 (QW-A0-RC4 10-20): KEPT copies of the go register (same D, same reset, same edge as `go`), one per
    //: <= 2 issue-loop copy groups / descriptor load groups, so no go-qualified enable drives more than ~26 loads.
    //: REGROOT < 8: unused (instantiations tie it to {32{go}}).
    input  wire [31:0]       go_cp,
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
    input  wire [3:0]        i_split_copy,
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
    input  wire [G*W*((INT8_WEIGHT != 0 && WCONV == 0) ? 8 : 16)-1:0] wrom_q,
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
    //: XTX (HIER_HARD only): the leaves see their inputs XTX cycles later, so every S3-referenced valid / tag / split
    //: line that meets the leaves' results is XTX cycles longer (same order, same arithmetic)
    // REGROOT5 adds a real output landing per hard LSL on its existing
    // ck_tx entry. The complete tile data/valid path advances one edge.
    //: REGROOT 9 (QW-CB16A0-2 10-20, A0 rc10): the rung-0 crossing (hub ck / ck_dw / ck_de -> ck_tx[g]) and the leaf
    //: result + fault return (ck_tx[g] -> ck) are LANDED crossings (ot_qw_lw ring on the source root, ot_qw_lr read on the
    //: destination root, K = L9K): + L9K edges each, so the leaves' results are 2 * L9K edges later (priced in XTD).
    localparam integer L9  = (REGROOT >= 9 && HIER > 0 && HIER_HARD != 0 && XTX >= 2 && LOCAL_ROOTS != 0 && CHILD_CLOCKS != 0) ? 1 : 0;
    localparam integer L9K = 2;
    localparam integer XTD = (HIER > 0 && HIER_HARD != 0) ? XTX + ((REGROOT >= 5) ? 1 : 0) + ((L9 != 0) ? 2 * L9K : 0) : 0;
    localparam integer XDD = ((PART == 2) ? XD : 0) + XTD;
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
    //: REGROOT 8 (QW-A0-RC4 10-20, PRE-GATE NATIVE CENSUS <= 32 loads per driver): a consumer of the per-op split takes
    //: two identical split copies (copy c and its twin c + SPB, loaded on the same edge with the same value) and
    //: builds its low output bits (mask M) from one and the rest from the other: same value, half the cone each.
    function automatic [36:0] shr2(input [36:0] x, input [3:0] sa, input [3:0] sb, input [36:0] m);
        shr2 = ((x >> sa) & m) | ((x >> sb) & ~m);
    endfunction
    function automatic [36:0] msk2(input [3:0] sa, input [3:0] sb, input [36:0] m);
        msk2 = (((37'd1 << sa) - 37'd1) & m) | (((37'd1 << sb) - 37'd1) & ~m);
    endfunction
    //: REGROOT 8: the static group-index strap as per-consumer-group KEPT registers (TIDR argument: a strap is
    //: constant from before reset release, so a registered copy is the same value at every use): gbc[0..G-1] the
    //: KV-offset / K-limit pipelines of group g, so tile_id_q no longer fans into every group's shifters.
    wire [32*G-1:0] gbc;
    generate if (REGROOT >= 8) begin : g_gbc
        genvar gc;
        for (gc = 0; gc < G; gc = gc + 1) begin : g_c
            (* keep *) reg [31:0] q;
            always @(posedge clk) q <= gb;
            assign gbc[32*gc +: 32] = q;
        end
    end else begin : g_gbn
        assign gbc = {G{gb}};
    end endgenerate
    //: REGROOT 8 descriptor load enables: ldv[l] = go copy & kept idle copy (assigned in g_ctl_rr8)
    localparam integer NLDD = 75;          // descriptor-register load groups (<= 12 bits: ~2 mux loads per bit)
    localparam integer NLD  = NLDD + 6;    // + 4 split-copy tiers, wsrc copies, ktot copies
    wire [NLD-1:0] ldv;
    wire [4*AW-1:0] tsc, wcc;      // REGROOT 8: per-group KV-offset copies of ts / wcs (descriptor load groups)
    //: REGROOT 8 one-hot split copies (1 << split, loaded with the descriptor): a shift by the split becomes an AND-OR
    //: of constant shifts, each one-hot bit driving <= one consumer's output bits.  Owners: 0..3 tsh quarters,
    //: 4..7 osh quarters, 8 / 9 kc_a low / high half, 10..13 KV q offset per group, 14..17 K-limit shift per group,
    //: 18..21 e_gm group compare per group.
    localparam integer NOH = 22;
    wire [16*NOH-1:0] sph;
    function automatic [36:0] shro(input [36:0] x, input [15:0] oh);
        integer kk;
        begin
            shro = 37'd0;
            for (kk = 0; kk < 16; kk = kk + 1) if (oh[kk]) shro = shro | (x >> kk);
        end
    endfunction

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

    //: REGROOT 6 (QW-CLUSTER3/A0 10-19, safe-design item 3): per-destination KEPT copies of the go-latched split /
    //: wsrc fields (split_r[3:0] drove 415/335/281/235 and wsrc_r 89 mapped loads in NK c1r9f).  Each copy loads the
    //: canonical next-state (the same go enable): same value on the same edge, 0 cycles.  Copy owners:
    //: spc 0..7 the round-step shifters (tsh/osh even/odd set bits of GT, low/high halves), 8 pr_a/kpad_a, 9 kc_a,
    //: 10..13 KV-offset q per group, 14..17 KV-offset c per group, 18..21 K-limit mask per group, 22..25 K-limit
    //: shift / e_gm per group, 26 e_split.  wsc 0 kc_a, 1 tstep_r, 2 e_wsrc / e_gm.  REGROOT < 6: plain aliases.
    //: REGROOT 7 (QW-CLUSTER3/A0 rc2, from the rc1 mapped census: 46 registers > 32, max 88): +18 split copies
    //: (round-step shifter quarters 27..34, kpad 35, K-limit kdif 36..39 / compare 40..43, kc_a high half 44), a
    //: tstep high-half wsrc copy (wsc 3) and per-destination ktot copies (kpad + four K-limit groups).  Copies
    //: 24.. load a second next-state mux that holds from copy 0 (equal after the first go; every consumer's first
    //: use follows a go), so no next-state net drives more than ~25 copy D pins.
    localparam integer SPB = 45;          // REGROOT 8: twin of split copy c is c + SPB
    localparam integer NSPC = (REGROOT >= 8) ? 2*SPB : (REGROOT >= 7) ? 45 : 27;
    wire [4*NSPC-1:0] spc;
    wire [4:0]        wsc;        // REGROOT 8: copy 4 = kc_a high half
    wire [5*NW-1:0]   ktc;        // ktot copies: 0 kpad/kc_a, 1..4 K-limit group 0..3 (REGROOT 7; else ktot_r)
    wire [4:0]        acc;        // active copies (assigned in the issue block)
    wire              klc;        // k_last copy (assigned in the issue block)
    generate if (REGROOT >= 6) begin : g_rr6
        initial if (FAST_ISSUE == 0 || LANES == 0 || KV_PREP < 2 || G > 4)
            $fatal(1, "ot_qwen_w12_matvec_part REGROOT 6 needs FAST_ISSUE, LANES, KV_PREP >= 2 and G <= 4");
        wire ld_go = (REGROOT >= 8) ? ldv[NLDD+4] : (rst_n && !pend && !active && go);
        wire [3:0] split_nx = ld_go ? i_split : split_r;
        wire       wsrc_nx  = ld_go ? i_wsrc : wsrc_r;
        genvar sc;
        wire [3:0] split_nx2 = ld_go ? i_split : spc[3:0];      // REGROOT 7 second tier (copies 24..) holds from copy 0
        wire [15:0] spt;                                         // REGROOT 8 tier next-state (4 tiers)
        for (sc = 0; sc < 4; sc = sc + 1) begin : g_spt
            // QW-CB16A0-3 rc11 (V7): tiers 1..3 on the same-edge copy (NL rc11 in-flow census: ib_i[125] 33 loads with tiers 2..3 only)
            assign spt[4*sc +: 4] = (REGROOT >= 8 && ldv[NLDD + sc]) ? ((SPLIT_CP != 0 && sc >= 1) ? i_split_copy : i_split) : spc[4*((REGROOT >= 8) ? 23*sc : 0) +: 4];
        end
        for (sc = 0; sc < NSPC; sc = sc + 1) begin : g_sp
            (* keep *) reg [3:0] q;
            if (REGROOT >= 8) begin : g_t8
                //: REGROOT 8: four tiers of <= 23 copies; tier t loads on its own enable ldv[NLDD+t] and holds from its
                //: first copy (an enable flop for that copy; every copy holds the same value)
                always @(posedge clk) q <= spt[4*(sc / 23) +: 4];
            end else begin : g_t7
                always @(posedge clk) q <= (REGROOT >= 7 && sc >= 24) ? split_nx2 : split_nx;
            end
            assign spc[4*sc +: 4] = q;
        end
        for (sc = 0; sc < 5; sc = sc + 1) begin : g_ws
            if (sc < 3 || (sc == 3 && REGROOT >= 7) || (sc == 4 && REGROOT >= 8)) begin : g_w
                (* keep *) reg q;
                always @(posedge clk) q <= wsrc_nx;
                assign wsc[sc] = q;
            end else begin : g_wa
                assign wsc[sc] = wsc[(sc == 4) ? 0 : 1];
            end
        end
        if (REGROOT >= 7) begin : g_ktc
            wire [NW-1:0] ktot_nx = ((REGROOT >= 8) ? ldv[NLDD+5] : ld_go) ? i_k : ktot_r;
            for (sc = 0; sc < 5; sc = sc + 1) begin : g_kt
                (* keep *) reg [NW-1:0] q;
                always @(posedge clk) q <= ktot_nx;
                assign ktc[NW*sc +: NW] = q;
            end
        end else begin : g_kta
            assign ktc = {5{ktot_r}};
        end
    end else begin : g_rr_alias
        assign spc = {NSPC{split_r}};
        assign wsc = {5{wsrc_r}};
        assign ktc = {5{ktot_r}};
    end endgenerate

generate if (FAST_ISSUE == 0) begin : g_issue_legacy
    assign acc = {5{active}};
    assign klc = k_last;
    assign ldv = {NLD{1'b0}}; assign tsc = {4{ts_r}}; assign wcc = {4{wcs_r}}; assign sph = {NOH{16'd1 << split_r}};
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
    //: TP-setting bench mutants (qwen-tp8 2026-10-12; TMUT 0 = the real constants, synthesis-identical): 4 = the
    //: round-step products ts*(GT>>S) / ots*(GT>>S) built from a stale 2*GT (a TP4 constant on a TP8 tile).
    //: (a stale-2*GT pr_a or e_gm bound was tried as TMUT 5: unobservable -- it only touches groups no result port reads)
    localparam integer GT_TS = (TMUT == 4) ? (GT << 1) : GT;
    reg [AW+PRW-1:0] tsh [0:NB_GT-1];
    reg [AW+PRW-1:0] osh [0:NB_GT-1];
    reg [NW:0]       kpad_a;
    localparam [AW+PRW-1:0] SH_LO = {(AW+PRW)/2{1'b1}};   // REGROOT 6: low half of a round-step shifter (own copy)
    //: REGROOT 7: quarters (Q0|Q1 = SH_LO, Q2|Q3 = ~SH_LO), each with its own split copy; REGROOT 6 aliases the halves
    localparam [AW+PRW-1:0] SH_Q0 = {(AW+PRW)/4{1'b1}};
    localparam [AW+PRW-1:0] SH_Q1 = SH_LO & ~SH_Q0;
    localparam [AW+PRW-1:0] SH_Q2 = ~SH_LO & {((AW+PRW)/2 + (AW+PRW)/4 + 1){1'b1}};
    localparam [AW+PRW-1:0] SH_Q3 = ~SH_LO & ~SH_Q2;
    //: REGROOT 8: one round-step term and the octant masks; octant o of term b uses the REGROOT 7 quarter copy of
    //: quarter o/2 (even octant) or its twin + SPB (odd octant)
    function automatic [AW+PRW-1:0] shterm(input integer bb, input [3:0] sh, input [AW-1:0] x);
        shterm = ((((GT_TS >> bb) & 1) != 0) && bb >= sh) ? ({{PRW{1'b0}}, x} << (bb - sh)) : {(AW+PRW){1'b0}};
    endfunction
    function automatic [AW+PRW-1:0] octm(input integer o);
        integer lo, hi, bi;
        begin
            lo = (o * (AW+PRW)) / 8; hi = ((o + 1) * (AW+PRW)) / 8;
            octm = {(AW+PRW){1'b0}};
            for (bi = 0; bi < AW+PRW; bi = bi + 1) if (bi >= lo && bi < hi) octm[bi] = 1'b1;
        end
    endfunction
    //: the same term from a one-hot split copy (REGROOT 8): OR over k of (k == split) & term(k)
    function automatic [AW+PRW-1:0] shtoh(input integer bb, input [15:0] oh, input [AW-1:0] x);
        integer kk;
        begin
            shtoh = {(AW+PRW){1'b0}};
            for (kk = 0; kk < 16; kk = kk + 1)
                if (oh[kk] && (((GT_TS >> bb) & 1) != 0) && bb >= kk) shtoh = shtoh | ({{PRW{1'b0}}, x} << (bb - kk));
        end
    endfunction
    //: the REGROOT 7 quarter copy (tsh: quarters 0..3 -> 2p, 27+2p, 2p+1, 28+2p; osh: 4+2p, 31+2p, 5+2p, 32+2p)
    function automatic integer qcp(input integer q, input integer par, input integer osh_sel);
        qcp = (osh_sel == 0) ? ((q == 0) ? 2*par : (q == 1) ? 27 + 2*par : (q == 2) ? 2*par + 1 : 28 + 2*par)
                             : ((q == 0) ? 4 + 2*par : (q == 1) ? 31 + 2*par : (q == 2) ? 5 + 2*par : 32 + 2*par);
    endfunction
    if (REGROOT >= 8) begin : g_terms8
        always @(posedge clk) begin : p_terms8
            integer b, o;
            reg [AW+PRW-1:0] ta, oa8;
            for (b = 0; b < NB_GT; b = b + 1) begin
                ta = {(AW+PRW){1'b0}}; oa8 = {(AW+PRW){1'b0}};
                for (o = 0; o < 8; o = o + 1) begin
                    ta  = ta  | (shtoh(b, sph[16*(o/2) +: 16], ts_r)  & octm(o));
                    oa8 = oa8 | (shtoh(b, sph[16*(4+o/2) +: 16], ots_r) & octm(o));
                end
                tsh[b] <= ta; osh[b] <= oa8;
            end
            pr_a <= GT >> spc[4*8 +: 4];
            //: (1 << S) - 1 as two halves from copy 35 and its twin
            kpad_a <= {1'b0, ktc[0 +: NW]} + msk2(spc[4*35 +: 4], spc[4*(35+SPB) +: 4], {(NW+1)/2{1'b1}});
        end
    end else begin : g_terms7
        always @(posedge clk) begin : p_terms
            integer b;
            for (b = 0; b < NB_GT; b = b + 1) begin
                tsh[b] <= (((((GT_TS >> b) & 1) != 0 && b >= spc[4*(2*(b%2)) +: 4]) ? ({{PRW{1'b0}}, ts_r} << (b - spc[4*(2*(b%2)) +: 4])) : {(AW+PRW){1'b0}}) & SH_Q0)
                        | (((((GT_TS >> b) & 1) != 0 && b >= spc[4*(((REGROOT >= 7) ? 27+2*(b%2) : 2*(b%2))) +: 4]) ? ({{PRW{1'b0}}, ts_r} << (b - spc[4*(((REGROOT >= 7) ? 27+2*(b%2) : 2*(b%2))) +: 4])) : {(AW+PRW){1'b0}}) & SH_Q1)
                        | (((((GT_TS >> b) & 1) != 0 && b >= spc[4*(2*(b%2)+1) +: 4]) ? ({{PRW{1'b0}}, ts_r} << (b - spc[4*(2*(b%2)+1) +: 4])) : {(AW+PRW){1'b0}}) & SH_Q2)
                        | (((((GT_TS >> b) & 1) != 0 && b >= spc[4*(((REGROOT >= 7) ? 28+2*(b%2) : 2*(b%2)+1)) +: 4]) ? ({{PRW{1'b0}}, ts_r} << (b - spc[4*(((REGROOT >= 7) ? 28+2*(b%2) : 2*(b%2)+1)) +: 4])) : {(AW+PRW){1'b0}}) & SH_Q3);
                osh[b] <= (((((GT_TS >> b) & 1) != 0 && b >= spc[4*(4+2*(b%2)) +: 4]) ? ({{PRW{1'b0}}, ots_r} << (b - spc[4*(4+2*(b%2)) +: 4])) : {(AW+PRW){1'b0}}) & SH_Q0)
                        | (((((GT_TS >> b) & 1) != 0 && b >= spc[4*(((REGROOT >= 7) ? 31+2*(b%2) : 4+2*(b%2))) +: 4]) ? ({{PRW{1'b0}}, ots_r} << (b - spc[4*(((REGROOT >= 7) ? 31+2*(b%2) : 4+2*(b%2))) +: 4])) : {(AW+PRW){1'b0}}) & SH_Q1)
                        | (((((GT_TS >> b) & 1) != 0 && b >= spc[4*(5+2*(b%2)) +: 4]) ? ({{PRW{1'b0}}, ots_r} << (b - spc[4*(5+2*(b%2)) +: 4])) : {(AW+PRW){1'b0}}) & SH_Q2)
                        | (((((GT_TS >> b) & 1) != 0 && b >= spc[4*(((REGROOT >= 7) ? 32+2*(b%2) : 5+2*(b%2))) +: 4]) ? ({{PRW{1'b0}}, ots_r} << (b - spc[4*(((REGROOT >= 7) ? 32+2*(b%2) : 5+2*(b%2))) +: 4])) : {(AW+PRW){1'b0}}) & SH_Q3);
            end
            pr_a <= GT >> spc[4*8 +: 4];
            kpad_a <= {1'b0, ktc[0 +: NW]} + ((1 << spc[4*((REGROOT >= 7) ? 35 : 8) +: 4]) - 1);
        end
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
    //: REGROOT 8: kc_a halves from one-hot split copies 8 (low) / 9 (high) and wsrc copies 0 / 4
    wire [36:0] kc_ls = shro({{(37-NW){1'b0}}, kpad_a[NW-1:0]}, sph[16*8 +: 16]);
    wire [36:0] kc_hs = shro({{(37-NW){1'b0}}, kpad_a[NW-1:0]}, sph[16*9 +: 16]);
    always @(posedge clk) begin
        tsg_a <= tsum; otsg_a <= osum;
        if (REGROOT >= 8)
            //: quarters: 9 / 9+SPB the low half, 44 / 44+SPB the high half
            kc_a <= {wsc[4] ? kc_hs[NW-1:NW/2] : ktc[NW-1:NW/2], wsc[0] ? kc_ls[NW/2-1:0] : ktc[NW/2-1:0]};
        else
        kc_a <= wsc[0] ? {kpad_a[NW-1:0] >> spc[4*((REGROOT >= 7) ? 44 : 9) +: 4]} & {{(NW-NW/2){1'b1}}, {(NW/2){1'b0}}}
                       | {kpad_a[NW-1:0] >> spc[4*9 +: 4]} & {(NW/2){1'b1}} : ktc[0 +: NW];   // ceil(K/S) (K + S - 1 < 2^NW)
        tstep_r[AW/2-1:0] <= !wsc[1] ? ts_r[AW/2-1:0] : tsg_a[AW/2-1:0];
        tstep_r[AW-1:AW/2] <= !wsc[3] ? ts_r[AW-1:AW/2] : tsg_a[AW-1:AW/2];
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
    if (REGROOT < 6) begin : g_ctl_all
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
        assign acc = {5{active}};
        assign klc = k_last;
        assign ldv = {NLD{1'b0}}; assign tsc = {4{ts_r}}; assign wcc = {4{wcs_r}}; assign sph = {NOH{16'd1 << split_r}};
    end else if (REGROOT < 8) begin : g_ctl_rr6
        assign ldv = {NLD{1'b0}}; assign tsc = {4{ts_r}}; assign wcc = {4{wcs_r}}; assign sph = {NOH{16'd1 << split_r}};
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
                    xk <= i_xbase; xc <= i_xbase; xk_base <= i_xbase;
                end
            end else begin
                wrom_re <= !wsrc_r; kv_re <= wsrc_r;
                if (!j_last) begin
                    j <= j + 1'b1; xc <= xc_j;
                end else begin
                    j <= 0;
                    if (!k_last) begin
                        k <= k_1; k_last <= (k_2 == k_r);
                        xk <= xk_k; xc <= xk_k;
                    end else begin
                        k <= 0; k_last <= (k_r == 1);
                        xk <= xk_base; xc <= xk_base;
                        if (!t_last) begin
                            t <= t_1; t_last <= (t_2 == tiles_r);
                        end else begin
                            active <= 1'b0;
                        end
                    end
                end
            end
        end

        //: REGROOT 6 (QW-CLUSTER3/A0 10-19, safe-design item 3): the issue loop's broad control state (active, pend,
        //: j_last, k_last, t_last) is copied per destination field group as KEPT registers that load the canonical
        //: next-state wires below (same edge, same value; 0 cycles).  Each loop address field below owns its copies, so
        //: no control register or field-select decode drives more than one ~24-bit field.  The canonical registers stay
        //: in the reduced block (j/k/t counters, op fields, ROM/KV read enables).
        wire act_nx  = pend ? ((pcnt == 0) ? 1'b1 : active)
                            : (!active ? (go && !(KV_PREP > 0 && i_wsrc)) : !(j_last && k_last && t_last));
        wire pend_nx = pend ? (pcnt != 0) : ((!active && go && KV_PREP > 0 && i_wsrc) ? 1'b1 : pend);
        wire [$clog2(IL)-1:0] j_nx = pend ? j : (!active ? (go ? {$clog2(IL){1'b0}} : j) : (!j_last ? j + 1'b1 : {$clog2(IL){1'b0}}));
        wire jl_nx = (j_nx == IL - 1);
        wire kl_nx = pend ? k_last : (!active ? (go ? kc_is_1 : k_last)
                                              : (j_last ? (!k_last ? (k_2 == k_r) : (k_r == 1)) : k_last));
        wire tl_nx = pend ? t_last : (!active ? (go ? (i_tiles == 1) : t_last)
                                              : ((j_last && k_last && !t_last) ? (t_2 == tiles_r) : t_last));
        localparam integer NGF = (REGROOT >= 7) ? 12 : 9;    // cur, base_k, base_t, oa, ot, nb, nb_t, lb, wrom_addr (+ REGROOT 7: cur/base_k/base_t high halves)
        localparam integer HC = (REGROOT >= 7) ? AW/2 : AW;  // low-half width owned by groups 0..2
        wire [NGF-1:0] fa, fp, fjl, fkl, ftl;
        genvar fg;
        for (fg = 0; fg < NGF; fg = fg + 1) begin : g_fc
            (* keep *) reg a, p;
            (* keep *) reg jl, kl, tl;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin a <= 1'b0; p <= 1'b0; end
                else begin a <= act_nx; p <= pend_nx; end
            always @(posedge clk) if (rst_n) begin jl <= jl_nx; kl <= kl_nx; tl <= tl_nx; end
            assign fa[fg] = a; assign fp[fg] = p; assign fjl[fg] = jl; assign fkl[fg] = kl; assign ftl[fg] = tl;
        end
        //: copies for the consumers outside the loop: kv_addr groups 0..3, e_v / progress / idle (4); k_last for the tag
        for (fg = 0; fg < 5; fg = fg + 1) begin : g_ac
            (* keep *) reg a;
            always @(posedge clk or negedge rst_n) if (!rst_n) a <= 1'b0; else a <= act_nx;
            assign acc[fg] = a;
        end
        if (1) begin : g_kc
            (* keep *) reg kl;
            always @(posedge clk) if (rst_n) kl <= kl_nx;
            assign klc = kl;
        end
            for (fg = 0; fg < ((REGROOT >= 7) ? 2 : 1); fg = fg + 1) begin : g_hf
            localparam integer C = (fg == 0) ? 0 : 9;          // copy set: low half 0..2, high half 9..11
            localparam integer L = (fg == 0) ? 0 : HC;          // bit range [L, H)
            localparam integer HH = (fg == 0) ? HC : AW;
            always @(posedge clk) if (rst_n && !fp[C]) begin
                if (!fa[C]) begin if (go) cur[HH-1:L] <= i_wbase[HH-1:L]; end
                else if (!fjl[C]) begin if ((((j + 1'b1) >> jsh_r) << jsh_r) == (j + 1'b1)) cur[HH-1:L] <= cur_js[HH-1:L]; end
                else if (!fkl[C]) cur[HH-1:L] <= bk_k[HH-1:L];
                else if (!ftl[C]) cur[HH-1:L] <= bt_t[HH-1:L];
            end
            always @(posedge clk) if (rst_n && !fp[C+1]) begin
                if (!fa[C+1]) begin if (go) base_k[HH-1:L] <= i_wbase[HH-1:L]; end
                else if (fjl[C+1]) begin if (!fkl[C+1]) base_k[HH-1:L] <= bk_k[HH-1:L]; else if (!ftl[C+1]) base_k[HH-1:L] <= bt_t[HH-1:L]; end
            end
            always @(posedge clk) if (rst_n && !fp[C+2]) begin
                if (!fa[C+2]) begin if (go) base_t[HH-1:L] <= i_wbase[HH-1:L]; end
                else if (fjl[C+2] && fkl[C+2] && !ftl[C+2]) base_t[HH-1:L] <= bt_t[HH-1:L];
            end
        end
        always @(posedge clk) if (rst_n && !fp[3]) begin
            if (!fa[3]) begin if (go) oa <= i_obase; end
            else if (!fjl[3]) oa <= oa_j;
            else oa <= (fkl[3] && !ftl[3]) ? ot_t : ot;
        end
        always @(posedge clk) if (rst_n && !fp[4]) begin
            if (!fa[4]) begin if (go) ot <= i_obase; end
            else if (fjl[4] && fkl[4] && !ftl[4]) ot <= ot_t;
        end
        always @(posedge clk) if (rst_n && !fp[5]) begin
            if (!fa[5]) begin if (go) nb <= 0; end
            else if (!fjl[5]) nb <= nb_j;
            else nb <= (fkl[5] && !ftl[5]) ? nbt_t : nb_t;
        end
        always @(posedge clk) if (rst_n && !fp[6]) begin
            if (!fa[6]) begin if (go) nb_t <= 0; end
            else if (fjl[6] && fkl[6] && !ftl[6]) nb_t <= nbt_t;
        end
        always @(posedge clk) if (rst_n && !fp[7]) begin
            if (!fa[7]) begin if (go) lb <= 0; end
            else if (fjl[7] && fkl[7] && !ftl[7]) lb <= lb_t;
        end
        always @(posedge clk) if (rst_n && !fp[8] && fa[8]) wrom_addr <= cur;

    end else begin : g_ctl_rr8
        //: REGROOT 8 (QW-A0-RC4 10-20, PRE-GATE NATIVE CENSUS: no driver > 32 loads; rc7 mapped census NK 103 / NL 104
        //: drivers > 32, max 262 / 291 = the shared go-load enable rst_n & !pend & !active & go over ~400 descriptor
        //: bits).  Same values on the same edges, 0 cycles:
        //:  (1) the go-latched descriptor (plus per-group KV-offset copies of ts / wcs and 22 one-hot split copies) is
        //:      NLDD load groups of <= 12 bits; group l loads on ldv[l] = go_cp[NGOF + l%14] & idle copy l/14 (kept,
        //:      async reset 1, D = !act_nx & !pend_nx), i.e. exactly rst_n & !pend & !active & go (go_cp is reset like
        //:      go, so nothing loads in reset);
        //:  (2) every loop address field is cut into <= 12-bit chunks (oa / ot thirds; cur / base_k / base_t /
        //:      wrom_addr / xc / xk halves), each chunk with its own kept {active, pend, j_last, k_last, t_last} copy
        //:      and a go copy shared by two chunks; the canonical active / k_last keep only the counters.
        wire ra, rp, rkl, rtl, ra2, rp2;   // the counters' kept control copies (g_rc below)
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                active <= 1'b0; pend <= 1'b0; pcnt <= 4'd0;
                wrom_re <= 1'b0; kv_re <= 1'b0;
                split_fault <= 1'b0;
            end else if (rp2) begin
                wrom_re <= 1'b0; kv_re <= 1'b0;
                if (pcnt == 0) begin pend <= 1'b0; active <= 1'b1; end
                else pcnt <= pcnt - 1'b1;
            end else if (!ra2) begin
                wrom_re <= 1'b0; kv_re <= 1'b0;
                if (go) begin
                    if (KV_PREP > 0 && i_wsrc) begin pend <= 1'b1; pcnt <= KV_PREP - 1; end
                    else active <= 1'b1;
                    if (PRUNE && i_split < SMIN) split_fault <= 1'b1;
                    t <= 0; k <= 0; j <= 0;
                    t_last <= (i_tiles == 1); k_last <= kc_is_1;
                end
            end else begin
                wrom_re <= !wsrc_r; kv_re <= wsrc_r;
                if (!j_last) begin
                    j <= j + 1'b1;
                end else begin
                    j <= 0;
                    if (!rkl) begin
                        k <= k_1; k_last <= (k_2 == k_r);
                    end else begin
                        k <= 0; k_last <= (k_r == 1);
                        if (!rtl) begin
                            t <= t_1; t_last <= (t_2 == tiles_r);
                        end else begin
                            active <= 1'b0;
                        end
                    end
                end
            end
        end
        //: the counters' own kept control copy set (ra / rp / rkl / rtl): the canonical active / pend / k_last /
        //: t_last registers above are written but no longer read here (Yosys merged the unkept canonical k_last into
        //: one field copy in the first rc8 census: g_fc[19].kl 50 loads)
        wire act_nx  = rp ? ((pcnt == 0) ? 1'b1 : ra)
                          : (!ra ? (go && !(KV_PREP > 0 && i_wsrc)) : !(j_last && rkl && rtl));
        wire pend_nx = rp ? (pcnt != 0) : ((!ra && go && KV_PREP > 0 && i_wsrc) ? 1'b1 : rp);
        wire [$clog2(IL)-1:0] j_nx = rp ? j : (!ra ? (go ? {$clog2(IL){1'b0}} : j) : (!j_last ? j + 1'b1 : {$clog2(IL){1'b0}}));
        wire jl_nx = (j_nx == IL - 1);
        wire kl_nx = rp ? rkl : (!ra ? (go ? kc_is_1 : rkl)
                                     : (j_last ? (!rkl ? (k_2 == k_r) : (k_r == 1)) : rkl));
        wire tl_nx = rp ? rtl : (!ra ? (go ? (i_tiles == 1) : rtl)
                                     : ((j_last && rkl && !rtl) ? (t_2 == tiles_r) : rtl));
        if (1) begin : g_rc
            (* keep *) reg a, p, kl, tl;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin a <= 1'b0; p <= 1'b0; end
                else begin a <= act_nx; p <= pend_nx; end
            always @(posedge clk) if (rst_n) begin kl <= kl_nx; tl <= tl_nx; end
            assign ra = a; assign rp = p; assign rkl = kl; assign rtl = tl;
            //: a second {active, pend} copy for the counter block itself (rc8 r3 NL: g_rc.a 34 loads)
            (* keep *) reg a2, p2;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin a2 <= 1'b0; p2 <= 1'b0; end
                else begin a2 <= act_nx; p2 <= pend_nx; end
            assign ra2 = a2; assign rp2 = p2;
        end
        wire idle_nx = !act_nx && !pend_nx;
        //: field chunk groups: 0 cur lo, 1 base_k lo, 2 base_t lo, 3 oa[7:0], 4 ot[7:0], 5 nb, 6 nb_t, 7 lb,
        //: 8 wrom_addr lo, 9 cur hi, 10 base_k hi, 11 base_t hi, 12 oa[15:8], 13 oa[23:16], 14 ot[15:8], 15 ot[23:16],
        //: 16 wrom_addr hi, 17 xc lo, 18 xc hi, 19 xk lo, 20 xk hi
        localparam integer NGF = 21;
        localparam integer NGOF = (NGF + 1) / 2;   // go copies 0..NGOF-1 serve the field groups (two each)
        localparam integer HC = AW / 2;
        wire [NGF-1:0] fa, fp, fjl, fkl, ftl, fgo;
        genvar fg;
        for (fg = 0; fg < NGF; fg = fg + 1) begin : g_fc
            (* keep *) reg a, p;
            (* keep *) reg jl, kl, tl;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin a <= 1'b0; p <= 1'b0; end
                else begin a <= act_nx; p <= pend_nx; end
            always @(posedge clk) if (rst_n) begin jl <= jl_nx; kl <= kl_nx; tl <= tl_nx; end
            assign fa[fg] = a; assign fp[fg] = p; assign fjl[fg] = jl; assign fkl[fg] = kl; assign ftl[fg] = tl;
            assign fgo[fg] = go_cp[fg / 2];
        end
        for (fg = 0; fg < 5; fg = fg + 1) begin : g_ac
            (* keep *) reg a;
            always @(posedge clk or negedge rst_n) if (!rst_n) a <= 1'b0; else a <= act_nx;
            assign acc[fg] = a;
        end
        if (1) begin : g_kc
            (* keep *) reg kl;
            always @(posedge clk) if (rst_n) kl <= kl_nx;
            assign klc = kl;
        end
        //: descriptor load groups
        //: load group l = go copy NGOF + l % NLG AND idle copy l / NLG: a distinct (go, idle) pair per group, so no two
        //: groups share an enable gate (rc8 r2: groups with the same pair were merged, 48-82 loads)
        localparam integer NLG = 14;
        wire [(NLD+NLG-1)/NLG-1:0] idc;
        for (fg = 0; fg < (NLD + NLG - 1) / NLG; fg = fg + 1) begin : g_ld
            (* keep *) reg i;
            always @(posedge clk or negedge rst_n) if (!rst_n) i <= 1'b1; else i <= idle_nx;
            assign idc[fg] = i;
        end
        for (fg = 0; fg < NLD; fg = fg + 1) begin : g_le
            assign ldv[fg] = go_cp[NGOF + fg % NLG] && idc[fg / NLG];
        end
        wire [AW-1:0] sbase_in = (INT8_WEIGHT != 0 && INT8_SCALE_WCS_BASE != 0) ? i_wcs : i_wbase;
        localparam integer DW = 3*NW + 5 + 1 + 4 + 3 + 12*AW + 8*AW + 16*NOH;
        wire [15:0] oh_in = 16'd1 << ((SPLIT_CP != 0) ? i_split_copy : i_split);
        wire [DW-1:0] d_in = {i_nout, i_tiles, i_k, i_wsrc, i_round, i_oen, i_amax, i_rmax, i_mmode, i_split, i_jsh,
                              i_mbase, sbase_in, i_wcs, i_ts, i_ks, i_js, i_xks, i_xjs, i_xcs, i_ots, i_ojs, i_xbase,
                              {4{i_ts}}, {4{i_wcs}}, {NOH{oh_in}}};
        (* keep *) reg [4*AW-1:0] tsc_q, wcc_q;
        (* keep *) reg [16*NOH-1:0] oh_q;
        wire [DW-1:0] d_cur = {nout_r, tiles_r, ktot_r, wsrc_r, round_r, oen_r, amax_r, rmax_r, mmode_r, split_r, jsh_r,
                               mbase_r, scale_base_r, wcs_r, ts_r, ks_r, js_r, xks_r, xjs_r, xcs_r, ots_r, ojs_r, xk_base,
                               tsc_q, wcc_q, oh_q};
        localparam integer CH = (DW + NLDD - 1) / NLDD;
        wire [DW-1:0] d_nx;
        genvar db;
        for (db = 0; db < DW; db = db + 1) begin : g_dn
            assign d_nx[db] = ldv[db / CH] ? d_in[db] : d_cur[db];
        end
        always @(posedge clk)
            {nout_r, tiles_r, ktot_r, wsrc_r, round_r, oen_r, amax_r, rmax_r, mmode_r, split_r, jsh_r,
             mbase_r, scale_base_r, wcs_r, ts_r, ks_r, js_r, xks_r, xjs_r, xcs_r, ots_r, ojs_r, xk_base,
             tsc_q, wcc_q, oh_q} <= d_nx;
        assign tsc = tsc_q; assign wcc = wcc_q; assign sph = oh_q;
        //: address field chunks: [L, H) of field group C
        for (fg = 0; fg < 2; fg = fg + 1) begin : g_hf
            localparam integer C = (fg == 0) ? 0 : 9;
            localparam integer L = (fg == 0) ? 0 : HC;
            localparam integer HH = (fg == 0) ? HC : AW;
            always @(posedge clk) if (!fp[C]) begin
                if (!fa[C]) begin if (fgo[C]) cur[HH-1:L] <= i_wbase[HH-1:L]; end
                else if (!fjl[C]) begin if ((((j + 1'b1) >> jsh_r) << jsh_r) == (j + 1'b1)) cur[HH-1:L] <= cur_js[HH-1:L]; end
                else if (!fkl[C]) cur[HH-1:L] <= bk_k[HH-1:L];
                else if (!ftl[C]) cur[HH-1:L] <= bt_t[HH-1:L];
            end
            always @(posedge clk) if (!fp[C+1]) begin
                if (!fa[C+1]) begin if (fgo[C+1]) base_k[HH-1:L] <= i_wbase[HH-1:L]; end
                else if (fjl[C+1]) begin if (!fkl[C+1]) base_k[HH-1:L] <= bk_k[HH-1:L]; else if (!ftl[C+1]) base_k[HH-1:L] <= bt_t[HH-1:L]; end
            end
            always @(posedge clk) if (!fp[C+2]) begin
                if (!fa[C+2]) begin if (fgo[C+2]) base_t[HH-1:L] <= i_wbase[HH-1:L]; end
                else if (fjl[C+2] && fkl[C+2] && !ftl[C+2]) base_t[HH-1:L] <= bt_t[HH-1:L];
            end
            localparam integer CW8 = (fg == 0) ? 8 : 16;      // wrom_addr chunk group
            localparam integer CX = (fg == 0) ? 17 : 18;      // xc chunk group
            localparam integer CK = (fg == 0) ? 19 : 20;      // xk chunk group
            always @(posedge clk) if (!fp[CW8] && fa[CW8]) wrom_addr[HH-1:L] <= cur[HH-1:L];
            always @(posedge clk) if (!fp[CX]) begin
                if (!fa[CX]) begin if (fgo[CX]) xc[HH-1:L] <= i_xbase[HH-1:L]; end
                else if (!fjl[CX]) xc[HH-1:L] <= xc_j[HH-1:L];
                else if (!fkl[CX]) xc[HH-1:L] <= xk_k[HH-1:L];
                else xc[HH-1:L] <= xk_base[HH-1:L];
            end
            always @(posedge clk) if (!fp[CK]) begin
                if (!fa[CK]) begin if (fgo[CK]) xk[HH-1:L] <= i_xbase[HH-1:L]; end
                else if (fjl[CK]) begin
                    if (!fkl[CK]) xk[HH-1:L] <= xk_k[HH-1:L];
                    else xk[HH-1:L] <= xk_base[HH-1:L];
                end
            end
        end
        for (fg = 0; fg < 3; fg = fg + 1) begin : g_ot
            localparam integer CA = (fg == 0) ? 3 : 11 + fg;  // oa thirds: 3, 12, 13
            localparam integer CT = (fg == 0) ? 4 : 13 + fg;  // ot thirds: 4, 14, 15
            localparam integer L = fg * AW / 3;
            localparam integer HH = (fg + 1) * AW / 3;
            always @(posedge clk) if (!fp[CA]) begin
                if (!fa[CA]) begin if (fgo[CA]) oa[HH-1:L] <= i_obase[HH-1:L]; end
                else if (!fjl[CA]) oa[HH-1:L] <= oa_j[HH-1:L];
                else oa[HH-1:L] <= (fkl[CA] && !ftl[CA]) ? ot_t[HH-1:L] : ot[HH-1:L];
            end
            always @(posedge clk) if (!fp[CT]) begin
                if (!fa[CT]) begin if (fgo[CT]) ot[HH-1:L] <= i_obase[HH-1:L]; end
                else if (fjl[CT] && fkl[CT] && !ftl[CT]) ot[HH-1:L] <= ot_t[HH-1:L];
            end
        end
        always @(posedge clk) if (!fp[5]) begin
            if (!fa[5]) begin if (fgo[5]) nb <= 0; end
            else if (!fjl[5]) nb <= nb_j;
            else nb <= (fkl[5] && !ftl[5]) ? nbt_t : nb_t;
        end
        always @(posedge clk) if (!fp[6]) begin
            if (!fa[6]) begin if (fgo[6]) nb_t <= 0; end
            else if (fjl[6] && fkl[6] && !ftl[6]) nb_t <= nbt_t;
        end
        always @(posedge clk) if (!fp[7]) begin
            if (!fa[7]) begin if (fgo[7]) lb <= 0; end
            else if (fjl[7] && fkl[7] && !ftl[7]) lb <= lb_t;
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
        //: from the go's latched fields: (1) q, c; (2) the shifted rows of both products, four carry-save
        //: quarters (q low / high bits, c low / high bits) each reduced to two; (3) the eight rows reduced to two
        //: and their kept prefix sum -- ready after KV_PREP = 3.  q = g >> S and c = g mod 2^S are both at most
        //: the group index g < GT, so each has clog2(GT) bits (the rows above are always zero).  [W12 HBM fmax:
        //: one 30-row tree in stage (2) was -190 ps at 0.833 ns SS in the routed tile]
        localparam integer QW = $clog2(GT);           // q <= g < GT
        localparam integer CW = $clog2(GT);           // c <= g < GT
        localparam integer QL = (QW + 1) / 2, CL = (CW + 1) / 2;
        reg [QW-1:0] q_p [0:G-1];
        reg [CW-1:0] c_p [0:G-1];
        reg [AW-1:0] off [0:G-1];
        genvar gq, rb;
        for (gq = 0; gq < G; gq = gq + 1) begin : g_off
            wire [AW-1:0] a_s, osum;
            wire [QW*AW-1:0] qrows;
            wire [CW*AW-1:0] crows;
            for (rb = 0; rb < QW; rb = rb + 1) begin : g_rq
                assign qrows[rb*AW +: AW] = q_p[gq][rb] ? (tsc[AW*gq +: AW] << rb) : {AW{1'b0}};
            end
            for (rb = 0; rb < CW; rb = rb + 1) begin : g_rc
                assign crows[rb*AW +: AW] = c_p[gq][rb] ? (wcc[AW*gq +: AW] << rb) : {AW{1'b0}};
            end
            wire [31:0] gbq = gbc[32*gq +: 32] + gq;
            //: REGROOT 8: low half of q / c from copy 10+g / 14+g, the rest from the twin
            wire [31:0] qv = (REGROOT >= 8) ? shro({5'd0, gbq}, sph[16*(10+gq) +: 16])
                                            : (gb + gq) >> spc[4*(10+gq) +: 4];
            wire [31:0] cv = (REGROOT >= 8) ? ({5'd0, gbq} & msk2(spc[4*(14+gq) +: 4], spc[4*(14+gq+SPB) +: 4], (37'd1 << (CW/2)) - 37'd1))
                                            : (gb + gq) & ((1 << spc[4*(14+gq) +: 4]) - 1);
            wire [8*AW-1:0] part;
            ot_qwen_w12_csa_tree #(.W(AW), .N(QL)) u_q0 (.rows(qrows[QL*AW-1:0]), .s(part[0*AW +: AW]), .c(part[1*AW +: AW]));
            ot_qwen_w12_csa_tree #(.W(AW), .N(QW-QL)) u_q1 (.rows(qrows[QW*AW-1:QL*AW]), .s(part[2*AW +: AW]), .c(part[3*AW +: AW]));
            ot_qwen_w12_csa_tree #(.W(AW), .N(CL)) u_c0 (.rows(crows[CL*AW-1:0]), .s(part[4*AW +: AW]), .c(part[5*AW +: AW]));
            ot_qwen_w12_csa_tree #(.W(AW), .N(CW-CL)) u_c1 (.rows(crows[CW*AW-1:CL*AW]), .s(part[6*AW +: AW]), .c(part[7*AW +: AW]));
            reg  [8*AW-1:0] r_part;
            wire [AW-1:0] cs_s, cs_c;
            ot_qwen_w12_csa_tree #(.W(AW), .N(8)) u_cs (.rows(r_part), .s(cs_s), .c(cs_c));
            if (KV_PREP >= 4) begin : g_cs_reg
                //: KV_PREP >= 4 (margin rule 2026-10-06; tile_tp4_t4 SS -18.9 ps on r_part -> 8-row CSA -> prefix sum
                //: -> off): the two carry-save rows are registered before the kept prefix sum (offset ready after 4)
                reg [AW-1:0] cs_s_q, cs_c_q;
                always @(posedge clk) begin cs_s_q <= cs_s; cs_c_q <= cs_c; end
                ot_qwen_w12_kadd #(.W(AW)) u_sum (.a(cs_s_q), .b(cs_c_q), .s(osum));
            end else begin : g_cs_comb
                ot_qwen_w12_kadd #(.W(AW)) u_sum (.a(cs_s), .b(cs_c), .s(osum));
            end
            always @(posedge clk) begin
                q_p[gq] <= qv[QW-1:0];
                c_p[gq] <= cv[CW-1:0];
                r_part <= part;
                off[gq] <= osum;
            end
            ot_qwen_w12_kadd #(.W(AW)) u_ka (.a(cur), .b(off[gq]), .s(a_s));
            always @(posedge clk)
                if (acc[gq]) kv_addr[gq*AW +: AW] <= a_s;
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
        else e_v <= acc[4];
    end
    //: the element's round (SCALE_LOCAL scale addressing), beside the tag
    reg [NW-1:0] e_t, s1_t, s1b_t, s2_t, s3_t;
    wire [NW-1:0] m_t;
    ot_hdc_delay #(.W(NW), .D(MEM_EXTRA)) u_mtt (.clk(clk), .rst_n(rst_n), .d(e_t), .q(m_t));
    always @(posedge clk) begin e_t <= t; s1_t <= m_t; s1b_t <= s1_t; s2_t <= s1b_t; s3_t <= s2_t; end
    always @(posedge clk) begin
        e_first <= (k == 0); e_last <= klc;
        e_oen <= oen_r; e_amax <= amax_r; e_wsrc <= wsc[2]; e_round <= round_r; e_mmode <= mmode_r;
        e_split <= spc[4*26 +: 4]; e_oa <= oa; e_ots <= ots_r; e_nb <= nb; e_lb <= lb;
        e_rem <= {1'b0, nout_r};
        e_rmax <= rmax_r; e_j <= j; e_mbase <= mbase_r;
        e_opend <= t_last && klc && j_last;              // the op's last element
    end
    generate if (LANES && FAST_ISSUE != 0 && KV_PREP >= 2) begin : g_gm_fast
        //: k*S + c < K  <=>  k < ceil((K - c) / S) (K > c): the per-group K-step limit is constant through the op, a
        //: two-stage pipeline from the latched fields, ready by the KV op's first element (KV_PREP >= 2)
        reg [NW:0] kdif [0:G-1];
        reg [NW:0] klim [0:G-1];
        genvar gk;
        for (gk = 0; gk < G; gk = gk + 1) begin : g_kl
            wire [3:0]  sa = spc[4*(18+gk) +: 4], sb = spc[4*(22+gk) +: 4];
            wire [3:0]  sd = spc[4*((REGROOT >= 7) ? 36+gk : 18+gk) +: 4], sc = spc[4*((REGROOT >= 7) ? 40+gk : 22+gk) +: 4];
            wire [NW-1:0] kt = ktc[NW*(1+gk) +: NW];
            if (REGROOT >= 8) begin : g_k8
                //: REGROOT 8: each split use takes copy c for its low bits and twin c + SPB for the rest
                wire [3:0] sa2 = spc[4*(18+gk+SPB) +: 4];
                wire [3:0] sd2 = spc[4*(36+gk+SPB) +: 4];
                wire [31:0] gbk = gbc[32*gk +: 32] + gk;
                wire [31:0] c32 = {5'd0, gbk} & msk2(sa, sa2, 37'hFF);
                wire [36:0] kdm = msk2(sd, sd2, (37'd1 << ((NW+1)/2)) - 37'd1);
                wire [36:0] kls = shro({{(36-NW){1'b0}}, kdif[gk]}, sph[16*(14+gk) +: 16]);
                wire [36:0] gsh = shro({5'd0, gbk}, sph[16*(18+gk) +: 16]);
                wire [36:0] tsh_gt = shro(GT, sph[16*(18+gk) +: 16]);
                always @(posedge clk) begin
                    kdif[gk] <= ({{(32-NW){1'b0}}, kt} > c32) ? (kt - c32[NW:0] + kdm[NW:0]) : {(NW+1){1'b0}};
                    klim[gk] <= kls[NW:0];
                    e_gm[gk] <= (gsh < tsh_gt) && (!wsc[2] || ({1'b0, k} < klim[gk]));
                end
            end else begin : g_k7
            wire [31:0] c32 = (gb + gk) & ((1 << sa) - 1);
            always @(posedge clk) begin
                kdif[gk] <= ({{(32-NW){1'b0}}, kt} > c32) ? (kt - c32[NW:0] + ((1 << sd) - 1)) : {(NW+1){1'b0}};
                klim[gk] <= kdif[gk] >> sb;
                e_gm[gk] <= (((gb + gk) >> sc) < (GT >> sc)) && (!wsc[2] || ({1'b0, k} < klim[gk]));
            end
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
    reg [GL*W*((INT8_WEIGHT != 0 && WCONV == 0) ? 8 : 16)-1:0] mq_wrom;
    reg [GL*W*32-1:0] mq_kv;
    reg [GL*32-1:0]   mq_x;
    reg [GL*W*32-1:0] s2_w, s3_w;
    reg [GL*32-1:0]   s2_x, s3_x;
    wire [GL*32-1:0]  s3x_d;                       // the x word S3 takes (HIER: the leaves' pin flops take it too)
    reg [G-1:0]      s1_gm, s1b_gm, s2_gm;
    integer l;
    //: the BF16 round of x: x + 0x7FFF + x[16] as a kept prefix add (bit-identical to the flattened `+`)
    wire [GL*32-1:0] x_rnd;
    genvar xr;
    generate for (xr = 0; xr < GL; xr = xr + 1) begin : g_xrnd
        if (FAST_ISSUE != 0 && !(REGROOT >= 8 && HIER > 0 && HIER_HARD != 0 && XTX >= 2)) begin : g_keep_round
            ot_qwen_w12_kadd #(.W(32)) u_r (.a(s2_x[32*xr +: 32]), .b(32'h7FFF + {31'd0, s2_x[32*xr + 16]}), .s(x_rnd[32*xr +: 32]));
        end else begin : g_legacy_round
            assign x_rnd[32*xr +: 32] = s2_x[32*xr +: 32] + 32'h7FFF + {31'd0, s2_x[32*xr + 16]};
        end
    end endgenerate
    // REGROOT (Q-ROMPARENT 10-16): the ROM word register mq_wrom and the weight operand s2_w take the regional root of
    // their ROM column (lanes [0, G*W/2) = west column ck_reg[2], the rest = east ck_reg[3]); same values, same edges.
    generate if (LANES && REGROOT != 0) begin : g_operand_rr
        localparam integer HL = G * W / 2;
        localparam integer WB = (INT8_WEIGHT != 0 && WCONV == 0) ? 8 : 16;
        integer lw, le;
        // REGROOT 3 (Q-A0FIX2 10-19, landed select): the s2_w operand selects (s1b_gm / s1b_wsrc) were one hub flop on
        // root ck broadcast ~490 um into both gutter roots (NL c1r9e cross_clock ck -> ck_dw 505 endpoints, worst
        // -235 ps: 700 ps of repeaters + the 150 ps distinct-entry reserve).  Each half now keeps its own copy of the
        // S1B select on its own regional root, taken from the hub's S1 register: the entry crossing is one flop -> one
        // flop (no logic, single fanout) and the fan-out to the half's 1,024 operand flops stays inside one root.  Same
        // values on the same edges (s1b_* <= s1_* on the shared tile clock): 0 cycles, bit-identical.
        wire           wsrc_w, wsrc_e;
        wire [G-1:0]   gm_w, gm_e;
        // REGROOT4: same S1->S1B edge, one select owner per two lanes.
        // Each FP operand has sixteen variable upper bits, so two lanes
        // consume at most 32 mux select inputs. No old half-select flops
        // remain in this branch. S1 wsrc drives exactly 32 copy D pins at
        // production G=4,W=16; actual mapped primitive census is mandatory.
        localparam integer CSP = (G * W + 1) / 2;
        wire [CSP-1:0] wsrc_local, gm_local;
        if (REGROOT >= 4) begin : g_csel
            (* keep *) reg [CSP-1:0] wsrc_q, gm_q;
            for (genvar cp=0; cp<CSP; cp=cp+1) begin : g_cp
                wire copy_clk = (2*cp < HL) ? ck_reg[2] : ck_reg[3];
                always @(posedge copy_clk) begin
                    wsrc_q[cp] <= s1_wsrc;
                    gm_q[cp] <= s1_gm[(2*cp)/W];
                end
            end
            assign wsrc_local = wsrc_q;
            assign gm_local = gm_q;
            assign wsrc_w=1'b0; assign wsrc_e=1'b0;
            assign gm_w='0; assign gm_e='0;
        end else if (REGROOT >= 3) begin : g_lsel
            (* keep *) reg           s1b_wsrc_w, s1b_wsrc_e;
            (* keep *) reg [G/2-1:0] s1b_gm_w;
            (* keep *) reg [G-G/2-1:0] s1b_gm_e;
            always @(posedge ck_reg[2]) begin s1b_wsrc_w <= s1_wsrc; s1b_gm_w <= s1_gm[G/2-1:0]; end
            always @(posedge ck_reg[3]) begin s1b_wsrc_e <= s1_wsrc; s1b_gm_e <= s1_gm[G-1:G/2]; end
            assign wsrc_w = s1b_wsrc_w; assign wsrc_e = s1b_wsrc_e;
            assign gm_w = {{(G-G/2){1'b0}}, s1b_gm_w};
            assign gm_e = {s1b_gm_e, {(G/2){1'b0}}};
            assign wsrc_local='0; assign gm_local='0;
        end else begin : g_hsel
            assign wsrc_w = s1b_wsrc; assign wsrc_e = s1b_wsrc;
            assign gm_w = s1b_gm; assign gm_e = s1b_gm;
            assign wsrc_local='0; assign gm_local='0;
        end
        always @(posedge ck_reg[2]) begin
            mq_wrom[0 +: HL*WB] <= wrom_q[0 +: HL*WB];
            for (lw = 0; lw < HL; lw = lw + 1)
                if (INT8_WEIGHT != 0 && WCONV == 0)
                    s2_w[32*lw +: 32] <= !(REGROOT >= 4 ? gm_local[lw/2] : gm_w[lw / W]) ? 32'd0 : (REGROOT >= 4 ? wsrc_local[lw/2] : wsrc_w) ? mq_kv[32*lw +: 32] :
                                              {int8_bf16(mq_wrom[8*lw +: 8]), 16'h0000};
                else
                    s2_w[32*lw +: 32] <= !(REGROOT >= 4 ? gm_local[lw/2] : gm_w[lw / W]) ? 32'd0 : (REGROOT >= 4 ? wsrc_local[lw/2] : wsrc_w) ? mq_kv[32*lw +: 32] :
                                              {mq_wrom[16*lw +: 16], 16'h0000};
        end
        always @(posedge ck_reg[3]) begin
            mq_wrom[HL*WB +: HL*WB] <= wrom_q[HL*WB +: HL*WB];
            for (le = HL; le < G * W; le = le + 1)
                if (INT8_WEIGHT != 0 && WCONV == 0)
                    s2_w[32*le +: 32] <= !(REGROOT >= 4 ? gm_local[le/2] : gm_e[le / W]) ? 32'd0 : (REGROOT >= 4 ? wsrc_local[le/2] : wsrc_e) ? mq_kv[32*le +: 32] :
                                              {int8_bf16(mq_wrom[8*le +: 8]), 16'h0000};
                else
                    s2_w[32*le +: 32] <= !(REGROOT >= 4 ? gm_local[le/2] : gm_e[le / W]) ? 32'd0 : (REGROOT >= 4 ? wsrc_local[le/2] : wsrc_e) ? mq_kv[32*le +: 32] :
                                              {mq_wrom[16*le +: 16], 16'h0000};
        end
        always @(posedge clk) begin
            s1_gm <= m_gm; s1b_gm <= s1_gm; s2_gm <= s1b_gm;
            mq_kv <= kv_q; mq_x <= x_q;
            s2_x <= mq_x;
            s3_w <= s2_w;
            s3_x <= s3x_d;
        end
    end else if (LANES) begin : g_operand
        always @(posedge clk) begin
            s1_gm <= m_gm; s1b_gm <= s1_gm; s2_gm <= s1b_gm;
            mq_x <= x_q;
            s2_x <= mq_x;
            s3_w <= s2_w;
            s3_x <= s3x_d;
        end
        if (GLUE_HARD != 0) begin:g_hard
            if (W != 16 || G != 4 || HIER != 2 || WCONV != 1 || LOCAL_ROOTS == 0 || CHILD_CLOCKS == 0) begin:g_bad
                initial $fatal(1,"GLUE_HARD operand requires fixed 64-lane ROM consumer configuration");
            end
            for(genvar cg=0;cg<8;cg=cg+1)begin:g_consumer
                wire [127:0] w_d, w_q;
                for(genvar gg=0;gg<4;gg=gg+1)begin:g_group
                    for(genvar ll=0;ll<2;ll=ll+1)begin:g_lane
                        assign w_d[16*(2*gg+ll)+:16]=wrom_q[16*(16*gg+2*cg+ll)+:16];
                        assign s2_w[32*(16*gg+2*cg+ll)+:32]={w_q[16*(2*gg+ll)+:16],16'd0};
                    end
                end
                ot_qwen_tile_operand u_operand(.clk(ck_tx[cg]),.w_d(w_d),.gm_d(s1_gm),.wsrc_d(s1_wsrc),.w_q(w_q));
            end
        end else begin:g_soft
            always @(posedge clk)begin
                mq_wrom <= wrom_q; mq_kv <= kv_q;
                for (l = 0; l < G * W; l = l + 1)
                    if (INT8_WEIGHT != 0 && WCONV == 0)
                        s2_w[32*l +: 32] <= !s1b_gm[l / W] ? 32'd0 : s1b_wsrc ? mq_kv[32*l +: 32] :
                                                  {int8_bf16(mq_wrom[8*l +: 8]), 16'h0000};
                    else
                        s2_w[32*l +: 32] <= !s1b_gm[l / W] ? 32'd0 : s1b_wsrc ? mq_kv[32*l +: 32] :
                                                  {mq_wrom[16*l +: 16], 16'h0000};
            end
        end
    end endgenerate
    genvar xg;
    wire [2*GL-1:0] round_local;
    generate if (REGROOT >= 4 && LANES) begin : g_roundc
        // Same S1B->S2 edge; one select owner per sixteen output bits.
        (* keep *) reg [2*GL-1:0] round_q;
        always @(posedge clk) round_q <= {2*GL{s1b_round}};
        assign round_local=round_q;
    end else begin : g_round_legacy
        assign round_local={2*GL{s2_round}};
    end endgenerate
    generate for (xg = 0; xg < GL; xg = xg + 1) begin : g_s3xd
        assign s3x_d[32*xg +: 16] = !s2_gm[xg] ? 16'd0 :
                                    round_local[2*xg] ? 16'd0 : s2_x[32*xg +: 16];
        assign s3x_d[32*xg+16 +: 16] = !s2_gm[xg] ? 16'd0 :
                                    round_local[2*xg+1] ? x_rnd[32*xg+16 +: 16] : s2_x[32*xg+16 +: 16];
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
    wire [GI*W*32-1:0] lvl_h;                       // HIER: the leaves' last tree level
    wire               tfault_h;
    genvar g, gl;
    //: LRST: kept reset copies (async assert, released one edge after rst_n): one per lane group, one per tree level
    wire [G-1:0]  rst_g;
    wire [LG:0]   rst_t;
    // LRST = 2 (struct-close 2026-10-09, "-cl"): the same copies as keep_hierarchy instances.  With LRST = 1 the ORFS
    // yosys (0.68) opt_merge folds the identical (* keep *) flops back into ONE (qfd_tile_rp1p / tile_e_rp2np post-CTS:
    // the only startpoint is u_me.g_lrst.rt[0] -> lane multipliers / tree adders, -45..-75 ps TT, fanout tree 200+ ps
    // of wire).  Same reset behaviour (async assert, release one edge after rst_n), 0 cycles.
    generate if (LRST >= 2) begin : g_lrst2
        for (g = 0; g < G; g = g + 1) begin : g_rg
            ot_qwen_lrst_ff u_rg (.clk(clk), .rst_n(rst_n), .q(rst_g[g]));
        end
        for (g = 0; g <= LG; g = g + 1) begin : g_rt
            ot_qwen_lrst_ff u_rt (.clk(clk), .rst_n(rst_n), .q(rst_t[g]));
        end
    end else if (LRST != 0) begin : g_lrst
        (* keep *) reg [G-1:0] rg;
        (* keep *) reg [LG:0]  rt;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin rg <= {G{1'b0}}; rt <= {(LG+1){1'b0}}; end
            else begin rg <= {G{1'b1}}; rt <= {(LG+1){1'b1}}; end
        end
        assign rst_g = rg; assign rst_t = rt;
    end else begin : g_nolrst
        assign rst_g = {G{rst_n}}; assign rst_t = {(LG+1){rst_n}};
    end endgenerate
    generate if (HIER > 0) begin : g_hier
`ifndef SYNTHESIS
        initial if (PART == 2 || !LANES || !(PRUNE && SMIN >= LG) || (W % HIER) != 0 || LG < 2) begin
            $display("FAIL HIER=%0d needs PART != 2, LANES, every tree level adding (SMIN %0d >= LG %0d), W %% NPL == 0, LG >= 2",
                     HIER, SMIN, LG);
            $finish;
        end
`endif
        //: lane-slice leaves (W / HIER of them); lvl[LG] / lfault / tfault come from the leaves
        localparam integer NS = W / HIER;
        wire [NS-1:0] stf;
        wire [W*32-1:0] top;
        //: REGROOT 9: ONE ring of the hub-root (ck) half of the rung-0 word, shared by every leaf's read (the control
        //: fields, the round / mask selects and the raw x are the same word for all leaves):
        //: {s2_v, s2_first, split tag, sel (4 G), s2_x (G words)}.
        localparam integer L9C  = 1 + 1 + 4 + 4 * G + G * 32;
        localparam integer L9CC = (L9C + 23) / 24;
        wire [4*L9C-1:0]  l2c_bank;
        wire [4*L9CC-1:0] l2c_vld;
        if (L9 != 0) begin : g_l2c
            wire [4*G-1:0] sel;
            for (gl = 0; gl < G; gl = gl + 1) begin : g_s
                assign sel[4*gl +: 4] = {round_local[2*gl+1], round_local[2*gl], s2_gm[gl], s2_gm[gl]};
            end
            ot_qw_lw #(.W(L9C)) u_qlw2c (.ck(clk), .rsi(rst_n), .i({s2_v, s2_first, s2_tag[TW-6 -: 4], sel, s2_x[G*32-1:0]}),
                .bank(l2c_bank), .vld(l2c_vld));
        end else begin : g_nl2c
            assign l2c_bank = {4*L9C{1'b0}};
            assign l2c_vld  = {4*L9CC{1'b0}};
        end
        for (g = 0; g < NS; g = g + 1) begin : g_sl
            wire [G*HIER*32-1:0] w_in;
            wire [G*HIER-1:0] lf;
            for (gl = 0; gl < G * HIER; gl = gl + 1) begin : g_wi
                assign w_in[32*gl +: 32] = s2_w[32*((gl / HIER) * W + g * HIER + (gl % HIER)) +: 32];
                assign lfault[(gl / HIER) * W + g * HIER + (gl % HIER)] = lf[gl];
            end
            if (HIER_HARD != 0) begin : g_hd
`ifndef SYNTHESIS
                initial if (G != 4 || HIER != 2 || IL != 8 || MUL_LAT != 8 || ACC_LAT != 7 || TREE_LAT != 7 || LRST != 3 || ANR != 1) begin
                    $display("FAIL HIER_HARD: engine parameters differ from the hardened leaf ot_qwen_tile_lsl"); $finish;
                end
`endif
                //: LRR: one reset relay flop per leaf (asynchronous assert, release one edge later), so the tile reset port
                //: drives 8 relay flops instead of every leaf's relays across the frame
                wire rst_l;
                if (LRR != 0) begin : g_lrr
                    (* keep *) reg rq;
                    always @(posedge ((LOCAL_ROOTS != 0 && CHILD_CLOCKS != 0) ? ck_tx[g] : clk) or negedge rst_n) if (!rst_n) rq <= 1'b0; else rq <= 1'b1;
                    assign rst_l = rq;
                end else begin : g_lrn
                    assign rst_l = rst_n;
                end
                //: XTX: registered transmit rungs per leaf (one kept instance per leaf and rung, so Yosys opt_merge cannot
                //: fold the 8 identical copies back into one broadcast).  Rung 1 takes the ROUNDED / masked x (s3x_d), so the
                //: BF16 round + mask is the only logic before a register and every later hop is register -> wire ->
                //: register (<= ~350 um each across the 1,296 um cluster).  Only the valid bit is reset.
                localparam integer XW = 1 + 1 + 4 + G * HIER * 32 + G * 32;
                wire [XW-1:0] tx_d = {s2_v, s2_first, s2_tag[TW-6 -: 4], w_in, s3x_d[G*32-1:0]};
                wire [XW-1:0] tx_q;
                //: REGROOT 8 (QW-A0-RC4 10-20, rc7 gates: ck -> ck_tx rung-0 setup FAIL -58..-203 ps, every endpoint
                //: behind the shared BF16 round / mask of s3x_d): rung 0 captures the RAW s2 operands (register ->
                //: wire -> register, the only ck -> ck_tx crossing) and each leaf's own round + mask sits between rung 0
                //: and rung 1 (both ck_tx[g]): same values on the same edges, 0 cycles.  The round is the exact identity
                //: hi(x + 0x7FFF + x[16]) = x[31:16] + (x[15] & (x[16] | |x[14:0])); the mask / round selects arrive
                //: as two copies per group (one per 16-bit half).
                localparam integer XW0 = (REGROOT >= 8 && XTX >= 2) ? 1 + 1 + 4 + G * HIER * 32 + G * 32 + 4 * G : XW;
                wire [XW0-1:0] tx_d0;
                if (REGROOT >= 8 && XTX >= 2) begin : g_raw
                    wire [4*G-1:0] sel;
                    for (gl = 0; gl < G; gl = gl + 1) begin : g_s
                        assign sel[4*gl +: 4] = {round_local[2*gl+1], round_local[2*gl], s2_gm[gl], s2_gm[gl]};
                    end
                    assign tx_d0 = {s2_v, s2_first, s2_tag[TW-6 -: 4], w_in, sel, s2_x[G*32-1:0]};
                end else begin : g_cooked
                    assign tx_d0 = tx_d;
                end
                if (L9 != 0) begin : g_tx9
                    //: REGROOT 9: rung 0 = LANDED crossing.  Rings on the source roots (the shared hub ring g_l2c; the
                    //: leaf's west / east weight lanes on ck_dw / ck_de beside s2_w), reads on ck_tx[g] beside the leaf.
                    //: r0q after edge n = the raw rung-0 word of edge n - L9K (plain rung 0: edge n).  Rung 1.. unchanged.
                    localparam integer HWB = G * HIER * 16;                 // one weight half (west lanes = groups < G/2)
                    wire [XW*(XTX+1)-1:0] tc;
                    wire [XW0-1:0] r0q;
                    wire [L9C-1:0] co;
                    wire [HWB-1:0] ow, oe;
                    wire [4*HWB-1:0] bw, be;
                    wire [4*((HWB+23)/24)-1:0] vw, ve;
                    ot_qw_lr #(.W(L9C), .K(L9K)) u_qlr2c (.ck(ck_tx[g]), .rsi(rst_n), .bank(l2c_bank), .vld(l2c_vld), .o(co));
                    ot_qw_lw #(.W(HWB)) u_qlw2w (.ck(ck_reg[2]), .rsi(rst_n), .i(w_in[0 +: HWB]), .bank(bw), .vld(vw));
                    ot_qw_lw #(.W(HWB)) u_qlw2e (.ck(ck_reg[3]), .rsi(rst_n), .i(w_in[HWB +: HWB]), .bank(be), .vld(ve));
                    ot_qw_lr #(.W(HWB), .K(L9K)) u_qlr2w (.ck(ck_tx[g]), .rsi(rst_n), .bank(bw), .vld(vw), .o(ow));
                    ot_qw_lr #(.W(HWB), .K(L9K)) u_qlr2e (.ck(ck_tx[g]), .rsi(rst_n), .bank(be), .vld(ve), .o(oe));
                    assign r0q = {co[L9C-1 -: 6], oe, ow, co[L9C-7:0]};
                    genvar rr;
                    for (rr = 1; rr < XTX; rr = rr + 1) begin : g_r
                        wire [XW-1:0] qo;
                        ot_qwen_tx_ff #(.W(XW)) u_tx (.clk(ck_tx[g]), .rst_n(rst_l), .d(tc[XW*rr +: XW]), .q(qo));
                        assign tc[XW*(rr+1) +: XW] = qo;
                    end
                    if (1) begin : g_lx
                        wire [G*32-1:0] xr = r0q[G*32-1:0];
                        wire [4*G-1:0]  sr = r0q[G*32 +: 4*G];
                        wire [G*32-1:0] xm;
                        for (gl = 0; gl < G; gl = gl + 1) begin : g_x
                            wire [31:0] x = xr[32*gl +: 32];
                            wire        cy = x[15] & (x[16] | (|x[14:0]));
                            wire [15:0] hi;
                            ot_qwen_w12_kadd #(.W(16)) u_r (.a(x[31:16]), .b({15'd0, cy}), .s(hi));
                            assign xm[32*gl +: 16]    = !sr[4*gl]   ? 16'd0 : sr[4*gl+2] ? 16'd0 : x[15:0];
                            assign xm[32*gl+16 +: 16] = !sr[4*gl+1] ? 16'd0 : sr[4*gl+3] ? hi : x[31:16];
                        end
                        assign tc[XW*1 +: XW] = {r0q[XW0-1 -: (XW - G*32)], xm};
                    end
                    assign tc[XW-1:0] = tx_d;
                    assign tx_q = tc[XW*XTX +: XW];
                end else if (XTX > 0) begin : g_tx
                    wire [XW*(XTX+1)-1:0] tc;
                    wire [XW0-1:0] r0q;
                    genvar rr;
                    for (rr = 0; rr < XTX; rr = rr + 1) begin : g_r
                        localparam integer RW = (rr == 0) ? XW0 : XW;   // rung 0: the raw operand word (REGROOT 8)
                        wire [RW-1:0] di = (rr == 0) ? tx_d0 : tc[XW*rr +: XW];
                        wire [RW-1:0] qo;
                        ot_qwen_tx_ff #(.W(RW)) u_tx (.clk((LOCAL_ROOTS != 0 && CHILD_CLOCKS != 0) ? ck_tx[g] : clk), .rst_n(rst_l), .d(di), .q(qo));
                        if (rr == 0) begin : g_q0
                            assign r0q = qo;
                        end else begin : g_qn
                            assign tc[XW*(rr+1) +: XW] = qo;
                        end
                    end
                    if (REGROOT >= 8 && XTX >= 2) begin : g_lx
                        //: the leaf's round + mask on its rung-0 copy (ck_tx[g])
                        wire [G*32-1:0] xr = r0q[G*32-1:0];
                        wire [4*G-1:0]  sr = r0q[G*32 +: 4*G];
                        wire [G*32-1:0] xm;
                        for (gl = 0; gl < G; gl = gl + 1) begin : g_x
                            wire [31:0] x = xr[32*gl +: 32];
                            wire        cy = x[15] & (x[16] | (|x[14:0]));
                            wire [15:0] hi;
                            ot_qwen_w12_kadd #(.W(16)) u_r (.a(x[31:16]), .b({15'd0, cy}), .s(hi));
                            assign xm[32*gl +: 16]    = !sr[4*gl]   ? 16'd0 : sr[4*gl+2] ? 16'd0 : x[15:0];
                            assign xm[32*gl+16 +: 16] = !sr[4*gl+1] ? 16'd0 : sr[4*gl+3] ? hi : x[31:16];
                        end
                        assign tc[XW*1 +: XW] = {r0q[XW0-1 -: (XW - G*32)], xm};
                    end else begin : g_lc
                        assign tc[XW*1 +: XW] = r0q;
                    end
                    assign tc[XW-1:0] = tx_d;
                    assign tx_q = tc[XW*XTX +: XW];
                end else begin : g_ntx
                    assign tx_q = tx_d;
                end
                // Native physical parent binds the reset/fault-pin-registered successor.
                // Arithmetic and data edge count are unchanged; the compiler releases
                // reset one child edge later and observes faults one edge later.
`ifdef OT_QWEN_LSL_FP1
                ot_qwen_tile_lsl_fp1
`else
                ot_qwen_tile_lsl
`endif
                u_lh (.clk(CHILD_CLOCKS ? ck_lsl[g] : clk), .rst_n(rst_l), .v_d(tx_q[XW-1]), .first_d(tx_q[XW-2]), .split_d(tx_q[XW-3 -: 4]),
                    .w_d(tx_q[G*32 +: G*HIER*32]), .x_d(tx_q[G*32-1:0]), .t_out(leaf_out), .lfault(lf_raw), .tfault(stf_raw));
                wire [G*HIER-1:0] lf_raw;
                wire              stf_raw;
                if (L9 != 0) begin : g_fl9
                    //: REGROOT 9: the fault pins return with the result word through the landed crossing in g_out9
                end else if (REGROOT >= 8) begin : g_fl
                    //: REGROOT 8 (rc7 gates: leaf fault pins -> fault_q setup FAIL -33..-300 ps through the OR): the
                    //: leaf's fault pins land in kept clk registers first (register -> wire -> register crossing), the
                    //: OR follows on clk.  Faults are observed one edge later (a status, not a scheduled data edge).
                    (* keep *) reg [G*HIER:0] q;
                    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 0; else q <= {stf_raw, lf_raw};
                    assign lf = q[G*HIER-1:0];
                    assign stf[g] = q[G*HIER];
                end else begin : g_fd
                    assign lf = lf_raw;
                    assign stf[g] = stf_raw;
                end
                wire [HIER*32-1:0] leaf_out;
                if (L9 != 0) begin : g_out9
                    //: REGROOT 9: the leaf's result word and fault pins return through ONE landed crossing: ring on
                    //: ck_tx[g] beside the leaf (the slots capture the child pins, replacing the outland register),
                    //: read on the hub root ck.  Results (and the status-only faults) arrive L9K edges later (XTD).
                    localparam integer RW9 = 1 + G * HIER + HIER * 32;
                    wire [4*RW9-1:0] rb;
                    wire [4*((RW9+23)/24)-1:0] rv;
                    wire [RW9-1:0] ro;
                    ot_qw_lw #(.W(RW9)) u_qlw3 (.ck(ck_tx[g]), .rsi(rst_n), .i({stf_raw, lf_raw, leaf_out}), .bank(rb), .vld(rv));
                    ot_qw_lr #(.W(RW9), .K(L9K)) u_qlr3 (.ck(clk), .rsi(rst_n), .bank(rb), .vld(rv), .o(ro));
                    assign lf = ro[HIER*32 +: G*HIER];
                    assign stf[g] = ro[RW9-1];
                    assign top[HIER*32*g +: HIER*32] = ro[HIER*32-1:0];
                end else if (REGROOT >= 5) begin : g_outland
                    (* keep *) reg [HIER*32-1:0] q;
                    always @(posedge ((LOCAL_ROOTS != 0 && CHILD_CLOCKS != 0) ? ck_tx[g] : clk)) q <= leaf_out;
                    assign top[HIER*32*g +: HIER*32]=q;
                end else begin : g_direct_out
                    assign top[HIER*32*g +: HIER*32]=leaf_out;
                end
            end else begin : g_sf
            ot_qwen_w12_lane_slice #(.G(G), .NPL(HIER), .IL(IL), .MUL_LAT(MUL_LAT), .ACC_LAT(ACC_LAT),
                .TREE_LAT(TREE_LAT), .LRST(LRST), .ANR(ANR), .TMUT((g == 0) ? TMUT : 0)) u_ls (
                .clk(clk), .rst_n(rst_n), .v_d(s2_v), .first_d(s2_first), .split_d(s2_tag[TW-6 -: 4]),
                .w_d(w_in), .x_d(s3x_d[G*32-1:0]), .t_out(top[HIER*32*g +: HIER*32]), .lfault(lf), .tfault(stf[g]));
            end
        end
        assign sum = {GL*W*32{1'b0}};
        assign lvl_h = {{((GI - 1) * W * 32){1'b0}}, top};
        assign tfault_h = |stf;
    end else begin : g_flat
        assign lvl_h = {GI*W*32{1'b0}};
        assign tfault_h = 1'b0;
    end endgenerate
    generate if (LANES && HIER == 0) begin : g_lanes
        for (g = 0; g < G; g = g + 1) begin : g_grp
            for (gl = 0; gl < W; gl = gl + 1) begin : g_lane
                localparam integer LI = g * W + gl;
                wire rst_l;                              // LRST 3: the lane's own kept reset copy
                if (LRST >= 3) begin : g_lr
                    ot_qwen_lrst_ff u_rl (.clk(clk), .rst_n(rst_g[g]), .q(rst_l));
                end else begin : g_lg
                    assign rst_l = rst_g[g];
                end
                wire [31:0] prod, fb_pre, acc_in;
                reg  [31:0] acc_q;
                wire f0, f1;
                //: every product is BF16 x BF16 (weights, x rounded; BF16 KV, q and
                //: probabilities rounded), so every lane has the small exact multiplier
                if (MUL_LAT == 5) begin : g_legacy_mul
                    ot_hdc_bmul u_mul (.clk(clk), .rst_n(rst_l), .v(s3_v),
                                     .a(s3_w[32*LI +: 32]), .b(s3_x[32*g +: 32]), .y(prod), .fault(f0));
                end else begin : g_candidate_mul
                    ot_qwen_w12_bmul #(.LAT(MUL_LAT)) u_mul (.clk(clk), .rst_n(rst_l), .v(s3_v),
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
                    ot_hdc_fadd u_add (clk, rst_l, vline[MUL_LAT], acc_in, prod,
                                       sum[32*LI +: 32], f1);
                end else begin : g_ladd
                    ot_qwen_w12_ladd #(.LAT(ACC_LAT), .ANR(ANR)) u_add (clk, rst_l, vline[MUL_LAT], acc_in, prod,
                                                       sum[32*LI +: 32], f1);
                end
                ot_hdc_delay #(.W(32), .D(FB - 1)) u_fb (.clk(clk), .rst_n(rst_l), .d(sum[32*LI +: 32]), .q(fb_pre));
                assign lfault[LI] = f0 | f1;
            end
        end
    end else if (HIER == 0) begin : g_no_lanes
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
    // PART2 has no local levels below LV0; their real faults arrive through
    // t_fault_in. Define every absent local bit before the full-vector OR.
    assign tfault[LV0:0] = {(LV0 + 1){1'b0}};
    wire [LG*4+3:0] split_at;                       // split at each level's input
    assign split_at[4*LV0+3 -: 4] = t_split;
    generate
        for (lv = LV0 + 1; lv <= ((HIER > 0) ? LV0 : LG); lv = lv + 1) begin : g_lvl
            localparam integer ALWAYS = PRUNE && (SMIN >= lv);
            localparam integer HOLD_TO = PRUNE ? NPG : G;      // held positions [G >> lv, HOLD_TO)
            wire [3:0] sp_sel;                      // split when the level's sums emerge
            ot_hdc_delay #(.W(4), .D(TA)) u_sd (.clk(clk), .rst_n(rst_t[lv]), .d(split_at[4*lv-1 -: 4]), .q(sp_sel));
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
                ot_hdc_delay #(.W(HOLD_TO*W*32), .D(TA)) u_hold (.clk(clk), .rst_n(rst_t[lv]),
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
                wire rst_a;                              // LRST 3: the adder's own kept reset copy
                if (LRST >= 3) begin : g_ra
                    ot_qwen_lrst_ff u_ra (.clk(clk), .rst_n((TMUT == 2 && lv == LV0 + 1 && p == 0) ? 1'b0 : rst_t[lv]), .q(rst_a));
                end else begin : g_rl
                    assign rst_a = rst_t[lv];
                end
                ot_qwen_w12_tadd #(.LAT(TREE_LAT), .ANR(ANR)) u_add (clk, rst_a, vline[SD + TL*(lv-1) + XDD] && (split_at[4*lv-1 -: 4] >= lv),
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
        if (HIER > 0) begin : g_hlvl
            assign lvl[LG] = lvl_h;
            assign tfault[LG:LV0+1] = {{(LG - LV0 - 1){1'b0}}, tfault_h};
        end
    endgenerate
    // PART 1: the tile's top level and its valid, towards the tree above
    assign t_out = lvl[LG][W*32-1:0];
    assign t_vout = vline[SD + OD + XTD];           // XTX: the leaves' results (t_out) are XTD cycles later
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
            n_last_issued <= n_last_issued + ((acc[4] && klc) ? 16'd1 : 16'd0);
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
    wire idle_c = !acc[4] && !pend && !e_v && !(|m_vl) && !s1_v && !s1b_v && !s2_v && !s3_v && !(|vline) && !(|post_pending) && !(|tv) && !ov1
                  && !ov2 && !ord_busy && !mx_we;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) idle <= 1'b1;
        else idle <= idle_c && !(go && ready);
    end
endmodule


// ot_qwen_w12_ladd #(LAT): ot_hdc_fp32_add_lat (bit-identical to ot_hdc_qadd / ot_hdc_fadd) with the qadd port
// shape: fault = a valid result's err.
module ot_qwen_w12_ladd #(parameter integer LAT = 7, parameter integer ANR = 0) (
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
    // ANR = 1 (hardcore-1010 D): ot_hdc_fp32_add_lat_nr (valid-only cut resets + HSPLIT), bit-identical
    generate if (ANR != 0) begin : g_nr
        ot_hdc_fp32_add_lat_nr #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                               .valid_out(vo));
    end else begin : g_r
        ot_hdc_fp32_add_lat #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                            .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

// The split-tree pair adder: ot_hdc_qadd at LAT 3 (the legacy netlist), else ot_qwen_w12_ladd #(LAT).
module ot_qwen_w12_tadd #(parameter integer LAT = 3, parameter integer ANR = 0) (
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
        ot_qwen_w12_ladd #(.LAT(LAT), .ANR(ANR)) u (clk, rst_n, v, a, b, y, fault);
    end endgenerate
endmodule

// ot_qwen_w12_kadd #(W): a + b (mod 2^W) through ot_qwen_w12_ksa, the keep-prefix Kogge-Stone adder
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

// struct-close 2026-10-09: one kept local reset copy (ot_qwen_w12_matvec_part LRST = 2).  keep_hierarchy stops opt_merge
// from folding the identical copies (plain (* keep *) regs are merged by the ORFS yosys).
(* keep_hierarchy *)
module ot_qwen_lrst_ff (input wire clk, input wire rst_n, output reg q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= 1'b1;
endmodule


// el1011-q-tile 2026-10-11 (textbook class 1 / 2 / 4): one hardened lane-slice leaf of ot_qwen_w12_matvec_part HIER.
// NPL lane positions of each of the G groups (G * NPL lanes: BF16 product + FP32 circulating accumulator) and their
// whole split tree (every level adds; the tree only combines equal positions across groups, so a position slice is
// closed under it).  Boundary: the input pins land on flops that ARE the engine's S3 registers (v, first, split, w,
// x); the output is the last tree level's register; the lane / tree faults are flop-driven ORs.  Own valid line,
// first line, split delay and reset relay, so the leaf is one small local clock tree with no long control nets.
module ot_qwen_w12_lane_slice #(
    parameter integer G = 4,
    parameter integer NPL = 2,
    parameter integer IL = 8,
    parameter integer MUL_LAT = 5,
    parameter integer ACC_LAT = 5,
    parameter integer TREE_LAT = 3,
    parameter integer LRST = 0,
    parameter integer ANR = 0,
    parameter integer TMUT = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 v_d,          // S2 valid (the pin flop is S3)
    input  wire                 first_d,
    input  wire [3:0]           split_d,
    input  wire [G*NPL*32-1:0]  w_d,          // lane (g, j) at g * NPL + j
    input  wire [G*32-1:0]      x_d,          // S3's x word per group
    output wire [NPL*32-1:0]    t_out,        // the last level: position j at j
    output wire [G*NPL-1:0]     lfault,
    output wire                 tfault
);
    localparam integer LG = $clog2(G);
    localparam integer FB = IL - ACC_LAT;
    localparam integer SD = MUL_LAT + ACC_LAT;
    localparam integer TA = TREE_LAT;
    localparam integer TL = TA + 1;
    localparam integer OD = TL * LG;
    //: pin flops = S3
    (* keep *) reg s3_v, s3_first;
    (* keep *) reg [3:0] s3_split;
    (* keep *) reg [G*NPL*32-1:0] s3_w;
    (* keep *) reg [G*32-1:0] s3_x;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) s3_v <= 1'b0; else s3_v <= v_d;
    always @(posedge clk) begin s3_first <= first_d; s3_split <= split_d; s3_w <= w_d; s3_x <= x_d; end
    wire [SD+OD:0] vline;
    ot_hdc_vline #(.D(SD + OD)) u_v (.clk(clk), .rst_n(rst_n), .v(s3_v), .vd(vline));
    wire [MUL_LAT:0] fl_first;
    ot_hdc_vline #(.D(MUL_LAT)) u_first (.clk(clk), .rst_n(rst_n), .v(s3_first && s3_v), .vd(fl_first));
    wire [3:0] t_split;
    ot_hdc_delay #(.W(4), .D(SD)) u_ts (.clk(clk), .rst_n(rst_n), .d(s3_split), .q(t_split));
    //: reset relay (LRST semantics of the engine: async assert, release one edge after rst_n)
    wire [G-1:0] rst_g;
    wire [LG:0]  rst_t;
    genvar g, gl, lv, p;
    generate if (LRST >= 2) begin : g_lrst2
        for (g = 0; g < G; g = g + 1) begin : g_rg
            ot_qwen_lrst_ff u_rg (.clk(clk), .rst_n(rst_n), .q(rst_g[g]));
        end
        for (g = 0; g <= LG; g = g + 1) begin : g_rt
            ot_qwen_lrst_ff u_rt (.clk(clk), .rst_n(rst_n), .q(rst_t[g]));
        end
    end else if (LRST != 0) begin : g_lrst
        (* keep *) reg [G-1:0] rg;
        (* keep *) reg [LG:0]  rt;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin rg <= {G{1'b0}}; rt <= {(LG+1){1'b0}}; end
            else begin rg <= {G{1'b1}}; rt <= {(LG+1){1'b1}}; end
        end
        assign rst_g = rg; assign rst_t = rt;
    end else begin : g_nolrst
        assign rst_g = {G{rst_n}}; assign rst_t = {(LG+1){rst_n}};
    end endgenerate
    //: lanes
    wire [G*NPL*32-1:0] sum;
    wire [G*NPL-1:0] lf;
    generate
        for (g = 0; g < G; g = g + 1) begin : g_grp
            for (gl = 0; gl < NPL; gl = gl + 1) begin : g_lane
                localparam integer LI = g * NPL + gl;
                wire rst_l;
                if (LRST >= 3) begin : g_lr
                    ot_qwen_lrst_ff u_rl (.clk(clk), .rst_n(rst_g[g]), .q(rst_l));
                end else begin : g_lg
                    assign rst_l = rst_g[g];
                end
                wire [31:0] prod, fb_pre, acc_in;
                reg  [31:0] acc_q;
                wire f0, f1;
                if (MUL_LAT == 5) begin : g_legacy_mul
                    ot_hdc_bmul u_mul (.clk(clk), .rst_n(rst_l), .v(s3_v),
                                     .a(s3_w[32*LI +: 32]), .b(s3_x[32*g +: 32]), .y(prod), .fault(f0));
                end else begin : g_candidate_mul
                    ot_qwen_w12_bmul #(.LAT(MUL_LAT)) u_mul (.clk(clk), .rst_n(rst_l), .v(s3_v),
                                     .a(s3_w[32*LI +: 32]), .b(s3_x[32*g +: 32]), .y(prod), .fault(f0));
                end
                always @(posedge clk) acc_q <= fl_first[MUL_LAT-1] ? 32'd0 : fb_pre;
                assign acc_in = acc_q;
                if (ACC_LAT == 5) begin : g_fadd
                    ot_hdc_fadd u_add (clk, rst_l, vline[MUL_LAT], acc_in, prod, sum[32*LI +: 32], f1);
                end else begin : g_ladd
                    ot_qwen_w12_ladd #(.LAT(ACC_LAT), .ANR(ANR)) u_add (clk, rst_l, vline[MUL_LAT], acc_in, prod,
                                                       sum[32*LI +: 32], f1);
                end
                ot_hdc_delay #(.W(32), .D(FB - 1)) u_fb (.clk(clk), .rst_n(rst_l), .d(sum[32*LI +: 32]), .q(fb_pre));
                assign lf[LI] = f0 | f1;
            end
        end
    endgenerate
    assign lfault = lf;
    //: the slice's split tree (every level adds)
    wire [G*NPL*32-1:0] lvl [0:LG];
    wire [LG:0] tf;
    assign lvl[0] = sum;
    assign tf[0] = 1'b0;
    wire [LG*4+3:0] split_at;
    assign split_at[3:0] = t_split;
    generate
        for (lv = 1; lv <= LG; lv = lv + 1) begin : g_lvl
            wire [3:0] sp_sel;
            ot_hdc_delay #(.W(4), .D(TA)) u_sd (.clk(clk), .rst_n(rst_t[lv]), .d(split_at[4*lv-1 -: 4]), .q(sp_sel));
            reg  [3:0] sp_out;
            always @(posedge clk) sp_out <= sp_sel;
            assign split_at[4*lv+3 -: 4] = sp_out;
            localparam integer PAIRS = (G >> lv) * NPL;
            wire [PAIRS-1:0] pf;
            reg  [PAIRS*32-1:0] lq;
            for (p = 0; p < PAIRS; p = p + 1) begin : g_add
                localparam integer PW = p / NPL, PL = p % NPL;
                wire [31:0] s_out;
                wire rst_a;
                if (LRST >= 3) begin : g_ra
                    ot_qwen_lrst_ff u_ra (.clk(clk), .rst_n((TMUT == 2 && lv == 1 && p == 0) ? 1'b0 : rst_t[lv]), .q(rst_a));
                end else begin : g_rl
                    assign rst_a = rst_t[lv];
                end
                ot_qwen_w12_tadd #(.LAT(TREE_LAT), .ANR(ANR)) u_add (clk, rst_a, vline[SD + TL*(lv-1)] && (split_at[4*lv-1 -: 4] >= lv),
                                   lvl[lv-1][32*((2*PW)*NPL + PL) +: 32], lvl[lv-1][32*((2*PW+1)*NPL + PL) +: 32],
                                   s_out, pf[p]);
                always @(posedge clk) lq[32*p +: 32] <= s_out;
            end
            if (PAIRS < G * NPL) begin : g_lp
                assign lvl[lv] = {{((G * NPL - PAIRS) * 32){1'b0}}, lq};
            end else begin : g_lf
                assign lvl[lv] = lq;
            end
            assign tf[lv] = |pf;
        end
    endgenerate
    assign t_out = lvl[LG][NPL*32-1:0];
    assign tfault = |tf;
endmodule

//: el1011-q-tile r3: one registered transmit rung (kept hierarchy so identical per-leaf copies survive opt_merge); the
//: MSB is the valid bit (async reset), the rest is datapath (no reset)
(* keep_hierarchy *)
module ot_qwen_tx_ff #(parameter integer W = 8) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(posedge clk or negedge rst_n) if (!rst_n) q[W-1] <= 1'b0; else q[W-1] <= d[W-1];
    always @(posedge clk) q[W-2:0] <= d[W-2:0];
endmodule
