`timescale 1ns/1ps
// Canonical V rows at one row/cycle per pair. The explicit INIT_CYCLES
// reservation covers u_pv's 128 SRAM initialization writes. A return occupies
// its compiled cycle, and never waits for a free slot or consumer readiness.
// RETURN_LATENCY includes the service's row/exp capture edge (external + 1).
module ot_qwen_tp8_vrow_static #(
 parameter integer PAIR=0, RETURN_LATENCY=17, INIT_CYCLES=128
) (
 input wire clk,rst_n,start,input wire [13:0] context_len,input wire [15:0] epoch,
 output wire lo_req_valid,hi_req_valid,input wire lo_req_ready,hi_req_ready,
 output wire [2:0] req_slot,output wire [13:0] req_t,output wire [15:0] req_epoch,
 input wire lo_rsp_valid,hi_rsp_valid,
 input wire [2:0] lo_rsp_slot,hi_rsp_slot,input wire [13:0] lo_rsp_t,hi_rsp_t,
 input wire [15:0] lo_rsp_epoch,hi_rsp_epoch,
 input wire [1023:0] lo_vrow,hi_vrow,input wire [63:0] lo_exp,hi_exp,
 output wire out_valid,input wire out_ready,output wire [1023:0] out_vrow,
 output wire [63:0] out_exp,output wire [13:0] out_t,output wire [15:0] out_epoch,
 output wire out_first,out_last,output reg done,fault
);
 reg active,issuing;
 reg [13:0] limit,next_t;
 reg [15:0] ep;
 reg [31:0] init_left;
 reg [2:0] slot;
 reg [RETURN_LATENCY-1:0] due;
 reg [13:0] tags[0:RETURN_LATENCY-1];
 reg [2:0] slots[0:RETURN_LATENCY-1];
 wire issue=active && issuing && init_left==0 && !fault;
 wire expected=due[RETURN_LATENCY-1];
 wire [13:0] expected_t=tags[RETURN_LATENCY-1];
 wire expected_hi=expected_t[8];
 wire observed=lo_rsp_valid || hi_rsp_valid;
 wire good=expected && (expected_hi ? hi_rsp_valid&&!lo_rsp_valid : lo_rsp_valid&&!hi_rsp_valid)
  && (expected_hi ? hi_rsp_t : lo_rsp_t)==expected_t
  && (expected_hi ? hi_rsp_slot : lo_rsp_slot)==slots[RETURN_LATENCY-1]
  && (expected_hi ? hi_rsp_epoch : lo_rsp_epoch)==ep;
 assign lo_req_valid=issue && !next_t[8];
 assign hi_req_valid=issue && next_t[8];
 assign req_t=next_t;assign req_slot=slot;assign req_epoch=ep;
 assign out_valid=active && observed && good && !fault;
 assign out_vrow=expected_hi ? hi_vrow : lo_vrow;
 assign out_exp=expected_hi ? hi_exp : lo_exp;
 assign out_t=expected_t;assign out_epoch=ep;
 assign out_first=expected_t<256;
 assign out_last=expected_t+14'd256>=limit;
 integer i;
 initial begin
  if(RETURN_LATENCY<1 || INIT_CYCLES<128 || PAIR<0 || PAIR>1)
   $fatal(1,"Invalid static V geometry");
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   active<=0;issuing<=0;limit<=0;next_t<=0;ep<=0;init_left<=0;slot<=0;
   due<=0;done<=0;fault<=0;
   for(i=0;i<RETURN_LATENCY;i=i+1)begin tags[i]<=0;slots[i]<=0;end
  end else begin
   done<=0;
   if(start)begin
    if(active || (|due) || observed || context_len==0 || context_len>8192)fault<=1;
    else begin
     active<=context_len>PAIR*128;issuing<=context_len>PAIR*128;
     limit<=context_len;ep<=epoch;next_t<=14'(PAIR*128);slot<=0;
     init_left<=INIT_CYCLES;due<=0;
     if(context_len<=PAIR*128)done<=1;
    end
   end else begin
    if(init_left!=0)init_left<=init_left-1'b1;
    due[0]<=issue;tags[0]<=next_t;slots[0]<=slot;
    for(i=1;i<RETURN_LATENCY;i=i+1)begin due[i]<=due[i-1];tags[i]<=tags[i-1];slots[i]<=slots[i-1];end
    if(issue)begin
     slot<=slot+1'b1;
     if(next_t[6:0]==127)begin
      if(next_t+129>=limit)issuing<=0;else next_t<=next_t+129;
     end else if(next_t+1>=limit)issuing<=0;else next_t<=next_t+1'b1;
    end
    if((lo_req_valid&&!lo_req_ready)||(hi_req_valid&&!hi_req_ready))fault<=1;
    if(observed!=expected || (observed&&!good) || (out_valid&&!out_ready))fault<=1;
    // Last physical row of this pair, not the end of one residue chain.
    if(out_valid && (expected_t[6:0]==127 ? expected_t+129>=limit : expected_t+1>=limit))begin active<=0;done<=1;end
   end
  end
 end
endmodule
