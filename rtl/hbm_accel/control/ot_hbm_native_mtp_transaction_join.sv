`timescale 1ns/1ps
`default_nettype none
// Full native201-bit command ownership. Backend must echo the actual accepted
// identity; an untagged legacy done signal is deliberately not an input.
module ot_hbm_native_mtp_transaction_join #(
 parameter integer ENABLE=0,SEQ_W=32,EPOCH_W=8
)(
 input wire clk,rst_n,external_fault,backend_quiescent,
 input wire job_v,output wire job_rdy,input wire [31:0] job_id,
 input wire [3:0] job_generation,input wire [EPOCH_W-1:0] job_epoch,
 input wire [178:0] job_config,provider_controls,
 input wire [516:0] f_mtp,output wire [178:0] t_mtp,
 output wire eng_cmd_v,input wire eng_cmd_rdy,output wire [200:0] eng_cmd,
 output wire [31:0] eng_job,output wire [3:0] eng_generation,
 output wire [SEQ_W-1:0] eng_sequence,output wire [EPOCH_W-1:0] eng_epoch,
 input wire eng_cpl_v,output wire eng_cpl_rdy,input wire [31:0] eng_cpl_job,
 input wire [3:0] eng_cpl_generation,input wire [SEQ_W-1:0] eng_cpl_sequence,
 input wire [EPOCH_W-1:0] eng_cpl_epoch,input wire eng_cpl_fault,
 output reg active,inflight,identity_fault,fault
);
 reg [178:0] config_q;
 reg [31:0] owner_job;reg [3:0] owner_gen;
 reg [EPOCH_W-1:0] owner_epoch;reg [SEQ_W-1:0] sequence_q;
 reg start_q,done_q;
 wire owned=eng_cpl_job==owner_job && eng_cpl_generation==owner_gen &&
  eng_cpl_sequence==sequence_q && eng_cpl_epoch==owner_epoch;
 assign job_rdy=ENABLE && !active && !inflight && backend_quiescent && !external_fault;
 assign eng_cmd_v=ENABLE && active && !inflight && !fault && !external_fault &&
  !done_q && f_mtp[82] && sequence_q!={SEQ_W{1'b1}};
 assign eng_cmd={f_mtp[148+:136],f_mtp[131+:17],f_mtp[99+:32],f_mtp[95+:4],f_mtp[87+:8],f_mtp[83+:4]};
 assign eng_job=owner_job;assign eng_generation=owner_gen;
 assign eng_sequence=sequence_q;assign eng_epoch=owner_epoch;
 // Consume orphan/stale completions too, poisoning this job rather than
 // deadlocking a full response queue or allowing it to finish a newer job.
 assign eng_cpl_rdy=ENABLE && !external_fault;
 reg [178:0] controls;
 always @* begin
  controls=config_q;controls[0]=start_q;
  controls[48+:34]=provider_controls[48+:34];
  controls[84+:55]=provider_controls[84+:55];
  controls[139]=provider_controls[139] && active && !fault && !external_fault;
  controls[82]=eng_cmd_v && eng_cmd_rdy;
  controls[83]=done_q;
 end
 assign t_mtp=ENABLE?controls:179'b0;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   active<=0;inflight<=0;identity_fault<=0;fault<=0;config_q<=0;
   owner_job<=0;owner_gen<=0;owner_epoch<=0;sequence_q<=0;start_q<=0;done_q<=0;
  end else begin
   start_q<=0;done_q<=0;
   if(ENABLE && job_v && job_rdy) begin
    active<=1;inflight<=0;identity_fault<=0;fault<=0;config_q<=job_config;
    owner_job<=job_id;owner_gen<=job_generation;owner_epoch<=job_epoch;sequence_q<=0;start_q<=1;
   end
   if(eng_cmd_v && eng_cmd_rdy) inflight<=1;
   if(eng_cpl_v && eng_cpl_rdy) begin
    if(!active || !inflight || !owned) begin identity_fault<=1;fault<=1;end
    else if(eng_cpl_fault) begin fault<=1;inflight<=0;end
    else begin done_q<=1;inflight<=0;sequence_q<=sequence_q+1'b1;end
   end
   if(ENABLE && active && f_mtp[82] && sequence_q=={SEQ_W{1'b1}}) fault<=1;
   if(active && f_mtp[81] && !inflight) active<=0;
   if(external_fault) begin fault<=1;active<=0;inflight<=0;done_q<=0;end
  end
 end
endmodule
`default_nettype wire
