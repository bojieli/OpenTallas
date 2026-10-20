`timescale 1ns/1ps
// Full chunk: five stationary banks x eight BF16 weights, selected by real
// per-row bank; six SRAM skew rings; native mul7 + golden left-fold add5.
// All external data/control pins capture once before work. Total43 captures
// (input1 + product7 + fold35), II1; one more than selected-input core42.
module ot_s81svc7_chunk(
 input wire clk,rst_n,iv,input wire[143:0]b,input wire[2:0]bank,
 input wire[7:0]we,input wire[2:0]wbank,input wire[127:0]wd,
 output wire ov,output wire[31:0]y,output wire[2:0]fault_parts
);
 (* keep *)reg[143:0]b_pin;
 (* keep *)reg[2:0]bank_pin,wbank_pin;
 (* keep *)reg[7:0]we_pin;
 (* keep *)reg[127:0]wd_pin;
 (* keep *)reg iv_pin,load_reset0;
 (* keep *)reg[3:0]load_run;
 always @(posedge clk)begin
  b_pin<=b;bank_pin<=bank;wbank_pin<=wbank;we_pin<=we;wd_pin<=wd;iv_pin<=iv;
  load_reset0<=rst_n;load_run<={4{load_reset0}};
 end
 wire[143:0]sk_b;wire[23:0]sk_bank;
 wire[127:0]a;
 genvar k;
 generate for(k=0;k<8;k=k+1)begin:g_lane
  if(k<2)begin:g_zero
   assign sk_b[k*18+:18]=b_pin[k*18+:18];
   assign sk_bank[k*3+:3]=bank_pin;
  end else begin:g_ring
   wire valid_ignored;
   ot_s81svc7_skew_sram #(.W(21),.D(5*(k-1)))u_skew(.clk(clk),.rst_n(rst_n),
    .iv(iv_pin),.i({bank_pin,b_pin[k*18+:18]}),.ov(valid_ignored),
    .o({sk_bank[k*3+:3],sk_b[k*18+:18]}));
  end
  // 80bits/lane, 640bits/chunk: below the2kb SRAM threshold.
  reg[79:0]weights;
  integer j;
  always @(posedge clk)for(j=0;j<5;j=j+1)
   if(load_run[k/2]&&we_pin[k]&&wbank_pin==j)weights[j*16+:16]<=wd_pin[k*16+:16];
  assign a[k*16+:16]=weights[sk_bank[k*3+:3]*16+:16];
 end endgenerate
 ot_s81svc7_chunk_core u_core(.clk(clk),.rst_n(rst_n),.iv(iv_pin),.a(a),.b(sk_b),
  .ov(ov),.y(y),.fault_parts(fault_parts));
endmodule
