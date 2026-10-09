`timescale 1ns/1ps
// HGI unit9/op2. The sorted insertion recurrence is the existing A3 selector's.
// This opt-in engine leaves the legacy DS router/SELECT implementations intact.
// Dispatcher resolves descriptor addresses/strides; streams one row at a time.
// No output of a row precedes validation of all its scores (NaN fail closed).
module ot_hgi_idx_topk #(
 parameter bit ENABLE=0, parameter integer MAX_K=2048,
 parameter bit MUTANT_TIE=0
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
 localparam IDLE=0,FILL=1,EMIT=2,FINISH=3;
 reg [1:0] state;
 reg [31:0] n,m,row,cursor,emit_cursor;
 reg [11:0] k;
 reg values_enabled;
 localparam integer EW=$clog2(MAX_K);
 wire [EW-1:0] emit_index=emit_cursor[EW-1:0];
 reg [52:0] cells[0:MAX_K-1];
 reg [31:0] values[0:MAX_K-1];
 wire [31:0] canon=(in_score[30:0]==0)?32'd0:in_score;
 wire [31:0] monotone=canon[31]?~canon:(canon|32'h80000000);
 wire [19:0] index_key=MUTANT_TIE?cursor[19:0]:~cursor[19:0];
 wire [52:0] key={1'b1,monotone,index_key};
 wire nan=(in_score[30:23]==8'hff)&&(in_score[22:0]!=0);
 wire [MAX_K-1:0] greater;
 genvar g;
 generate for(g=0;g<MAX_K;g=g+1) begin:compare
  assign greater[g]=key>cells[g];
 end endgenerate
 assign cmd_ready=state==IDLE;
 assign in_ready=ENABLE&&state==FILL;
 assign out_valid=ENABLE&&state==EMIT;
 assign out_id={{12{1'b0}},MUTANT_TIE?cells[emit_index][19:0]:~cells[emit_index][19:0]};
 assign out_score=values[emit_index];
 assign out_row=row;
 assign out_values_valid=out_valid&&values_enabled;
 assign out_last=state==EMIT&&emit_cursor+1==k;
 integer i;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   state<=IDLE; values_enabled<=0; done<=0;error<=0;n<=0;m<=0;k<=0;row<=0;cursor<=0;emit_cursor<=0;
   for(i=0;i<MAX_K;i=i+1) begin cells[i]<=0; values[i]<=0; end
  end else begin
   done<=0;
   case(state)
    IDLE: if(cmd_valid) begin
     error<=0;
     if(!ENABLE||cmd_unit!=9||cmd_op!=2) begin error<=1;done<=1;end
     else if(cmd_param[24:12]!=0||cmd_param[11:0]==0||cmd_param[11:0]>MAX_K||
       cmd_param[11:0]>cmd_n||cmd_n==0||cmd_n>1048576||cmd_m==0) begin error<=2;done<=1;end
     else begin
      values_enabled<=cmd_values;n<=cmd_n;m<=cmd_m;k<=cmd_param[11:0];row<=0;cursor<=0;state<=FILL;
      for(i=0;i<MAX_K;i=i+1) begin cells[i]<=0;values[i]<=0;end
     end
    end
    FILL: if(in_valid) begin
     if(nan) begin error<=3;done<=1;state<=IDLE;end
     else begin
      for(i=0;i<MAX_K;i=i+1) if(greater[i]) begin
       if(i==0) begin cells[i]<=key;values[i]<=in_score;end
       else if(greater[i-1]) begin cells[i]<=cells[i-1];values[i]<=values[i-1];end
       else begin cells[i]<=key;values[i]<=in_score;end
      end
      cursor<=cursor+1;
      if(cursor+1==n) begin state<=EMIT;emit_cursor<=0;end
     end
    end
    EMIT: if(out_ready) begin
     emit_cursor<=emit_cursor+1;
     if(emit_cursor+1==k) begin
      if(row+1==m) state<=FINISH;
      else begin
       row<=row+1;cursor<=0;state<=FILL;
       for(i=0;i<MAX_K;i=i+1) begin cells[i]<=0;values[i]<=0;end
      end
     end
    end
    FINISH: begin done<=1;state<=IDLE;end
    default:state<=IDLE;
   endcase
  end
 end
endmodule
