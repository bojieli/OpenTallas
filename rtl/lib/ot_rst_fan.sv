`timescale 1ns/1ps
// RST-FAN-1 (HEAD-CROSSING-1119, COORD ruling on hd_lep0N u_rrl_657: 157 reset loads over 992 um from one relay):
// equal-depth reset fan with explicit leaves.  Die-agnostic: one async-assert / synchronous-release relay net is split
// into a tree of kept copy flops so that every flop drives a small, local set of reset pins (each hop <= the 405 um
// register reach when the copies are sited on their children), and EVERY leaf releases on the same clock edge.
//
//   LEVELS 1: rst_n_in -> leaf[LEAVES]                                                    release = rst_n_in + 1 edge
//   LEVELS 2: rst_n_in -> root -> leaf[LEAVES]                                                      + 2 edges
//   LEVELS 3: rst_n_in -> root -> n1[N1] -> leaf[LEAVES]                                            + 3 edges
//   LEVELS 4: rst_n_in -> root -> n1[N1] -> n2[N2] -> leaf[LEAVES]                                  + 4 edges
//   LEVELS 5: rst_n_in -> root -> n1[N1] -> n2[N2] -> n3[N3] -> leaf[LEAVES]                        + 5 edges
//            (RST-FAN-1d: COORD 300 um hop cap on hd_lep0N; 4 hops of 300 um from one root cannot span its leaves)
// Assertion is asynchronous through every level (each flop's reset pin is its parent's Q, so rst_n_in low clears the
// whole tree within one propagation, no clock needed); release is synchronous, one edge per level, so the depth D =
// LEVELS is uniform for every leaf (no leaf can release on another edge: all paths have the same register count).
// D = 1 on every flop (no wide D broadcast); every flop is kept so synthesis cannot merge the copies (they are
// logically identical: same D, same reset), exactly as ot_rst_relay_tree3.
//
// Parent maps (8 bits per entry; MAPX 0 = proportional default, MAPX 1 = the explicit maps below):
//   PL[8*l+:8] = parent of leaf l (an n3 index at LEVELS 5, an n2 index at LEVELS 4, an n1 index at LEVELS 3)
//   PM[8*j+:8] = parent n1 of n2 node j (LEVELS >= 4)
//   PQ[8*m+:8] = parent n2 of n3 node m (LEVELS 5 only)
// Placement: the kit / plan relay_sites site each copy (g_n1[k].n1_r, g_n2[j].n2_r, g_leaf[l].leaf_r, root_r) on its
// children; the maps only decide which copy feeds which child.
module ot_rst_fan #(
  parameter integer LEAVES = 1,
  parameter integer LEVELS = 4,
  parameter integer N1 = 1,
  parameter integer N2 = 1,
  parameter integer N3 = 1,
  parameter integer MAPX = 0,
  parameter [8*LEAVES-1:0] PL = {(8*LEAVES){1'b0}},
  parameter [8*N2-1:0] PM = {(8*N2){1'b0}},
  parameter [8*N3-1:0] PQ = {(8*N3){1'b0}}
)(
  input  wire              clk,
  input  wire              rst_n_in,
  output wire [LEAVES-1:0] rst_n
);
  localparam integer NP = (LEVELS >= 5) ? N3 : (LEVELS >= 4) ? N2 : N1;   // number of leaf parents at LEVELS 3 / 4 / 5
  wire root_q;
  wire [N1-1:0] n1_q;
  wire [N2-1:0] n2_q;
  wire [N3-1:0] n3_q;
  genvar k, j, m, l;
  generate
    if (LEVELS >= 2) begin : g_root
      (* keep="true",dont_touch="true",async_reg="true" *) reg root_r;
      always @(posedge clk or negedge rst_n_in)
        if (!rst_n_in) root_r <= 1'b0; else root_r <= 1'b1;
      assign root_q = root_r;
    end else begin : g_noroot
      assign root_q = rst_n_in;
    end
    if (LEVELS >= 3) begin : g_l1
      for (k = 0; k < N1; k = k + 1) begin : g_n1
        (* keep="true",dont_touch="true" *) reg n1_r;
        always @(posedge clk or negedge root_q)
          if (!root_q) n1_r <= 1'b0; else n1_r <= 1'b1;
        assign n1_q[k] = n1_r;
      end
    end else begin : g_nol1
      assign n1_q = {N1{root_q}};
    end
    if (LEVELS >= 4) begin : g_l2
      for (j = 0; j < N2; j = j + 1) begin : g_n2
        localparam integer P = (MAPX != 0) ? PM[8*j+:8] : (j * N1) / N2;
        (* keep="true",dont_touch="true" *) reg n2_r;
        always @(posedge clk or negedge n1_q[P])
          if (!n1_q[P]) n2_r <= 1'b0; else n2_r <= 1'b1;
        assign n2_q[j] = n2_r;
      end
    end else begin : g_nol2
      assign n2_q = {N2{root_q}};
    end
    if (LEVELS >= 5) begin : g_l3
      for (m = 0; m < N3; m = m + 1) begin : g_n3
        localparam integer P = (MAPX != 0) ? PQ[8*m+:8] : (m * N2) / N3;
        (* keep="true",dont_touch="true" *) reg n3_r;
        always @(posedge clk or negedge n2_q[P])
          if (!n2_q[P]) n3_r <= 1'b0; else n3_r <= 1'b1;
        assign n3_q[m] = n3_r;
      end
    end else begin : g_nol3
      assign n3_q = {N3{root_q}};
    end
    for (l = 0; l < LEAVES; l = l + 1) begin : g_leaf
      localparam integer P = (LEVELS < 3) ? 0 : (MAPX != 0) ? PL[8*l+:8] : (l * NP) / LEAVES;
      wire pr;
`ifdef OT_RST_FAN_MUT_SKEW
      if (l == 0) begin : g_mut assign pr = rst_n_in; end else      // MUTANT: leaf 0 skips its parents
`endif
      if (LEVELS >= 5) begin : g_p3 assign pr = n3_q[P]; end
      else if (LEVELS == 4) begin : g_p2 assign pr = n2_q[P]; end
      else if (LEVELS == 3) begin : g_p1 assign pr = n1_q[P]; end
      else begin : g_p0 assign pr = root_q; end
      (* keep="true",dont_touch="true" *) reg leaf_r;
      always @(posedge clk or negedge pr)
        if (!pr) leaf_r <= 1'b0; else leaf_r <= 1'b1;
      assign rst_n[l] = leaf_r;
    end
  endgenerate
`ifndef SYNTHESIS
  integer i;
  initial begin
    if (LEVELS < 1 || LEVELS > 5) $fatal(1, "ot_rst_fan: LEVELS must be 1..5");
    if (LEAVES < 1 || N1 < 1 || N2 < 1 || N3 < 1 || N1 > 255 || N2 > 255 || N3 > 255) $fatal(1, "ot_rst_fan: bad copy counts");
    if (MAPX != 0) begin
      for (i = 0; i < LEAVES; i = i + 1) if (LEVELS >= 3 && PL[8*i+:8] >= NP) $fatal(1, "ot_rst_fan: PL[%0d] out of range", i);
      for (i = 0; i < N2; i = i + 1) if (LEVELS >= 4 && PM[8*i+:8] >= N1) $fatal(1, "ot_rst_fan: PM[%0d] out of range", i);
      for (i = 0; i < N3; i = i + 1) if (LEVELS >= 5 && PQ[8*i+:8] >= N2) $fatal(1, "ot_rst_fan: PQ[%0d] out of range", i);
    end
  end
`endif
endmodule
