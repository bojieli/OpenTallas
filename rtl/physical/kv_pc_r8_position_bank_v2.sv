`timescale 1ns/1ps
// CANDIDATE D-KV landing event. Decode is frozen from actual B36 R8 geometry.
// Existing position IDs only; every replica carries the same118 data flops.
// No reset, new pin, flow control or arbitrary phase selector.
(* keep_hierarchy = 1 *)
module kv_pc_r8_position_bank_v2 #(parameter integer MUT=0)(
 input wire clk,input wire [1:0] stack_id,input wire [2:0] group_id,
 input wire [17:0] tok_i,input wire [15:0] epoch_i,
 output wire [17:0] tok_o,output wire [15:0] epoch_o
);
 (* keep=1 *) reg [17:0] tok1,tok2,tok3;
 (* keep=1 *) reg [15:0] ep1,ep2,ep3,ep4;
 always @(posedge clk) begin
  tok1<=tok_i;tok2<=tok1;tok3<=tok2;
  ep1<=epoch_i;ep2<=ep1;ep3<=ep2;ep4<=ep3;
 end
 wire wn=(stack_id==2'd1)&&((group_id==2)||(group_id==3)||(group_id==4)||(group_id==6));
 wire ws=(stack_id==((MUT==1)?2'd1:2'd0))&&((group_id==2)||(group_id==4));
 assign tok_o=wn?tok1:ws?tok3:tok_i;
 assign epoch_o=((stack_id==2'd2)&&(group_id==1))?ep4:
                ((stack_id==2'd0)&&(group_id==3))?ep3:epoch_i;
endmodule
