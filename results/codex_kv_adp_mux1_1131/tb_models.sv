`timescale 1ps/1fs
module tb;
 reg ck=0; always #416.5 ck=~ck;
 reg rce=0,wce=0;reg[8:0]ra=0,wa=0;reg[127:0]wd=0,mask=0;
 wire[127:0]oldq,newq;
 integer mutant=0,errors=0,checks=0,t,i;
 reg[127:0] shadow[0:511],expected=0;
 reg valid=0;
 wire[8:0]mra=ra^(mutant!=0?9'd1:9'd0);
 ot_sram_1r1w_512x128_m4_r2c2 gold(.clk(ck),.r_ce_in(rce),.r_addr_in(ra),.rd_out(oldq),.w_ce_in(wce),.w_addr_in(wa),.wd_in(wd),.w_mask_in(mask),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(14'b0));
 ot_sram_1r1w_512x128_m1_r2c2 gate(.clk(ck),.r_ce_in(rce),.r_addr_in(mra),.rd_out(newq),.w_ce_in(wce),.w_addr_in(wa),.wd_in(wd),.w_mask_in(mask),.rr_en(2'b0),.rr_addr(18'b0),.cr_en(2'b0),.cr_sel(14'b0));
 function automatic[127:0] pattern(input integer a,input integer n);
  pattern={32'(a*32'h1234567+n),32'(a^n^32'hf013a55a),32'(a+n*13),32'(a*7-n)};
 endfunction
 initial begin
  if($value$plusargs("MUT=%d",mutant))begin end
  for(i=0;i<512;i=i+1)shadow[i]=0;
  // Fill every word before observing; the proof never relies on power-up SRAM data.
  for(t=0;t<4096;t=t+1)begin
   @(negedge ck);
   if(t<512)begin wce=1;wa=9'(t);wd=pattern(t,0);mask='1;rce=0;ra=0;end
   else if(t<1024)begin wce=0;rce=1;ra=9'(t-512);end
   else begin
    wce=(t%5!=0);rce=(t%7!=0);wa=9'((t*173)^29);ra=(t%3==0)?wa:9'((t*43)^71);
    wd=pattern(t,t>>9);mask=pattern(t*17,t*31);
   end
   if(rce)begin expected=shadow[ra];valid=1;end
   if(wce)shadow[wa]=(shadow[wa]&~mask)|(wd&mask);
   @(posedge ck);#1;
   if(valid)begin
    checks=checks+1;
    if(oldq!==expected || newq!==expected)begin
     errors=errors+1;
     if(errors<4)$display("MISMATCH t=%0d old=%032h new=%032h want=%032h",t,oldq,newq,expected);
    end
   end
  end
  if(mutant==0)begin
   if(errors!=0)$fatal(1,"BASE FAIL errors=%0d",errors);
   $display("BASE PASS checks=%0d full512word map, masked writes, read hold, same-edge old-word",checks);
  end else begin
   if(errors==0)$fatal(1,"MUTANT NOT CAUGHT");
   $display("MUTANT CAUGHT errors=%0d",errors);
  end
  $finish;
 end
endmodule
