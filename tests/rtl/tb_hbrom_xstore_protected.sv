`timescale 1ns/1ps
// TEST ONLY synchronous masked SRAM; no macro timing or protection claim.
module ot_sram_1r1w_128x256_m1_r2c2(input clk,r_ce_in,input[6:0]r_addr_in,output reg[255:0]rd_out,
 input w_ce_in,input[6:0]w_addr_in,input[255:0]wd_in,w_mask_in,
 input[1:0]rr_en,input[11:0]rr_addr,input[1:0]cr_en,input[15:0]cr_sel);
 reg[255:0]mem[0:127];integer i;
 initial for(i=0;i<128;i=i+1)mem[i]=0;
 always @(posedge clk)begin
  if(r_ce_in)rd_out<=mem[r_addr_in];
  if(w_ce_in)mem[w_addr_in]<=(mem[w_addr_in]&~w_mask_in)|(wd_in&w_mask_in);
 end
endmodule
module xcase #(parameter SP=0,parameter FULL_SWEEP=0)(output reg done);
 reg clk=0;always #5 clk=~clk;
 reg rst=0,re=0,we=0;reg[6:0]ra=0,wa=0;reg[1:0]oh=0;reg[2047:0]wd=0;
 wire rv,ce,fault,pending;wire[787:0]rd;
 ot_hbrom_xstore_protected #(.SP(SP))dut(clk,rst,re,ra,we,wa,oh,wd,rv,rd,ce,fault,pending);
 reg[787:0]expected=0;integer beat,b,f,n,w,bitno,a,z;integer words;
 task tick;begin @(posedge clk);#1;end endtask
 task flip(input integer position);
  integer bank,bitoff;begin bank=position/256;bitoff=position%256;
   case(bank)
    0:dut.g_macro[0].u_x.mem[0][bitoff]=~dut.g_macro[0].u_x.mem[0][bitoff];
    1:dut.g_macro[1].u_x.mem[0][bitoff]=~dut.g_macro[1].u_x.mem[0][bitoff];
    2:dut.g_macro[2].u_x.mem[0][bitoff]=~dut.g_macro[2].u_x.mem[0][bitoff];
    3:dut.g_macro[3].u_x.mem[0][bitoff]=~dut.g_macro[3].u_x.mem[0][bitoff];
   endcase
  end
 endtask
 task read_check(input integer kind);
  begin
   @(negedge clk);re=1;tick();@(negedge clk);re=0;
   tick();if(rv)$fatal(1,"early response1");tick();if(rv)$fatal(1,"early response2");tick();
   if(kind<2)begin
    if(!rv||rd!==expected||ce!==(kind==1))$fatal(1,"read mismatch SP%0d kind%0d",SP,kind);
   end else if(rv)$fatal(1,"UE leaked output");
   tick();if(kind==2&&!fault)$fatal(1,"UE not sticky");
  end
 endtask
 initial begin
  done=0;words=(SP==3)?14:13;repeat(2)tick();@(negedge clk);rst=1;
  // repeated and reversed beat writes, each word retains untouched bits.
  for(n=0;n<8;n=n+1)begin
   beat=(n==0||n==1)?1:(n%2);
   @(negedge clk);we=1;oh=1<<beat;
   for(b=0;b<2048;b=b+1)wd[b]=$random;
   for(b=0;b<788;b=b+1)begin
    f=(b<532)?SP*532+b:2128+SP*256+b-532;
    if(f/2048==beat)expected[b]=wd[f%2048];
   end
   tick();@(negedge clk);we=0;
   repeat(3)tick();read_check(0);
  end
  // Default checks data/check endpoints of every codeword; FULL_SWEEP checks every bit.
  for(w=0;w<words;w=w+1)for(bitno=0;bitno<72;bitno=bitno+(FULL_SWEEP?1:71))begin
   @(negedge clk);flip(w*72+bitno);read_check(1);@(negedge clk);flip(w*72+bitno);
  end
  // Default checks two double-bit patterns; FULL_SWEEP checks all pairs.
  for(a=0;a<72;a=a+(FULL_SWEEP?1:71))for(z=a+1;z<72;z=z+(FULL_SWEEP?1:70))begin
   @(negedge clk);flip(a);flip(z);read_check(2);
   @(negedge clk);rst=0;tick();@(negedge clk);flip(a);flip(z);rst=1;
  end
  read_check(0);done=1;
 end
endmodule
module tb;
 wire[3:0]done;
 xcase #(0)c0(done[0]);xcase #(1)c1(done[1]);xcase #(2)c2(done[2]);xcase #(3)c3(done[3]);
 initial begin wait(&done);$display("PASS: all leaves partial writes and per-codeword fault gates; exhaustive codec tested separately");$finish;end
endmodule
