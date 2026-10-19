`timescale 1ns/1ps
module tb_idx_control_ring;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[7:0]din=0;
 wire[7:0]a3,a4,a5;wire[2:0]c3,c4,c5;
 ot_hbm_idx_link_control_ring #(.W(8),.FIELD(2)) idr(.clk(clk),.rst_n(rst_n),.din(din),.age3(a3),.age4(a4),.age5(a5));
 ot_hbm_idx_link_control_ring #(.W(3),.FIELD(0),.RESET_PAYLOAD(1)) ctr(.clk(clk),.rst_n(rst_n),.din(din[2:0]),.age3(c3),.age4(c4),.age5(c5));
 reg[7:0]hist[0:4];integer errs=0,checks=0,n=0,age=0,resets=0;
 always @(posedge clk)begin
  if(!rst_n)begin for(integer i=0;i<5;i++)hist[i]=0;age=0;end
  else begin for(integer i=4;i>0;i--)hist[i]=hist[i-1];hist[0]=din;age++;end
 end
 always @(negedge clk)begin
  if(rst_n)begin
   if(age>=5)begin
    checks++;if({a3,a4,a5}!=={hist[2],hist[3],hist[4]})errs++;
   end
   checks++;if({c3,c4,c5}!=={hist[2][2:0],hist[3][2:0],hist[4][2:0]})errs++;
  end
 end
 initial begin
  for(n=0;n<4000;n++)begin
   @(negedge clk);#1;
   if(n%137==0||n%137==1)begin rst_n=0;resets++;end else rst_n=1;
   din=8'((n*73)^(n>>2)^((n%7)*19));
  end
  @(negedge clk);#1;
  $display("IDX_CONTROL_RING checks%0d resetedges%0d errors%0d",checks,resets,errs);
  if(errs||checks<7000||resets<50)$fatal(1,"control ring exact fixed-age/reset mismatch");
  $display("IDX_CONTROL_RING PASS");$finish;
 end
endmodule
