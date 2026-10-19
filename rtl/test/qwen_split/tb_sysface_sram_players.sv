`timescale 1ns/1ps
module tb_sysface_sram_players;
 parameter NE=64,AW=$clog2(NE),MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,cfg_we=0,start=0,start_seg=0,halt=0;
 reg [AW:0] cfg_addr=0;reg[31:0]cfg_data=0;
 wire v0,v1,r0,r1,f0,f1;wire[2:0]p0,p1;wire[3:0]k0,k1;wire[4:0]b0,b1;
 ot_qwen_d2d_cal #(.NE(NE),.AW(AW)) refcal(ck,rst_n,cfg_we,cfg_addr,cfg_data,start,start_seg,halt,v0,p0,k0,b0,r0,f0);
 ot_qwen_d2d_cal_sram #(.NE(NE),.AW(AW),.MUT(MUT)) dut(ck,rst_n,cfg_we,cfg_addr,cfg_data,start,start_seg,halt,v1,p1,k1,b1,r1,f1);
 integer checks=0,events=0,errs=0;reg compare=0;
 task tick;begin @(posedge ck);#1;
 if(compare)begin checks++;if({v0,r0,f0}!={v1,r1,f1} || (v0 && {p0,k0,b0}!={p1,k1,b1}))begin
  if(errs<8)$display("MISMATCH check=%0d ref=%b/%b/%b/%h got=%b/%b/%b/%h",checks,v0,r0,f0,{p0,k0,b0},v1,r1,f1,{p1,k1,b1});errs++;end
 if(v0)events++;end @(negedge ck);end endtask
 task wr(input integer a,input[31:0]x);begin cfg_we=1;cfg_addr=a;cfg_data=x;tick();cfg_we=0;end endtask
 function automatic[31:0]word(input integer dt,last,p,k,b,rep);word=(dt<<18)|(last<<17)|(p<<14)|(k<<10)|(b<<5)|rep;endfunction
 task reset;begin compare=0;rst_n=0;cfg_we=0;start=0;halt=0;repeat(3)tick();rst_n=1;tick();end endtask
 task run(input integer seg,limit);integer n;begin compare=1;start_seg=seg;start=1;tick();start=0;n=0;while(r0 && n<limit)begin tick();n++;end
 if(r0)begin $display("TIMEOUT");errs++;end repeat(3)tick();compare=0;end endtask
 integer i,j;
 initial begin
 reset();
if(NE==64)begin
wr(0,32'h00080820);
wr(1,32'h71d40840);
wr(2,32'h6b980860);
wr(3,32'h6b980880);
wr(4,32'h6b9808a0);
wr(5,32'h6b9808c0);
wr(6,32'h6b9808e0);
wr(7,32'h6b980900);
wr(8,32'h6b980920);
wr(9,32'h6b980940);
wr(10,32'h6b980960);
wr(11,32'h6b980980);
wr(12,32'h6b9809a0);
wr(13,32'h6b9809c0);
wr(14,32'h6b9809e0);
wr(15,32'h6b980a00);
wr(16,32'h6b980a20);
wr(17,32'h6b980a40);
wr(18,32'h6b980a60);
wr(19,32'h6b980a80);
wr(20,32'h6b980aa0);
wr(21,32'h6b980ac0);
wr(22,32'h6b980ae0);
wr(23,32'h6b980b00);
wr(24,32'h6b980b20);
wr(25,32'h6b980b40);
wr(26,32'h6b980b60);
wr(27,32'h6b980b80);
wr(28,32'h6b980ba0);
wr(29,32'h6b980bc0);
wr(30,32'h6b980be0);
wr(31,32'h6b980c00);
wr(32,32'h6b980c20);
wr(33,32'h6b980c40);
wr(34,32'h6b980c60);
wr(35,32'h6b980c80);
wr(36,32'h6b9804a0);
wr(37,32'h05f404a0);
wr(38,32'h05f404a0);
wr(39,32'h05f404a0);
wr(40,32'h05f404a0);
wr(41,32'h05f404a0);
wr(42,32'h05f404a0);
wr(43,32'h05f404a0);
wr(44,32'h05f41000);
wr(45,32'h052a4080);
wr(46,32'h00095000);
wr(47,32'h03440000);
wr(48,32'h00064080);
wr(NE,46);end
if(NE==16)begin
wr(0,32'h0435c000);
wr(1,32'h00058800);
wr(2,32'h0005801f);
wr(3,32'h0007841f);
wr(4,32'h0341c000);
wr(5,32'h00058800);
wr(6,32'h0005801f);
wr(7,32'h0007841f);
wr(NE,4);end
 if(NE==32)begin for(i=0;i<NE;i++)wr(i,word(1,i==15 || i==31,i%8,i%16,i%24,i%3));wr(NE,16);end
 repeat(4)tick();run(1,400000);run(0,400000);run(1,400000);
 // Stop/restart during a real frame; restart must use cached SEG1 heads.
 start=1;start_seg=0;tick();start=0;repeat(7)tick();halt=1;tick();halt=0;repeat(4)tick();run(1,400000);
 // Every logical row, consecutive dt1, bursts, terminal row near row wrap.
 reset();for(i=0;i<NE;i++)wr(i,word(1,i==NE-1,i%8,i%16,i%24,i%3));wr(NE,NE-3);
 repeat(4)tick();run(0,1000);run(1,1000);
 // Reload with changed segment base; exactly four stopped edges suffice.
 wr(NE,NE-2);repeat(4)tick();run(1,1000);
 // Invalid early start never stalls or gets silently accepted.
 for(j=0;j<4;j++)begin reset();wr(0,word(1,1,0,0,0,0));wr(1,word(1,1,1,1,1,0));wr(NE,0);
 repeat(j)tick();start=1;tick();start=0;
 if(!f1)begin $display("PREFETCH_FAULT_MISSING stopped=%0d",j);errs++;end end
 if(errs)$display("SYSFACE_SRAM FAIL errors=%0d checks=%0d events=%0d NE=%0d MUT=%0d",errs,checks,events,NE,MUT);
 else $display("SYSFACE_SRAM PASS checks=%0d events=%0d NE=%0d MUT=%0d",checks,events,NE,MUT);
 $finish;end
endmodule
