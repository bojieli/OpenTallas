`timescale 1ns/1ps
// RST-FAN-1 (HEAD-CROSSING-1119): ot_rst_relay_tree3 with ROOT COPIES and EXPLICIT GROUPS, same 3-edge release.
// The root, group and local flops release on edges 1/2/3 after rst_n_in exactly as ot_rst_relay_tree3 (every output
// of both modules is the same function of rst_n_in and clk, cycle for cycle: tb_rst_fan checks it), but
//   * ROOTS kept root copies (g_root[r].root_r), each driving only the groups mapped to it, and
//   * GROUPS groups of contiguous local indices with free boundaries: group g = locals [GS[g], GS[g+1]) (GS[GROUPS] =
//     REGIONS), so a group can end where the local index space jumps across the die (tree3's fixed 32-local blocks
//     put locals 1300 um apart under one group_r on hd_lep0N),
// so the root -> group and group -> local hops can each be sited inside the 405 um register reach.  0 added cycles.
//   GS[16*g+:16] = first local of group g (GS[0] = 0, strictly ascending, each group 1..32 locals)
//   RM[4*g+:4]   = root copy of group g (< ROOTS)
// Async assertion cascades through reset pins; D = 1 on every flop; every flop kept (copies are logically identical).
module ot_rst_relay_tree3m #(parameter integer REGIONS = 32, parameter integer GROUPS = 1, parameter integer ROOTS = 1,
                             parameter [16*GROUPS-1:0] GS = {(16*GROUPS){1'b0}},
                             parameter [4*GROUPS-1:0] RM = {(4*GROUPS){1'b0}})(
 input wire clk, rst_n_in, output wire [REGIONS-1:0] rst_n);
 function integer grp_of(input integer l);
  integer g;
  begin
   grp_of = 0;
   for (g = 0; g < GROUPS; g = g + 1) if (GS[16*g+:16] <= l) grp_of = g;
  end
 endfunction
 wire [ROOTS-1:0] root_q;
 wire [GROUPS-1:0] group_q;
 genvar r, g, l;
 generate for (r = 0; r < ROOTS; r = r + 1) begin : g_root
     (* keep="true",dont_touch="true",async_reg="true" *) reg root_r;
     assign root_q[r] = root_r;
     always @(posedge clk or negedge rst_n_in)
         if (!rst_n_in) root_r <= 1'b0; else root_r <= 1'b1;
 end
 for (g = 0; g < GROUPS; g = g + 1) begin : g_group
     localparam integer R = RM[4*g+:4];
     (* keep="true",dont_touch="true",async_reg="true" *) reg group_r;
     assign group_q[g] = group_r;
     always @(posedge clk or negedge root_q[R])
         if (!root_q[R]) group_r <= 1'b0; else group_r <= 1'b1;
 end
 for (l = 0; l < REGIONS; l = l + 1) begin : g_local
     localparam integer G = grp_of(l);
     (* keep="true",dont_touch="true" *) reg local_r;
     assign rst_n[l] = local_r;
     always @(posedge clk or negedge group_q[G])
         if (!group_q[G]) local_r <= 1'b0; else local_r <= 1'b1;
 end endgenerate
`ifndef SYNTHESIS
 integer i, n;
 initial begin
  if (GS[15:0] != 0) $fatal(1, "ot_rst_relay_tree3m: GS[0] must be 0");
  for (i = 0; i < GROUPS; i = i + 1) begin
   n = ((i + 1 < GROUPS) ? GS[16*(i+1)+:16] : REGIONS) - GS[16*i+:16];
   if (n < 1 || n > 32) $fatal(1, "ot_rst_relay_tree3m: group %0d holds %0d locals (1..32)", i, n);
   if (RM[4*i+:4] >= ROOTS) $fatal(1, "ot_rst_relay_tree3m: RM[%0d] >= ROOTS", i);
  end
  for (i = 0; i < ROOTS; i = i + 1) begin
   n = 0;
   for (int k = 0; k < GROUPS; k = k + 1) if (RM[4*k+:4] == i) n = n + 1;
   if (n < 1 || n > 48) $fatal(1, "ot_rst_relay_tree3m: root %0d drives %0d groups (1..48)", i, n);
  end
 end
`endif
endmodule
