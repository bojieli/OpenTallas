`timescale 1ns/1ps
module tb_tx_ring_phase;
parameter integer PH=0,D=4,K=2;
reg src=0,dst=0,rn=0;
initial begin #10;forever #5 src=~src;end
initial begin #(15.0+PH*0.001);forever begin dst=1;#5;dst=0;#5;end end
integer wi=0,ri=0,checks=0;wire[15:0]q;
dsdv_tx_ring_slice #(.W(16),.D(D),.K(K))u(.src_ck(src),.dst_ck(dst),.rn(rn),.d(16'(wi)),.q(q));
always @(posedge src)if(!rn)wi<=0;else wi<=wi+1;
always @(posedge dst)begin
 if(!rn)ri<=0;
 else begin
  if(ri>K+2)begin
   #0.001;
   if(q!==16'(ri-K))$fatal(1,"TX_RING_PHASE_FAIL phase=%0d ri=%0d q=%0d expected=%0d",PH,ri,q,ri-K);
   checks=checks+1;
  end
  ri<=ri+1;
 end
end
initial begin
 #101;rn=1;#1200;rn=0;#93;rn=1;#1200;
 if(checks<200)$fatal(1,"TX_RING_PHASE_VACUOUS %0d",checks);
 $display("TX_RING_PHASE_PASS phase=%0d D=%0d K=%0d checks=%0d",PH,D,K,checks);$finish;
end
endmodule
