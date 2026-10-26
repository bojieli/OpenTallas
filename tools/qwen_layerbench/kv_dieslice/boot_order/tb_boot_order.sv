`timescale 1ns/1ps
module tb_boot_order;
 `include "d2d_cal_image_mu.svh"
 reg ck=0;always #0.4165 ck=~ck;
 reg rst_n=0,request=0,all_installed=0,program_ready=0,btx=0,brx=0;
 reg [5:0]ba=0;reg[31:0]bd=0;
 integer mode=0,cyc=0,first_epoch=-1,first_fault=-1,starts=0,comparisons=0;
 wire ordered,legacy;
 wire installed=(mode==4)?all_installed:(all_installed&&program_ready);
 qkd_d2d_boot_event_bridge #(.ENABLE(1)) orderer(ck,rst_n,request,installed,ordered);
 qkd_d2d_boot_event_bridge default_legacy(ck,rst_n,request,installed,legacy);
 wire epoch_go=(mode==0||mode==3)?legacy:ordered;
 wire tx,rx,cs,seg,ready,running,adm,tok,fault;wire[5:0]addr,layer;wire[31:0]data;
 wire rtx,rrx,rcs,rseg,rready,rrunning,radm,rtok,rfault;wire[5:0]raddr,rlayer;wire[31:0]rdata;
 qkd_d2d_cal_seq_pin_bc4 dut(.ck(ck),.rst_n(rst_n),.reload(1'b0),.epoch_go(epoch_go),.halt(1'b0),.bcfg_tx_we(btx),.bcfg_rx_we(brx),.bcfg_addr(ba),.bcfg_data(bd),.cfg_tx_we(tx),.cfg_rx_we(rx),.cfg_addr(addr),.cfg_data(data),.cal_start(cs),.cal_seg(seg),.cal_ready(ready),.running(running),.layer(layer),.adm_done(adm),.tok_start(tok),.fault(fault));
 qkd_d2d_cal_seq_pin_bc4 ref_dut(.ck(ck),.rst_n(rst_n),.reload(1'b0),.epoch_go(request),.halt(1'b0),.bcfg_tx_we(btx),.bcfg_rx_we(brx),.bcfg_addr(ba),.bcfg_data(bd),.cfg_tx_we(rtx),.cfg_rx_we(rrx),.cfg_addr(raddr),.cfg_data(rdata),.cal_start(rcs),.cal_seg(rseg),.cal_ready(rready),.running(rrunning),.layer(rlayer),.adm_done(radm),.tok_start(rtok),.fault(rfault));
 initial begin
 void'($value$plusargs("MODE=%d",mode));repeat(8)@(negedge ck);rst_n=1;
 for(cyc=0;cyc<5000;cyc=cyc+1)begin
  @(negedge ck);request=(cyc==100);btx=0;brx=0;
  all_installed=cyc>=(mode<2?80:380);program_ready=(mode!=5)&&cyc>=(mode<2?80:420);
  if(cyc>=(mode<2?8:300)&&cyc<(mode<2?74:366))begin
   integer w;w=cyc-(mode<2?8:300);btx=!w[0];brx=w[0];ba=w<64?w/2:32;
   if(w<64)bd=w[0]?D2D_CAL_K_RX_IMG[32*(w/2)+:32]:D2D_CAL_K_TX_IMG[32*(w/2)+:32];
   else bd=w[0]?D2D_CAL_K_RX_SEG2:D2D_CAL_K_TX_SEG2;
  end
  #0.01;
  if(legacy!==request)$fatal(1,"legacy mode changed");
  if(mode<2)begin
   if({tx,rx,addr,data,cs,seg,ready,running,layer,adm,tok,fault}!=={rtx,rrx,raddr,rdata,rcs,rseg,rready,rrunning,rlayer,radm,rtok,rfault})$fatal(1,"normal configured cycle changed mode%0d cyc%0d",mode,cyc);
   comparisons++;
  end
  if(epoch_go&&first_epoch<0)first_epoch=cyc;
  if(fault&&first_fault<0)first_fault=cyc;
  starts+=cs;
 end
 case(mode)
  0,1:if(fault||first_epoch!=100)$fatal(1,"normalbootbad");
  2:if(fault||first_epoch!=420||starts==0)$fatal(1,"accepted-install ordering bad");
  3:if(!fault||!dut.f_early||first_fault!=176)$fatal(1,"early bypass mutant notcaught");
  4:if(first_epoch>=420||first_epoch<0)$fatal(1,"cfg-only substitute mutant notcaught");
  5:if(first_epoch!=-1||starts!=0)$fatal(1,"unaccepted programme emittedboot");
 endcase
 $display("BOOT_ORDER_EXPECTED mode%0d compared%0d first_epoch%0d first_fault%0d starts%0d early%0d",mode,comparisons,first_epoch,first_fault,starts,dut.f_early);$finish;
 end
endmodule
