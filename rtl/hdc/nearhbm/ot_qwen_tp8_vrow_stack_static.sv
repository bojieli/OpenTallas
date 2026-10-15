`timescale 1ns/1ps
// One compiler-fixed issuer per HBM stack. Four issuers retain the existing
// four-stack row ABI while issuing four independent rows per edge. A stack
// owns t=512*n+128*STACK+c (c=0..127), not a separate FP reduction tree.
// first/last retain the canonical old two-pair accumulation meaning; done is
// separately the last physical row of THIS stack. No ready signal moves a slot.
module ot_qwen_tp8_vrow_stack_static #(
 parameter integer STACK=0, RETURN_LATENCY=17, INIT_CYCLES=128
)(
 input wire clk,rst_n,start,input wire[13:0] context_len,input wire[15:0] epoch,
 output wire req_valid,input wire req_ready,output wire[2:0] req_slot,
 output wire[13:0] req_t,output wire[15:0] req_epoch,
 input wire rsp_valid,input wire[2:0] rsp_slot,input wire[13:0] rsp_t,
 input wire[15:0] rsp_epoch,input wire[1023:0] rsp_vrow,input wire[63:0] rsp_exp,
 output wire out_valid,input wire out_ready,output wire[1023:0] out_vrow,
 output wire[63:0] out_exp,output wire[13:0] out_t,output wire[15:0] out_epoch,
 output wire out_first,out_last,output reg done,fault
);
 reg active,issuing;
 reg[13:0] limit,next_t;
 reg[15:0] ep;
 reg[31:0] init_left;
 reg[2:0] slot;
 reg[RETURN_LATENCY-1:0] due;
 reg[13:0] tags[0:RETURN_LATENCY-1];
 reg[2:0] slots[0:RETURN_LATENCY-1];
 wire issue=active&&issuing&&init_left==0&&!fault;
 wire expected=due[RETURN_LATENCY-1];
 wire[13:0] expected_t=tags[RETURN_LATENCY-1];
 wire good=expected&&rsp_valid&&rsp_t==expected_t&&rsp_slot==slots[RETURN_LATENCY-1]&&rsp_epoch==ep;
 assign req_valid=issue;
 assign req_t=next_t;assign req_slot=slot;assign req_epoch=ep;
 assign out_valid=active&&rsp_valid&&good&&!fault;
 assign out_vrow=rsp_vrow;assign out_exp=rsp_exp;
 assign out_t=expected_t;assign out_epoch=ep;
 assign out_first=expected_t<256;
 assign out_last=expected_t+14'd256>=limit;
 integer i;
 initial if(RETURN_LATENCY<1||INIT_CYCLES<128||STACK<0||STACK>3)
  $fatal(1,"Invalid four-stack static V geometry");
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   active<=0;issuing<=0;limit<=0;next_t<=0;ep<=0;init_left<=0;slot<=0;
   due<=0;done<=0;fault<=0;
   for(i=0;i<RETURN_LATENCY;i=i+1)begin tags[i]<=0;slots[i]<=0;end
  end else begin
   done<=0;
   if(start)begin
    if(active||(|due)||rsp_valid||context_len==0||context_len>8192)fault<=1;
    else begin
     active<=context_len>STACK*128;issuing<=context_len>STACK*128;
     limit<=context_len;ep<=epoch;next_t<=14'(STACK*128);slot<=0;
     init_left<=INIT_CYCLES;due<=0;
     if(context_len<=STACK*128)done<=1;
    end
   end else begin
    if(init_left!=0)init_left<=init_left-1'b1;
    due[0]<=issue;tags[0]<=next_t;slots[0]<=slot;
    for(i=1;i<RETURN_LATENCY;i=i+1)begin due[i]<=due[i-1];tags[i]<=tags[i-1];slots[i]<=slots[i-1];end
    if(issue)begin
     slot<=slot+1'b1;
     if(next_t[6:0]==127)begin
      if(next_t+385>=limit)issuing<=0;else next_t<=next_t+385;
     end else if(next_t+1>=limit)issuing<=0;else next_t<=next_t+1'b1;
    end
    if(req_valid&&!req_ready)fault<=1;
    if(rsp_valid!=expected||(rsp_valid&&!good)||(out_valid&&!out_ready))fault<=1;
    if(out_valid&&(expected_t[6:0]==127?expected_t+385>=limit:expected_t+1>=limit))begin active<=0;done<=1;end
   end
  end
 end
endmodule
