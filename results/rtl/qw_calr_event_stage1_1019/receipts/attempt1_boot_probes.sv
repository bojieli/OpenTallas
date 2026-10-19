`timescale 1ns/1ps
// Passive observation only. Values at posedge are the actual pre-NBA inputs
// sampled by that edge. No output, delay, force, or functional state exists.
module qw_calr_probe #(parameter UB=1)(input ck,rst_n,pw_v,dw_v,start,
 input [9:0] pw_addr,input [2:0] dw_addr,input [5:0] stage,
 input [UB-1:0] start_user,iu,input rom_req,rom_valid,i_any,
 input [9:0] rom_first,input [2:0] rom_n,input [115:0] ic,
 input image_ready,fault);
 integer edge_id=0,epoch=0;reg was_reset=1;
 always @(posedge ck) begin
  edge_id=edge_id+1;
  if(!rst_n)was_reset=1;
  else begin
   if(was_reset)begin epoch=epoch+1;was_reset=0;$display("QWEVENT|%0t|%m|%0d|%0d|RESET_RELEASE|0|0",$time,edge_id,epoch);end
   if(pw_v)$display("QWEVENT|%0t|%m|%0d|%0d|PW_CAPTURE|%0d|0",$time,edge_id,epoch,pw_addr);
   if(dw_v)$display("QWEVENT|%0t|%m|%0d|%0d|DW_CAPTURE|%0d|0",$time,edge_id,epoch,dw_addr);
   if(start)$display("QWEVENT|%0t|%m|%0d|%0d|CAL_START|%0d|%0d",$time,edge_id,epoch,stage,start_user);
   if(rom_req)$display("QWEVENT|%0t|%m|%0d|%0d|CAL_ROM_REQUEST|%0d|%0d",$time,edge_id,epoch,rom_first,rom_n);
   if(rom_valid)$display("QWEVENT|%0t|%m|%0d|%0d|CAL_ROM_RESPONSE|0|0",$time,edge_id,epoch);
   if(i_any)$display("QWEVENT|%0t|%m|%0d|%0d|CAL_ISSUE_CAPTURE|%h|%0d",$time,edge_id,epoch,ic,iu);
  end
 end
endmodule
bind qfd_dv_cmd_cal_mu qw_calr_probe #(.UB(UB)) stage1_probe
(.ck(ck),.rst_n(rst_n),.pw_v(pw_v),.dw_v(dw_v),.pw_addr(pw_addr),.dw_addr(dw_addr),
 .start(start),.stage(stage),.start_user(start_user),.rom_req(rom_req),.rom_first(rom_first),.rom_n(rom_n),
 .rom_valid(rom_valid),.i_any(i_any),.iu(iu),.ic(ic),.image_ready(image_ready),.fault(fault));
module qw_commit_probe(input ck,rst_n,begin_v,auth_v,pw_v,dw_v,commit_v,ready,fault,
 input[9:0]pw_addr,input[2:0]dw_addr,input[15:0]commit_epoch);
 integer edge_id=0;
 always @(posedge ck)begin
  edge_id=edge_id+1;
  if(rst_n)begin
   if(begin_v)$display("QWEVENT|%0t|%m|%0d|0|INSTALL_BEGIN|0|0",$time,edge_id);
   if(auth_v)$display("QWEVENT|%0t|%m|%0d|0|INSTALL_AUTH|0|0",$time,edge_id);
   if(pw_v)$display("QWEVENT|%0t|%m|%0d|0|MACRO_PW_RECEIPT|%0d|0",$time,edge_id,pw_addr);
   if(dw_v)$display("QWEVENT|%0t|%m|%0d|0|MACRO_DW_RECEIPT|%0d|0",$time,edge_id,dw_addr);
   if(commit_v)$display("QWEVENT|%0t|%m|%0d|%0d|INSTALL_COMMIT|%0d|%0d",$time,edge_id,commit_epoch,ready,fault);
  end
 end
endmodule
bind qkd_program_commit qw_commit_probe stage1_probe
(.ck(ck),.rst_n(rst_n),.begin_v(begin_v),.auth_v(auth_v),.pw_v(pw_v),.dw_v(dw_v),
 .pw_addr(pw_addr),.dw_addr(dw_addr),.commit_v(commit_v),.ready(ready),.fault(fault),.commit_epoch(commit_epoch));
