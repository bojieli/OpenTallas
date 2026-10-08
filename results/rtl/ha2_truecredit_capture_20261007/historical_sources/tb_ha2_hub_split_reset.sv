`timescale 1ns/1ps
module tb_ha2_hub_split_reset;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[1:0] v=0;reg[1087:0] d=0;
 wire[1:0] oldv,midv,newv;wire[1087:0] oldd,midd,newd;
 integer checked=0;
 for(genvar i=0;i<2;i=i+1)begin:g_lane
  ot_ha2_delay_quiet #(.W(544),.D(35)) oldring(.clk(clk),.rst_n(rst_n),.v_in(v[i]),.d_in(d[i*544+:544]),.v_out(oldv[i]),.d_out(oldd[i*544+:544]),.quiet());
  ot_ha2_delay_quiet #(.W(544),.D(34)) newring(.clk(clk),.rst_n(rst_n),.v_in(v[i]),.d_in(d[i*544+:544]),.v_out(midv[i]),.d_out(midd[i*544+:544]),.quiet());
 end
 ot_ha2_hub_launch_single launch(.clk(clk),.rst_n(rst_n),.v_in(midv),.d_in(midd),.v_out(newv),.d_out(newd),.quiet());
 initial begin
  for(integer n=0;n<250;n=n+1)begin
   @(negedge clk);rst_n=!(n<3 || n==23 || n==61 || n==62 || n==127);
   v[0]=n%3!=0;v[1]=n%7<4;
   for(integer j=0;j<34;j=j+1)d[j*32+:32]=(n<<16)^j;
   @(posedge clk);#1;
   if(oldv!==newv)$fatal(1,"SPLIT_RESET_VALID n=%0d",n);
   for(integer i=0;i<2;i=i+1)if(oldv[i])begin
    if(oldd[i*544+:544]!==newd[i*544+:544])$fatal(1,"SPLIT_RESET_DATA");checked=checked+1;
   end
  end
  if(checked<50)$fatal(1,"SPLIT_RESET_COVERAGE");
  $display("PASS_SPLIT_RESET checked=%0d resets=4",checked);$finish;
 end
endmodule
