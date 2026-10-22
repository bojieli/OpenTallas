`timescale 1ns/1ps
module tb_storage;
 parameter integer MUT=0;
 reg ck=0,rst_n=0;
 always #5 ck=~ck;
 reg[513:0] d;
 wire[513:0] q;
 reg[513:0] gold[0:13];
 reg[511:0] gold3[0:2];
 wire[511:0] q3;
 qfd_dv_sram_delay #(.W(512),.D(3)) delay3(.ck(ck),.rst_n(rst_n),.d(d[511:0]),.q(q3));
 reg write;
 reg[4:0] wa,ra;
 reg[511:0] wd;
 wire[511:0] fq;
 reg[511:0] fm[0:31];
 reg[31:0] known=0;
 reg[511:0] expect_f;
 reg check_f;
 qfd_dv_sram_delay #(.MUT(MUT==1)) delay14(.ck(ck),.rst_n(rst_n),.d(d),.q(q));
 qfd_dv_sram_lookahead #(.MUT(MUT==2)) fifo8(.ck(ck),.write(write),.wa(wa),.wd(wd),.ra(ra),.q(fq));
 integer cycle,i,j,checks=0;
 initial begin
  d=0;wd=0;write=0;wa=0;ra=0;
  begin for(i=0;i<14;i=i+1) gold[i]=0; for(i=0;i<3;i=i+1) gold3[i]=0; end
  for(cycle=0;cycle<1200;cycle=cycle+1) begin
   @(negedge ck);
   rst_n=(cycle>=4 && !(cycle>=507 && cycle<512));
   for(j=0;j<17;j=j+1) d[j*30+:30]=$urandom;
   for(j=0;j<16;j=j+1) wd[j*32+:32]=$urandom;
   d[513:510]=cycle[3:0];
   write=(cycle<32 || ($urandom%4)!=0);
   wa=cycle<32?5'(cycle):5'($urandom);
   ra=(cycle%3==0)?wa:5'($urandom);
   @(posedge ck);
   if(!rst_n) begin for(i=0;i<14;i=i+1) gold[i]=0; for(i=0;i<3;i=i+1) gold3[i]=0; end
   else begin for(i=13;i>0;i=i-1) gold[i]=gold[i-1]; gold[0]=d;
    for(i=2;i>0;i=i-1) gold3[i]=gold3[i-1]; gold3[0]=d[511:0]; end
   if(write) begin fm[wa]=wd;known[wa]=1;end
   expect_f=fm[ra];check_f=known[ra];
   #1;
   if(q!==gold[13]) $fatal(1,"SAFE_STORAGE_DELAY cycle=%0d",cycle);
   if(q3!==gold3[2]) $fatal(1,"SAFE_STORAGE_SCALE_WAIT cycle=%0d",cycle);
   if(check_f && fq!==expect_f) $fatal(1,"SAFE_STORAGE_FORWARD cycle=%0d ra=%0d wa=%0d",cycle,ra,wa);
   checks=checks+1;
  end
  $display("SAFE_STORAGE_PASS fullwidth514+512 delay14+delay3 cycles=%0d resets=2 ring_wraps=37",checks);
  $finish;
 end
endmodule
