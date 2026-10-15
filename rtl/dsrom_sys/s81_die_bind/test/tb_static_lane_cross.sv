`timescale 1ns/1ps
module tb_static_lane_cross;
 parameter integer W=1101, PHASE=2, RSLIP=0;
 reg wc=0,rc=0,wr=0,rr=0;
 always #5 wc=~wc;
 initial begin #(PHASE); forever #5 rc=~rc; end
 reg [W-1:0] i; wire [W-1:0] o; wire fault;
 integer wi=0,ri=0,epoch=0,checked=0;
 function automatic [W-1:0] word(input integer n);
   integer k; begin
     for(k=0;k<W;k=k+1) word[k]=((n*1103515245+12345)>>(k%31)) ^ (k/31) ^ (n>>(k%7));
   end
 endfunction
 always @(negedge wc) i=word(wi);
 always @(posedge wc) if(wr) wi<=wi+1; else wi<=0;
 ot_s81_static_lane_cross #(.W(W)) dut(wc,wr,i,rc,rr,o,fault);
 always @(posedge rc) begin
   if(!rr) ri=0;
   else begin
     #1;
     if(ri>=4) begin
       if(!RSLIP && o!==word(ri-4)) $fatal(1,"edge %0d data mismatch phase%0d",ri,PHASE);
       if(!RSLIP && fault) $fatal(1,"aligned epoch fault");
       checked=checked+1;
     end else if(o!==0) $fatal(1,"startup output");
     ri=ri+1;
   end
 end
 initial begin
   i=word(0);
   repeat(3) begin
     wr=0;rr=0; #30; // release both before the same numbered source/destination edge
     @(negedge wc); #1;wr=1;
     @(posedge wc); #(0.1+10*RSLIP); rr=1;
     repeat(96) @(negedge wc);
   end
   #1; if(RSLIP && !fault) $fatal(1,"epoch slip not detected");
   $display("STATIC_LANE_CROSS PASS W=%0d phase=%0d checked=%0d",W,PHASE,checked);$finish;
 end
endmodule
