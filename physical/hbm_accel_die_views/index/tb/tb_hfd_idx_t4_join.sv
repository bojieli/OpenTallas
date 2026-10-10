`timescale 1ps/1fs
module tb_hfd_idx_t4_join;
 reg ck=0; always #5 ck=~ck;
 reg rst=0;
 reg [615:0] taps=0;
 wire [3:0] tc; wire [609:0] s; reg sc=0; wire fault;
 hfd_idx_t4_join dut(.ck(ck),.rst(rst),.taps(taps),.tap_credit(tc),.s(s),.sc(sc),.fault(fault));
 integer sent[0:3],credit[0:3],received=0,pending=0,cycle=0;
 function automatic [152:0] word(input integer beat,tap);
   reg [152:0] w;
   begin
     w=0; w[0]=(beat==341);
     for(integer l=0;l<4;l=l+1) begin
       w[1+l]=(beat+tap+l)%2;
       w[5+l]=(beat+tap+l)%3!=0;
       w[9+16*l +:16]=16'(beat*16+tap*4+l);
       w[73+20*l +:20]=20'(beat*768+tap*4+l);
     end
     word=w;
   end
 endfunction
 function automatic [608:0] expected(input integer beat);
   reg [608:0] w; reg [152:0] tapw;
   begin
     w=0; w[0]=(beat==341);
     for(integer t=0;t<4;t=t+1) begin
       tapw=word(beat,t);
       w[1+4*t +:4]=tapw[1 +:4];
       w[17+4*t +:4]=tapw[5 +:4];
       w[33+64*t +:64]=tapw[9 +:64];
       w[289+80*t +:80]=tapw[73 +:80];
     end
     expected=w;
   end
 endfunction
 initial begin
   for(integer t=0;t<4;t=t+1) begin sent[t]=0; credit[t]=128; end
   repeat(4) @(negedge ck); rst=1;
   repeat(4) @(negedge ck);
   while(received<342 || pending!=0) begin
     @(negedge ck); cycle=cycle+1;
     if(s[0]) begin
       if(s[609:1]!==expected(received)) $fatal(1,"lane/order/drop beat=%0d",received);
       received=received+1; pending=pending+1;
     end
     if(fault) $fatal(1,"fault cycle=%0d",cycle);
     taps=0; sc=0;
     for(integer t=0;t<4;t=t+1) begin
       if(tc[t]) credit[t]=credit[t]+1;
       if(sent[t]<342 && credit[t]>0 && (cycle%(t+2)!=0)) begin
`ifdef MUT_SWAP
         taps[t*154 +:154]={word(sent[t],3-t),1'b1};
`else
         taps[t*154 +:154]={word(sent[t],t),1'b1};
`endif
         sent[t]=sent[t]+1; credit[t]=credit[t]-1;
       end
     end
     // Initial >128-cycle stall exhausts downstream reservations. Thereafter
     // delayed, irregular returns exercise independent tap skew and refill.
`ifndef MUT_DROP_CREDIT
     if(cycle>500 && pending>0 && cycle%3!=0) begin sc=1; pending=pending-1; end
`endif
     if(cycle>5000) $fatal(1,"credit/drop timeout sent=%0d,%0d,%0d,%0d recv=%0d",sent[0],sent[1],sent[2],sent[3],received);
   end
   @(negedge ck); sc=0; taps=0;
   repeat(8) @(negedge ck);
   if(fault) $fatal(1,"late credit fault");
   $display("PASS atomic T4 join beats=%0d cycles=%0d depth128 downstreamstall500",received,cycle);
   $finish;
 end
endmodule
