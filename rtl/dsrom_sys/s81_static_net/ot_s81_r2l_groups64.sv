`timescale 1ns/1ps
`default_nettype none
// Local 64-bit payload/phase banks eliminate one half-cycle marker driving all 4k bank FF.
// The final payload register is the old wrapper's output pin register: zero added edges.
module ot_s81_r2l_slice64 #(parameter integer MUT=0)(
 input wire ck,fi,rs,input wire [65:0] di,
 output reg [63:0] data,output wire raw_valid,raw_live,raw_fault);
 reg [1:0] reset_q;
 always @(posedge ck or negedge rs)if(!rs)reset_q<=0;else reset_q<={reset_q[0],1'b1};
 reg [65:0] capture_q;
 always @(negedge fi)capture_q<=di;
 wire [64:0] word;
 ot_s81_static_ratio_cross #(.W(65),.NS(4),.ND(3),.VBIT(0),.MUT(MUT)) engine(
  .w_ck(fi),.w_rst_n(capture_q[0]),.i(capture_q[65:1]),
  .r_ck(ck),.r_rst_n(reset_q[1]),.o(word),.o_live(raw_live),.fault(raw_fault));
 assign raw_valid=word[0];
 always @(posedge ck)data<=word[64:1];
endmodule

// One actual status leaf performs the original final status register, including consensus fault checks.
module ot_s81_r2l_join8(input wire ck,input wire [7:0] valid_i,live_i,fault_i,
 output reg valid_o,live_o,fault_o);
 always @(posedge ck)begin
  valid_o<=(&valid_i)&&(&live_i);
  live_o<=&live_i;
  fault_o<=(|fault_i)||((|live_i)&&!(&live_i))||((|valid_i)&&!(&valid_i));
 end
endmodule

// 17 independent phase-compensated clock entries, delivered to actual leaves by the die.
// ck[0..7] slice read entries; ck[8] status entry; fi[0..7] forwarded source entries.
module dsfd_r2l_groups64 #(parameter integer MUT=0)(
 input wire [8:0] ck,input wire [7:0] fi,input wire [0:0] rs,
 input wire [513:0] di0,output wire [514:0] o);
 wire [7:0] v,l,f;
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:group
  ot_s81_r2l_slice64 #(.MUT((MUT==1 && g==7)?1:0)) u(
   .ck(ck[g]),.fi(fi[g]),.rs(rs[0]),.di({di0[2+64*g+:64],di0[1:0]}),
   .data(o[1+64*g+:64]),.raw_valid(v[g]),.raw_live(l[g]),.raw_fault(f[g]));
 end endgenerate
 ot_s81_r2l_join8 status(.ck(ck[8]),.valid_i(v),.live_i(l),.fault_i(f),
  .valid_o(o[0]),.live_o(o[513]),.fault_o(o[514]));
endmodule
`default_nettype wire
