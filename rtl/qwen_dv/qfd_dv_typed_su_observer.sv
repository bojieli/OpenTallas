`timescale 1ns/1ps
// Selected source contract, default off. This replaces the existing GI su_obs
// register when integrated; do not append it after that register. SU unit is
// implicit in the dedicated port. No producer permission/ready path exists.
module qfd_dv_typed_su_observer #(
 parameter integer ENABLE=0
)(
 input wire ck,rst_n,
 input wire su_issue,input wire[1:0]cmd_user,input wire[8:0]su_pidx,
 input wire[3:0]cmd_slice,
 output reg[15:0]observation,output reg fault
);
 wire legacy_valid=su_issue&&cmd_user==0;
 always@(posedge ck or negedge rst_n)begin
  if(!rst_n)begin observation<=0;fault<=0;end
  else if(ENABLE==0)observation<={legacy_valid,legacy_valid,2'd2,3'd0,su_pidx};
  else begin
   observation<={su_issue,cmd_user,cmd_slice,su_pidx};
   // Current profile: unicast slice0..11 and canonical128-instruction user stride.
   if(su_issue&&(cmd_slice>=12||su_pidx[8:7]!=cmd_user))fault<=1;
  end
 end
endmodule
