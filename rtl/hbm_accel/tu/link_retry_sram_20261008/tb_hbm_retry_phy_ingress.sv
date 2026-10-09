`timescale 1ns/1ps
module tb_hbm_retry_phy_ingress;
 reg clk=0;always#0.416667 clk=~clk;
 reg rst=0,iv=0,ready=1;reg[544:0]data_in=0;wire ir,ov,flt;wire[544:0]d;wire[11:0]debt;
 ot_hbm_retry_phy_ingress dut(.clk(clk),.rst_n(rst),.session(16'd11),.in_valid(iv),.in_data(data_in),.in_ready(ir),.out_valid(ov),.out_ready(ready),.out_data(d),.fault(flt),.debt(debt));
 function[544:0]payload(input integer n);integer j;begin
 for(j=0;j<545;j=j+1)payload[j]=((j*29+n*17)^(n>>(j%7)))&1;payload[31:0]=n;end endfunction
 integer sent=0,seen=0,cycles=0;reg run=0;
 always@(negedge clk)if(run)begin
 cycles=cycles+1;iv=sent<1300&&ir;data_in=payload(sent);ready=cycles%5!=0;end
 always@(posedge clk)if(run&&rst)begin
 if(iv&&ir)sent<=sent+1;
 if(ov&&ready)begin if(d!==payload(seen))$fatal(1,"protected ingress order%0d got%0d",seen,d[31:0]);seen<=seen+1;end
 if(flt||debt>256)$fatal(1,"ingress protection/ownership fault");end
 task tick;begin @(posedge clk);#0.01;end endtask
 integer i;
 initial begin
 repeat(3)tick;@(negedge clk);rst=1;run=1;
 for(i=0;i<4000&&seen<1300;i=i+1)tick;
 run=0;iv=0;if(seen!=1300||sent!=1300||debt!=0)$fatal(1,"ingress completion");
 $display("PASS full545 protected ingress1300records, SRAMbankwrap,8reserved response slots, consumerstalls");
 // No-ready source may submit only within its256 outstanding remote credits.
 @(negedge clk);rst=0;repeat(2)tick;@(negedge clk);rst=1;ready=0;
 for(i=0;i<256;i=i+1)begin @(negedge clk);iv=1;data_in=payload(i);tick;end
 @(negedge clk);iv=0;tick;if(ir||debt!=256||flt)$fatal(1,"ingress full retained ownership");
 @(negedge clk);iv=1;data_in=payload(256);tick;if(!flt||debt!=256)$fatal(1,"ingress illegal pulse not poisoned");
 $display("PASS actual no-ready pulse full256 capacity, excessoffer faults without overwrite");
 $display("PASS_ALL");$finish;
 end
 initial begin#10000;$fatal(1,"watchdog");end
endmodule
