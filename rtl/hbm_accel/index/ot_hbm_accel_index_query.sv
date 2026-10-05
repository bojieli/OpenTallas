`timescale 1ps/1fs
// Actual hardware quantiser on source SU/VM FP32 blocks; no host quantisation.
// Single accepted query: 32 heads x 4 blocks x 32 words. All output storage is
// prepaid before the first no-stall quantiser issue; backpressure only at ingress.
module ot_hbm_accel_index_query #(parameter integer ENABLE=0)(
 input wire clk,por_n,start,
 output wire start_ready,
 input wire block_v,output wire block_r,
 input wire [4:0] block_head,input wire [1:0] block_number,
 input wire [1023:0] block_data,input wire [15:0] head_weight,
 output wire ql_v,input wire ql_r,output wire [7:0] ql_head,
 output wire [511:0] ql_codes,output wire [31:0] ql_sc,output wire [15:0] ql_w,
 output reg done,output reg fault
);
generate if(!ENABLE)begin:off
 assign start_ready=0;assign block_r=0;assign ql_v=0;assign ql_head=0;
 assign ql_codes=0;assign ql_sc=0;assign ql_w=0;
 always @* begin done=0;fault=0;end
end else begin:on
 reg active;
 reg [7:0] accepted;
 reg [5:0] sent;
 reg [3:0] seen[0:31];
 reg [511:0] codes[0:31];reg[31:0] scales[0:31];reg[15:0] weights[0:31];
 reg [6:0] tag[0:12];
 wire take=block_v&&block_r;
 assign start_ready=!active&&!fault;
 assign block_r=active&&accepted<128&&!fault;
 assign ql_head={3'b0,sent[4:0]};
 assign ql_codes=codes[sent[4:0]];assign ql_sc=scales[sent[4:0]];assign ql_w=weights[sent[4:0]];
 assign ql_v=active&&sent<32&&(&seen[sent[4:0]])&&!fault;
 wire qv,qfault;wire[255:0] q;wire signed[9:0] qe;wire[511:0] qy;
 ot_hdc_actquant u_quant(.clk(clk),.rst_n(por_n),.v(take),.fp4(1'b1),.x(block_data),
 .vo(qv),.q(q),.e(qe),.y(qy),.fault(qfault));
 integer h,t,l;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   active<=0;accepted<=0;sent<=0;done<=0;fault<=0;
   for(h=0;h<32;h=h+1)seen[h]<=0;
  end else begin
   done<=0;
   tag[0]<={block_head,block_number};
   for(t=1;t<13;t=t+1)tag[t]<=tag[t-1];
   if(start&&start_ready)begin
    active<=1;accepted<=0;sent<=0;
    for(h=0;h<32;h=h+1)seen[h]<=0;
   end
   if(take)begin
    if({block_head,block_number}!==accepted[6:0])fault<=1;
    if(block_number==0)weights[block_head]<=head_weight;
    else if(weights[block_head]!=head_weight)fault<=1;
    accepted<=accepted+1;
   end
   if(qv)begin
    if(!active||qfault||qe < -127||qe>125||seen[tag[12][6:2]][tag[12][1:0]])fault<=1;
    else begin
     seen[tag[12][6:2]][tag[12][1:0]]<=1;
     scales[tag[12][6:2]][8*tag[12][1:0]+:8]<=8'(qe+127);
     for(l=0;l<32;l=l+1)codes[tag[12][6:2]][128*tag[12][1:0]+4*l+:4]<=q[8*l+:4];
    end
   end
   if(ql_v&&ql_r)begin
    sent<=sent+1;
    if(sent==31)begin active<=0;done<=1;end
   end
  end
 end
end endgenerate
endmodule
