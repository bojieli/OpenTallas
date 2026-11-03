module tb;
 reg clk=0;always #5 clk=~clk;
 reg rn=0,p=0,fall=0,pad=0;
 wire old,oldd;wire[3:0] rr,dd,offr,offd;
 ot_dp_landing_origin_s #(.PADW(1),.FWD_COPY(0)) gold(clk,rn,p,fall,pad,old,oldd);
 ot_dp_landing_origin_s_regional #(.ENABLE(1)) gate(clk,rn,p,fall,pad,rr,dd);
 ot_dp_landing_origin_s_regional #(.ENABLE(0)) off(clk,rn,p,fall,pad,offr,offd);
 integer n;
 initial begin
  for(n=0;n<2048;n=n+1) begin
   @(negedge clk);#1;
   rn=!(n<64 || (n>=600&&n<664) || (n>=1400&&n<1464));
   p=(n<80)?1:((n>550&&n<680)?1:$random);
   fall=$random;pad=$random;
   @(posedge clk);#1;
   if(n>0 && ({4{old}}!==rr || {4{oldd}}!==dd || {4{old}}!==offr || {4{oldd}}!==offd)) begin
    $display("REGION_MISMATCH cycle=%0d rn=%b old=%b/%b regional=%b/%b",n,rn,old,oldd,rr,dd);$fatal(1);
   end
  end
  $display("REGIONAL_LOCKSTEP_PASS cycles=2048 cold64 warm64x2 all8outputs defaultOFFandON");$finish;
 end
endmodule
