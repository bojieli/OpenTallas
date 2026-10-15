`timescale 1ns/1ps
`default_nettype none
// Host initialization adapter for the distinct32-SM two-word programme family.
// Final frame/begin/commit B responses wait for actual tagged target ACKs.
// Normal execution sees only one fixed launch and staged range/epoch fields.
module ot_hbm_host_sm_pair_install #(
 parameter[7:0]TARGET_BASE=128,parameter[31:0]PARTICIPATING=32'hffffffff,
 parameter integer MUT=0
)(
 input wire clk,rst_n,
 input wire[11:0]s_awaddr,input wire s_awvalid,output reg s_awready,
 input wire[31:0]s_wdata,input wire[3:0]s_wstrb,input wire s_wvalid,output reg s_wready,
 output reg[1:0]s_bresp,output reg s_bvalid,input wire s_bready,
 input wire[11:0]s_araddr,input wire s_arvalid,output reg s_arready,
 output reg[31:0]s_rdata,output reg[1:0]s_rresp,output reg s_rvalid,input wire s_rready,
 output reg cfg_begin_v,cfg_commit_v,cfg_we,
 output reg[7:0]cfg_target,output reg[15:0]cfg_epoch,
 output reg[10:0]cfg_addr,output reg[255:0]cfg_data,
 input wire cfg_ack_v,input wire[1:0]cfg_ack_kind,input wire[7:0]cfg_ack_target,
 input wire[10:0]cfg_ack_addr,input wire[15:0]cfg_ack_epoch,input wire[1:0]cfg_ack_resp,
 input wire[31:0]target_ready,target_active,target_fault,
 input wire[31:0][15:0]target_ready_epoch,
 output reg launch_v,output reg[15:0]launch_epoch,
 output reg[9:0]start_base,output reg[10:0]start_limit,
 output reg[15:0]start_loops,output reg fault);
 reg rm,rl,live;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)begin rm<=0;rl<=0;end else begin rm<=1;rl<=rm;end
 reg av,wv,arv,awr,wr,arr;reg[11:0]aa_pin,ar_pin;reg[31:0]wd_pin;reg[3:0]ws_pin;
 reg ackv;reg[1:0]ackkind,ackresp;reg[7:0]acktarget;reg[10:0]ackaddr;reg[15:0]ackepoch;
 reg[31:0]ready_q,active_q,fault_q;reg[31:0][15:0]epochs_q;
 always @(posedge clk)begin
  av<=s_awvalid;aa_pin<=s_awaddr;wv<=s_wvalid;wd_pin<=s_wdata;ws_pin<=s_wstrb;
  arv<=s_arvalid;ar_pin<=s_araddr;awr<=s_awready;wr<=s_wready;arr<=s_arready;
  ackv<=cfg_ack_v;ackkind<=cfg_ack_kind;acktarget<=cfg_ack_target;ackaddr<=cfg_ack_addr;ackepoch<=cfg_ack_epoch;ackresp<=cfg_ack_resp;
  ready_q<=target_ready;active_q<=target_active;fault_q<=target_fault;epochs_q<=target_ready_epoch;
 end
 wire take_aw=live&&av&&awr,take_w=live&&wv&&wr,take_ar=live&&arv&&arr;
 reg ah,wh,rh;reg[11:0]aa,ra;reg[31:0]wd;reg[3:0]ws;
 reg[223:0]assembly;reg[2:0]piece;reg selected,end_reached;
 reg[7:0]selected_target;reg[10:0]pc;
 reg[31:0]begun;reg[31:0][15:0]install_epochs;
 reg pending;reg[1:0]pending_kind;reg[7:0]pending_target;reg[10:0]pending_addr;reg[15:0]pending_epoch;
 reg[9:0]base;reg[10:0]limit;reg[15:0]loops,required_epoch;
 reg range_set,loops_set,epoch_set,launched;reg[31:0]seen_active;
 reg[31:0]epoch_matches;reg aggregate_ready;reg[2:0]guard;
 wire execute=ah&&wh&&!pending&&!s_bvalid;
 wire[7:0]selected_index=selected_target-TARGET_BASE;
 function automatic valid_target(input[7:0]t);
 begin valid_target=0;for(integer n=0;n<32;n=n+1)if(t==TARGET_BASE+8'(n)&&PARTICIPATING[n])valid_target=1;end
 endfunction
 wire common_write_ok=ws==15&&!fault&&!launched&&!(|(active_q&PARTICIPATING))&&!(|(fault_q&PARTICIPATING));
 wire frame_ok=selected&&!end_reached&&begun[selected_index]&&common_write_ok;
 // Payload pins are unreset; only reset valid pins authorize a transfer.
 always @(posedge clk)begin
  if(execute&&aa==12'hf24&&frame_ok&&piece==7)begin
   cfg_data<={wd,assembly};cfg_addr<=pc;cfg_target<=selected_target;cfg_epoch<=install_epochs[selected_index];
  end
  if(execute&&common_write_ok&&(aa==12'hf4c||aa==12'hf50)&&piece==0)begin
   cfg_target<=wd[7:0];cfg_epoch<=wd[23:8];cfg_addr<=0;
  end
 end
 always @(posedge clk or negedge rl)begin
 if(!rl)begin
  live<=0;s_awready<=0;s_wready<=0;s_arready<=0;ah<=0;wh<=0;rh<=0;
  s_bvalid<=0;s_bresp<=0;s_rvalid<=0;s_rresp<=0;s_rdata<=0;
  cfg_begin_v<=0;cfg_commit_v<=0;cfg_we<=0;launch_v<=0;fault<=0;
  selected<=0;end_reached<=0;piece<=0;pc<=0;selected_target<=TARGET_BASE;
  begun<=0;install_epochs<=0;pending<=0;pending_kind<=0;pending_target<=0;pending_addr<=0;pending_epoch<=0;
  base<=0;limit<=0;loops<=0;required_epoch<=0;range_set<=0;loops_set<=0;epoch_set<=0;
  launched<=0;seen_active<=0;epoch_matches<=0;aggregate_ready<=0;guard<=0;
  launch_epoch<=0;start_base<=0;start_limit<=0;start_loops<=0;
 end else begin
  live<=1;cfg_begin_v<=0;cfg_commit_v<=0;cfg_we<=0;launch_v<=0;
  s_awready<=!s_awready&&!ah&&!take_aw&&!pending&&!s_bvalid;
  s_wready<=!s_wready&&!wh&&!take_w&&!pending&&!s_bvalid;
  s_arready<=!s_arready&&!rh&&!take_ar&&!s_rvalid;
  if(take_aw)begin ah<=1;aa<=aa_pin;end
  if(take_w)begin wh<=1;wd<=wd_pin;ws<=ws_pin;end
  if(take_ar)begin rh<=1;ra<=ar_pin;end
  if(s_bvalid&&s_bready)s_bvalid<=0;
  if(s_rvalid&&s_rready)s_rvalid<=0;
  if(guard!=0)guard<=guard-1'b1;
  for(integer n=0;n<32;n=n+1)epoch_matches[n]<=epochs_q[n]==required_epoch;
  aggregate_ready<=((ready_q&epoch_matches&PARTICIPATING)==PARTICIPATING)&&!(|(active_q&PARTICIPATING))&&!(|(fault_q&PARTICIPATING));
  if(launched)begin
   seen_active<=seen_active|active_q;
   if((seen_active&PARTICIPATING)==PARTICIPATING&&!(|(active_q&PARTICIPATING)))begin launched<=0;seen_active<=0;end
  end
  if(rh)begin
   rh<=0;s_rvalid<=1;s_rresp<=0;
   case(ra)
    12'hf30:s_rdata<={20'b0,guard,piece,pending,launched,aggregate_ready,epoch_set,range_set,fault};
    12'hf4c:s_rdata<=begun;
    12'hf50,12'hf54:s_rdata<=ready_q;
    12'hf58:s_rdata<={16'b0,required_epoch};
    default:begin s_rdata<=32'hffffffff;s_rresp<=2;end
   endcase
  end
  if(live&&ackv)begin
   if(!pending||ackkind!=pending_kind||acktarget!=pending_target||ackaddr!=pending_addr||ackepoch!=pending_epoch)begin
    fault<=1;if(pending)begin pending<=0;s_bvalid<=1;s_bresp<=2;end
   end
   else begin
    pending<=0;s_bvalid<=1;s_bresp<=ackresp;guard<=4;
    if(ackresp>=2)fault<=1;
    else case(pending_kind)
     1:begin begun[pending_target-TARGET_BASE]<=1;install_epochs[pending_target-TARGET_BASE]<=pending_epoch;end
     2:begun[pending_target-TARGET_BASE]<=0;
     0:begin
      if(pc[10])begin pc[10]<=0;if(pc[9:0]==1023)end_reached<=1;else pc[9:0]<=pc[9:0]+1'b1;end
      else pc[10]<=1;
     end
     default:begin fault<=1;end
    endcase
   end
  end
  if(execute)begin
   ah<=0;wh<=0;s_bvalid<=1;s_bresp<=0;
   if(!common_write_ok)begin fault<=1;s_bresp<=2;end
   else case(aa)
    12'hf20:begin
     if(piece!=0||wd[31:19]!=0||!valid_target(wd[7:0]))begin fault<=1;s_bresp<=2;end
     else begin selected_target<=wd[7:0];pc<=wd[18:8];selected<=1;end_reached<=0;end
    end
    12'hf24:begin
     if(!frame_ok)begin fault<=1;s_bresp<=2;end
     else begin
      piece<=piece+1'b1;
      if(piece<7)assembly[piece*32+:32]<=wd;
      else begin
       cfg_we<=1;pending<=MUT==1?0:1;s_bvalid<=MUT==1?1:0;
       pending_kind<=0;pending_target<=selected_target;pending_addr<=pc;pending_epoch<=install_epochs[selected_index];
      end
     end
    end
    12'hf4c,12'hf50:begin
     if(piece!=0||wd[31:24]!=0||wd[23:8]==0||!valid_target(wd[7:0])||
       (aa==12'hf50&&(!begun[wd[7:0]-TARGET_BASE]||install_epochs[wd[7:0]-TARGET_BASE]!=wd[23:8])))begin fault<=1;s_bresp<=2;end
     else begin
      cfg_begin_v<=aa==12'hf4c;cfg_commit_v<=aa==12'hf50;pending<=1;s_bvalid<=0;
      pending_kind<=aa==12'hf4c ? 1:2;pending_target<=wd[7:0];pending_addr<=0;pending_epoch<=wd[23:8];
     end
    end
    12'hf28:begin
     if(piece!=0||wd[31:25]!=0||wd[24:12]>1024||wd[11:0]>=wd[24:12])begin fault<=1;s_bresp<=2;end
     else begin base<=wd[9:0];limit<=wd[22:12];range_set<=1;guard<=4;end
    end
    12'hf2c:begin
     if(piece!=0||wd[31:16]!=0||wd[15:0]==0||!range_set)begin fault<=1;s_bresp<=2;end
     else begin loops<=wd[15:0];loops_set<=1;guard<=4;end
    end
    12'hf58:begin
     if(piece!=0||wd[31:16]!=0||wd[15:0]==0)begin fault<=1;s_bresp<=2;end
     else begin required_epoch<=wd[15:0];epoch_set<=1;guard<=4;end
    end
    12'hf30:begin
     if(wd!=1||piece!=0||guard!=0||!range_set||!loops_set||!epoch_set||
       !(MUT==2?1'b1:aggregate_ready)||begun!=0)begin fault<=1;s_bresp<=2;end
     else begin launch_v<=1;launch_epoch<=required_epoch;start_base<=base;start_limit<=limit;start_loops<=loops;launched<=1;seen_active<=0;guard<=7;end
    end
    default:begin fault<=1;s_bresp<=2;end
   endcase
  end
 end end
endmodule
`default_nettype wire
