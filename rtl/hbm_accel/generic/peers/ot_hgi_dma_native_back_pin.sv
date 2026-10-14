`timescale 1ns/1ps
`default_nettype none
// Local BACK face: explicit local-offset/mirror translation, registered native
// read requests and returns, and a two-entry command station. BACK itself keeps
// its NS1/NB8/VCR8 configuration; placement must bind a matching STK view.
module ot_hgi_dma_native_back_pin #(parameter integer SID=0)(
 input wire clk,rst_n,input wire mv_v,input wire [226:0] mv,output wire mv_ready,
 output wire engine_mv_v,output wire [226:0] engine_mv,input wire engine_mv_ready,
 input wire engine_src,engine_done,engine_fault,engine_quiet,
 output reg src,done,fault,quiet,
 input wire [128:0] local_q,output wire [2064:0] local_r,
 output wire [135:0] native_rq,input wire [7:0] native_cr,input wire [2055:0] native_rr
);
 ot_hgi_b2_dma_cmd_pin u_cmd(.clk(clk),.rst_n(rst_n),.in_v(mv_v),.in_data(mv),.in_ready(mv_ready),
  .out_v(engine_mv_v),.out_data(engine_mv),.out_ready(engine_mv_ready));
 reg [7:0] cr_q,rr_v;reg [2047:0] rr_data;
 reg [135:0] rq_q;
 assign native_rq=rq_q;
 assign local_r[2064]=1'b1;assign local_r[2063:2056]=cr_q;
 for(genvar b=0;b<8;b=b+1)begin:lane
  assign local_r[b*257 +:257]={rr_v[b],rr_data[b*256 +:256]};
  always @(posedge clk)begin
   rq_q[b*17 +:16]<={local_q[b*16+13],local_q[b*16+13]?2'b00:2'(SID),local_q[b*16 +:13]};
   rr_data[b*256 +:256]<=native_rr[b*257 +:256];
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin cr_q<=0;rr_v<=0;src<=0;done<=0;fault<=0;quiet<=0;
   for(integer b=0;b<8;b=b+1)rq_q[b*17+16]<=0;
  end else begin
   cr_q<=native_cr;src<=engine_src;done<=engine_done;
   fault<=engine_fault||fault;
   quiet<=engine_quiet&&!engine_mv_v&&!mv_v;
   for(integer b=0;b<8;b=b+1)begin
    rr_v[b]<=native_rr[b*257+256];rq_q[b*17+16]<=local_q[b*16+15];
    if(local_q[b*16+15] && (local_q[b*16+14] || local_q[b*16 +:3]!=3'(b)))fault<=1;
   end
  end
 end
endmodule
`default_nettype wire
