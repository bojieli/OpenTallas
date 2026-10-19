`timescale 1ns/1ps
`default_nettype none
(* keep_hierarchy=1 *) module ot_cache_safe_q #(parameter W=1)(input wire clk,input wire[W-1:0]d,output reg[W-1:0]q);always @(posedge clk)q<=d;endmodule
(* keep_hierarchy=1 *) module ot_cache_safe_rq #(parameter W=1)(input wire clk,rst_n,input wire[W-1:0]d,output reg[W-1:0]q);always @(posedge clk or negedge rst_n)if(!rst_n)q<=0;else q<=d;endmodule
(* keep_hierarchy=1 *) module ot_cache_safe_reset_phase(input wire clk,rst_n,output reg q);always @(posedge clk or negedge rst_n)if(!rst_n)q<=0;else q<=1;endmodule
(* keep_hierarchy=1 *) module ot_cache_safe_write16(input wire clk,rst_n,input wire[3:0]select_d,input wire[15:0]data0,data1,data2,data3,output reg[15:0]q);
 wire [3:0] sel;
 ot_cache_safe_rq #(.W(4)) u_sel(.clk(clk),.rst_n(rst_n),.d(select_d),.q(sel));
 wire [15:0] incoming=({16{sel[0]}}&data0)|({16{sel[1]}}&data1)|({16{sel[2]}}&data2)|({16{sel[3]}}&data3);
 always @(posedge clk)if(|sel)q<=incoming;
endmodule


(* keep_hierarchy=1 *) module ot_cache_safe_reset_release(input wire clk,phase0,output reg q);always @(posedge clk or negedge phase0)if(!phase0)q<=0;else q<=phase0;endmodule
(* keep_hierarchy=1 *) module ot_cache_safe_reset_buf(input wire a,output wire y);
 (* keep=1 *) BUFx4_ASAP7_75t_R u_buf(.A(a),.Y(y));
endmodule
`ifndef SYNTHESIS
module BUFx4_ASAP7_75t_R(input wire A,output wire Y);assign Y=A;endmodule
`endif
(* keep_hierarchy=1 *) module ot_cache_safe_advance(input wire running,input wire[8:0]elapsed,input wire[2:0]phase,input wire[6:0]emitted,rows,input wire sticky,output wire q);
 assign q=running&&elapsed>=2&&phase!=1&&emitted<rows&&!sticky;
endmodule
(* keep_hierarchy=1 *) module ot_cache_safe_meta8 #(parameter W=8)(input wire clk,rst_n,open_pred,input wire[W-1:0]data_d,output wire[W-1:0]q);
 wire select_q;wire[W-1:0]incoming_q;
 ot_cache_safe_rq u_select(.clk(clk),.rst_n(rst_n),.d(open_pred),.q(select_q));
 ot_cache_safe_q #(.W(W)) u_in(.clk(clk),.d(data_d),.q(incoming_q));
 ot_cache_safe_rq #(.W(W)) u_store(.clk(clk),.rst_n(rst_n),.d(select_q?incoming_q:q),.q(q));
endmodule
(* keep_hierarchy=1 *) module ot_cache_safe_bank_meta #(parameter BANK=0)(
 input wire clk,input wire[4:0]rst_n,input wire open_pred,open_bank,input wire[15:0]open_epoch,input wire[6:0]open_count,input wire[9:0]open_base,
 input wire read_bank_d,retire_bank_d,input wire[15:0]read_epoch,input wire[5:0]read_row,input wire[9:0]read_tag,input wire[15:0]retire_epoch,
 output wire[15:0]epoch,output wire[6:0]count,output wire[9:0]base,output wire read_id_ok,retire_id_ok);
 wire[32:0]incoming={open_base,open_count,open_epoch};wire[32:0]stored;
 assign {base,count,epoch}=stored;
 genvar k;generate for(k=0;k<5;k=k+1)begin:g_m
 localparam W=(k==4)?1:8;
 ot_cache_safe_meta8 #(.W(W)) u_m(.clk(clk),.rst_n(rst_n[k]),.open_pred(open_pred&&(open_bank==BANK)),.data_d(incoming[k*8+:W]),.q(stored[k*8+:W]));
 end endgenerate
 wire read_bq,retire_bq;
 ot_cache_safe_q u_rbank(.clk(clk),.d(read_bank_d),.q(read_bq));
 ot_cache_safe_q u_tbank(.clk(clk),.d(retire_bank_d),.q(retire_bq));
 assign read_id_ok=read_bq==BANK&&read_epoch==epoch&&{1'b0,read_row}<count&&read_tag==10'(base+read_row);
 assign retire_id_ok=retire_bq==BANK&&retire_epoch==epoch;
endmodule
`default_nettype wire
