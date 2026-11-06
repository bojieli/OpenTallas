`timescale 1ps/1fs
module tb;
 parameter real PHASE_PS=166.6;
 localparam integer W=544,LAT=4;
 reg clk=0,rst=0; always #416.5 clk=~clk;
 integer c=-1,pub=0,checks=0,errors=0,reset_checks=0,fall_checks=0;
 reg[W-1:0] raw=0,canonical=0; reg raw_v=0,canonical_v=0;
 wire[W-1:0] old_raw,default_raw,fall_raw,canonical_old;
 ot_s81_pma_bm #(.W(W),.LAT(LAT)) old_capture(clk,raw_v,raw,old_raw);
 ot_s81hd_pma_rx_capture #(.W(W),.LAT(LAT)) default_capture(clk,raw_v,raw,default_raw);
 ot_s81hd_pma_rx_capture #(.W(W),.LAT(LAT),.FIRST_FALL(1)) fall_capture(clk,raw_v,raw,fall_raw);
 ot_s81_pma_bm #(.W(W),.LAT(LAT)) canonical_capture(clk,canonical_v,canonical,canonical_old);
 function automatic[W-1:0] word(input integer n);
  reg[63:0] x; integer b;
  begin x=64'hd1b54a32d192ed03 ^ (64'(n)*64'h9e3779b97f4a7c15);for(b=0;b<W;b=b+1)begin x=x^(x<<13);x=x^(x>>7);x=x^(x<<17);word[b]=x[31]^x[0];end word[31:0]=word[31:0]^32'(n);end
 endfunction
 function automatic valid(input integer n);valid=((n%11)!=3)&&((n%17)!=5);endfunction
 function automatic[W-1:0] expected(input integer n);expected=valid(n)?word(n):{W{1'b0}};endfunction
 reg[W-1:0] toggles=0,last_source=0; reg[1:0] rs_r=0;
 // Literal RXQ reset synchronizer: capture pipe itself has no reset, unchanged.
 always@(posedge clk or negedge rst)if(!rst)rs_r<=0;else rs_r<={rs_r[0],1'b1};
 initial begin #1900.25 rst=1; #30417.5 rst=0; #833.4 rst=1; #34152.9 rst=0; #1666.1 rst=1; #42500.3 rst=0; #200.7 rst=1;end
 // Canonical source-labelled reference: word n is published by NBA at source
 // rise n. This defines the held/rising word calendar, not a physical hold fix.
 always@(posedge clk)begin
  c=c+1;canonical<=word(c);canonical_v<=valid(c);
  #1;
  if(c>=LAT+2)begin
   checks=checks+1;if(!rs_r[1])reset_checks=reset_checks+1;
   if(default_raw!==old_raw)begin errors++;if(errors<4)$display("DEFAULT mismatch c%0d",c);end
   if(canonical_old!==expected(c-LAT))begin errors++;if(errors<4)$display("CANONICAL mismatch c%0d",c);end
   if(fall_raw!==expected(c-LAT+1))begin errors++;if(errors<4)$display("AGE mismatch c%0d phase%0.1f",c,PHASE_PS);end
   if(fall_capture.l[0]!==expected(c-1))begin errors++;if(errors<4)$display("FIRST_EDGE mismatch c%0d",c);end
   for(integer s=1;s<LAT;s=s+1)if(fall_capture.l[s]!==expected(c-s))begin errors++;if(errors<4)$display("TAIL_EDGE mismatch c%0d stage%0d",c,s);end
  end
  if(c==310)begin
   if(toggles!=={W{1'b1}})errors++;
   if(checks<250||reset_checks<3||fall_checks<250)errors++;
   $display("RXCAP_RESULT phase_ps=%0.1f checks=%0d fall_checks=%0d reset_checks=%0d errors=%0d all544bits=%0d canonical_output_advance_rck=1 raw_model_advance_rck=%0d",PHASE_PS,checks,fall_checks,reset_checks,errors,toggles=={W{1'b1}},PHASE_PS<0?0:1);
   if(errors)$fatal(1,"RXCAP_FAIL");$finish;
  end
 end
 initial begin
  #(416.5+PHASE_PS);
  forever begin raw<=word(pub);raw_v<=valid(pub);toggles=toggles|(word(pub)^last_source);last_source=word(pub);pub=pub+1;#833;end
 end
 always@(negedge clk)begin
  #1;
  if(c>=LAT+2)begin fall_checks++;
   if(fall_capture.l[0]!==expected(c))begin errors++;if(errors<4)$display("FALL_CAPTURE mismatch c%0d",c);end
   for(integer s=1;s<LAT;s=s+1)if(fall_capture.l[s]!==expected(c-s))begin errors++;if(errors<4)$display("TAIL_STABILITY mismatch c%0d stage%0d",c,s);end
  end
 end
endmodule
