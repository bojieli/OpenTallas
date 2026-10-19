`timescale 1ns/1ps
// Balanced synchronous-release reset tree. The root, group and local flops
// release on edges1/2/3, exactly the existing SYNC_STAGES2+TREE_STAGES1 contract.
// Async assertion cascades through reset pins; constant D=1 means each group
// drives only <=32 reset pins, without a matching wide D broadcast.
module ot_rst_relay_tree3 #(parameter integer REGIONS=32, parameter integer LEAVES=32,
                           parameter integer GROUPS=(REGIONS+LEAVES-1)/LEAVES)(
 input wire clk, rst_n_in, output wire [REGIONS-1:0] rst_n);
 (* keep="true",dont_touch="true",async_reg="true" *) reg root_r;
 wire [GROUPS-1:0] group_q;
 always @(posedge clk or negedge rst_n_in)
     if(!rst_n_in) root_r<=1'b0; else root_r<=1'b1;
 genvar g,l;
 generate for(g=0;g<GROUPS;g=g+1) begin:g_group
     (* keep="true",dont_touch="true",async_reg="true" *) reg group_r;
     assign group_q[g]=group_r;
     always @(posedge clk or negedge root_r)
         if(!root_r) group_r<=1'b0; else group_r<=1'b1;
 end
 for(l=0;l<REGIONS;l=l+1) begin:g_local
     (* keep="true",dont_touch="true" *) reg local_r;
     assign rst_n[l]=local_r;
     always @(posedge clk or negedge group_q[l/LEAVES])
         if(!group_q[l/LEAVES]) local_r<=1'b0; else local_r<=1'b1;
 end endgenerate
`ifndef SYNTHESIS
 initial if(GROUPS>32 || LEAVES>32) $fatal(1,"reset fanout requires another explicitly priced tree shape");
`endif
endmodule
