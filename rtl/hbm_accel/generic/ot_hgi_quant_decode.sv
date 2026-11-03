`timescale 1ns/1ps
// HGI-1 approved G8; arithmetic modules are reused byte-identically.
// Record dispatcher supplies one complete 32-FP32 beat. No output backpressure.
// generic_enable=0 preserves the DS margin core and legacy_fp4 selection.
module ot_hgi_quant_decode #(parameter integer MUTANT=0,
 // el1011-hbm-fq/qvm: 0 = the alignment delay lines; K > 0 = K-slot lane rings (legal only when v is high at most once
 // every I edges with K * I > 14: the transport launches at most once every 4 edges, K = 4)
 parameter integer XRING=0, VRING=0,
 // DIE-HBM-61 RE-FORM 11-03: BQS6=1 builds bq with S6SPLIT=1 (+1 edge) and this alignment pipe one shorter, so vo/y/fault
 // keep their edge exactly; BQS6=0 (default) is unchanged
 parameter integer BQS6=0,
 // DIE-HBM-61 RE-FORM round 2: BQPIPE=1 builds bq with PIPE=1 (the two 2-level max stages split, +2 edges) and this
 // alignment pipe two shorter, so vo/y/fault keep their edge exactly; BQPIPE=0 (default) is unchanged
 parameter integer BQPIPE=0,
 // BQS4=1: bq S4SPLIT=1 (+1 edge), alignment pipe one shorter; 0 (default) unchanged
 parameter integer BQS4=0)(
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
 ot_hfd_actquant_m #(.MR(1),.MLAT(6),.XRING(XRING)) aq(
 .clk(clk),.rst_n(rst_n),.v(take && !e4),.fp4(fp4),.x(x),
 .vo(av),.q(q),.e(exponent),.y(ay),.fault(af));
 ot_hgi_fp4qdq #(.S6SPLIT(BQS6),.PIPE(BQPIPE),.S4SPLIT(BQS4)) bq(.clk(clk),.rst_n(rst_n),.v(take && e4),.x(x),.vo(bv),.y(by),.fault(bf));
 // hgi-1010/c: ot_hgi_fp4qdq is one edge longer (S5A / S5B); this alignment pipe one shorter (14)
 localparam integer AL=14-BQS6-2*BQPIPE-BQS4;
 reg [AL-1:0] valid_pipe,fault_pipe;
 reg [511:0] value_pipe[0:AL-1]; integer i;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin valid_pipe<=0; fault_pipe<=0; end
  else begin valid_pipe<={valid_pipe[AL-2:0],bv}; fault_pipe<={fault_pipe[AL-2:0],bf}; end
 end
 wire [511:0] vq;
 generate if(VRING==0) begin:g_vl
 always @(posedge clk) begin
  value_pipe[0]<=by;
  for(i=1;i<AL;i=i+1)value_pipe[i]<=value_pipe[i-1];
 end
 assign vq=value_pipe[AL-1];
 end else begin:g_vr
  // by is registered (byq, unenabled), then written to a VRING-slot lane ring at the edge after; read 14 edges after bv
  reg [511:0] byq; always @(posedge clk) byq<=by;
  ot_hfd_lane_ring #(.L(32),.LW(16),.K(VRING)) u_vr(.clk(clk),.rst_n(rst_n),.pv(bv),.d(byq),.rv(valid_pipe[AL-1]),.q(vq));
 end endgenerate
 assign vo=av|valid_pipe[AL-1];
 assign y=valid_pipe[AL-1] ? vq : ay;
 assign fault=vo && (valid_pipe[AL-1] ? fault_pipe[AL-1] : af);
endmodule
