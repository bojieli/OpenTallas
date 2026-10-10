`timescale 1ns/1ps
// Three registered boundary relays around the measured, byte-identical TOPK core.
// Command, score and result are each captured before boundary logic. A command
// retires only after its final accepted output; faults clear prefetched scores.
module ot_hgi_idx_topk_registered #(
 parameter bit ENABLE=0, parameter integer MAX_K=2048, parameter bit MUTANT_TIE=0,
 parameter bit MUTANT_EARLY_DONE=0
)(
 input wire clk,rst_n,
 input wire cmd_valid, output wire cmd_ready,
 input wire [3:0] cmd_unit, input wire [5:0] cmd_op,
 input wire [24:0] cmd_param, input wire [31:0] cmd_n,cmd_m,
 input wire cmd_values,
 input wire in_valid, output wire in_ready, input wire [31:0] in_score,
 output wire out_valid, input wire out_ready,
 output wire [31:0] out_id,out_score,out_row,
 output wire out_last, output wire out_values_valid, output reg done, output reg [3:0] error
);
 reg active,c_valid,s_valid,q_valid,pending_done;
 reg [3:0] c_unit;
 reg [5:0] c_op;
 reg [24:0] c_param;
 reg [31:0] c_n,c_m,s_score;
 reg c_values;
 reg [31:0] q_id,q_score,q_row;
 reg q_last,q_values;
 wire core_cmd_ready,core_in_ready,core_out_valid,core_done;
 wire [3:0] core_error;
 wire [31:0] core_id,core_score,core_row;
 wire core_last,core_values;
 wire core_out_ready=!q_valid||out_ready;
 assign cmd_ready=!active&&!c_valid&&core_cmd_ready&&!pending_done&&!q_valid;
 assign in_ready=active&&(!s_valid||core_in_ready);
 assign out_valid=q_valid;
 assign out_id=q_id;assign out_score=q_score;assign out_row=q_row;
 assign out_last=q_last;assign out_values_valid=q_valid&&q_values;
 ot_hgi_idx_topk #(.ENABLE(ENABLE),.MAX_K(MAX_K),.MUTANT_TIE(MUTANT_TIE)) core(
  .clk(clk),.rst_n(rst_n),.cmd_valid(c_valid),.cmd_ready(core_cmd_ready),
  .cmd_unit(c_unit),.cmd_op(c_op),.cmd_param(c_param),.cmd_n(c_n),.cmd_m(c_m),.cmd_values(c_values),
  .in_valid(s_valid&&active),.in_ready(core_in_ready),.in_score(s_score),
  .out_valid(core_out_valid),.out_ready(core_out_ready),.out_id(core_id),.out_score(core_score),
  .out_row(core_row),.out_last(core_last),.out_values_valid(core_values),.done(core_done),.error(core_error));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   active<=0;c_valid<=0;s_valid<=0;q_valid<=0;pending_done<=0;done<=0;error<=0;
   c_unit<=0;c_op<=0;c_param<=0;c_n<=0;c_m<=0;c_values<=0;s_score<=0;
   q_id<=0;q_score<=0;q_row<=0;q_last<=0;q_values<=0;
  end else begin
   done<=0;
   if(c_valid&&core_cmd_ready)c_valid<=0;
   if(cmd_valid&&cmd_ready)begin
    active<=1;c_valid<=1;c_unit<=cmd_unit;c_op<=cmd_op;c_param<=cmd_param;
    c_n<=cmd_n;c_m<=cmd_m;c_values<=cmd_values;error<=0;
   end
   if(in_ready)begin
    s_valid<=in_valid;
    if(in_valid)s_score<=in_score;
   end
   if(core_out_ready)begin
    q_valid<=core_out_valid;
    if(core_out_valid)begin
     q_id<=core_id;q_score<=core_score;q_row<=core_row;
     q_last<=core_last;q_values<=core_values;
    end
   end
   if(core_done)begin pending_done<=1;error<=core_error;end
   if((pending_done||core_done)&&((!q_valid||out_ready)||MUTANT_EARLY_DONE))begin
    done<=1;active<=0;pending_done<=0;c_valid<=0;s_valid<=0;
   end
  end
 end
endmodule
