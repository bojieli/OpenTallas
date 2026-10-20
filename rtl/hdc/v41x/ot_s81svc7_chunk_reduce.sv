`timescale 1ns/1ps
// Internal reduction leaf: eight already staggered FP32 product streams.
// Preserve the original left fold exactly. Each add is golden add4+inputpin1.
// Operand arrivals: lanes0/1 at0, lanei>=2 at5*(i-1). Output latency35.
// Output fault_parts are REGISTERED fields; enclosing head ORs these at its
// next registered arithmetic/egress boundary. No combinational output pin.
module ot_s81svc7_chunk_reduce(
 input wire clk,rst_n,iv,input wire[255:0]p,input wire[7:0]pf,
 output wire ov,output wire[31:0]y,output wire[2:0]fault_parts
);
 wire[255:0]acc;wire[7:0]av,af;
 wire[13:0]errors;wire[6:0]carry_fault;
 (* keep *)reg[6:0]left_pin,right_pin,valid_pin;
 wire[13:0]metadata;wire any_valid;
 // All seven fault/valid histories have the SAME four-edge offset. Pack
 // them in one word: one read/write port carries every stage each cycle.
 ot_s81svc7_skew_sram #(.W(14),.D(4))u_faults(.clk(clk),.rst_n(rst_n),
  .iv(|valid_pin),.i({valid_pin,left_pin|right_pin}),.ov(any_valid),.o(metadata));
 assign acc[31:0]=p[31:0];assign av[0]=iv;assign af[0]=pf[0];
 genvar k;
 generate for(k=1;k<8;k=k+1)begin:g_fold
  wire[1:0]err;
  ot_s81svc7_add_native u_add(.clk(clk),.rst_n(rst_n),.valid_in(av[k-1]),
    .a(acc[(k-1)*32+:32]),.b(p[k*32+:32]),.y(acc[k*32+:32]),
    .err(err),.valid_out(av[k]));
  // Real metadata input-pin capture, then four SRAM captures: total5.
  // The pure golden bench reference uses a five-edge FF history instead.
  always @(posedge clk)begin
   left_pin[k-1]<=af[k-1];right_pin[k-1]<=pf[k];valid_pin[k-1]<=av[k-1];
  end
  wire fd=metadata[k-1],fdv=metadata[7+k-1];
  assign carry_fault[k-1]=fd;
  assign errors[(k-1)*2+:2]=err;
  assign af[k]=(av[k]&&(|err))|(fdv&&fd);
 end endgenerate
 assign y=acc[255:224];assign ov=av[7];
 `ifdef SVC7_CHUNK_MUT_FAULT
 assign fault_parts={1'b0,errors[13:12]};
`else
 assign fault_parts={carry_fault[6],errors[13:12]};
`endif
endmodule
