`timescale 1ns/1ps
module tb_su_f12_softplus;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,v=0,mutant=0;reg[31:0] x=0;
 wire[31:0] gy,dy;wire gv,dv,gf,df;
 ot_hbm_su_static_side_softplus #(.LM(3),.LA(3)) gold(.clk({3{clk}}),.rst_n(rst_n),.v(v),.x(x),.sp(),.r(gy),.vo(gv),.fault(gf));
 ot_hbm_su_static_side_softplus__b1f12 #(.LM(4),.LA(4)) dut(.clk({3{clk}}),.rst_n(rst_n),.v(v),.x(x^(mutant?32'h00800000:32'd0)),.sp(),.r(dy),.vo(dv),.fault(df));
 reg[35:0] vv=0;reg[31:0] yy[0:35];
 integer seed=17387,count=0;
 always @(posedge clk) begin
  if(!rst_n)vv<=0;else vv<={vv[34:0],gv};
  yy[0]<=gy;for(integer k=1;k<36;k=k+1)yy[k]<=yy[k-1];
  #1;
  if(rst_n)begin
   if(dv!==vv[35])$fatal(1,"F12 side valid mismatch t%0t dv%0b gv36%0b",$time,dv,vv[35]);
   if(dv)begin
    if(dy!==yy[35])$fatal(1,"F12 side data mismatch got%h exp%h MUT%0b",dy,yy[35],mutant);
    count=count+1;
   end
  end
 end
 initial begin
  mutant=$test$plusargs("MUT");
  for(integer k=0;k<36;k=k+1)yy[k]=0;
  repeat(4)@(negedge clk);rst_n=1;
  for(integer n=0;n<256;n=n+1)begin
   @(negedge clk);v=1;
   case(n%16)
    0:x=32'h00000000;1:x=32'h80000000;2:x=32'h3f800000;3:x=32'hbf800000;
    4:x=32'h7f800000;5:x=32'hff800000;6:x=32'h7fc00000;7:x=32'h00000001;
    default:x={1'($random(seed)),8'(120+($random(seed)&15)),23'($random(seed))};
   endcase
   @(negedge clk);v=0;repeat(2)@(negedge clk);
  end
  repeat(250)@(negedge clk);
  if(count!=256)$fatal(1,"F12 side missing outputs %0d",count);
  $display("SU_F12_SOFTPLUS PASS count%0d retime36 MUT%0b",count,mutant);$finish;
 end
endmodule
