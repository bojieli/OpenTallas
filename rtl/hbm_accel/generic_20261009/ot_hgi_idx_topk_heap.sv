`timescale 1ns/1ps
// hgi-1010/g2 2026-10-10: IDX.TOPK as BANKED-SRAM PIPELINED HEAPS (successor of the flop insertion / systolic arrays).
// The drop-in core (same module name, parameters and ports as ot_hgi_idx_topk.sv) is ot_hgi_idx_topk_heap_dropin.sv
// (a route / bench uses ONE of those two files); the wide engine
// ot_hgi_idx_topk_hw takes IW scores a beat (the rate fix: the IDX reader can hand over a VM sector a cycle).
//
// Why: the flop designs hold MAX_K x 85 b in flops behind one-cycle 2,048-way selects / enables (feasibility 67b2d0326
// item (e): ~1.23 M cells, post-CTS TT -1.4 to -1.7 ns).  Here every K-sized structure is SRAM and every select is a
// registered 2- or W-way compare:
//   * W min-heaps (heap h takes scores i with (i / IW) mod (W / IW) = h / IW, lane i mod IW), each holding the top k of
//     its sub-stream: node 1 is the k-th largest so far.  Level j of a heap is its own store (levels <= 6 and the stray
//     last level in flops, levels 7..10 in 1R1W macros, 4 nodes a word).  A score enters a heap only if its key beats
//     the root ("replace-min" + top-down sift, one level every 2 cycles, one op every 4 cycles a heap).  Stage j reads the four
//     grandchildren (level j + 2, one word) for stage j + 1, so the compare at each level is register -> 2 x 53 b compare
//     -> register; the one hazard (the op 2 stages ahead writing that word in the same cycle) is a registered bypass.
//   * a score whose key is below the max of the W roots (registered, may lag: only admits more) is dropped at the
//     front end (no heap op): steady state the heaps see ~k ln(n / Wk) of n scores.
//   * after the row: each heap extracts its k nodes in ascending order (replace-min with +INF, same pipeline) into a
//     reverse buffer (SRAM, address k-1-i), and a W-way merge of the W descending runs emits the row's k results in
//     rank order, one a cycle.  The levels are re-cleared (one word a cycle a level, all levels at once) during the merge.
// Keys: {1, monotone(canonical score), ~index} (53 b, unique), exactly the sorted-insertion recurrence's key, so the
// result (ids, values, order, ties to the lowest index, -0 canonical for ordering, raw value out) is bit-identical.
// NaN anywhere in a row fails the command closed (error 3) before any output of that row.
// Cycles a row (W heaps, k, n): fill max(n / IW, 2 x survivors a heap) + 2k extract + k merge + ~30; the level clear
// ((k >> 3) + 1 cycles: only the words a k-node heap can use) overlaps the merge.
// Mutants (bench): MUT_BYP no bypass (stale grandchildren), MUT_CLR no inter-row clear, MUT_REV unreversed runs.
// r3 (hgi-1010/g2): a < b over W bits as a log-depth (lt, eq) tree whose every level is a (* keep *) net -- written as
// `a < b`, ABC mapped the 53-bit key compares as MAJ ripples (~1.4 ns in the hgi-idx-topk-wide preroute).
module ot_topk_lt #(parameter integer W = 53) (input wire [W-1:0] a, input wire [W-1:0] b, output wire lt);
 localparam integer L = $clog2(W), N = 1 << L;
 (* keep *) wire [N-1:0] tl [0:L];
 (* keep *) wire [N-1:0] te [0:L];
 genvar l, i;
 for (i = 0; i < N; i = i + 1) begin : g0
  if (i < W) begin : g_b assign tl[0][i] = ~a[i] & b[i]; assign te[0][i] = ~(a[i] ^ b[i]); end
  else begin : g_p assign tl[0][i] = 1'b0; assign te[0][i] = 1'b1; end
 end
 for (l = 0; l < L; l = l + 1) begin : g_l
  for (i = 0; i < (N >> (l + 1)); i = i + 1) begin : g_n     // node i of level l+1 = (hi 2i+1, lo 2i)
   assign tl[l + 1][i] = tl[l][2 * i + 1] | (te[l][2 * i + 1] & tl[l][2 * i]);
   assign te[l + 1][i] = te[l][2 * i + 1] & te[l][2 * i];
  end
  for (i = (N >> (l + 1)); i < N; i = i + 1) begin : g_z assign tl[l + 1][i] = 1'b0; assign te[l + 1][i] = 1'b1; end
 end
 assign lt = tl[L][0];
endmodule

module ot_hgi_topk_lvl #(parameter integer DEPTH=1, parameter integer AW=1) (
 input wire clk,
 input wire r_ce, input wire [AW-1:0] r_a, output wire [215:0] rd,
 input wire w_ce, input wire [AW-1:0] w_a, input wire [1:0] w_s, input wire [53:0] w_d, input wire w_all
);
 wire [255:0] wmask = w_all ? {40'd0, {216{1'b1}}} : ({202'd0, {54{1'b1}}} << (54 * w_s));
 wire [255:0] wdat = w_all ? 256'd0 : {40'd0, w_d, w_d, w_d, w_d};
 generate if (DEPTH <= 16) begin : g_ff
  reg [215:0] m [0:DEPTH-1]; reg [215:0] q;
  integer i;
  always @(posedge clk) begin
   if (r_ce) q <= (r_a < DEPTH) ? m[r_a] : 216'd0;
   if (w_ce && w_a < DEPTH) m[w_a] <= (m[w_a] & ~wmask[215:0]) | (wdat[215:0] & wmask[215:0]);
  end
  assign rd = q;
 end else if (DEPTH <= 128) begin : g_m128
  wire [255:0] q;
  ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(r_ce), .r_addr_in(7'(r_a)), .rd_out(q), .w_ce_in(w_ce),
   .w_addr_in(7'(w_a)), .wd_in(wdat), .w_mask_in(wmask), .rr_en(2'b0), .rr_addr(14'd0), .cr_en(2'b0), .cr_sel(16'd0));
  assign rd = q[215:0];
 end else if (DEPTH <= 256) begin : g_m256
  wire [255:0] q;
  ot_sram_1r1w_256x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(r_ce), .r_addr_in(8'(r_a)), .rd_out(q), .w_ce_in(w_ce),
   .w_addr_in(8'(w_a)), .wd_in(wdat), .w_mask_in(wmask), .rr_en(2'b0), .rr_addr(14'd0), .cr_en(2'b0), .cr_sel(16'd0));
  assign rd = q[215:0];
 end else begin : g_m1024
  wire [255:0] q;
  ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(r_ce), .r_addr_in(10'(r_a)), .rd_out(q), .w_ce_in(w_ce),
   .w_addr_in(10'(w_a)), .wd_in(wdat), .w_mask_in(wmask), .rr_en(2'b0), .rr_addr(18'd0), .cr_en(2'b0), .cr_sel(16'd0));
  assign rd = q[215:0];
 end endgenerate
endmodule

// One pipelined min-heap of capacity k (runtime, <= MAX_K): op = INS (enters only if x > root) or EXT (outputs the root,
// sifts +INF).  One op every 2 cycles.  Entries {nz, key[52:0]}; key 0 = empty, key all-ones = +INF.
module ot_hgi_topk_heap #(parameter integer MAX_K=2048, parameter integer MUT_BYP=0, parameter integer MUT_CLR=0) (
 input wire clk, rst_n,
 input wire [$clog2(MAX_K+1)-1:0] k,
 input wire op_v, input wire op_ext, input wire [53:0] op_x, output wire op_rdy,
 output reg ext_v, output reg [53:0] ext_d,
 output wire [52:0] root_key,
 input wire clr_go, output wire idle
);
 localparam integer LV = $clog2(MAX_K + 1);           // levels 0..LV-1
 localparam integer PW = LV + 1;                       // node index width
 localparam integer KW = $clog2(MAX_K + 1);
 localparam [53:0] INF = {1'b0, {53{1'b1}}};
 function automatic integer qd(input integer j);       // words (4 nodes) of level j
  integer c; begin c = (1 << j); if (MAX_K + 1 - (1 << j) < c) c = MAX_K + 1 - (1 << j); qd = (c + 3) / 4; end
 endfunction
 function automatic integer awf(input integer d); begin awf = (d <= 1) ? 1 : $clog2(d); end endfunction
 function automatic integer qmaxf(input integer dummy);
  integer jj, mx; begin mx = 1; for (jj = 2; jj < LV; jj = jj + 1) if (qd(jj) > mx) mx = qd(jj); qmaxf = mx; end
 endfunction
 localparam integer QMAX = qmaxf(0);
 reg [53:0] h1, h2, h3;                               // levels 0 and 1
 // TWO cycles a level (hgi-1010/g2 r2: the one-cycle level -- macro clk->q, pair / bypass select, 2 x 53-b compare,
 // write data into the next macro -- missed by ~750 ps at TT on the first route): A_j selects the node's children from
 // the REGISTERED grandchild word (read at A_{j-1}, landed in rdr) plus the bypass, into flops; B_j compares and writes.
 // An op enters every 4 cycles (two levels apart): the only write to a level between a word's read and its use is then
 // the op one ahead, caught by the per-level last-write register (byp).
 reg a_v [0:LV]; reg [PW-1:0] a_p [0:LV]; reg [53:0] a_x [0:LV];
 reg b_v [0:LV]; reg [PW-1:0] b_p [0:LV]; reg [53:0] b_x [0:LV]; reg [53:0] b_c0 [0:LV], b_c1 [0:LV];
 wire [215:0] rdq [0:LV+1];                           // level j store read word (j >= 2), valid the cycle after the read
 reg  [215:0] rdr [0:LV+1];                           // ... registered
 reg byp_v [0:LV+1]; reg [PW-1:0] byp_p [0:LV+1]; reg [53:0] byp_d [0:LV+1];
 wire wr_v [0:LV]; wire [PW-1:0] wr_p [0:LV]; wire [53:0] wr_d [0:LV];
 wire mv [0:LV]; wire [PW-1:0] mi [0:LV];
 wire [53:0] sc0 [0:LV], sc1 [0:LV];                  // A-stage child selects
 reg [1:0] ent_c; reg clr_b; reg [$clog2(QMAX+1):0] clr_c, clr_l; reg clr_p;
 // clear extent: only words that can hold a node <= the largest k used since the last clear (a level of k's heap has
 // <= (k + 1) / 2 nodes = (k >> 3) + 1 words); reset clears everything
 reg [KW-1:0] dk;
 wire [KW:0] dkl = (dk >> 3) + 1;
 assign root_key = h1[52:0];
 wire ent = op_v && op_rdy;
 assign op_rdy = ent_c == 2'd0 && !clr_b && !clr_p;
 wire root_lt_x; ot_topk_lt #(.W(53)) u_ent (.a(h1[52:0]), .b(op_x[52:0]), .lt(root_lt_x));
 genvar j;
 generate for (j = 0; j < LV; j = j + 1) begin : g_st
  // A_j: children of a_p[j] (level j + 1)
  if (j == 0) begin : g_c0
   assign sc0[j] = h2; assign sc1[j] = h3;
  end else if (j + 1 < LV) begin : g_cn
   wire [107:0] pr = a_p[j][0] ? rdr[j + 1][215:108] : rdr[j + 1][107:0];
   assign sc0[j] = (MUT_BYP == 0 && byp_v[j + 1] && byp_p[j + 1] == {a_p[j][PW-2:0], 1'b0}) ? byp_d[j + 1] : pr[53:0];
   assign sc1[j] = (MUT_BYP == 0 && byp_v[j + 1] && byp_p[j + 1] == {a_p[j][PW-2:0], 1'b1}) ? byp_d[j + 1] : pr[107:54];
  end else begin : g_cl
   assign sc0[j] = 54'd0; assign sc1[j] = 54'd0;
  end
  // B_j: compare, write node b_p[j], move to the smaller child
  wire [PW:0] n0 = {b_p[j], 1'b0}, n1 = {b_p[j], 1'b1};
  wire e0 = (j + 1 < LV) && (n0 <= k), e1 = (j + 1 < LV) && (n1 <= k);
  wire c0_lt_x, c1_lt_x, c1_lt;
  ot_topk_lt #(.W(53)) u_l0 (.a(b_c0[j][52:0]), .b(b_x[j][52:0]), .lt(c0_lt_x));
  ot_topk_lt #(.W(53)) u_l1 (.a(b_c1[j][52:0]), .b(b_x[j][52:0]), .lt(c1_lt_x));
  ot_topk_lt #(.W(53)) u_lc (.a(b_c1[j][52:0]), .b(b_c0[j][52:0]), .lt(c1_lt));
  wire x_le0 = !c0_lt_x, x_le1 = !c1_lt_x;
  wire take1 = e1 && c1_lt;
  wire stop = !e0 || (take1 ? x_le1 : x_le0);
  assign wr_v[j] = b_v[j]; assign wr_p[j] = b_p[j];
  assign wr_d[j] = stop ? b_x[j] : (take1 ? b_c1[j] : b_c0[j]);
  assign mv[j] = b_v[j] && !stop; assign mi[j] = {b_p[j][PW-2:0], take1};
 end endgenerate
 // level stores j >= 2: written by B_j, read (grandchildren word) at A_{j-2}
 generate for (j = 2; j < LV; j = j + 1) begin : g_lv
  localparam integer D = qd(j), A = awf(qd(j));
  wire [PW-1:0] wp = wr_p[j];
  wire [PW-1:0] rp = a_p[j - 2];
  ot_hgi_topk_lvl #(.DEPTH(D), .AW(A)) u_l (.clk(clk),
   .r_ce(a_v[j - 2]), .r_a(A'(rp & ((1 << (j - 2)) - 1))), .rd(rdq[j]),
   .w_ce(wr_v[j] || clr_b), .w_a(clr_b ? A'(clr_c) : A'((wp & ((1 << j) - 1)) >> 2)), .w_s(wp[1:0]), .w_d(wr_d[j]),
   .w_all(clr_b));
  always @(posedge clk) rdr[j] <= rdq[j];
 end endgenerate
 integer i;
 reg any_v;
 always @* begin any_v = 1'b0; for (i = 0; i < LV; i = i + 1) any_v = any_v | a_v[i] | b_v[i]; end
 assign idle = !any_v && ent_c == 2'd0 && !clr_b && !clr_p;
 wire clr_start = clr_p && !any_v && ent_c == 2'd0 && !clr_b;
 always @(posedge clk or negedge rst_n) begin
  if (!rst_n) begin
   ent_c <= 2'd0; ext_v <= 1'b0; clr_b <= 1'b0; clr_p <= 1'b1; clr_c <= 0; clr_l <= 0; dk <= MAX_K;
   for (i = 0; i <= LV; i = i + 1) begin a_v[i] <= 1'b0; b_v[i] <= 1'b0; byp_v[i] <= 1'b0; end
   byp_v[LV + 1] <= 1'b0;
  end else begin
   ent_c <= ent ? 2'd3 : (ent_c != 2'd0 ? ent_c - 2'd1 : 2'd0);
   ext_v <= ent && op_ext;
   a_v[0] <= ent && (op_ext || root_lt_x);
   for (i = 1; i < LV; i = i + 1) a_v[i] <= mv[i - 1];
   for (i = 0; i < LV; i = i + 1) b_v[i] <= a_v[i];
   for (i = 2; i < LV; i = i + 1) if (wr_v[i]) byp_v[i] <= 1'b1; else if (clr_start) byp_v[i] <= 1'b0;
   if (clr_go && MUT_CLR == 0) clr_p <= 1'b1;
   if (ent && k > dk) dk <= k;
   if (clr_start) begin
    clr_p <= 1'b0; clr_b <= 1'b1; clr_c <= 0; clr_l <= (dkl < QMAX) ? dkl : QMAX; dk <= 0;
   end
   if (clr_b) begin clr_c <= clr_c + 1'b1; if (clr_c + 1 >= clr_l) clr_b <= 1'b0; end
  end
 end
 always @(posedge clk) begin
  if (ent) begin a_p[0] <= {{(PW-1){1'b0}}, 1'b1}; a_x[0] <= op_ext ? INF : op_x; if (op_ext) ext_d <= h1; end
  for (i = 1; i < LV; i = i + 1) begin a_p[i] <= mi[i - 1]; a_x[i] <= b_x[i - 1]; end
  for (i = 0; i < LV; i = i + 1) begin b_p[i] <= a_p[i]; b_x[i] <= a_x[i]; b_c0[i] <= sc0[i]; b_c1[i] <= sc1[i]; end
  for (i = 2; i < LV; i = i + 1) if (wr_v[i]) begin byp_p[i] <= wr_p[i]; byp_d[i] <= wr_d[i]; end
  if (wr_v[0]) h1 <= wr_d[0];
  if (LV > 1 && wr_v[1]) begin if (wr_p[1][0]) h3 <= wr_d[1]; else h2 <= wr_d[1]; end
  if (clr_start) begin h1 <= 54'd0; h2 <= 54'd0; h3 <= 54'd0; end
 end
endmodule

// Wide engine: IW scores a beat (in_nw valid, the row's last beat may be partial), W heaps (W a multiple of IW).
module ot_hgi_idx_topk_hw #(
 parameter bit ENABLE=0, parameter integer MAX_K=2048, parameter bit MUTANT_TIE=0,
 parameter integer IW=1, parameter integer W=2,
 // bench mutants (must FAIL): MUT_BYP no grandchild bypass, MUT_CLR no inter-row level clear, MUT_REV reverse buffer
 // written in extraction (ascending) order
 parameter integer MUT_BYP=0, parameter integer MUT_CLR=0, parameter integer MUT_REV=0
)(
 input wire clk,rst_n,
 input wire cmd_valid, output wire cmd_ready,
 input wire [3:0] cmd_unit, input wire [5:0] cmd_op,
 input wire [24:0] cmd_param, input wire [31:0] cmd_n,cmd_m,
 input wire cmd_values,
 input wire in_valid, output wire in_ready, input wire [IW*32-1:0] in_score, input wire [$clog2(IW+1)-1:0] in_nw,
 output wire out_valid, input wire out_ready,
 output wire [31:0] out_id,out_score,out_row,
 output wire out_last, output wire out_values_valid, output reg done, output reg [3:0] error
);
 localparam integer KW = $clog2(MAX_K + 1);
 localparam integer G = W / IW;                         // heap groups (beats rotate over them)
 localparam integer FD = 8;                             // survivor FIFO a heap
 localparam integer RD = (MAX_K + 3) / 4;               // reverse buffer words
 localparam integer RA = (RD <= 1) ? 1 : $clog2(RD);
 localparam integer HW = (W <= 1) ? 1 : $clog2(W);
 localparam [2:0] IDLE=0, START=1, FILL=2, FLUSH=3, EXT=4, MERGE=5, ABORT=6, FIN=7;
 // reset standard (ot_rst_relay): the port drives only the relay; heap h resets from region h, the control from region W.
 // Release is 3 edges after the port; cmd_ready waits for it (up).
 wire [W:0] rr;
 ot_rst_relay #(.REGIONS(W + 1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
 wire rn = rr[W];
 reg up;
 always @(posedge clk or negedge rn) if (!rn) up <= 1'b0; else up <= 1'b1;
 reg [2:0] st;
 reg [31:0] n, m, row, cursor;
 reg [KW-1:0] k;
 reg values_enabled;
 // ---------------------------------------------------------------- heaps
 wire hp_v [0:W-1]; wire hp_ext; wire [53:0] hp_x [0:W-1];
 assign hp_ext = st == EXT;
 wire hp_rdy [0:W-1], hx_v [0:W-1], h_idle [0:W-1]; wire [53:0] hx_d [0:W-1]; wire [52:0] h_root [0:W-1];
 reg clr_go;
 genvar h, l;
 generate for (h = 0; h < W; h = h + 1) begin : g_h
  ot_hgi_topk_heap #(.MAX_K(MAX_K), .MUT_BYP(MUT_BYP), .MUT_CLR(MUT_CLR)) u_hp (.clk(clk), .rst_n(rr[h]), .k(k), .op_v(hp_v[h]),
   .op_ext(hp_ext), .op_x(hp_x[h]), .op_rdy(hp_rdy[h]), .ext_v(hx_v[h]), .ext_d(hx_d[h]), .root_key(h_root[h]),
   .clr_go(clr_go), .idle(h_idle[h]));
 end endgenerate
 reg [52:0] gth; integer i, q;
 // registered max root (the front-end drop threshold; any lag only admits more): a registered tournament of keep
 // comparators, one level an edge
 localparam integer WP = (W <= 1) ? 1 : (1 << $clog2(W)), WL = (W <= 1) ? 0 : $clog2(W);
 reg [52:0] gt [0:WL][0:WP-1];
 genvar gl, gi;
 for (gi = 0; gi < WP; gi = gi + 1) begin : g_gt0 always @(posedge clk) gt[0][gi] <= (gi < W) ? h_root[gi] : 53'd0; end
 for (gl = 0; gl < WL; gl = gl + 1) begin : g_gtl
  for (gi = 0; gi < (WP >> (gl + 1)); gi = gi + 1) begin : g_gtn
   wire lo_lt; ot_topk_lt #(.W(53)) u_c (.a(gt[gl][2 * gi]), .b(gt[gl][2 * gi + 1]), .lt(lo_lt));
   always @(posedge clk) gt[gl + 1][gi] <= lo_lt ? gt[gl][2 * gi + 1] : gt[gl][2 * gi];
  end
 end
 always @* gth = gt[WL][0];
 reg all_idle;
 always @* begin all_idle = 1'b1; for (i = 0; i < W; i = i + 1) all_idle = all_idle & h_idle[i]; end
 // ---------------------------------------------------------------- front end: F1 (beat) -> keys -> survivor FIFOs
 reg f1_v; reg [IW*32-1:0] f1_s; reg [$clog2(IW+1)-1:0] f1_nw; reg [19:0] f1_c; reg [$clog2(G+1)-1:0] f1_g, grp;
 reg [53:0] ff [0:W*FD-1]; reg [3:0] fc [0:W-1]; reg [2:0] fw [0:W-1], fr [0:W-1];
 reg [3:0] fmax;
 always @* begin fmax = 4'd0; for (i = 0; i < W; i = i + 1) if (fc[i] > fmax) fmax = fc[i]; end
 wire f1_nan; wire [53:0] f1_e [0:IW-1]; wire [IW-1:0] f1_nl;
 generate for (l = 0; l < IW; l = l + 1) begin : g_key
  wire [31:0] s = f1_s[32 * l +: 32];
  wire [31:0] canon = (s[30:0] == 31'd0) ? 32'd0 : s;
  wire [31:0] mono = canon[31] ? ~canon : (canon | 32'h80000000);
  wire [19:0] idx = f1_c + l;
  assign f1_e[l] = {s == 32'h80000000, 1'b1, mono, MUTANT_TIE ? idx : ~idx};
  assign f1_nl[l] = (l < f1_nw) && (s[30:23] == 8'hff) && (s[22:0] != 23'd0);
 end endgenerate
 assign f1_nan = f1_v && (|f1_nl);
 wire [IW-1:0] f1_gt;                                   // lane key above the drop threshold
 generate for (l = 0; l < IW; l = l + 1) begin : g_flt
  ot_topk_lt #(.W(53)) u_c (.a(gth), .b(f1_e[l][52:0]), .lt(f1_gt[l]));
 end endgenerate
 // in_ready leaves a flop compare: room is judged one edge late (<= FD - 4: up to 3 beats in flight past fc)
 reg in_ok;
 always @(posedge clk or negedge rn) if (!rn) in_ok <= 1'b0; else in_ok <= fmax <= FD - 4;
 assign in_ready = ENABLE && st == FILL && in_ok;
 wire beat = in_valid && in_ready;
 // ---------------------------------------------------------------- reverse buffers and merge
 reg [KW-1:0] xi [0:W-1], xo [0:W-1];                   // extract ops issued / results written
 reg [RA:0] mw [0:W-1]; reg mi_q [0:W-1];               // merge: next word to read, read in flight
 reg [53:0] mf [0:W*8-1]; reg [3:0] mc [0:W-1]; reg [2:0] mr [0:W-1], mwp [0:W-1];
 reg [KW-1:0] mp [0:W-1];                               // entries popped a run
 wire [215:0] rb_q [0:W-1];
 generate for (h = 0; h < W; h = h + 1) begin : g_rb
  wire [KW-1:0] wa = (MUT_REV != 0) ? xo[h] : k - 1'b1 - xo[h];
  // heap ops: INS from the survivor FIFO head (FILL / FLUSH), EXT k times (EXT); issued the cycle the heap is ready
  assign hp_v[h] = ((st == FILL || st == FLUSH) && fc[h] != 4'd0) || (st == EXT && xi[h] != k);
  assign hp_x[h] = ff[h * FD + fr[h]];
  ot_hgi_topk_lvl #(.DEPTH(RD), .AW(RA)) u_rb (.clk(clk), .r_ce(st == MERGE && !mi_q[h] && ({mw[h], 2'b00} < k) &&
   (mc[h] + 4'd4 <= 4'd8)), .r_a(RA'(mw[h])), .rd(rb_q[h]), .w_ce(hx_v[h]), .w_a(RA'(wa >> 2)), .w_s(wa[1:0]),
   .w_d(hx_d[h]), .w_all(1'b0));
 end endgenerate
 // merge pick: the largest head, only when every unfinished run has a head
 // a tournament over the W run heads (keep comparators, log2 W levels); a run without a head never wins
 reg mg_ok; wire [HW-1:0] mg_h; wire mg_any; wire [53:0] mg_e;
 always @* begin mg_ok = 1'b1; for (i = 0; i < W; i = i + 1) if (mc[i] == 4'd0 && mp[i] != k) mg_ok = 1'b0; end
 wire tv [0:WL][0:WP-1]; wire [53:0] te_ [0:WL][0:WP-1]; wire [HW-1:0] th [0:WL][0:WP-1];
 for (gi = 0; gi < WP; gi = gi + 1) begin : g_t0
  if (gi < W) begin : g_r assign tv[0][gi] = mc[gi] != 4'd0; assign te_[0][gi] = mf[gi * 8 + mr[gi]]; assign th[0][gi] = gi; end
  else begin : g_z assign tv[0][gi] = 1'b0; assign te_[0][gi] = 54'd0; assign th[0][gi] = 0; end
 end
 for (gl = 0; gl < WL; gl = gl + 1) begin : g_tl
  for (gi = 0; gi < (WP >> (gl + 1)); gi = gi + 1) begin : g_tn
   wire lo_lt; ot_topk_lt #(.W(53)) u_c (.a(te_[gl][2 * gi][52:0]), .b(te_[gl][2 * gi + 1][52:0]), .lt(lo_lt));
   wire hi = tv[gl][2 * gi + 1] && (!tv[gl][2 * gi] || lo_lt);
   assign tv[gl + 1][gi] = tv[gl][2 * gi] || tv[gl][2 * gi + 1];
   assign te_[gl + 1][gi] = hi ? te_[gl][2 * gi + 1] : te_[gl][2 * gi];
   assign th[gl + 1][gi] = hi ? th[gl][2 * gi + 1] : th[gl][2 * gi];
  end
 end
 assign mg_any = tv[WL][0]; assign mg_e = te_[WL][0]; assign mg_h = th[WL][0];
 reg [KW-1:0] emitted;
 reg [53:0] of [0:3]; reg of_l [0:3]; reg [2:0] oc; reg [1:0] ow, orp;
 wire mg_go = st == MERGE && emitted != k && mg_ok && mg_any && oc <= 3'd2;
 wire [53:0] oe = of[orp];
 wire [31:0] o_mono = oe[51:20];
 wire [31:0] o_canon = o_mono[31] ? {1'b0, o_mono[30:0]} : ~o_mono;
 assign out_valid = ENABLE && oc != 3'd0;
 assign out_id = {12'd0, MUTANT_TIE ? oe[19:0] : ~oe[19:0]};
 assign out_score = oe[53] ? 32'h80000000 : o_canon;
 assign out_row = row;
 assign out_last = of_l[orp];
 assign out_values_valid = out_valid && values_enabled;
 wire o_pop = out_valid && out_ready;
 assign cmd_ready = st == IDLE && up;
 // ---------------------------------------------------------------- control
 always @(posedge clk or negedge rn) begin
  if (!rn) begin
   st <= IDLE; done <= 1'b0; error <= 4'd0; n <= 0; m <= 0; k <= 0; row <= 0; cursor <= 0; values_enabled <= 1'b0;
   f1_v <= 1'b0; grp <= 0; clr_go <= 1'b0; emitted <= 0; oc <= 0; ow <= 0; orp <= 0;
   for (i = 0; i < W; i = i + 1) begin
    fc[i] <= 0; fw[i] <= 0; fr[i] <= 0; xi[i] <= 0; xo[i] <= 0; mw[i] <= 0; mi_q[i] <= 1'b0;
    mc[i] <= 0; mr[i] <= 0; mwp[i] <= 0; mp[i] <= 0;
   end
  end else begin
   done <= 1'b0; clr_go <= 1'b0;
   // F1 capture
   f1_v <= beat;
   if (beat) begin
    f1_s <= in_score; f1_nw <= in_nw; f1_c <= cursor[19:0]; f1_g <= grp; grp <= (grp + 1 == G) ? 0 : grp + 1;
    cursor <= cursor + in_nw;
    if (cursor + in_nw >= n) st <= FLUSH;
   end
   // survivors -> FIFOs, FIFOs -> heaps (INS)
   for (i = 0; i < W; i = i + 1) begin : fifo
    reg push, pop;
    push = f1_v && !f1_nan && (st == FILL || st == FLUSH) && (i / IW == f1_g) && ((i % IW) < f1_nw) &&
           f1_gt[i % IW];
    pop = (st == FILL || st == FLUSH) && fc[i] != 0 && hp_rdy[i];
    if (push) begin ff[i * FD + fw[i]] <= f1_e[i % IW]; fw[i] <= fw[i] + 1'b1; end
    if (pop) fr[i] <= fr[i] + 1'b1;
    fc[i] <= fc[i] + push - pop;
   end
   case (st)
    IDLE: if (cmd_valid) begin
     error <= 4'd0;
     if (!ENABLE || cmd_unit != 9 || cmd_op != 2) begin error <= 4'd1; done <= 1'b1; end
     else if (cmd_param[24:12] != 0 || cmd_param[11:0] == 0 || cmd_param[11:0] > MAX_K ||
              cmd_param[11:0] > cmd_n || cmd_n == 0 || cmd_n > 1048576 || cmd_m == 0) begin error <= 4'd2; done <= 1'b1; end
     else begin
      values_enabled <= cmd_values; n <= cmd_n; m <= cmd_m; k <= cmd_param[KW-1:0]; row <= 0; st <= START;
     end
    end
    START: if (all_idle) begin cursor <= 0; grp <= 0; st <= FILL; end
    FILL, FLUSH: begin
     if (f1_nan) begin error <= 4'd3; done <= 1'b1; st <= ABORT; f1_v <= 1'b0;
      for (i = 0; i < W; i = i + 1) begin fc[i] <= 0; fr[i] <= 0; fw[i] <= 0; end
     end else if (st == FLUSH && !f1_v && !beat) begin : fl
      reg e; e = all_idle;
      for (i = 0; i < W; i = i + 1) e = e && fc[i] == 0;
      if (e) begin st <= EXT; for (i = 0; i < W; i = i + 1) begin xi[i] <= 0; xo[i] <= 0; end end
     end
    end
    EXT: begin : ex
     reg e; e = 1'b1;
     for (i = 0; i < W; i = i + 1) begin
      if (xi[i] != k && hp_rdy[i]) xi[i] <= xi[i] + 1'b1;
      if (hx_v[i]) xo[i] <= xo[i] + 1'b1;
      e = e && (xo[i] + hx_v[i] == k);
     end
     if (e) begin
      st <= MERGE; clr_go <= 1'b1; emitted <= 0;
      for (i = 0; i < W; i = i + 1) begin mw[i] <= 0; mi_q[i] <= 1'b0; mc[i] <= 0; mr[i] <= 0; mwp[i] <= 0; mp[i] <= 0; end
     end
    end
    MERGE: begin
     for (i = 0; i < W; i = i + 1) begin : run
      reg rd_go, pop; reg [3:0] np; reg [KW+1:0] base; reg [2:0] wp;
      rd_go = !mi_q[i] && ({mw[i], 2'b00} < k) && (mc[i] + 4'd4 <= 4'd8);
      mi_q[i] <= rd_go;
      if (rd_go) mw[i] <= mw[i] + 1'b1;
      np = 0;
      if (mi_q[i]) begin                                  // the word read last cycle lands: up to 4 entries < k
       base = {mw[i] - 1'b1, 2'b00};
       for (q = 0; q < 4; q = q + 1) if (base + q < k) begin wp = mwp[i] + np[2:0]; mf[i * 8 + wp] <= rb_q[i][54 * q +: 54]; np = np + 1; end
       mwp[i] <= mwp[i] + np[2:0];
      end
      pop = mg_go && mg_h == i;
      if (pop) begin mr[i] <= mr[i] + 1'b1; mp[i] <= mp[i] + 1'b1; end
      mc[i] <= mc[i] + np - pop;
     end
     if (emitted == k && oc == 0) begin
      if (row + 1 == m) begin st <= FIN; end
      else begin row <= row + 1; st <= START; end
     end
    end
    ABORT: if (all_idle) begin clr_go <= 1'b1; st <= IDLE; end
    FIN: begin done <= 1'b1; st <= IDLE; end
    default: st <= IDLE;
   endcase
   // output FIFO
   if (mg_go) begin of[ow] <= mg_e; of_l[ow] <= emitted + 1'b1 == k; ow <= ow + 1'b1; emitted <= emitted + 1'b1; end
   if (o_pop) orp <= orp + 1'b1;
   oc <= oc + mg_go - o_pop;
  end
 end
endmodule


// Registered boundary around the wide engine (the die wrapper ot_hgi_idx_topk_registered, IW scores a beat): command,
// score beat and result are each captured in a flop; a command retires only after its last accepted output.
module ot_hgi_idx_topk_wreg #(
 parameter bit ENABLE=0, parameter integer MAX_K=2048, parameter integer IW=4, parameter integer W=4,
 parameter integer MUT_BYP=0
)(
 input wire clk,rst_n,
 input wire cmd_valid, output wire cmd_ready,
 input wire [3:0] cmd_unit, input wire [5:0] cmd_op,
 input wire [24:0] cmd_param, input wire [31:0] cmd_n,cmd_m,
 input wire cmd_values,
 input wire in_valid, output wire in_ready, input wire [IW*32-1:0] in_score, input wire [$clog2(IW+1)-1:0] in_nw,
 output wire out_valid, input wire out_ready,
 output wire [31:0] out_id,out_score,out_row,
 output wire out_last, output wire out_values_valid, output reg done, output reg [3:0] error
);
 reg active,c_valid,s_valid,q_valid,pending_done,h_v;   // h_v: a command held at the pin (cmd_ready = !h_v, a flop)
 reg [3:0] c_unit; reg [5:0] c_op; reg [24:0] c_param; reg [31:0] c_n,c_m; reg c_values;
 reg [IW*32-1:0] s_score; reg [$clog2(IW+1)-1:0] s_nw;
 reg [31:0] q_id,q_score,q_row; reg q_last,q_values;
 wire core_cmd_ready,core_in_ready,core_out_valid,core_done; wire [3:0] core_error;
 wire [31:0] core_id,core_score,core_row; wire core_last,core_values;
 wire core_out_ready=!q_valid||out_ready;
 assign cmd_ready=!h_v;
 wire go=h_v&&!active&&!c_valid&&core_cmd_ready&&!pending_done&&!q_valid;
 assign in_ready=active&&(!s_valid||core_in_ready);
 assign out_valid=q_valid; assign out_id=q_id; assign out_score=q_score; assign out_row=q_row;
 assign out_last=q_last; assign out_values_valid=q_valid&&q_values;
 ot_hgi_idx_topk_hw #(.ENABLE(ENABLE),.MAX_K(MAX_K),.IW(IW),.W(W),.MUT_BYP(MUT_BYP)) core(
  .clk(clk),.rst_n(rst_n),.cmd_valid(c_valid),.cmd_ready(core_cmd_ready),
  .cmd_unit(c_unit),.cmd_op(c_op),.cmd_param(c_param),.cmd_n(c_n),.cmd_m(c_m),.cmd_values(c_values),
  .in_valid(s_valid&&active),.in_ready(core_in_ready),.in_score(s_score),.in_nw(s_nw),
  .out_valid(core_out_valid),.out_ready(core_out_ready),.out_id(core_id),.out_score(core_score),
  .out_row(core_row),.out_last(core_last),.out_values_valid(core_values),.done(core_done),.error(core_error));
 always @(posedge clk) begin
  if(cmd_valid&&cmd_ready)begin c_unit<=cmd_unit;c_op<=cmd_op;c_param<=cmd_param;c_n<=cmd_n;c_m<=cmd_m;c_values<=cmd_values;end
  if(in_ready&&in_valid)begin s_score<=in_score;s_nw<=in_nw;end
  if(core_out_ready&&core_out_valid)begin q_id<=core_id;q_score<=core_score;q_row<=core_row;q_last<=core_last;q_values<=core_values;end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;c_valid<=0;s_valid<=0;q_valid<=0;pending_done<=0;done<=0;error<=0;h_v<=0;end
  else begin
   done<=0;
   if(c_valid&&core_cmd_ready)c_valid<=0;
   if(cmd_valid&&cmd_ready)h_v<=1;
   if(go)begin h_v<=0;active<=1;c_valid<=1;error<=0;end
   if(in_ready)s_valid<=in_valid;
   if(core_out_ready)q_valid<=core_out_valid;
   if(core_done)begin pending_done<=1;error<=core_error;end
   if((pending_done||core_done)&&(!q_valid||out_ready))begin done<=1;active<=0;pending_done<=0;c_valid<=0;s_valid<=0;end
  end
 end
endmodule
