`timescale 1ns/1ps
// Fixed source-binding candidate. The engine command/read calendar is untouched.
// FACE's registered epoch arrives one edge after the CTLM start/user/token.
module qfd_embedding_validation_arm #(parameter integer ENABLE=0)(
 input wire ck,rst_n,core_start,input wire[1:0]core_user,input wire[17:0]core_token,
 input wire[15:0]registered_epoch,input wire native_read,release_slot,
 output wire validation_start,output wire[17:0]validation_token,
 output wire[15:0]validation_epoch,output wire fault);
 generate if(ENABLE==0)begin:g_off
  assign validation_start=core_start;assign validation_token=core_token;
  assign validation_epoch=registered_epoch;assign fault=1'b0;
 end else begin:g_on
  reg start_q,validated,fault_q;reg[1:0]user_q;reg[17:0]token_q;
  assign validation_start=start_q;assign validation_token=token_q;
  assign validation_epoch=registered_epoch;assign fault=fault_q;
  always @(posedge ck or negedge rst_n)
   if(!rst_n)begin start_q<=0;validated<=0;fault_q<=0;user_q<=0;token_q<=0;end
   else begin
    start_q<=core_start;
    if(core_start)begin
     user_q<=core_user;token_q<=core_token;
     if(start_q||validated||release_slot)fault_q<=1;
    end
    if(start_q)begin
     validated<=1;
     if(registered_epoch[1:0]!=user_q||release_slot)fault_q<=1;
    end
    // Before means strictly before: a read on the validation edge faults.
    if(native_read&&(!validated||release_slot))fault_q<=1;
    if(release_slot)begin
     validated<=0;
     if(!validated||start_q||core_start)fault_q<=1;
    end
   end
 end endgenerate
endmodule
