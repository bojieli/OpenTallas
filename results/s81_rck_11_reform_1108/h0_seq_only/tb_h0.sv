`timescale 1ps/1ps
// S81-TYPES-7-RCK 11-08: lock-step of ot_s81_kp4_enc H0_SEQ_ONLY=0 (original) vs =1, under random power-up state,
// real valid gaps, warm resets and a mid-stream start.  Mutants (-D) must be caught.
module tb;
 reg clk=0,rst_n=0,tx_v=0;
 reg [511:0] tx_d=0;
 wire av,bv,af,bf; wire [543:0] ad,bd;
 always #416 clk=~clk;
 ot_s81_kp4_enc #(.PIN_FAULT(1),.H0_SEQ_ONLY(0)) A(.clk(clk),.rst_n(rst_n),.tx_v(tx_v),.tx_d(tx_d),.p_v(av),.p_d(ad),.fault(af));
`ifdef MUT_H0_SEQ
 ot_s81_kp4_enc #(.PIN_FAULT(1),.H0_SEQ_ONLY(1),.MUT(0)) B(.clk(clk),.rst_n(rst_n),.tx_v(tx_v),.tx_d(tx_d^{511'b0,(tx_v&&$urandom%97==0)}),.p_v(bv),.p_d(bd),.fault(bf));
`else
 ot_s81_kp4_enc #(.PIN_FAULT(1),.H0_SEQ_ONLY(1)) B(.clk(clk),.rst_n(rst_n),.tx_v(tx_v),.tx_d(tx_d),.p_v(bv),.p_d(bd),.fault(bf));
`endif
 integer i,j,checks=0,errors=0,frames=0;
 initial begin
  for(i=0;i<6000;i=i+1) begin
   @(negedge clk);
   rst_n=(i%1500)>=20;
   tx_v=(i>=40)&&((i%113)!=55)&&((i%113)!=56)&&!((i%1500)>=700&&(i%1500)<730);
   for(j=0;j<16;j=j+1)tx_d[j*32+:32]=$urandom;
   @(posedge clk);#1;
   if(i>5)begin
    checks++;
    if(av)frames++;
    if({av,ad,af}!=={bv,bd,bf})begin errors++;if(errors<8)$display("H0_BAD cycle=%0d av=%b bv=%b",i,av,bv);end
   end
  end
  $display("H0_RESULT checks=%0d errors=%0d valid_beats=%0d",checks,errors,frames);
  if(errors||checks<5900||frames<1000)$fatal(1,"h0 lockstep FAIL");
  $display("h0 lockstep PASS");$finish;
 end
endmodule
