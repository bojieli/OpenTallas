`timescale 1ns/1ps
// Hardened SRAM return with ADDR_PIPE=2 == ADDR_PIPE=0 fed the same requests two cycles late;
// address faults keep their original cycle (DUT fault == reference fault two cycles later).
module tb_fh_margin_addr_pipe;
 parameter integer MUT=0;   // 1: reference without the 2-cycle input delay
 parameter integer AP=2;    // DUT ADDR_PIPE (2, or 3 = quadrant pin stage: reference fed AP cycles late)
 reg clk=0,rst_n=0; always #0.5 clk=~clk;
 reg [3:0] re,we; reg [95:0] ra,wa; reg [63:0] wm; reg [2047:0] wd;
 reg [3:0] re1,re2,we1,we2,re3,we3; reg [95:0] ra1,ra2,wa1,wa2,ra3,wa3; reg [63:0] wm1,wm2,wm3; reg [2047:0] wd1,wd2,wd3;
 always @(posedge clk) begin re1<=re;re2<=re1;we1<=we;we2<=we1;ra1<=ra;ra2<=ra1;wa1<=wa;wa2<=wa1;wm1<=wm;wm2<=wm1;wd1<=wd;wd2<=wd1;
  re3<=re2;we3<=we2;ra3<=ra2;wa3<=wa2;wm3<=wm2;wd3<=wd2; end
 wire [3:0] rex=AP==3?re3:re2, wex=AP==3?we3:we2; wire [95:0] rax=AP==3?ra3:ra2, wax=AP==3?wa3:wa2;
 wire [63:0] wmx=AP==3?wm3:wm2; wire [2047:0] wdx=AP==3?wd3:wd2;
 wire [2047:0] d0,d1; wire [63:0] v0,v1,c0,c1,p0,p1,k0,k1; wire f0,f1; wire [3:0] a0,a1;
 ot_hdc_v41_fh_sram_return_hardened #(.ADDR_PIPE(0)) ref0(.clk(clk),.rst_n(rst_n),
  .rd_en(MUT?re:rex),.rd_addr(MUT?ra:rax),.rd_data(d0),.rd_valid(v0),.corrected(c0),.poisoned(p0),
  .wr_en(MUT?we:wex),.wr_addr(MUT?wa:wax),.wr_mask(MUT?wm:wmx),.wr_data(MUT?wd:wdx),.wr_committed(k0),.fault(f0),.address_fault_bits(a0));
 ot_hdc_v41_fh_sram_return_hardened #(.ADDR_PIPE(AP)) dut(.clk(clk),.rst_n(rst_n),
  .rd_en(re),.rd_addr(ra),.rd_data(d1),.rd_valid(v1),.corrected(c1),.poisoned(p1),
  .wr_en(we),.wr_addr(wa),.wr_mask(wm),.wr_data(wd),.wr_committed(k1),.fault(f1),.address_fault_bits(a1));
 reg [3:0] a1q1,a1q2,a1q3; always @(posedge clk) begin a1q1<=a1; a1q2<=a1q1; a1q3<=a1q2; end
 integer i,g,seed=11,rv=0;
 initial begin
  re=0;we=0;ra=0;wa=0;wm=0;wd=0;
  repeat(3)@(negedge clk); rst_n=1;
  for(i=0;i<3000;i=i+1) begin
   @(negedge clk);
   if(i>6 && {d1,v1,c1,p1,k1}!=={d0,v0,c0,p0,k0}) $fatal(1,"data lockstep %0d",i);
   if(i>6 && a0!==(AP==3?a1q3:a1q2)) $fatal(1,"address fault cycle %0d",i);
   if(|v1) rv=rv+1;
   for(g=0;g<4;g=g+1) begin
    // first 16 cycles initialise rows 0..15 of every lane; then bank-aligned rows 0..15 (dense
    // reuse, read-after-write in flight) and rare out-of-range read addresses
    re[g]=(i<16)?0:$random(seed); we[g]=(i<16)?1:$random(seed);
    ra[g*24+:24]=((($random(seed)&15)<<2)|g) + ((($random(seed)&4095)==0)?24'h800000:0);
    wa[g*24+:24]=(i<16)?((i<<2)|g):((($random(seed)&15)<<2)|g);
   end
   wm=(i<16)?{64{1'b1}}:{$random(seed),$random(seed)};
   for(g=0;g<64;g=g+1) wd[32*g+:32]=$random(seed);
  end
  if(rv<500) $fatal(1,"read coverage %0d",rv);
  $display("PASS ADDR_PIPE=%0d == ADDR_PIPE=0 with requests +%0d, cycles=3000 reads=%0d",AP,AP,rv); $finish;
 end
endmodule
