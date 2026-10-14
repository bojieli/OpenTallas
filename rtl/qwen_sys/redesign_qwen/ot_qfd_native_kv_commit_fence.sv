`timescale 1ns/1ps
// Candidate receiver COMMIT fence, distinct from formatter emission/queue
// acceptance. Native K/V each has one128-byte row. Every quadrant must post
// and commit both rows. ACK identity must come from the actual storage write.
// ack_credit may drive the receiver's quadrant credit ONLY after this check.
module ot_qfd_native_kv_commit_fence #(parameter integer ENABLE=0,MUT_OR=0)(
 input wire clk,rst_n,
 input wire begin_v,input wire [15:0] begin_epoch,input wire [5:0] begin_layer,input wire [17:0] begin_pos,
 output wire begin_ready,
 input wire formatter_emitted,
 input wire [3:0] posted_v,posted_kind,
 input wire [4*16-1:0] posted_epoch,input wire [4*6-1:0] posted_layer,input wire [4*18-1:0] posted_pos,
 input wire [3:0] ack_v,ack_kind,
 input wire [4*16-1:0] ack_epoch,input wire [4*6-1:0] ack_layer,input wire [4*18-1:0] ack_pos,
 output reg [3:0] ack_credit,output wire committed,output reg fault
);
 reg active,emitted;reg [15:0] epoch;reg [5:0] layer;reg [17:0] pos;
 reg [7:0] posted,acked;reg [7:0] pn,an;reg [3:0] credits;reg err;integer q,ix;
 assign begin_ready=ENABLE!=0&&(!active||committed)&&!fault;
 assign committed=ENABLE!=0&&active&&emitted&&!fault&&(MUT_OR!=0?(|acked):(&acked));
 always_comb begin
  pn=posted;an=acked;credits=0;err=0;ix=0;
  for(q=0;q<4;q=q+1)begin
   if(posted_v[q])begin
    ix=posted_kind[q]*4+q;
    if(!active||pn[ix]||posted_epoch[16*q+:16]!=epoch||posted_layer[6*q+:6]!=layer||posted_pos[18*q+:18]!=pos)err=1;
    else pn[ix]=1;
   end
   if(ack_v[q])begin
    ix=ack_kind[q]*4+q;
    if(!active||!pn[ix]||an[ix]||ack_epoch[16*q+:16]!=epoch||ack_layer[6*q+:6]!=layer||ack_pos[18*q+:18]!=pos)err=1;
    else begin an[ix]=1;credits[q]=1;end
   end
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;emitted<=0;epoch<=0;layer<=0;pos<=0;posted<=0;acked<=0;ack_credit<=0;fault<=0;end
  else if(ENABLE!=0)begin
   ack_credit<=fault||err?4'd0:credits;
   if(begin_v)begin
    if(!begin_ready||begin_pos>=8192||(|posted_v)||(|ack_v))fault<=1;
    else begin active<=1;emitted<=0;epoch<=begin_epoch;layer<=begin_layer;pos<=begin_pos;posted<=0;acked<=0;end
   end else begin
    posted<=pn;acked<=an;
    if(formatter_emitted)begin if(!active)fault<=1;else emitted<=1;end
    if(err)fault<=1;
   end
  end
 end
endmodule
