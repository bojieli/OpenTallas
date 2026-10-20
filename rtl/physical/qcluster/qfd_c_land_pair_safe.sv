`timescale 1ns/1ps
`default_nettype none
// Opt-in full-shape combined half-ring: one source-root writer and destination-root reader.
// The 4xW bank is internal; W257/258 represents one REAL half of a514/516-bit crossing.
// Source-model candidate only: synth/native32 and physical linked-root proof precede any gate.
module qfd_c_land_pair_safe #(parameter integer W=258, parameter integer K=2, parameter integer G=15)(
 input wire ck_w,ck_r,rst_w,rst_r,input wire[W-1:0]i,output wire[W-1:0]o);
 localparam integer NG=(W+G-1)/G;
 localparam integer NR=(NG+5)/6;
 wire[NR-1:0]rw0;
 (* keep=1 *)reg rr0;
 genvar root;
 generate for(root=0;root<NR;root=root+1)begin:g_rst_root
  qfd_c_pair_reset_copy #(.ID(root))u(.ck(ck_w),.d(rst_w),.q(rw0[root]));
 end endgenerate
 always @(posedge ck_r)rr0<=rst_r;
 genvar g;
 generate for(g=0;g<(W+G-1)/G;g=g+1)begin:g_slice
  localparam integer N=(W-g*G<G)?W-g*G:G;
  wire[4*N-1:0]bank; wire[3:0]vld;
  qfd_c_pair_w_slice #(.W(N))u_w(.ck(ck_w),.rsi(rw0[g/6]),.i(i[g*G+:N]),.bank(bank),.vld(vld));
  qfd_c_land_safe_r_slice #(.W(N),.K(K))u_r(.ck(ck_r),.rsi(rr0),.bank(bank),.vld(vld),.o(o[g*G+:N]));
 end endgenerate
`ifndef SYNTHESIS
 initial if(W<257 || W>258 || G>15 || G<1 || K<1 || K>3)$fatal(1,"invalid combined half-ring shape");
`endif
endmodule
// Five same-edge reset copies: one for slot/valid state and one per physical bank.
// A first-stage region copy above drives at most6groups x5 second-stage FFs=30.
(* keep_hierarchy=1 *)
module qfd_c_pair_reset_copy #(parameter integer ID=0)(input wire ck,d,output reg q);
 (* keep=1 *)wire source_reset=d;
 always @(posedge ck)q<=source_reset;
 wire unused_id=ID[0];
endmodule

(* keep_hierarchy=1 *)
module qfd_c_pair_w_slice #(parameter integer W=15)(
 input wire ck,rsi,input wire[W-1:0]i,output wire[4*W-1:0]bank,output wire[3:0]vld);
 wire ctrl;
 qfd_c_pair_reset_copy #(.ID(4))rc(.ck(ck),.d(rsi),.q(ctrl));
 (* keep=1 *)reg[3:0]sel,v;
 always @(posedge ck)
  if(!ctrl)begin sel<=4'b0001;v<=0;end
  else begin sel<={sel[2:0],sel[3]};v<=v|sel;end
 genvar s;
 generate for(s=0;s<4;s=s+1)begin:g_bank
  wire active;
  qfd_c_pair_reset_copy #(.ID(s))rc(.ck(ck),.d(rsi),.q(active));
  reg[W-1:0]b;
  always @(posedge ck)if(active && sel[s])b<=i;
  assign bank[s*W+:W]=b;
 end endgenerate
 assign vld=v;
endmodule
`default_nettype wire
