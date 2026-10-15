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

// el1011-hbm-idx 10-11: WREG=1 registers the write port (ce / address / mask / data flops next to the macro, write one edge
// after the B stage): the macro's wd_in / w_mask_in / w_addr_in see flop -> pin only (the w8 route had B-stage compare ->
// select -> wd_in in one cycle across the block).  The heap's last-write register (byp) covers the extra edge (see heap).
// el1011-hold3 2026-10-12: FFMAX = deepest level kept in flops (default 16 = the closed heap_rt_b netlist).  The M5
// heap re-route (ot_hgi_topk_heap_tile_m5 TT -43.86 / FF -55.41: the 8- and 16-word flop levels 5/6 = 5,184 flops behind
// one write-address decode (wa_q 3,462 loads) and a 16:1 x 216-b read mux, setup AND hold failing on the same store =
// skew over one 16k-flop root) builds with -DOT_TOPK_HEAP_FFMAX=4: levels 5/6 move into 128x256 macros (same sync read /
// masked sync write), ~10.8k flops on the root.
module ot_hgi_topk_lvl #(parameter integer DEPTH=1, parameter integer AW=1, parameter integer WREG=0, parameter integer FFMAX=16) (
 input wire clk,
 input wire r_ce, input wire [AW-1:0] r_a, output wire [215:0] rd,
 input wire w_ce_i, input wire [AW-1:0] w_a_i, input wire [1:0] w_s, input wire [53:0] w_d, input wire w_all
);
 wire [255:0] wmask_c = w_all ? {40'd0, {216{1'b1}}} : ({202'd0, {54{1'b1}}} << (54 * w_s));
 wire [255:0] wdat_c = w_all ? 256'd0 : {40'd0, w_d, w_d, w_d, w_d};
 wire w_ce; wire [AW-1:0] w_a; wire [255:0] wmask, wdat;
 generate if (WREG != 0) begin : g_wr
  reg wce_q; reg [AW-1:0] wa_q; reg [255:0] wm_q, wd_q;
  always @(posedge clk) begin wce_q <= w_ce_i; wa_q <= w_a_i; wm_q <= wmask_c; wd_q <= wdat_c; end
  assign w_ce = wce_q; assign w_a = wa_q; assign wmask = wm_q; assign wdat = wd_q;
 end else begin : g_wc
  assign w_ce = w_ce_i; assign w_a = w_a_i; assign wmask = wmask_c; assign wdat = wdat_c;
 end endgenerate
 generate if (DEPTH <= FFMAX) begin : g_ff
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

`ifndef OT_TOPK_TILE_HARD   // the hierarchical w8 top reads the tile as a hardened macro (blackbox stub defines this)
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
 (* keep *) reg clr_bl [0:LV]; (* keep *) reg [$clog2(QMAX+1):0] clr_cl [0:LV];   // per-level clear copies
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
`ifdef OT_TOPK_HEAP_FFMAX
  localparam integer FFM = `OT_TOPK_HEAP_FFMAX;
`else
  localparam integer FFM = 16;
`endif
  ot_hgi_topk_lvl #(.DEPTH(D), .AW(A), .WREG(1), .FFMAX(FFM)) u_l (.clk(clk),
   .r_ce(a_v[j - 2]), .r_a(A'(rp & ((1 << (j - 2)) - 1))), .rd(rdq[j]),
   .w_ce_i(wr_v[j] || clr_bl[j]), .w_a_i(clr_bl[j] ? A'(clr_cl[j]) : A'((wp & ((1 << j) - 1)) >> 2)), .w_s(wp[1:0]),
   .w_d(wr_d[j]), .w_all(clr_bl[j]));
  always @(posedge clk) rdr[j] <= rdq[j];
 end endgenerate
 integer i;
 reg any_v;
 always @* begin any_v = 1'b0; for (i = 0; i < LV; i = i + 1) any_v = any_v | a_v[i] | b_v[i]; end
 assign idle = !any_v && ent_c == 2'd0 && !clr_b && !clr_p;
 wire clr_start = clr_p && !any_v && ent_c == 2'd0 && !clr_b;
 always @(posedge clk or negedge rst_n) begin
  if (!rst_n) begin
   for (i = 0; i <= LV; i = i + 1) begin clr_bl[i] <= 1'b0; clr_cl[i] <= 0; end
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
   // replicated copies (same recurrence; each level's store reads only its own)
   for (i = 0; i <= LV; i = i + 1) begin
    if (clr_start) begin clr_bl[i] <= 1'b1; clr_cl[i] <= 0; end
    if (clr_bl[i]) begin clr_cl[i] <= clr_cl[i] + 1'b1; if (clr_cl[i] + 1 >= clr_l) clr_bl[i] <= 1'b0; end
   end
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

// el1011-hbm-idx 10-11: ONE HEAP AS A HARDENED TILE (registered boundary): pin flops on every input, a 2-entry op FIFO
// in front of the heap, credit return (one pulse per op taken by the heap; the engine starts with OPC credits), registered
// ext / idle / root outputs.  The engine counts credits and holds a settle count after any op or clear so the registered
// idle can never be read stale.  W of these replace the flat heaps (hierarchical: one tile closes, W copies place).
module ot_hgi_topk_heap_tile #(parameter integer MAX_K=2048, parameter integer MUT_BYP=0, parameter integer MUT_CLR=0) (
 input wire clk, rst_n,
 input wire [$clog2(MAX_K+1)-1:0] k,
 input wire op_v, input wire op_ext, input wire [53:0] op_x,
 output reg op_cr,                                     // one edge per op the heap took
 output reg ext_v, output reg [53:0] ext_d,
 output reg [52:0] root_key,
 input wire clr_go, output reg idle
);
 localparam integer KW = $clog2(MAX_K + 1);
 reg [KW-1:0] k_p; reg v_p, x_p, c_p; reg [53:0] d_p;
 wire [1:0] trr;                                       // reset standard: the port drives only the relay
 ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(trr));
 reg [54:0] fq [0:1]; reg [1:0] fn; reg fh;           // {ext, x}
 wire h_rdy, h_xv, h_idle; wire [53:0] h_xd; wire [52:0] h_root;
 wire h_go = (fn != 2'd0) && h_rdy;
 wire [54:0] h_op = fq[fh];
 // el1011-hbm-idx 10-12: the hard w8 cluster instantiates its tiles WITHOUT parameters; bench mutants reach them by define
`ifdef OT_TOPK_HEAP_MUT_BYP
 localparam integer MBY = 1;
`else
 localparam integer MBY = MUT_BYP;
`endif
`ifdef OT_TOPK_HEAP_MUT_CLR
 localparam integer MCL = 1;
`else
 localparam integer MCL = MUT_CLR;
`endif
 ot_hgi_topk_heap #(.MAX_K(MAX_K), .MUT_BYP(MBY), .MUT_CLR(MCL)) u_h (.clk(clk), .rst_n(trr[0]), .k(k_p),
  .op_v(fn != 2'd0), .op_ext(h_op[54]), .op_x(h_op[53:0]), .op_rdy(h_rdy), .ext_v(h_xv), .ext_d(h_xd), .root_key(h_root),
  .clr_go(c_p), .idle(h_idle));
 always @(posedge clk) begin
  k_p <= k; d_p <= op_x; x_p <= op_ext;
  if (v_p) fq[fh ^ fn[0]] <= {x_p, d_p};                 // tail (credits keep fn + v_p <= 2)
  ext_d <= h_xd; root_key <= h_root;
 end
 always @(posedge clk or negedge trr[1]) begin
  if (!trr[1]) begin v_p <= 1'b0; c_p <= 1'b0; fn <= 2'd0; fh <= 1'b0; op_cr <= 1'b0; ext_v <= 1'b0; idle <= 1'b0; end
  else begin
   v_p <= op_v; c_p <= clr_go;
   fn <= fn + v_p - h_go; if (h_go) fh <= ~fh;
   op_cr <= h_go; ext_v <= h_xv;
   idle <= h_idle && fn == 2'd0 && !v_p && !c_p && !h_go;
  end
 end
endmodule

// el1011-hbm-idx 2026-10-12 (w8 split, textbook class 1): ONE LANE OF THE w8 ENGINE AS A HARD TILE (no parameters; the
// W = IW = 8, MAX_K 2,048 configuration of ot_hgi_idx_topk_hw LANE=1).  It holds what the cluster's g_h lane held: the
// lane relay's LAST stage (as pin flops: phase / k / clear / push), the 16 x 54 survivor FIFO, the heap credits and settle
// count, the extract counters, the lane status flops (quiet / extract done / FIFO room), the registered heap seam (its
// outer face abuts the heap tile ot_hgi_topk_heap_tile), the 1024 x 256 reverse-buffer SRAM with registered write / read
// and capture flop, the 8 x 54 run FIFO and the leaf head.  The merge leaf leaves on a CREDIT link (mv / md registered,
// MQD credits, credit return mcr into a pin flop) instead of the old one-cycle pop handshake with the cluster's relay node.
// Every input lands in a pin flop, every output is a register.
module ot_hgi_topk_lane_tile (
 input wire clk, rst_n,
 input wire [2:0] ph, input wire [11:0] kin, input wire clr, pv, input wire [53:0] pd, input wire mcr,
 output reg q, x, ok, output reg [52:0] root, output reg mv, output reg [53:0] md, output reg me,
 output wire [11:0] t_k, output reg t_op_v, t_op_ext, output wire t_clr_go, output reg [53:0] t_op_x,
 input wire t_op_cr, t_ext_v, t_idle, input wire [53:0] t_ext_d, input wire [52:0] t_root_key
);
 localparam integer KW = 12, FD = 16, FA = 4, RD = 512, RA = 9;
 localparam [2:0] MQD = 3'd6;                           // = ot_hgi_idx_topk_hw MQD
 localparam integer FTHR = 7;                           // = ot_hgi_idx_topk_hw FTHR at W = IW = 8 (checked there)
 localparam [2:0] SCV = 3'd5;
 localparam [2:0] IDLE = 0, FILL = 2, FLUSH = 3, EXT = 4, MERGE = 5;
`ifdef OT_TOPK_HEAP_MUT_REV
 localparam integer MUT_REV = 1;
`else
 localparam integer MUT_REV = 0;
`endif
 wire [1:0] rr;                                         // reset standard: the port drives only the relay
 ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
 // pin flops (relay stage 1)
 // lane_rt_d (10-12, rt_c TT -183): k and clear land in TWO pin flops each -- kl / clr_r feed the core, tk_q / tcg are the
 // S-face heap-seam output registers (rt_c pulled the shared kl flop into the 25-um seam window, so every k compare in the
 // merge / reverse-buffer logic crossed the tile: t_k -> mf -246 / -> wm_q -217 at SS); wa = k - 1 - xo is ONE adder k + ~xo.
 reg [2:0] lph; reg [KW-1:0] kl, tk_q; reg clr_r, tcg, p3_v, mcr_p; reg [53:0] p3_d;
 always @(posedge clk) begin kl <= kin; tk_q <= kin; p3_d <= pd; end
 always @(posedge clk or negedge rr[0])
  if (!rr[0]) begin lph <= IDLE; clr_r <= 1'b0; tcg <= 1'b0; p3_v <= 1'b0; mcr_p <= 1'b0; end
  else begin lph <= ph; clr_r <= clr; tcg <= clr; p3_v <= pv; mcr_p <= mcr; end
 wire fon = lph == FILL || lph == FLUSH, ex = lph == EXT, mg = lph == MERGE;
 wire pv_any = p3_v;                                    // stage 0 is the cluster's (it masks q with it)
 // survivor FIFO with ONE-HOT write / read pointers and a REGISTERED HEAD hd (== ff[fr] every cycle): t_op_x is a
 // flop -> wire -> flop copy of hd (rt_c: fr -> 16:1 mux -> t_op_x at the S-face window, 16 levels, -417 SS / -183 TT),
 // and the write enables are p3_v & fon & fwoh[i] (no 4 -> 16 decode on the 864-flop enable fan-out: lph / fw -> ff).
 reg [53:0] ff [0:FD-1]; reg [FA:0] fc; reg [FD-1:0] fwoh, froh; reg [53:0] hd;
 reg [1:0] cr; reg [2:0] sc;
 reg [KW-1:0] xi, xo;
 reg i_cr, i_xv, i_idle; reg [53:0] i_xd;               // heap seam pin flops
 wire hpv = (fon && fc != 0) || (ex && xi != kl);
 wire iss = hpv && cr != 2'd0;
 wire push = p3_v && fon;
 wire pop = fon && fc != 0 && cr != 2'd0;
 wire [FD-1:0] froh1 = {froh[FD-2:0], froh[FD-1]};
 wire [FD-1:0] frn = !fon ? {{(FD-1){1'b0}}, 1'b1} : (pop ? froh1 : froh);
 reg [53:0] m_a, m_b; integer fi;
 always @* begin
  m_a = 54'd0; m_b = 54'd0;
  for (fi = 0; fi < FD; fi = fi + 1) begin if (froh[fi]) m_a = m_a | ff[fi]; if (froh1[fi]) m_b = m_b | ff[fi]; end
 end
 always @(posedge clk) begin
  for (fi = 0; fi < FD; fi = fi + 1) if (push && fwoh[fi]) ff[fi] <= p3_d;
  hd <= (push && |(frn & fwoh)) ? p3_d : (!fon ? ff[0] : (pop ? m_b : m_a));
 end
 always @(posedge clk or negedge rr[0]) begin
  if (!rr[0]) begin
   fc <= 0; fwoh <= 1; froh <= 1; cr <= 2'd2; sc <= SCV; xi <= 0; xo <= 0;
   q <= 1'b0; x <= 1'b0; ok <= 1'b0;
  end else begin
   if (!fon) begin fc <= 0; fwoh <= 1; froh <= 1; end
   else begin fc <= fc + push - pop; if (push) fwoh <= {fwoh[FD-2:0], fwoh[FD-1]}; if (pop) froh <= froh1; end
   cr <= cr - iss + i_cr; sc <= (iss || clr_r) ? SCV : (sc != 3'd0 ? sc - 3'd1 : 3'd0);
   if (!ex) begin xi <= 0; xo <= 0; end else begin xi <= xi + iss; xo <= xo + i_xv; end
   q <= i_idle && sc == 3'd0 && fc == 0 && !pv_any;
   x <= ex && (xo + i_xv == kl);
   ok <= fc <= FTHR;
  end
 end
 // heap seam (registered both ways; the heap tile has its own pin flops / output regs)
 always @(posedge clk) begin t_op_x <= hd; i_xd <= t_ext_d; root <= t_root_key; end
 always @(posedge clk or negedge rr[0])
  if (!rr[0]) begin t_op_v <= 1'b0; t_op_ext <= 1'b0; i_cr <= 1'b0; i_xv <= 1'b0; i_idle <= 1'b0; end
  else begin t_op_v <= iss; t_op_ext <= ex; i_cr <= t_op_cr; i_xv <= t_ext_v; i_idle <= t_idle; end
 assign t_k = tk_q; assign t_clr_go = tcg;
 // reverse buffer: registered write (WREG) and read (rq_*), capture flop rbq next to the macro output
 wire [KW-1:0] wa = (MUT_REV != 0) ? xo : kl + ~xo;     // == kl - 1 - xo (mod 2^KW)
 reg [RA:0] mw; reg [RA-1:0] rq_a; reg rq_ce, s2, s3; reg [215:0] rbq; wire [215:0] rb_q;
 reg [53:0] mf [0:7]; reg [3:0] mc; reg [2:0] mr, mwp; reg [KW-1:0] mp; reg lh_v; reg [53:0] lh_d; reg [2:0] mcc;
 wire rd_go = mg && !rq_ce && !s2 && !s3 && ({mw, 2'b00} < kl) && (mc + 4'd4 <= 4'd8);
 ot_hgi_topk_lvl #(.DEPTH(RD), .AW(RA), .WREG(1)) u_rb (.clk(clk), .r_ce(rq_ce), .r_a(rq_a), .rd(rb_q), .w_ce_i(i_xv),
  .w_a_i(RA'(wa >> 2)), .w_s(wa[1:0]), .w_d(i_xd), .w_all(1'b0));
 wire lpop = lh_v && mcc != 3'd0;                       // send the head on a credit
 wire refill = mc != 4'd0 && (!lh_v || lpop);
 // words landing from this read, fixed at rd_go (one read in flight: rd_go waits for !rq_ce && !s2 && !s3) instead of
 // four k compares at s3 in front of the run-FIFO write enables (rt_c t_k -> mf, 16 levels)
 wire [KW-1:0] kd = kl - KW'({mw, 2'b00});
 reg [2:0] npr; integer lq;
 wire [2:0] np = s3 ? npr : 3'd0;
 always @(posedge clk) begin
  if (rd_go) begin rq_a <= RA'(mw); npr <= (|kd[KW-1:2]) ? 3'd4 : kd[2:0]; end
  rbq <= rb_q;
  for (lq = 0; lq < 4; lq = lq + 1) if (lq < np) mf[mwp + lq[2:0]] <= rbq[54 * lq +: 54];
  if (refill) lh_d <= mf[mr];
  if (lpop) md <= lh_d;
 end
 always @(posedge clk or negedge rr[1]) begin
  if (!rr[1]) begin mw <= 0; rq_ce <= 1'b0; s2 <= 1'b0; s3 <= 1'b0; mc <= 0; mr <= 0; mwp <= 0; mp <= 0; lh_v <= 1'b0; me <= 1'b0;
   mcc <= MQD; mv <= 1'b0; end
  else if (!mg) begin mw <= 0; rq_ce <= 1'b0; s2 <= 1'b0; s3 <= 1'b0; mc <= 0; mr <= 0; mwp <= 0; mp <= 0; lh_v <= 1'b0;
   me <= 1'b0; mcc <= MQD; mv <= 1'b0; end
  else begin
   rq_ce <= rd_go; s2 <= rq_ce; s3 <= s2;
   if (rd_go) mw <= mw + 1'b1;
   mwp <= mwp + np; mr <= mr + refill; mc <= mc + np - refill;
   if (lpop) mp <= mp + 1'b1;
   if (refill) lh_v <= 1'b1; else if (lpop) lh_v <= 1'b0;
   me <= !lh_v && mp == kl;
   mcc <= mcc - lpop + mcr_p; mv <= lpop;
  end
 end
endmodule
`endif


// el1011-hbm-idx r6 (2026-10-11, hierarchical w8h preroute -1.57 ns: tile ext_v -> global EXT-done AND -> broadcast clear of
// every lane's merge state, one cycle across 1,300 um; F1 key -> 53-b threshold compare -> push into 8 lane FIFOs; IO
// out_ready -> core output FIFO): a LANE-LOCAL engine.  Each heap lane (tile, survivor FIFO, credits, extract counters,
// reverse buffer, run FIFO, leaf head) runs from its own REGISTERED copy of the phase (lph), k and clear; lane status
// (quiet / extract done / FIFO room) returns through a registered pair stage and a registered AND; the front end pushes
// through a registered F2 (keys + threshold compares) and a per-lane F3 relay; the merge tree has a 2-entry relay node on
// every edge (leaf -> node, node -> node) and REGISTERED exhaustion; the max-root tournament has a relay per level.  The
// lags are absorbed by a settle counter (S_SET cycles of quiet before START->FILL, FLUSH->EXT, ABORT->IDLE), FD = 16
// survivor FIFOs (room judged 7 beats ahead), and a registered reverse-buffer write / read with a capture flop.
module ot_hgi_topk_mnode #(parameter bit UNARY=0) (
 input wire clk, rn, mrg,
 input wire av, input wire [53:0] ad, input wire ae,
 input wire bv, input wire [53:0] bd, input wire be,
 input wire cpop, output wire apop, output wire bpop,
 output wire ov, output wire [53:0] od, output reg oe
);
 // B2 (Claude hbm-group-B r2 2026-10-14, rt_g TT class 'g_rel en -> od 19 levels'): the 2-entry node buffer was a head /
 // spill pair (hd, pd): a parent pop (cpop = the parent's fire & pick, behind its 53-b compare) steered the load of all
 // 108 data flops of the child.  It is now a 2-entry POINTER FIFO with the same occupancy (hv = cnt >= 1, pv = cnt == 2)
 // and the same fire / pop rule on every edge: entries are written at wp and never move; cpop advances the 1-bit read
 // pointer and the count only, and od is a 2:1 mux of two flops by rp.  Cycle-identical to the head / spill pair.
 reg en; reg [1:0] cnt; reg wp, rp; reg [53:0] e0, e1;
 wire hv = cnt != 2'd0, pv = cnt == 2'd2;
 wire bvi = UNARY ? 1'b0 : bv; wire bei = UNARY ? 1'b1 : be;
 wire a_lt_b;
 generate if (UNARY) begin : g_u assign a_lt_b = 1'b0; end
 else begin : g_b ot_topk_lt #(.W(53)) u_c (.a(ad[52:0]), .b(bd[52:0]), .lt(a_lt_b)); end endgenerate
 wire fire = en && !pv && (av || bvi) && (av || ae) && (bvi || bei);
 wire pick_b = bvi && (!av || a_lt_b);
 wire [53:0] x = pick_b ? bd : ad;
 wire pop = cpop && hv;
 assign apop = fire && !pick_b; assign bpop = fire && pick_b;
 assign ov = hv; assign od = rp ? e1 : e0;
 always @(posedge clk or negedge rn) begin
  if (!rn) begin en <= 1'b0; cnt <= 2'd0; wp <= 1'b0; rp <= 1'b0; oe <= 1'b0; end
  else begin
   en <= mrg;
   if (!en) begin cnt <= 2'd0; wp <= 1'b0; rp <= 1'b0; oe <= 1'b0; end
   else begin
    oe <= ae && bei && !hv && !pv;                     // exhausted, registered (monotone: a lag only delays a fire)
    if (fire) wp <= ~wp;
    if (pop) rp <= ~rp;
    cnt <= cnt + {1'b0, fire} - {1'b0, pop};
   end
  end
 end
 // rt_i (Claude group-B4 10-14, rt_h gate 'g_rel en -> e0/e1' -63 ps, 218 endpoints): the free slot at wp is written
 // whenever the node is not full (!pv, a register decode), not on fire: while cnt < 2 the slot at wp holds no entry and
 // is never read before a fire advances cnt, so loading it every such edge stores the same value on the fire edge.
 always @(posedge clk) if (!pv) begin if (wp) e1 <= x; else e0 <= x; end
endmodule

// Wide engine: IW scores a beat (in_nw valid, the row's last beat may be partial), W heaps (W a multiple of IW).
module ot_hgi_idx_topk_hw #(
 parameter bit ENABLE=0, parameter integer MAX_K=2048, parameter bit MUTANT_TIE=0,
 parameter integer IW=1, parameter integer W=2,
 // bench mutants (must FAIL): MUT_BYP no grandchild bypass, MUT_CLR no inter-row level clear, MUT_REV reverse buffer
 // written in extraction (ascending) order
 parameter integer MUT_BYP=0, parameter integer MUT_CLR=0, parameter integer MUT_REV=0,
 // HUB=1 (el1011-hbm-idx r6, hgi_idx_topk_w8_hub): the heap tiles are OUTSIDE; every tile seam is registered on this side
 // (t_* outputs from flops, t_* inputs into pin flops; the tile has its own pin flops / registered outputs)
 parameter bit HUB=0,
 // LANE=1 (with HUB=1; el1011-hbm-idx 10-12 w8 split, textbook class 1: 23.7k cluster flops on one root): the per-lane glue
 // (survivor FIFO, credits, extract counters, reverse buffer, run FIFO, leaf head, heap seam) is the hard lane tile
 // ot_hgi_topk_lane_tile OUTSIDE (lt_* pins); this side keeps relay stage 0, the status / tournament / merge trees and a
 // per-lane merge credit FIFO (the leaf pop loop is cut at a registered credit link)
 parameter bit LANE=0
)(
 input wire clk,rst_n,
 input wire cmd_valid, output wire cmd_ready,
 input wire [3:0] cmd_unit, input wire [5:0] cmd_op,
 input wire [24:0] cmd_param, input wire [31:0] cmd_n,cmd_m,
 input wire cmd_values,
 input wire in_valid, output wire in_ready, input wire [IW*32-1:0] in_score, input wire [$clog2(IW+1)-1:0] in_nw,
 output wire out_valid, input wire out_ready,
 output wire [31:0] out_id,out_score,out_row,
 output wire out_last, output wire out_values_valid, output reg done, output reg [3:0] error,
 output wire [W*$clog2(MAX_K+1)-1:0] t_k, output wire [W-1:0] t_op_v, t_op_ext, t_clr_go, output wire [W*54-1:0] t_op_x,
 input wire [W-1:0] t_op_cr, t_ext_v, t_idle_i, input wire [W*54-1:0] t_ext_d, input wire [W*53-1:0] t_root_key,
 output wire [W*3-1:0] lt_ph, output wire [W*$clog2(MAX_K+1)-1:0] lt_k, output wire [W-1:0] lt_clr, lt_pv, lt_mcr,
 output wire [W*54-1:0] lt_pd,
 input wire [W-1:0] lt_q, lt_x, lt_ok, lt_mv, lt_me, input wire [W*53-1:0] lt_root, input wire [W*54-1:0] lt_md,
 output wire [1:0] rr_x
);
 localparam integer KW = $clog2(MAX_K + 1);
 localparam [2:0] SCV = HUB ? 3'd5 : 3'd3;              // settle count after an op / clear (covers the seam flops)
 localparam integer G = W / IW;                         // heap groups (beats rotate over them)
 localparam integer FD = 16, FA = 4;                    // survivor FIFO a heap
 localparam integer LRD = 2;                            // lane relay depth (phase / k / clear / push): <= ~500 um a stage
 localparam integer WP = (W <= 1) ? 1 : (1 << $clog2(W)), WL = (W <= 1) ? 0 : $clog2(W);
 // room: fc(t) -> lane flag -> WL AND levels = in_ok -> beat -> F1 -> F2 -> LRD relays -> fc: beats not yet counted
 localparam integer FTHR = FD - ((LRD + 3) + (1 + WL));
 localparam integer RD = (MAX_K + 3) / 4;               // reverse buffer words
 localparam integer RA = (RD <= 1) ? 1 : $clog2(RD);
 localparam integer S_SET = 12;                         // quiet cycles before a phase change (covers every status lag)
 localparam integer TL = 2 * WL + 1;                    // merge tree layers (relay, node, relay, ..., relay)
 localparam [2:0] IDLE=0, START=1, FILL=2, FLUSH=3, EXT=4, MERGE=5, ABORT=6, FIN=7;
 // reset standard (ot_rst_relay): the port drives only the relay; lane h resets from region h, the control from region W.
 // j3: two extra relay regions exported (rr_x) so a wrapper's own registers release on the engine's edge from the
 // same single port load (hub tile native audit: two relays on rst_n = capture 208.6 ps).  Unused elsewhere.
 wire [W+2:0] rr;
 ot_rst_relay #(.REGIONS(W + 3), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
 assign rr_x = rr[W+2:W+1];
 wire rn = rr[W];
 reg up;
 always @(posedge clk or negedge rn) if (!rn) up <= 1'b0; else up <= 1'b1;
 reg [2:0] st, pst;
 reg [31:0] n, m, row, cursor;
 reg [KW-1:0] k;
 reg values_enabled, clr_go;
 integer i;
 genvar h, l, gl, gi, gr;
 // ---------------------------------------------------------------- lane status: a registered AND tree (one level an edge)
 wire [W-1:0] l_q, l_x, l_ok;
 wire [2:0] ar [0:WL][0:WP-1];                          // {ok, x, q}
 for (gi = 0; gi < WP; gi = gi + 1) begin : g_ar0
  if (gi < W) begin : g_r assign ar[0][gi] = {l_ok[gi], l_x[gi], l_q[gi]}; end else begin : g_z assign ar[0][gi] = 3'b111; end
 end
 for (gl = 0; gl < WL; gl = gl + 1) begin : g_arl
  for (gi = 0; gi < (WP >> (gl + 1)); gi = gi + 1) begin : g_arn
   reg [2:0] a;
   always @(posedge clk or negedge rn) if (!rn) a <= 3'b000; else a <= ar[gl][2 * gi] & ar[gl][2 * gi + 1];
   assign ar[gl + 1][gi] = a;
  end
 end
 wire r_q = ar[WL][0][0], r_x = ar[WL][0][1], in_ok = ar[WL][0][2];
 // ---------------------------------------------------------------- max-root tournament (registered, a relay a level)
 wire [52:0] h_root [0:W-1];
 reg [52:0] gt [0:WL][0:WP-1];
 reg [52:0] gtr [0:WL][0:WP-1];
 reg [52:0] gth;
 for (gi = 0; gi < WP; gi = gi + 1) begin : g_gt0 always @(posedge clk) gt[0][gi] <= (gi < W) ? h_root[gi] : 53'd0; end
 for (gl = 0; gl < WL; gl = gl + 1) begin : g_gtl
  for (gi = 0; gi < (WP >> gl); gi = gi + 1) begin : g_gtr always @(posedge clk) gtr[gl][gi] <= gt[gl][gi]; end
  for (gi = 0; gi < (WP >> (gl + 1)); gi = gi + 1) begin : g_gtn
   wire lo_lt; ot_topk_lt #(.W(53)) u_c (.a(gtr[gl][2 * gi]), .b(gtr[gl][2 * gi + 1]), .lt(lo_lt));
   always @(posedge clk) gt[gl + 1][gi] <= lo_lt ? gtr[gl][2 * gi + 1] : gtr[gl][2 * gi];
  end
 end
 always @* gth = gt[WL][0];
 // ---------------------------------------------------------------- front end: F1 (beat) -> F2 (keys, compares) -> lanes
 // rt_i (rt_h gate 'st -> s_valid' -126 ps): FILL is a registered flag loaded with the state's next value (st_n).
 reg fill_q;
 assign in_ready = ENABLE && fill_q && in_ok;
 wire beat = in_valid && in_ready;
 reg f1_v; reg [$clog2(IW+1)-1:0] f1_nw; reg [$clog2(G+1)-1:0] f1_g, grp;
 wire f1_nan; wire [53:0] f1_e [0:IW-1]; wire [IW-1:0] f1_nl;
 // B2 (rt_g TT classes 'f1_c -> f2_gt 18 levels', 'f1_s -> f2_e 13 levels'): the key of each lane (negative-zero flag,
 // monotone score, ~index) and its NaN flag are formed from the beat and the cursor IN FRONT OF the F1 register (the beat
 // comes from the boundary FIFO's head register, the cursor is a register), so F1 -> F2 holds only the 53-b threshold
 // compare.  Same F1 / F2 edges, same keys: cycle-identical.
 reg [53:0] f1_k [0:IW-1]; reg [IW-1:0] f1_n;
 generate for (l = 0; l < IW; l = l + 1) begin : g_key
  wire [31:0] s = in_score[32 * l +: 32];
  wire [31:0] canon = (s[30:0] == 31'd0) ? 32'd0 : s;
  wire [31:0] mono = canon[31] ? ~canon : (canon | 32'h80000000);
  wire [19:0] idx = cursor[19:0] + l;
  always @(posedge clk) if (beat) begin
   f1_k[l] <= {s == 32'h80000000, 1'b1, mono, MUTANT_TIE ? idx : ~idx};
   f1_n[l] <= (l < in_nw) && (s[30:23] == 8'hff) && (s[22:0] != 23'd0);
  end
  assign f1_e[l] = f1_k[l];
  assign f1_nl[l] = f1_n[l];
 end endgenerate
 assign f1_nan = f1_v && (|f1_nl);
 wire [IW-1:0] f1_gt;                                   // lane key above the drop threshold
 generate for (l = 0; l < IW; l = l + 1) begin : g_flt
  ot_topk_lt #(.W(53)) u_c (.a(gth), .b(f1_e[l][52:0]), .lt(f1_gt[l]));
 end endgenerate
 reg f2_v; reg [53:0] f2_e [0:IW-1]; reg [IW-1:0] f2_gt; reg [$clog2(IW+1)-1:0] f2_nw; reg [$clog2(G+1)-1:0] f2_g;
 always @(posedge clk) begin
  for (i = 0; i < IW; i = i + 1) f2_e[i] <= f1_e[i];
  f2_gt <= f1_gt; f2_nw <= f1_nw; f2_g <= f1_g;
 end
 // ---------------------------------------------------------------- lanes
 wire l_lv [0:W-1], l_le [0:W-1], l_pop [0:W-1]; wire [53:0] l_ld [0:W-1];
 localparam integer MQD = 6;                            // LANE: merge credit FIFO (credit round trip 5 = full rate)
 if (LANE && (!HUB || W != 8 || IW != 8 || KW != 12 || FTHR != 7 || LRD != 2)) begin : g_lchk
  ot_ERROR_lane_tile_is_the_w8_configuration u_chk ();  // ot_hgi_topk_lane_tile hard-codes these
 end
 generate for (h = 0; h < W; h = h + 1) begin : g_h
  if (LANE) begin : g_lt
   wire f2p = f2_v && (h / IW == f2_g) && ((h % IW) < f2_nw) && f2_gt[h % IW];
   (* keep = 1 *) reg [2:0] ph0; (* keep = 1 *) reg [KW-1:0] k0;
   (* keep = 1 *) reg c0, pv0; (* keep = 1 *) reg [53:0] pd0;     // relay stage 0 (stage 1 = the tile's pin flops)
   always @(posedge clk) begin k0 <= k; pd0 <= f2_e[h % IW]; end
   always @(posedge clk or negedge rr[h])
    if (!rr[h]) begin ph0 <= IDLE; c0 <= 1'b0; pv0 <= 1'b0; end else begin ph0 <= st; c0 <= clr_go; pv0 <= f2p; end
   assign lt_ph[3 * h +: 3] = ph0; assign lt_k[KW * h +: KW] = k0; assign lt_clr[h] = c0; assign lt_pv[h] = pv0;
   assign lt_pd[54 * h +: 54] = pd0;
   assign l_q[h] = lt_q[h] && !pv0; assign l_x[h] = lt_x[h]; assign l_ok[h] = lt_ok[h];
   assign h_root[h] = lt_root[53 * h +: 53];
   // merge leaf: the tile sends (mv, md) on a credit; entries land straight in this FIFO (its entry flops are the pin
   // flops); exhaustion (me) leaves the tile one edge after its last item and is registered again here (mle)
   // j2 (native pin audit): mv / md / me land in pin registers first (lt_mv fanned out to 324 entry enables, 446 ps);
   // the credit round trip grows 5 -> 6 edges, the tile's MQD = 6 credits still bound pin stage + FIFO (full rate).
   reg men, mle, mcr, mv_p, me_p; reg [53:0] md_p; reg [53:0] mq [0:MQD-1]; reg [2:0] mqw, mqr, mqn;
   wire mpush = men && mv_p, mpop = l_pop[h];
   always @(posedge clk) begin md_p <= lt_md[54 * h +: 54]; if (mpush) mq[mqw] <= md_p; end
   always @(posedge clk or negedge rr[h])
    if (!rr[h]) begin men <= 1'b0; mle <= 1'b0; mcr <= 1'b0; mqw <= 0; mqr <= 0; mqn <= 0; mv_p <= 1'b0; me_p <= 1'b0; end
    else begin
     men <= st == MERGE; mv_p <= lt_mv[h]; me_p <= lt_me[h];
     if (!men) begin mle <= 1'b0; mcr <= 1'b0; mqw <= 0; mqr <= 0; mqn <= 0; end
     else begin
      mle <= me_p; mcr <= mpop;
      if (mpush) mqw <= (mqw == MQD - 1) ? 3'd0 : mqw + 3'd1;
      if (mpop) mqr <= (mqr == MQD - 1) ? 3'd0 : mqr + 3'd1;
      mqn <= mqn + mpush - mpop;
     end
    end
   assign l_lv[h] = mqn != 3'd0; assign l_ld[h] = mq[mqr]; assign l_le[h] = mle && mqn == 3'd0;
   assign lt_mcr[h] = mcr;
   assign t_k[KW * h +: KW] = '0; assign t_op_v[h] = 1'b0; assign t_op_ext[h] = 1'b0; assign t_op_x[54 * h +: 54] = '0;
   assign t_clr_go[h] = 1'b0;
  end else begin : g_ln
   assign lt_ph[3 * h +: 3] = '0; assign lt_k[KW * h +: KW] = '0; assign lt_clr[h] = 1'b0; assign lt_pv[h] = 1'b0;
   assign lt_pd[54 * h +: 54] = '0; assign lt_mcr[h] = 1'b0;
  reg [2:0] lph_s [0:LRD-1]; reg [KW-1:0] kl_s [0:LRD-1]; reg clr_s [0:LRD-1];   // LRD-deep lane relays
  wire [2:0] lph = lph_s[LRD - 1]; wire [KW-1:0] kl = kl_s[LRD - 1]; wire clr_r = clr_s[LRD - 1];
  for (gr = 0; gr < LRD; gr = gr + 1) begin : g_rl
   always @(posedge clk) kl_s[gr] <= (gr == 0) ? k : kl_s[gr == 0 ? 0 : gr - 1];
   always @(posedge clk or negedge rr[h])
    if (!rr[h]) begin lph_s[gr] <= IDLE; clr_s[gr] <= 1'b0; end
    else begin lph_s[gr] <= (gr == 0) ? st : lph_s[gr == 0 ? 0 : gr - 1]; clr_s[gr] <= (gr == 0) ? clr_go : clr_s[gr == 0 ? 0 : gr - 1]; end
  end
  wire fon = lph == FILL || lph == FLUSH, ex = lph == EXT, mg = lph == MERGE;
  reg pr_v [0:LRD-1]; reg [53:0] pr_d [0:LRD-1];        // F3..: the lane's LRD-deep relay of the front-end push
  wire f2p = f2_v && (h / IW == f2_g) && ((h % IW) < f2_nw) && f2_gt[h % IW];
  for (gr = 0; gr < LRD; gr = gr + 1) begin : g_pr
   always @(posedge clk) pr_d[gr] <= (gr == 0) ? f2_e[h % IW] : pr_d[gr == 0 ? 0 : gr - 1];
   always @(posedge clk or negedge rr[h]) if (!rr[h]) pr_v[gr] <= 1'b0; else pr_v[gr] <= (gr == 0) ? f2p : pr_v[gr == 0 ? 0 : gr - 1];
  end
  wire p3_v = pr_v[LRD - 1]; wire [53:0] p3_d = pr_d[LRD - 1];
  reg pv_any; integer lr;
  always @* begin pv_any = 1'b0; for (lr = 0; lr < LRD; lr = lr + 1) pv_any = pv_any | pr_v[lr]; end
  reg [53:0] ff [0:FD-1]; reg [FA:0] fc; reg [FA-1:0] fw, fr;
  reg [1:0] cr; reg [2:0] sc;                          // credits (2 = tile FIFO depth), settle count
  reg [KW-1:0] xi, xo;
  wire t_cr, t_idle, t_xv; wire [53:0] t_xd;
  wire hpv = (fon && fc != 0) || (ex && xi != kl);
  wire iss = hpv && cr != 2'd0;
  wire push = p3_v && fon;
  wire pop = fon && fc != 0 && cr != 2'd0;
  always @(posedge clk) if (push) ff[fw] <= p3_d;
  reg q_l, x_l, ok_l;
  always @(posedge clk or negedge rr[h]) begin
   if (!rr[h]) begin
    fc <= 0; fw <= 0; fr <= 0; cr <= 2'd2; sc <= SCV; xi <= 0; xo <= 0;
    q_l <= 1'b0; x_l <= 1'b0; ok_l <= 1'b0;
   end else begin
    if (!fon) begin fc <= 0; fw <= 0; fr <= 0; end
    else begin fc <= fc + push - pop; fw <= fw + push; fr <= fr + pop; end
    cr <= cr - iss + t_cr; sc <= (iss || clr_r) ? SCV : (sc != 3'd0 ? sc - 3'd1 : 3'd0);
    if (!ex) begin xi <= 0; xo <= 0; end else begin xi <= xi + iss; xo <= xo + t_xv; end
    q_l <= t_idle && sc == 3'd0 && fc == 0 && !pv_any;
    x_l <= ex && (xo + t_xv == kl);
    ok_l <= fc <= FTHR;
   end
  end
  assign l_q[h] = q_l; assign l_x[h] = x_l; assign l_ok[h] = ok_l;
  if (HUB) begin : g_seam
   reg o_v, o_e, i_cr, i_xv, i_idle; reg [53:0] o_x, i_xd; reg [52:0] i_root;
   always @(posedge clk) begin o_x <= ff[fr]; i_xd <= t_ext_d[54 * h +: 54]; i_root <= t_root_key[53 * h +: 53]; end
   always @(posedge clk or negedge rr[h])
    if (!rr[h]) begin o_v <= 1'b0; o_e <= 1'b0; i_cr <= 1'b0; i_xv <= 1'b0; i_idle <= 1'b0; end
    else begin o_v <= iss; o_e <= ex; i_cr <= t_op_cr[h]; i_xv <= t_ext_v[h]; i_idle <= t_idle_i[h]; end
   assign t_k[KW * h +: KW] = kl; assign t_op_v[h] = o_v; assign t_op_ext[h] = o_e; assign t_op_x[54 * h +: 54] = o_x;
   assign t_clr_go[h] = clr_r;
   assign t_cr = i_cr; assign t_xv = i_xv; assign t_xd = i_xd; assign h_root[h] = i_root; assign t_idle = i_idle;
  end else begin : g_tile
`ifdef OT_TOPK_TILE_HARD
  ot_hgi_topk_heap_tile u_hp (.clk(clk), .rst_n(rr[h]), .k(kl),
`else
  ot_hgi_topk_heap_tile #(.MAX_K(MAX_K), .MUT_BYP(MUT_BYP), .MUT_CLR(MUT_CLR)) u_hp (.clk(clk), .rst_n(rr[h]), .k(kl),
`endif
   .op_v(iss), .op_ext(ex), .op_x(ff[fr]), .op_cr(t_cr), .ext_v(t_xv), .ext_d(t_xd), .root_key(h_root[h]),
   .clr_go(clr_r), .idle(t_idle));
   assign t_k[KW * h +: KW] = '0; assign t_op_v[h] = 1'b0; assign t_op_ext[h] = 1'b0; assign t_op_x[54 * h +: 54] = '0;
   assign t_clr_go[h] = 1'b0;
  end
  // reverse buffer: registered write (WREG) and read (rq_*), capture flop rbq next to the macro output
  wire [KW-1:0] wa = (MUT_REV != 0) ? xo : kl - 1'b1 - xo;
  reg [RA:0] mw; reg [RA-1:0] rq_a; reg rq_ce, s2, s3; reg [215:0] rbq; wire [215:0] rb_q;
  reg [53:0] mf [0:7]; reg [3:0] mc; reg [2:0] mr, mwp; reg [KW-1:0] mp; reg lh_v, le; reg [53:0] lh_d;
  wire rd_go = mg && !rq_ce && !s2 && !s3 && ({mw, 2'b00} < kl) && (mc + 4'd4 <= 4'd8);
  ot_hgi_topk_lvl #(.DEPTH(RD), .AW(RA), .WREG(1)) u_rb (.clk(clk), .r_ce(rq_ce), .r_a(rq_a), .rd(rb_q), .w_ce_i(t_xv),
   .w_a_i(RA'(wa >> 2)), .w_s(wa[1:0]), .w_d(t_xd), .w_all(1'b0));
  wire lpop = l_pop[h];
  wire refill = mc != 4'd0 && (!lh_v || lpop);
  wire [KW+1:0] base = {mw - 1'b1, 2'b00};
  reg [2:0] np; integer lq;
  always @* begin np = 3'd0; for (lq = 0; lq < 4; lq = lq + 1) if (s3 && base + lq < kl) np = np + 1'b1; end
  always @(posedge clk) begin
   if (rd_go) rq_a <= RA'(mw);
   rbq <= rb_q;
   for (lq = 0; lq < 4; lq = lq + 1) if (lq < np) mf[mwp + lq[2:0]] <= rbq[54 * lq +: 54];
   if (refill) lh_d <= mf[mr];
  end
  always @(posedge clk or negedge rr[h]) begin
   if (!rr[h]) begin mw <= 0; rq_ce <= 1'b0; s2 <= 1'b0; s3 <= 1'b0; mc <= 0; mr <= 0; mwp <= 0; mp <= 0; lh_v <= 1'b0; le <= 1'b0; end
   else if (!mg) begin mw <= 0; rq_ce <= 1'b0; s2 <= 1'b0; s3 <= 1'b0; mc <= 0; mr <= 0; mwp <= 0; mp <= 0; lh_v <= 1'b0; le <= 1'b0; end
   else begin
    rq_ce <= rd_go; s2 <= rq_ce; s3 <= s2;
    if (rd_go) mw <= mw + 1'b1;
    mwp <= mwp + np; mr <= mr + refill; mc <= mc + np - refill;
    if (lpop) mp <= mp + 1'b1;
    if (refill) lh_v <= 1'b1; else if (lpop) lh_v <= 1'b0;
    le <= !lh_v && mp == kl;
   end
  end
  assign l_lv[h] = lh_v; assign l_ld[h] = lh_d; assign l_le[h] = le;
  end
 end endgenerate
 // ---------------------------------------------------------------- merge tree (relay node on every edge)
 wire tv [0:TL][0:WP-1]; wire [53:0] td [0:TL][0:WP-1]; wire te [0:TL][0:WP-1]; wire tp [0:TL][0:WP-1];
 for (gi = 0; gi < WP; gi = gi + 1) begin : g_lf
  if (gi < W) begin : g_r assign tv[0][gi] = l_lv[gi]; assign td[0][gi] = l_ld[gi]; assign te[0][gi] = l_le[gi]; assign l_pop[gi] = tp[0][gi]; end
  else begin : g_z assign tv[0][gi] = 1'b0; assign td[0][gi] = 54'd0; assign te[0][gi] = 1'b1; end
 end
 wire mrg = st == MERGE;
 for (gl = 1; gl <= TL; gl = gl + 1) begin : g_ly
  if (gl % 2 == 1) begin : g_rel
   for (gi = 0; gi < (WP >> ((gl - 1) / 2)); gi = gi + 1) begin : g_n
    wire bp_u;
    ot_hgi_topk_mnode #(.UNARY(1)) u_n (.clk(clk), .rn(rn), .mrg(mrg), .av(tv[gl - 1][gi]), .ad(td[gl - 1][gi]),
     .ae(te[gl - 1][gi]), .bv(1'b0), .bd(54'd0), .be(1'b1), .cpop(tp[gl][gi]), .apop(tp[gl - 1][gi]), .bpop(bp_u),
     .ov(tv[gl][gi]), .od(td[gl][gi]), .oe(te[gl][gi]));
   end
  end else begin : g_bin
   for (gi = 0; gi < (WP >> (gl / 2)); gi = gi + 1) begin : g_n
    ot_hgi_topk_mnode #(.UNARY(0)) u_n (.clk(clk), .rn(rn), .mrg(mrg), .av(tv[gl - 1][2 * gi]), .ad(td[gl - 1][2 * gi]),
     .ae(te[gl - 1][2 * gi]), .bv(tv[gl - 1][2 * gi + 1]), .bd(td[gl - 1][2 * gi + 1]), .be(te[gl - 1][2 * gi + 1]),
     .cpop(tp[gl][gi]), .apop(tp[gl - 1][2 * gi]), .bpop(tp[gl - 1][2 * gi + 1]),
     .ov(tv[gl][gi]), .od(td[gl][gi]), .oe(te[gl][gi]));
   end
  end
 end
 reg [KW-1:0] emitted;
 reg [53:0] of [0:3]; reg of_l [0:3]; reg [2:0] oc; reg [1:0] ow, orp;
 // rt_i (rt_h gate classes 'k -> out_row / st / emitted / of' -289..-72 ps: the 12-b emitted != k compare sat in front of
 // the root pop and every state / FIFO enable): a REMAINING count rem = k - emitted with registered flags rz (rem == 0)
 // and r1 (rem == 1), loaded at EXT -> MERGE (rem = k) and stepped by the pop; lr_q = (row + 1 == m) registered (row and
 // m are stable >= S_SET cycles before any MERGE exit).  emitted == k <=> rz; emitted + 1 == k <=> r1.
 reg [KW-1:0] rem; reg rz, r1, lr_q, mrg_q;
 wire mg_go = mrg_q && !rz && tv[TL][0] && oc <= 3'd2;     // root pop
 wire [53:0] mg_e = td[TL][0];
 assign tp[TL][0] = mg_go;
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
 always @(posedge clk) if (mg_go) begin of[ow] <= mg_e; of_l[ow] <= r1; end
 // ---------------------------------------------------------------- control
 reg [3:0] sct;
 wire act = beat || f1_v || f2_v;
 // next state of st (same decisions as the sequential case below, which now assigns st <= st_n)
 reg [2:0] st_n;
 always @* begin
  st_n = st;
  if (beat && cursor + in_nw >= n) st_n = FLUSH;
  case (st)
   IDLE: if (cmd_valid && ENABLE && cmd_unit == 9 && cmd_op == 2 && !(cmd_param[24:12] != 0 || cmd_param[11:0] == 0 ||
            cmd_param[11:0] > MAX_K || cmd_param[11:0] > cmd_n || cmd_n == 0 || cmd_n > 1048576 || cmd_m == 0)) st_n = START;
   START: if (r_q && sct >= S_SET) st_n = FILL;
   FILL, FLUSH: begin
    if (f1_nan) st_n = ABORT;
    else if (st == FLUSH && !act && r_q && sct >= S_SET) st_n = EXT;
   end
   EXT: if (r_x) st_n = MERGE;
   MERGE: if (rz && oc == 0) st_n = lr_q ? FIN : START;
   ABORT: if (r_q && sct >= S_SET) st_n = IDLE;
   FIN: st_n = IDLE;
   default: st_n = IDLE;
  endcase
 end
 always @(posedge clk or negedge rn) begin
  if (!rn) begin
   st <= IDLE; pst <= IDLE; done <= 1'b0; error <= 4'd0; n <= 0; m <= 0; k <= 0; row <= 0; cursor <= 0; values_enabled <= 1'b0;
   f1_v <= 1'b0; f2_v <= 1'b0; grp <= 0; clr_go <= 1'b0; emitted <= 0; oc <= 0; ow <= 0; orp <= 0; sct <= 0;
   rem <= 0; rz <= 1'b1; r1 <= 1'b0; lr_q <= 1'b0; mrg_q <= 1'b0; fill_q <= 1'b0;
  end else begin
   lr_q <= row + 1 == m; mrg_q <= st_n == MERGE; fill_q <= st_n == FILL;
   done <= 1'b0; clr_go <= 1'b0; pst <= st;
   sct <= (act || !r_q || pst != st) ? 4'd0 : (sct == 4'd15 ? sct : sct + 4'd1);
   f1_v <= beat;
   if (beat) begin
    f1_nw <= in_nw; f1_g <= grp; grp <= (grp + 1 == G) ? 0 : grp + 1;
    cursor <= cursor + in_nw;
    if (cursor + in_nw >= n) st <= FLUSH;
   end
   f2_v <= f1_v && !f1_nan && (st == FILL || st == FLUSH);
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
    START: if (r_q && sct >= S_SET) begin cursor <= 0; grp <= 0; st <= FILL; end
    FILL, FLUSH: begin
     if (f1_nan) begin error <= 4'd3; done <= 1'b1; st <= ABORT; f1_v <= 1'b0; f2_v <= 1'b0; end
     else if (st == FLUSH && !act && r_q && sct >= S_SET) st <= EXT;
    end
    EXT: if (r_x) begin st <= MERGE; clr_go <= 1'b1; emitted <= 0; rem <= k; rz <= k == 0; r1 <= k == 1; end
    MERGE: if (rz && oc == 0) begin
     if (lr_q) begin st <= FIN; end
     else begin row <= row + 1; st <= START; end
    end
    ABORT: if (r_q && sct >= S_SET) begin clr_go <= 1'b1; st <= IDLE; end
    FIN: begin done <= 1'b1; st <= IDLE; end
    default: st <= IDLE;
   endcase
   // output FIFO
   if (mg_go) begin ow <= ow + 1'b1; emitted <= emitted + 1'b1; rem <= rem - 1'b1; rz <= r1; r1 <= rem == 2; end
   st <= st_n;
   if (o_pop) orp <= orp + 1'b1;
   oc <= oc + mg_go - o_pop;
  end
 end
endmodule


// Registered boundary around the wide engine (the die wrapper ot_hgi_idx_topk_registered, IW scores a beat): command,
// score beat and result are each captured in a flop; a command retires only after its last accepted output.
// r6: the result side is a credit skid (head register q_* drives the pins + 4-entry buffer): the core sees a REGISTERED
// ready (room for one more after this cycle), out_ready only steers the local head load.
module ot_hgi_idx_topk_wreg #(
 parameter bit ENABLE=0, parameter integer MAX_K=2048, parameter integer IW=4, parameter integer W=4,
 parameter integer MUT_BYP=0, parameter bit HUB=0,
 // LANE=1 (with HUB=1; el1011-hbm-idx 10-12 w8 split, textbook class 1: 23.7k cluster flops on one root): the per-lane glue
 // (survivor FIFO, credits, extract counters, reverse buffer, run FIFO, leaf head, heap seam) is the hard lane tile
 // ot_hgi_topk_lane_tile OUTSIDE (lt_* pins); this side keeps relay stage 0, the status / tournament / merge trees and a
 // per-lane merge credit FIFO (the leaf pop loop is cut at a registered credit link)
 parameter bit LANE=0
)(
 input wire clk,rst_n,
 input wire cmd_valid, output wire cmd_ready,
 input wire [3:0] cmd_unit, input wire [5:0] cmd_op,
 input wire [24:0] cmd_param, input wire [31:0] cmd_n,cmd_m,
 input wire cmd_values,
 input wire in_valid, output wire in_ready, input wire [IW*32-1:0] in_score, input wire [$clog2(IW+1)-1:0] in_nw,
 output wire out_valid, input wire out_ready,
 output wire [31:0] out_id,out_score,out_row,
 output wire out_last, output wire out_values_valid, output reg done, output reg [3:0] error,
 output wire [W*$clog2(MAX_K+1)-1:0] t_k, output wire [W-1:0] t_op_v, t_op_ext, t_clr_go, output wire [W*54-1:0] t_op_x,
 input wire [W-1:0] t_op_cr, t_ext_v, t_idle_i, input wire [W*54-1:0] t_ext_d, input wire [W*53-1:0] t_root_key,
 output wire [W*3-1:0] lt_ph, output wire [W*$clog2(MAX_K+1)-1:0] lt_k, output wire [W-1:0] lt_clr, lt_pv, lt_mcr,
 output wire [W*54-1:0] lt_pd,
 input wire [W-1:0] lt_q, lt_x, lt_ok, lt_mv, lt_me, input wire [W*53-1:0] lt_root, input wire [W*54-1:0] lt_md
);
 reg active,c_valid,s_valid,q_valid,pending_done,h_v,o_rdy;   // h_v: a command held at the pin (cmd_ready = !h_v, a flop)
 reg [3:0] c_unit; reg [5:0] c_op; reg [24:0] c_param; reg [31:0] c_n,c_m; reg c_values;
 reg [IW*32-1:0] s_score; reg [$clog2(IW+1)-1:0] s_nw;
 reg [97:0] q_r; reg [97:0] b_r [0:3]; reg [1:0] bw, br; reg [2:0] bn;
 wire core_cmd_ready,core_in_ready,core_out_valid,core_done; wire [3:0] core_error;
 wire [31:0] core_id,core_score,core_row; wire core_last,core_values;
 wire core_out_ready=o_rdy;
 wire [97:0] c_r={core_values,core_last,core_row,core_score,core_id};
 wire push=core_out_valid&&o_rdy, pop=q_valid&&out_ready, q_load=!q_valid||pop;
 wire from_b=q_load&&bn!=3'd0, direct=q_load&&bn==3'd0&&push, to_b=push&&!direct;
 wire [2:0] bn_nx=bn+to_b-from_b;
 wire q_nx=q_load?(bn!=3'd0||push):1'b1;
 assign cmd_ready=!h_v;
 wire go=h_v&&!active&&!c_valid&&core_cmd_ready&&!pending_done&&!q_valid&&bn==3'd0;
 assign in_ready=active&&(!s_valid||core_in_ready);
 assign out_valid=q_valid; assign {out_values_valid,out_last,out_row,out_score,out_id}={q_valid&&q_r[97],q_r[96:0]};
 ot_hgi_idx_topk_hw #(.ENABLE(ENABLE),.MAX_K(MAX_K),.IW(IW),.W(W),.MUT_BYP(MUT_BYP),.HUB(HUB),.LANE(LANE)) core(
  .clk(clk),.rst_n(rst_n),.cmd_valid(c_valid),.cmd_ready(core_cmd_ready),
  .cmd_unit(c_unit),.cmd_op(c_op),.cmd_param(c_param),.cmd_n(c_n),.cmd_m(c_m),.cmd_values(c_values),
  .in_valid(s_valid&&active),.in_ready(core_in_ready),.in_score(s_score),.in_nw(s_nw),
  .out_valid(core_out_valid),.out_ready(core_out_ready),.out_id(core_id),.out_score(core_score),
  .out_row(core_row),.out_last(core_last),.out_values_valid(core_values),.done(core_done),.error(core_error),
  .t_k(t_k),.t_op_v(t_op_v),.t_op_ext(t_op_ext),.t_clr_go(t_clr_go),.t_op_x(t_op_x),.t_op_cr(t_op_cr),.t_ext_v(t_ext_v),
  .t_idle_i(t_idle_i),.t_ext_d(t_ext_d),.t_root_key(t_root_key),
  .lt_ph(lt_ph),.lt_k(lt_k),.lt_clr(lt_clr),.lt_pv(lt_pv),.lt_mcr(lt_mcr),.lt_pd(lt_pd),.lt_q(lt_q),.lt_x(lt_x),.lt_ok(lt_ok),
  .lt_mv(lt_mv),.lt_me(lt_me),.lt_root(lt_root),.lt_md(lt_md));
 always @(posedge clk) begin
  if(cmd_valid&&cmd_ready)begin c_unit<=cmd_unit;c_op<=cmd_op;c_param<=cmd_param;c_n<=cmd_n;c_m<=cmd_m;c_values<=cmd_values;end
  if(in_ready&&in_valid)begin s_score<=in_score;s_nw<=in_nw;end
  if(to_b)b_r[bw]<=c_r;
  if(from_b)q_r<=b_r[br]; else if(direct)q_r<=c_r;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;c_valid<=0;s_valid<=0;q_valid<=0;pending_done<=0;done<=0;error<=0;h_v<=0;o_rdy<=0;bw<=0;br<=0;bn<=0;end
  else begin
   done<=0;
   if(c_valid&&core_cmd_ready)c_valid<=0;
   if(cmd_valid&&cmd_ready)h_v<=1;
   if(go)begin h_v<=0;active<=1;c_valid<=1;error<=0;end
   if(in_ready)s_valid<=in_valid;
   q_valid<=q_nx; bn<=bn_nx; if(to_b)bw<=bw+1'b1; if(from_b)br<=br+1'b1;
   o_rdy<=({2'b00,q_valid}+bn+{2'b00,push})<=3'd2;   // occupancy if nothing pops: out_ready stays out of the credit (pin -> few levels)
   if(core_done)begin pending_done<=1;error<=core_error;end
   if((pending_done||core_done)&&bn==3'd0&&(!q_valid||out_ready))begin done<=1;active<=0;pending_done<=0;c_valid<=0;s_valid<=0;end
  end
 end
endmodule
