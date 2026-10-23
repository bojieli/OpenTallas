`timescale 1ns/1ps
// Cascaded asynchronous assertion, synchronous release at the same third edge
// as fault1's two synchronizer stages plus region register. No boot edge added.
(* keep_hierarchy="yes" *) module qfd_sysface_release_bit #(parameter integer ID=0)(input wire ck,rst_n,output reg q);
 always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=1;
endmodule
module qfd_sysface_reset_same3 #(parameter integer LEAVES=38,GROUPS=(LEAVES+31)/32)(
 input wire ck,rst_n,output wire[LEAVES-1:0]leaf_n
);
 wire s0;wire[GROUPS-1:0]s1;
 qfd_sysface_release_bit #(.ID(0)) u_s0(.ck(ck),.rst_n(rst_n),.q(s0));
 for(genvar g=0;g<GROUPS;g=g+1)begin:g_s1
  qfd_sysface_release_bit #(.ID(1+g)) u_s1(.ck(ck),.rst_n(s0),.q(s1[g]));
 end
 for(genvar n=0;n<LEAVES;n=n+1)begin:g_leaf
  qfd_sysface_release_bit #(.ID(1024+n)) u_leaf(.ck(ck),.rst_n(s1[n/32]),.q(leaf_n[n]));
 end
endmodule
