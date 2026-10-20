`timescale 1ns/1ps
`default_nettype none
// Full real257/258 half of514/516crossing. Keep complete15bit bank+read selection together.
// SameD4/K2/staticepochs/tworesetedges as paired candidate; physical strip contracts change no state.
module qfd_c_land_pair_strip #(parameter integer W=258,K=2,G=15)(
 input wire ck_w,ck_r,rst_w,rst_r,input wire[W-1:0]i,output wire[W-1:0]o);
 localparam integer NG=(W+G-1)/G,NR=(NG+5)/6;
 wire[NR-1:0]rw0;(* keep=1 *)reg rr0;
 genvar root,g;
 generate for(root=0;root<NR;root=root+1)begin:g_rst_root
  qfd_c_pair_reset_copy #(.ID(root))u(.ck(ck_w),.d(rst_w),.q(rw0[root]));
 end endgenerate
 always @(posedge ck_r)rr0<=rst_r;
 generate for(g=0;g<NG;g=g+1)begin:g_slice
  localparam integer N=(W-g*G<G)?W-g*G:G;
  qfd_c_pair_slice_strip #(.W(N),.K(K))u_pair(.ck_w(ck_w),.ck_r(ck_r),.rst_w(rw0[g/6]),.rst_r(rr0),.i(i[g*G+:N]),.o(o[g*G+:N]));
 end endgenerate
`ifndef SYNTHESIS
 initial if(W<257 || W>258 || G!=15 || K<1 || K>3)$fatal(1,"invalid production strip shape");
`endif
endmodule
(* keep_hierarchy=1 *)
module qfd_c_pair_slice_strip #(parameter integer W=15,K=2)(
 input wire ck_w,ck_r,rst_w,rst_r,input wire[W-1:0]i,output wire[W-1:0]o);
 wire[4*W-1:0]bank;wire[3:0]vld;
 qfd_c_pair_w_slice #(.W(W))u_w(.ck(ck_w),.rsi(rst_w),.i(i),.bank(bank),.vld(vld));
 qfd_c_land_safe_r_slice #(.W(W),.K(K))u_r(.ck(ck_r),.rsi(rst_r),.bank(bank),.vld(vld),.o(o));
endmodule
`default_nettype wire
