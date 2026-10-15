`timescale 1ns/1ps
module tb_static_column_ingress;
 parameter integer PHASE=2,TRUNK=17;
 reg wc=0,rc=0,rst=0,marker=0;
 always #5 wc=~wc;initial begin #(PHASE);forever #5 rc=~rc;end
 reg [1100:0] data=0;wire [1100:0] o;wire fault;
 ot_s81_static_column_ingress dut(wc,{data,marker},rc,rst,o,fault);
 integer cyc=0,j,seen=0;reg [1100:0] gold[0:2047];integer expected=0,first=-1,last=-1;
 function automatic[1100:0]word(input integer n);
  integer k;begin for(k=0;k<1101;k=k+1)word[k]=((n*1103515245+12345)>>(k%31))^(k/31)^(n>>(k%7));end
 endfunction
 always @(negedge wc)begin
   data=word(cyc);gold[cyc]=word(cyc);cyc=cyc+1;
 end
 always @(posedge rc)begin
  #1;
  // First output is input source edge marker assertion + fixed pin/ring delay.
  // A nonzero record cannot be an all-zero warmup. It must equal a source word
  // exactly, then advance on EVERY edge with no skipped, duplicated or held word.
  if(o!==0 && (^o)!==1'bx)begin
    if(first<0)begin
      for(j=0;j<cyc;j=j+1)if(o===gold[j])first=j;
      if(first<0)$fatal(1,"unrecognized initial record");
      if(first!=TRUNK+3)$fatal(1,"wrong first source epoch %0d expected%0d",first,TRUNK+3);
      expected=first;

    end
    if($time != 10*expected+66+PHASE)$fatal(1,"ingress wrong fixed edge time%0t source%0d",$time,expected);
    if(o!==gold[expected])$fatal(1,"ingress mismatch phase%0d expected%0d",PHASE,expected);
    if(fault)$fatal(1,"unexpected epoch fault phase%0d trunk%0d",PHASE,TRUNK);
    last=expected;expected=expected+1;seen=seen+1;
  end
 end
 initial begin
  #30;@(negedge wc);#1;rst=1;
  repeat(TRUNK)@(negedge wc);#1;marker=1;
  repeat(300)@(negedge wc);
  #1;if(seen<280)$fatal(1,"not enough output records %0d",seen);
  $display("STATIC_COLUMN_INGRESS PASS phase=%0d trunk=%0d first=%0d last=%0d words=%0d",PHASE,TRUNK,first,last,seen);$finish;
 end
endmodule
