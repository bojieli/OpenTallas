`timescale 1ns/1ps
module tb_merge;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,iv=0,ifin=0;reg[4:0]iblk=0;reg[511:0]iy=0;reg[15:0]if_=0;
 wire aov,bov;wire[511:0]ay,by;wire[15:0]af,bf;
 integer checks=0,errors=0,outputs=0;
 ot_hdc_v41x_attn_merge_x #(.H(16),.DPT(8),.MLEV(5),.FPL(5),.F12(1)) dut(.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),.iblk(iblk),.iy(iy),.if_(if_),.ov(aov),.oy(ay),.of_(af));
 ot_hdc_v41x_attn_merge_x_ref #(.H(16),.DPT(8),.MLEV(5),.FPL(5),.F12(1)) refdut(.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),.iblk(iblk),.iy(iy),.if_(if_),.ov(bov),.oy(by),.of_(bf));
 always @(posedge clk)begin
  #1;
  if(rst_n)begin
   checks=checks+1;
   if(aov!==bov || (bov && {ay,af}!=={by,bf}))begin errors=errors+1;if(errors<6)$display("MERGE_MISMATCH check=%0d ov=%b%b",checks,aov,bov);end
   if(bov)outputs=outputs+1;
  end
 end
 initial begin
  for(integer epoch=0;epoch<3;epoch=epoch+1)begin
   @(negedge clk);rst_n=0;iv=0;repeat(4)@(negedge clk);rst_n=1;
   for(integer job=0;job<3;job=job+1)begin
    for(integer blockn=0;blockn<20;blockn=blockn+1)begin
     for(integer dim=0;dim<8;dim=dim+1)begin
      if((blockn+dim+job)%5==1)begin iv=0;repeat(2)@(negedge clk);end
      iv=1;ifin=blockn==19;iblk=5'(blockn);
      for(integer h=0;h<16;h=h+1)iy[32*h+:32]=32'h3e800000+32'(epoch*777+job*311+blockn*101+dim*19+h*7);
      if_=16'((dim+blockn)%11==0 ? (1<<((dim+blockn)%16)):0);
      @(negedge clk);
     end
    end
    iv=0;ifin=0;repeat(40)@(negedge clk);
   end
  end
  $display("MERGE_RESULT checks=%0d outputs=%0d errors=%0d",checks,outputs,errors);
  if(outputs!=72 || errors!=0)$fatal(1,"merge equivalence");
  $finish;
 end
endmodule
