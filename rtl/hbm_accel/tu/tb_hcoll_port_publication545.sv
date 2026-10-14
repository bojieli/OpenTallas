`timescale 1ns/1ps
module tb_hcoll_port_publication545 #(parameter integer MUT=0);
 reg clk=0;always #5 clk=~clk;reg rn=0;reg[3:0]v;reg[544:0]a,b,c;wire[3:0]ov;wire[544:0]oa,ob,oc;
 ot_hcoll_port_publication545 #(.MUT(MUT)) dut(.clk(clk),.rst_n(rn),.qp_push(v[0]),.qr_push(v[1]),.rx_valid(v[2]),.rx_credit(v[3]),.qp_data(a),.qr_data(b),.rx_data(c),.out_qp_push(ov[0]),.out_qr_push(ov[1]),.out_rx_valid(ov[2]),.out_rx_credit(ov[3]),.out_qp_data(oa),.out_qr_data(ob),.out_rx_data(oc));
 initial begin
 v=0;a=0;b=0;c=0;repeat(4)@(negedge clk);rn=1;
 for(integer k=0;k<4096;k=k+1)begin
  v=k;for(integer i=0;i<545;i=i+1)begin a[i]=((i*13+k*23)^(k>>4))&1;b[i]=((i*31+k*7)^(i>>2))&1;c[i]=((i*19+k*29)^(k>>6))&1;end
  @(posedge clk);#1;
  if(oa!==a||ob!==b||oc!==c||ov!==v)$fatal(1,"PUB545 FAIL k=%0d",k);
  @(negedge clk);
  if(k%257==0)begin rn=0;#1;if(ov!==0)$fatal(1,"PUB545 FAIL reset");rn=1;end
 end
 $display("PUB545 PASS edges4096 full1635 payload +4control reset16");$finish;
 end
endmodule
