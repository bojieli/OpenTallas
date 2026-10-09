`timescale 1ns/1ps
// HGI-1 approved G8; arithmetic modules are reused byte-identically.
// Record dispatcher supplies one complete 32-FP32 beat. No output backpressure.
// generic_enable=0 preserves the DS margin core and legacy_fp4 selection.
module ot_hgi_quant_decode #(parameter integer MUTANT=0)(
 input wire clk,rst_n,v,generic_enable,legacy_fp4,
 input wire [127:0] header,input wire [1023:0] x,
 output wire vo,output wire [511:0] y,output wire fault,
 output wire decode_fault);
 wire [3:0] unit_code=header[127:124];
 wire [5:0] op=header[123:118];
 wire e4=generic_enable && op==6;
 wire legal=(unit_code==4) && (op==4 || op==5 || (op==6 && header[71:64]==16));
 assign decode_fault=v && generic_enable && !legal;
 wire take=v && (!generic_enable || legal);
 wire fp4=generic_enable ? ((op==5) ^ (MUTANT==1)) : legacy_fp4;
 wire av,af,bv,bf; wire [511:0] ay,by;wire [255:0] q;wire signed [9:0] exponent;
 ot_hfd_actquant_m #(.MR(1),.MLAT(6)) aq(
 .clk(clk),.rst_n(rst_n),.v(take && !e4),.fp4(fp4),.x(x),
 .vo(av),.q(q),.e(exponent),.y(ay),.fault(af));
 ot_hgi_fp4qdq bq(.clk(clk),.rst_n(rst_n),.v(take && e4),.x(x),.vo(bv),.y(by),.fault(bf));
 reg [14:0] valid_pipe,fault_pipe;
 reg [511:0] value_pipe[0:14]; integer i;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin valid_pipe<=0; fault_pipe<=0; end
  else begin valid_pipe<={valid_pipe[13:0],bv}; fault_pipe<={fault_pipe[13:0],bf}; end
 end
 always @(posedge clk) begin
  value_pipe[0]<=by;
  for(i=1;i<15;i=i+1)value_pipe[i]<=value_pipe[i-1];
 end
 assign vo=av|valid_pipe[14];
 assign y=valid_pipe[14] ? value_pipe[14] : ay;
 assign fault=vo && (valid_pipe[14] ? fault_pipe[14] : af);
endmodule
