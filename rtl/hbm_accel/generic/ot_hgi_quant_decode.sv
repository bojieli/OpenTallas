`timescale 1ns/1ps
// HGI-1 approved G8; arithmetic modules are reused byte-identically.
// Record dispatcher supplies one complete 32-FP32 beat. No output backpressure.
// generic_enable=0 preserves the DS margin core and legacy_fp4 selection.
// BQSPLIT=1 (hgi-1010/idleB, opt-in): the E4M3 path's S5 code stage is split in two (ot_hgi_fp4qdq SPLIT5) and the
// alignment pipe is one stage shorter, so the decode latency and every output are unchanged.
// HOLDLINE=n (opt-in): the three wide delay lines (aq x line, bq x line, the alignment value pipe; ~26k flop -> flop
// hops, the 24k hold endpoints of route f589c9afa) carry n retained BUFx2 per stage.
module ot_hgi_quant_decode #(parameter integer MUTANT=0, BQSPLIT=0, HOLDLINE=0)(
 input wire clk,rst_n,v,generic_enable,legacy_fp4,
 input wire [127:0] header,input wire [1023:0] x,
 output wire vo,output wire [511:0] y,output wire fault,
 output reg decode_fault);
 wire [3:0] unit_code=header[127:124];
 wire [5:0] op=header[123:118];
 wire e4=generic_enable && op==6;
 wire legal=(unit_code==4) && (op==4 || op==5 || (op==6 && header[71:64]==16));
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) decode_fault<=0; else decode_fault<=v && generic_enable && !legal;
 end
 wire take=v && (!generic_enable || legal);
 wire fp4=generic_enable ? ((op==5) ^ (MUTANT==1)) : legacy_fp4;
 wire av,af,bv,bf; wire [511:0] ay,by;wire [255:0] q;wire signed [9:0] exponent;
 ot_hfd_actquant_m #(.MR(1),.MLAT(6),.HOLDLINE(HOLDLINE)) aq(
 .clk(clk),.rst_n(rst_n),.v(take && !e4),.fp4(fp4),.x(x),
 .vo(av),.q(q),.e(exponent),.y(ay),.fault(af));
 ot_hgi_fp4qdq #(.SPLIT5(BQSPLIT),.HOLDLINE(HOLDLINE)) bq(.clk(clk),.rst_n(rst_n),.v(take && e4),.x(x),.vo(bv),.y(by),.fault(bf));
 localparam integer VP=15-(BQSPLIT!=0);
 reg [VP-1:0] valid_pipe,fault_pipe;
 wire [511:0] vp_q; integer i;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin valid_pipe<=0; fault_pipe<=0; end
  else begin valid_pipe<={valid_pipe[VP-2:0],bv}; fault_pipe<={fault_pipe[VP-2:0],bf}; end
 end
 generate if(HOLDLINE!=0) begin : g_vph
  ot_s81_head_min_delay #(.W(512),.D(VP),.ENABLE(1),.DEPTH(HOLDLINE)) u_vp(.clk(clk),.rst_n(rst_n),.d(by),.q(vp_q));
 end else begin : g_vp
  reg [511:0] value_pipe[0:VP-1];
  always @(posedge clk) begin
   value_pipe[0]<=by;
   for(i=1;i<VP;i=i+1)value_pipe[i]<=value_pipe[i-1];
  end
  assign vp_q=value_pipe[VP-1];
 end endgenerate
 assign vo=av|valid_pipe[VP-1];
 assign y=valid_pipe[VP-1] ? vp_q : ay;
 assign fault=vo && (valid_pipe[VP-1] ? fault_pipe[VP-1] : af);
endmodule
