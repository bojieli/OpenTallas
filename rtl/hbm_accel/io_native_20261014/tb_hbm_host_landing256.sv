`timescale 1ns/1ps
module tb_hbm_host_landing256;
 reg clk=0,rst_n=0,in_v=0,out_ready=0;reg[544:0]in_data=0;
 wire out_v,pop,fault;wire[511:0]out_data;
 integer checks=0,bad=0,got=0,lap,i,k,cycles=0;
 ot_hbm_host_landing256 dut(.*);
 function[511:0]word(input integer n);integer b;begin for(b=0;b<512;b=b+1)word[b]=((n*17+b*63)^(n>>(b%10)))&1;word[31:0]=n;end endfunction
 task tick;begin #0.416;clk=1;#0.001;
 if(rst_n && fault!==1'b0)bad=bad+1;
 #0.416;clk=0;cycles=cycles+1;end endtask
 initial begin
 repeat(4)tick;rst_n=1;
 for(lap=0;lap<2;lap=lap+1)begin
 out_ready=0;
 for(i=0;i<256;i=i+1)begin in_v=1;in_data={33'd0,word(lap*256+i)};tick;end
 in_v=0;repeat(3)tick;
 checks=checks+1;if(dut.count!==9'd256)bad=bad+1;
 for(i=0;i<256;i=i+1)begin
 k=0;while(!out_v&&k<5)begin tick;k=k+1;end
 checks=checks+1;if(out_v!==1'b1||out_data!==word(lap*256+i))bad=bad+1;
 // Hold the actual SRAM head across an external consumer stall.
 repeat(2)begin tick;checks=checks+1;if(out_v!==1'b1||out_data!==word(lap*256+i))bad=bad+1;end
 out_ready=1;tick;out_ready=0;got=got+1;
 end
 repeat(3)tick;checks=checks+1;if(dut.count!==9'd0||out_v!==1'b0)bad=bad+1;
 end
 if(bad==0)$display("HBM_HOST_LANDING_PASS words%0d checks%0d cycles%0d full256 two_laps_uninitialized_real_SRAM",got,checks,cycles);
 else $display("HBM_HOST_LANDING_FAIL bad%0d words%0d checks%0d fault%h",bad,got,checks,fault);
 $finish;
 end
endmodule
