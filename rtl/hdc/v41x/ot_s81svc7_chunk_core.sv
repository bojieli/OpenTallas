`timescale 1ns/1ps
// Selected/staggered BF16 operands -> exact eight-product left fold.
// This internal core does not own stationary weights or dequantization/skew.
// Native mul7 + seven native add5 =42 captures, II1. The enclosing group
// must respect its existing configuration/reset warm protocol before iv.
module ot_s81svc7_chunk_core(
 input wire clk,rst_n,iv,input wire[127:0]a,input wire[143:0]b,
 output wire ov,output wire[31:0]y,output wire[2:0]fault_parts
);
 wire[255:0]products;wire[7:0]mf,df;
 (* keep *)reg[7:0]dq_pin,pad_pin;
 (* keep *)reg iv_pin;
 genvar k;
 generate for(k=0;k<8;k=k+1)begin:g_mul
  ot_s81svc7_bmul_native u_mul(.clk(clk),.rst_n(rst_n),.a(a[k*16+:16]),
   .b(b[k*18+:16]),.pad(b[k*18+17]),.y(products[k*32+:32]),.flt(mf[k]));
  // Fault and pad pins capture before any metadata logic.
  always @(posedge clk)begin dq_pin[k]<=b[k*18+16];pad_pin[k]<=b[k*18+17];end
 end endgenerate
 always @(posedge clk)iv_pin<=iv;
 wire product_v;
 // Eight dq-fault histories and the real row-valid share one SRAM word.
 // Input-pin1 + SRAM6 matches the native product's seven data captures.
 ot_s81svc7_skew_sram #(.W(8),.D(6))u_dqfault(.clk(clk),.rst_n(rst_n),
  .iv(iv_pin),.i(dq_pin&~pad_pin),.ov(product_v),.o(df));
 wire[7:0]product_fault;
`ifdef SVC7_CORE_MUT_DQ
 assign product_fault=mf;
`else
 assign product_fault=mf|df;
`endif
 ot_s81svc7_chunk_reduce u_reduce(.clk(clk),.rst_n(rst_n),.iv(product_v),
  .p(products),.pf(product_fault),.ov(ov),.y(y),.fault_parts(fault_parts));
endmodule
