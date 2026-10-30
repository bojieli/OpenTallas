`timescale 1ns/1ps
module tb_static_dma_cmd_dispatch;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,v=0,busy=0,bad=0;reg[307:0]cmd=0;wire lv,sv,fault;integer src,dst,checks=0;
 ot_hbm_static_dma_cmd_dispatch u(clk,rst,v,cmd,busy,bad,lv,sv,fault);
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 initial begin
 for(src=0;src<4;src=src+1)for(dst=0;dst<4;dst=dst+1)begin
 rst=0;v=0;tick();rst=1;v=1;cmd='1;cmd[65:64]=2'(src);cmd[158:157]=2'(dst);#1;
 if(lv!==(src==0&&dst==1)||sv!==(src==1&&dst==0))$fatal(1,"DISPATCH_FIELD_OFFSET src=%0d dst=%0d",src,dst);
 tick();if(fault===((src==0&&dst==1)||(src==1&&dst==0)))$fatal(1,"DISPATCH_BAD_DIRECTION");checks=checks+1;
 end
 rst=0;v=0;tick();rst=1;cmd='1;cmd[65:64]=1;cmd[158:157]=0;busy=1;v=1;#1;if(lv||sv)$fatal(1,"DISPATCH_BUSY_ISSUED");tick();if(!fault)$fatal(1,"DISPATCH_BUSY_NOT_FAULTED");
 $display("PASS SHARED_CW308_DISPATCH directions=%0d correct227extraction/doubleoffset_poison/busy_fault noready",checks);$finish;
 end
endmodule
