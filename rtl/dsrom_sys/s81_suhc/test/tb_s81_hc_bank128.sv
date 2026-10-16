`timescale 1ns/1ps
module tb_s81_hc_bank128;
 reg ck=0;always #5 ck=~ck;
 reg rst=0,en=1,push,pop;reg[511:0]d;
 wire[511:0]refhead,head;wire rh,h,ro,o;
 ot_s81_hc_ccf_bankpipe_bank refbank(.clk(ck),.srs(rst),.pop_i(pop),.push_i(push),.data_i(d),.head_o(refhead),.hv_o(rh),.ovf_o(ro));
 ot_s81_hc_ccf_bankpipe_bank128 dut(.clk(ck&en),.srs(rst),.pop_i(pop),.push_i(push),.data_i(d),.head_o(head),.hv_o(h),.ovf_o(o));
 integer errors=0,checks=0,stop=0;
 initial begin
  if($value$plusargs("STOP=%d",stop))begin end
  for(integer c=0;c<3000;c=c+1)begin
   @(negedge ck);rst=(c>=5&&!(c>=1500&&c<1510));
   // Fill the real SRAM, drain, then random overlap/bypass/overflow/reset.
   push=(c<80)?1:((c<160)?0:($urandom_range(0,3)!=0));
   pop=(c<80)?0:((c<160)?1:($urandom_range(0,3)!=0));
   for(integer b=0;b<16;b=b+1)d[b*32+:32]=$random;
   if(stop&&c>2400)en=0;
   @(posedge ck);#1;
   if(c>15&&!(c>=1500&&c<1525))begin
    checks=checks+1;
    if({rh,ro}!=={h,o}||(rh&&refhead!==head))errors=errors+1;
   end
  end
  $display("BANK128 checks=%0d errors=%0d",checks,errors);
  if(errors)$fatal(1,"BANK128_FAIL");
  $display("BANK128_PASS");$finish;
 end
endmodule
