`timescale 1ps/1ps
module tb;
 reg clk=0,rst_n=0,tx_v=0;
 reg [511:0] tx_d=0;
 wire av,bv,af,bf; wire [543:0] ad,bd;
 always #416 clk=~clk;
 ot_s81_kp4_enc #(.PIN_FAULT(0)) A(.clk(clk),.rst_n(rst_n),.tx_v(tx_v),.tx_d(tx_d),.p_v(av),.p_d(ad),.fault(af));
 ot_s81_kp4_enc #(.PIN_FAULT(1)) B(.clk(clk),.rst_n(rst_n),.tx_v(tx_v),.tx_d(tx_d),.p_v(bv),.p_d(bd),.fault(bf));
 integer i,j,checks=0,errors=0,edges=0;reg lastf=0;
 initial begin
  for(i=0;i<2000;i=i+1) begin
   @(negedge clk);
   rst_n=(i%500)>=20;
   tx_v=((i%113)!=55)&&((i%113)!=56);
   for(j=0;j<16;j=j+1)tx_d[j*32+:32]=$urandom;
   @(posedge clk);#1;
   if(i>5)begin
    checks++;
    if({av,ad,af}!=={bv,bd,bf})begin errors++;if(errors<8)$display("FAULT_BAD cycle=%0d af=%b bf=%b",i,af,bf);end
    if(af!=lastf)edges++;
    lastf=af;
   end
  end
  $display("FAULT_RESULT checks=%0d errors=%0d fault_edges=%0d",checks,errors,edges);
  if(errors||checks<1900||edges<6)$fatal(1,"fault face lockstep FAIL");
  $display("fault face lockstep PASS");$finish;
 end
endmodule
