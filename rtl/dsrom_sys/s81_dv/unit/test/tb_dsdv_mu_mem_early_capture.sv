`timescale 1ns/1ps
module tb_dsdv_mu_mem_early_capture;
 reg ck=0; always #0.5 ck=~ck;
 reg [7:0] rst_n=0; reg we=0; reg [5:0] wa=0,ra=0,next_ra=0;
 reg [62:0] wd=0; wire [62:0] oldq,newq;
 dsdv_mu_mem #(.W(63)) anchor(.ck(ck),.rst_n(rst_n),.we(we),.wa(wa),.wd(wd),.ra(ra),.q(oldq));
 dsdv_mu_mem_early_capture #(.W(63)) dut(.ck(ck),.rst_n(rst_n),.we(we),.wa(wa),.wd(wd),.ra_current(ra),.ra_next(next_ra),.q(newq));
 integer i,checks=0; reg compare=0;
 always @(posedge ck) ra<=next_ra;
 always @(negedge ck) if(compare) begin
   if(oldq!==newq) $fatal(1,"EC_MEM IDENTITY edge%0d ra%0d old%h new%h",checks,ra,oldq,newq);
   checks=checks+1;
 end
 initial begin
   repeat(3) @(negedge ck); rst_n=255;
   // Explicit nonzero sentinels: write every real address through original pin registers.
   for(i=0;i<64;i=i+1) begin
     we=1;wa=6'(i);wd=63'h13579bdf0246801 ^ (63'(i)*63'h10203040501);
     next_ra=6'(i); @(negedge ck);
   end
   we=0; next_ra=ra; repeat(3) @(negedge ck); compare=1;
   for(i=0;i<1024;i=i+1) begin
     we=(i%5!=0);wa=(i%4==0)?ra:6'(i*13);wd=63'h7543210fedcba98 ^63'(i*32771);
     next_ra=(i%3==0)?ra:6'(i*7); @(negedge ck);
   end
   we=0; next_ra=ra; repeat(4) @(negedge ck);
   $display("EC_MEM PASS checks%0d",checks);$finish;
 end
endmodule
