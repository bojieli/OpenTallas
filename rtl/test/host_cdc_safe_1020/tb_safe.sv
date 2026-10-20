`timescale 1ns/1ps
module tb_safe;
 reg wclk=0,rclk=0;always #0.5 wclk=~wclk;always #0.71 rclk=~rclk;
 reg rst=0,iv=0,ocr=0;reg[545:0] id=0;
 wire ic0,ic1,wf0,wf1,ov0,ov1,rf0,rf1;wire[545:0] od0,od1;
 ot_qwen_die_cdc_ch #(.W(546),.PIPE(2)) legacy(.wclk(wclk),.wrst_n(rst),.i_v(iv),.i_d(id),.i_cr(ic0),.w_fault(wf0),.rclk(rclk),.rrst_n(rst),.o_v(ov0),.o_d(od0),.o_cr(ocr),.r_fault(rf0));
 ot_host_die_cdc_sram safe(.wclk(wclk),.wrst_n(rst),.i_v(iv),.i_d(id),.i_cr(ic1),.w_fault(wf1),.rclk(rclk),.rrst_n(rst),.o_v(ov1),.o_d(od1),.o_cr(ocr),.r_fault(rf1));
 integer cred=4,seq=0,sent=0,got=0,wcy=0,returns=0,errors=0,winr=0,wingot=0;
 bit tput;initial tput=$test$plusargs("TPUT");reg[31:0]rng=32'hf00d;
 reg[545:0] expected[0:8191];integer wr=0,rd=0;
 task err(input string msg);begin $display("FAIL %s time=%0t sent=%0d got=%0d",msg,$time,sent,got);$fatal;end endtask
 always @(negedge wclk)begin
  rng=(rng>>1)^((rng&1)?32'hd0000001:0);wcy=wcy+1;
  if(!rst)begin cred=4;iv=0;end
  else begin
   if(ic0)cred=cred+1;
   iv=(wcy>35)&&(cred>0)&&(tput||rng[1:0]!=0)&&(wcy<3900 || (wcy>4250&&wcy<7800));
   if(iv)begin
    cred=cred-1;seq=seq+1;id={17{32'(seq)}} ^ (546'(rng)<<2);expected[wr]=id;wr=wr+1;sent=sent+1;
   end
  end
 end
 always @(posedge wclk)begin #0.01;if(rst&&ic0!==ic1)err("credit edge changed");if(rst&&(wf0||wf1))err("write fault");end
 always @(posedge rclk)begin
  #0.01;
  if(rst)begin
   if(wcy>=5000&&wcy<7500)begin winr=winr+1;if(ov1)wingot=wingot+1;end
   if(ov0!==ov1)err("output valid edge changed");
   if(ov0)begin
    if(od0!==od1)err("SRAM transfer value mismatch");
    if(od1!==expected[rd])err("ordered scoreboard mismatch");
    rd=rd+1;got=got+1;returns=returns+1;
   end
   if(rf0||rf1)err("read credit fault");
  end
 end
 always @(negedge rclk)begin
  ocr=0;
  if(!rst)returns=0;
  else if(returns>0 && (tput||rng[2:1]!=0))begin returns=returns-1;ocr=1;end
 end
 initial begin
  #5;rst=1;
  wait(wcy==4100);#0.17;rst=0;#6;rd=0;wr=0;rst=1;
  wait(wcy==8200);#3;
  if(got<1000||rd!=wr)err("traffic incomplete");
  if(tput)begin if(wingot*2<winr)err("throughput below one frame per two read edges");
  $display("PASS HOST_CDC_SAFE_TPUT received=%0d read_edges=%0d budget_frames_per_read_edge=0.5",wingot,winr);end
  $display("PASS HOST_CDC_SAFE exact-cycle miter two clock domains sent=%0d received=%0d reset-flush=1",sent,got);$finish;
 end
endmodule
