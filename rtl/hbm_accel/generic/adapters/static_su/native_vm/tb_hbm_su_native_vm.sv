`timescale 1ns/1ps
// Minimum mechanism gate: all32nativebanks, externalDMApreload, fixed
// compiled LG selectors, simultaneousread/write and maskedreadback.
module tb_hbm_su_native_vm;
 parameter integer MUT_LG=0,MUT_BANK=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,preloading=1;
 reg [32*17-1:0] rq=0;reg [32*281-1:0] wq=0,pre=0;
 reg [31:0] rd=0,wr=0;
 wire [32*257-1:0] rr;wire [31:0] done,pdone,lf;
 wire [32*18-1:0] status;
 ot_hbm_su_native_vm #(.MUT_LG(MUT_LG),.MUT_BANK(MUT_BANK)) dut(
  .clk_bank({32{clk}}),.rst_n(rst_n),.lg_rq(rq),.lg_wq(wq),.lg_rr(rr),.lg_w_done(done),
  .cal_rd(rd),.cal_wr(wr),.rslot_v(32'hffffffff),.wslot_v(32'hffffffff),
  .rslot(64'd0),.wslot({32{preloading?3'd5:3'd0}}),.preload_wq(pre),.preload_done(pdone),.lg_fault(lf),.bank_status(status));
 function automatic [255:0] pattern(input integer bank,input integer phase);
  for(integer k=0;k<8;k=k+1)pattern[k*32+:32]=32'h3f800000+32'(bank*256+k*8+phase);
 endfunction
 function automatic [15:0] sector(input integer bank);
  sector=16'(((bank/8)<<13)|(bank%8));
 endfunction
 integer e,b,k,errors=0,reads=0,writes=0;
 bit cut;
 initial begin
  cut=$test$plusargs("MUT_CAL");
  repeat(4)@(negedge clk);rst_n=1;
  for(b=0;b<32;b=b+1)pre[b*281+:281]={1'b1,sector(b),pattern(b,0),8'hff};
  @(negedge clk);pre=0;
  repeat(12)@(negedge clk);preloading=0;
  for(e=0;e<36;e=e+1)begin
   rq=0;wq=0;rd=0;wr=0;
   // Literal programme slots, independent of observed DUTrequests.
   if(e==0||e==20)begin
    rd=32'hffffffff;if(cut&&e==0)rd[8]=0;
    for(b=0;b<32;b=b+1)rq[b*17+:17]={1'b1,sector(b)};
   end
   if(e==1)begin
    wr=32'hffffffff;
    for(b=0;b<32;b=b+1)wq[b*281+:281]={1'b1,sector(b),pattern(b,1),8'h55};
   end
   @(posedge clk);#1;
   for(b=0;b<32;b=b+1)begin
    if(rr[b*257+256]!==((e==10)||(e==30)))errors=errors+1;
    if(done[b]!==1'(e==8))errors=errors+1;
    if(rr[b*257+256])begin
     reads=reads+1;
     for(k=0;k<8;k=k+1)if(rr[b*257+k*32+:32]!==32'h3f800000+32'(b*256+k*8+((e==30&&!(k%2))?1:0)))errors=errors+1;
    end
    if(done[b])writes=writes+1;
   end
   @(negedge clk);
  end
  if(lf!==0||status!==0)errors=errors+1;
  if(errors)$fatal(1,"SU_NATIVE_VM FAIL errors=%0d reads=%0d writes=%0d lg_fault=%h status=%h",errors,reads,writes,lf,status);
  $display("SU_NATIVE_VM PASS banks=32 srams=96 reads=%0d writes=%0d return=10 done=7 masked_readback=32",reads,writes);$finish;
 end
endmodule
