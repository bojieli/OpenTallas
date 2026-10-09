`timescale 1ns/1ps
module tb_hbm_replay_sram;
 parameter TB_MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst=0,wv=0,rv=0;
 reg[550:0] wd=0;reg[11:0] ws=0,rs=0;reg[15:0] we=7,re=7;
 wire ov,ce,ue;wire[550:0] od;wire[11:0] os;wire[15:0] oe;
 ot_hbm_replay_sram #(.MUT(TB_MUT)) dut(.clk(clk),.rst_n(rst),.w_valid(wv),.w_data(wd),.w_seq(ws),.w_session(we),
 .r_valid(rv),.r_seq(rs),.r_session(re),.o_valid(ov),.o_data(od),.o_seq(os),.o_session(oe),.o_ce(ce),.o_ue(ue));
 function[550:0] data(input integer n);integer j;begin
 for(j=0;j<551;j=j+1)data[j]=(j*13+n*23)^(n>>(j%5));data[31:0]=n;end endfunction
 task tick;begin @(posedge clk);#1;end endtask
 task request(input[11:0] s,input[15:0] e);begin @(negedge clk);rv=1;rs=s;re=e;tick;@(negedge clk);rv=0;end endtask
 task response(input[11:0] s,input[15:0] e,input c,input u);
 integer waitn;begin waitn=0;while(!ov && waitn<10)begin tick;waitn=waitn+1;end
 if(!ov || os!==s || oe!==e || ce!==c || ue!==u || (!u && od!==data(s)) || (u && od!==0))$fatal(1,"bad replay response s%0d os%0d ce%b ue%b n%0d",s,os,ce,ue,waitn);
 if(waitn!=4)$fatal(1,"response latency%0d expected4",waitn);tick;end endtask
 integer i;integer seen=0;
 initial begin
 tick;@(negedge clk);rst=1;
 for(i=0;i<512;i=i+1)begin @(negedge clk);wv=1;ws=i;wd=data(i);tick;end
 @(negedge clk);wv=0;repeat(3)tick;
 for(i=0;i<512;i=i+1)begin request(i,7);response(i,7,0,0);end
 $display("PASS 512 full579-bit records protected in16 realSRAM macros; read4cycles");
 // Single-bit data corruption corrected; two-bit corruption poisoned.
 dut.g_bank[0].g_macro[0].u_mem.arr[4][17]=~dut.g_bank[0].g_macro[0].u_mem.arr[4][17];
 request(4,7);response(4,7,1,0);
 dut.g_bank[0].g_macro[0].u_mem.arr[4][18]=~dut.g_bank[0].g_macro[0].u_mem.arr[4][18];
 request(4,7);response(4,7,0,1);
 // Protection includes parity and session/sequence, not just TU payload.
 dut.g_bank[2].g_macro[3].u_mem.arr[2][25]=~dut.g_bank[2].g_macro[3].u_mem.arr[2][25];
 request(258,7);response(258,7,1,0);
 request(5,8);response(5,8,0,1);
 request(517,7);response(517,7,0,1);
 $display("PASS single data/check correction, double poison, staleepoch and stalealias rejection");
 // Back-to-back reads across bank boundaries; every output reserves a slot.
 seen=0;@(negedge clk);rv=1;rs=120;re=7;
 for(i=0;i<40;i=i+1)begin
  tick;if(ov)begin if(os!==120+seen || od!==data(120+seen) || ue)$fatal(1,"stream mismatch");seen=seen+1;end
  @(negedge clk);rs=rs+1;
 end
 rv=0;repeat(6)begin tick;if(ov)begin if(os!==120+seen || od!==data(120+seen)||ue)$fatal(1,"drain mismatch");seen=seen+1;end end
 if(seen!=40)$fatal(1,"stream count%0d",seen);
 $display("PASS one read perclock across banks, exact transactiontags");
 $display("PASS_ALL");$finish;
 end
 initial begin #100000;$fatal(1,"watchdog");end
endmodule
