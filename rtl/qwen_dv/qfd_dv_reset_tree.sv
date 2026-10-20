`timescale 1ns/1ps
// Existing two-stage face synchronizer feeds a kept 32-ary registered tree.
// Clocks run throughout reset. Every node drives <=32 D pins; every data
// leaf is assigned <=32 reset pins by reset_partition.py. Equal depth at all
// leaves: two extra reset-release edges, zero steady-state data edges.
module qfd_dv_reset_tree #(parameter integer N=32) (
 input wire ck,rst_n,output wire[N-1:0] q
);
 localparam integer B=(N+31)/32;
 wire[B-1:0] branch;
 genvar b,i;
 generate for(b=0;b<B;b=b+1) begin:g_branch
  (* keep_hierarchy="yes" *) qfd_dv_reset_copy #(.ID(b)) u_b(.ck(ck),.d(rst_n),.q(branch[b]));
 end
 for(i=0;i<N;i=i+1) begin:g_leaf
  (* keep_hierarchy="yes" *) qfd_dv_reset_copy #(.ID(1024+i)) u_l(.ck(ck),.d(branch[i/32]),.q(q[i]));
 end endgenerate
`ifndef SYNTHESIS
 initial if(N<1||N>1024) $fatal(1,"RESET_TREE_SIZE");
`endif
endmodule
(* keep_hierarchy="yes" *)
module qfd_dv_reset_copy #(parameter integer ID=0)(input wire ck,d,output reg q);
 always @(posedge ck) q<=d;
endmodule
