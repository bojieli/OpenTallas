`timescale 1ns/1ps
module tb_host_rx_admission;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,rv=0,reserved=1,valid=1,hcr=0,ccr=0;reg[4:0]icrn=0;reg[527:0]rd=0;
 wire rcr,hv,cv,iv,fault,open,quiet,deferred;wire[511:0]hd,cd,id;wire[1:0]ic;wire[23:0]cr,pc;
 qkd_host_rx_class_admission #(.MUT(MUT))dut(.ck(ck),.rst_n(rst_n),.die_id(3'd0),.rx_v(rv),.rx_d(rd),.rx_cr(rcr),.native_reserved(reserved),.ownership_valid(valid),.host_v(hv),.host_d(hd),.host_cr(hcr),.ctrl_v(cv),.ctrl_d(cd),.ctrl_cr(ccr),.ing_v(iv),.ing_cls(ic),.ing_d(id),.ing_crn(icrn),.credit_return(cr),.peer_credit(pc),.fault(fault),.admission_open(open),.launch_quiet(quiet),.deferred(deferred));
 integer hn=0,inn=0,cn=0;reg isolated=0;
 always @(posedge ck)if(rst_n)begin
  if(isolated&&(hv||iv))$fatal(1,"RESERVATION_LEAK");
  if(hv)begin if(hd!=512'(100+hn))$fatal(1,"HOST_ORDER");hn=hn+1;end
  if(iv)begin if(id!=512'(200+inn)||ic!=2'(inn%3))$fatal(1,"ING_ORDER");inn=inn+1;end
  if(cv)begin if(cd!=512'd999)$fatal(1,"CTRL_DATA");cn=cn+1;end
 end
 task tick(input integer n);repeat(n)@(negedge ck);endtask
 task send(input integer cls,input integer data);begin rv=1;rd={4'(cls),12'd0,512'(data)};tick(1);rv=0;end endtask
 initial begin
  tick(3);rst_n=1;tick(8);isolated=1;
  for(integer j=0;j<4;j++)send(0,100+j);
  for(integer j=0;j<16;j++)send(2+j%3,200+j);
  send(1,999);tick(12);
  if(hn||inn||cn!=1||!quiet||!deferred||fault)$fatal(1,"HELD_EXACT");
  isolated=0;reserved=0;tick(30);
  if(hn!=4||inn!=16||deferred||fault)$fatal(1,"RELEASE_EXACT h%0d i%0d f%0d",hn,inn,fault);
  hcr=1;icrn=16;tick(1);hcr=0;icrn=0;tick(1);
  repeat(3)begin hcr=1;tick(1);hcr=0;tick(1);end
  tick(10);if(fault)$fatal(1,"CREDIT_ACCOUNT");
  reserved=1;tick(5);isolated=1;send(0,104);tick(12);if(!deferred)$fatal(1,"SECOND_RESERVATION");
  valid=0;reserved=0;tick(12);if(!deferred||open)$fatal(1,"FAULT_RESERVATION_UNLOCK");
  $display("PASS actual_RX HOST4 ING16 CTRLlive retainedcredit/order faultlocked");$finish;
 end
 initial begin #50000;$fatal(1,"TIMEOUT");end
endmodule
