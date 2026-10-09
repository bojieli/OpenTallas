`timescale 1ns/1ps
`default_nettype none
// Native e_idx is generated-token index, NOT absolute context position.
// Completion is visible only after the last accepted token reaches the host.
module ot_hbm_native_mtp_emit_queue #(parameter integer ENABLE=0,DEPTH=8)(
 input wire clk,rst_n,external_fault,
 input wire job_v,output wire job_rdy,input wire [31:0] job_id,
 input wire [3:0] job_generation,input wire [7:0] job_epoch,
 input wire [37:0] emit,input wire native_done,input wire [2:0] native_status,
 output wire emit_ready,
 output wire host_v,input wire host_ready,output wire [80:0] host_data,
 output wire host_done_v,input wire host_done_ready,output wire [2:0] host_status,
 output wire [20:0] accepted_count,output reg fault
);
 localparam integer AW=$clog2(DEPTH);
 reg [80:0] storage[0:DEPTH-1];reg [AW-1:0] wp,rp;reg [AW:0] count;
 reg active,done_pending;reg [2:0] status;
 reg [31:0] job;reg [3:0] generation;reg [7:0] epoch;reg [20:0] accepted;
 wire pop=host_v && host_ready;
 assign job_rdy=ENABLE && !active && !done_pending && count==0 && !external_fault;
 assign emit_ready=ENABLE && active && !done_pending && !fault && !external_fault && (count<DEPTH || pop);
 wire push=emit[0] && emit_ready;
 wire valid_index=accepted<21'h100000 && emit[37:18]==accepted[19:0];
 assign host_v=ENABLE && count!=0;assign host_data=storage[rp];
 assign host_done_v=ENABLE && done_pending && count==0;
 assign host_status=status;assign accepted_count=accepted;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin wp<=0;rp<=0;count<=0;active<=0;done_pending<=0;status<=0;fault<=0;job<=0;generation<=0;epoch<=0;accepted<=0;end
  else begin
   if(job_v && job_rdy) begin active<=1;fault<=0;status<=0;job<=job_id;generation<=job_generation;epoch<=job_epoch;accepted<=0;end
   if(push) begin
    if(valid_index) begin storage[wp]<={epoch,generation,job,emit[37:18],emit[17:1]};wp<=wp+1'b1;accepted<=accepted+1'b1;end
    else begin fault<=1;status<=4;done_pending<=1;active<=0;end
   end
   if(pop) rp<=rp+1'b1;
   case({push&&valid_index,pop}) 2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:count<=count;endcase
   if(native_done && active) begin done_pending<=1;active<=0;status<=native_status;end
   if(external_fault && active) begin done_pending<=1;active<=0;fault<=1;status<=4;end
   if(host_done_v && host_done_ready) done_pending<=0;
  end
 end
endmodule
`default_nettype wire
