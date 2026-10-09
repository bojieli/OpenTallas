
`timescale 1ps/1fs
module tb;
parameter integer MUT=0;
reg clk=0;
// Explicit positive-edge period833.333ps; simulation precision1fs.
always begin #416.666 clk=1;#416.667 clk=0;end
reg [582:0] d=0;wire [582:0] orig,got;wire [38:0] tail;
ot_attn_bpipe #(.W(544),.N(5),.EW0(1)) a0(.clk(clk),.d(d[543:0]),.q(orig[543:0]));
ot_attn_fpipe #(.W(39),.N(5)) a1(.clk(clk),.d(d[582:544]),.q(orig[582:544]));
ot_attn_bpipe #(.W(544),.N(5),.EW0(1)) b0(.clk(clk),.d(d[543:0]),.q(got[543:0]));
ot_attn_half_qtail #(.N(MUT==2?4:5),.FLAT(1)) b1(.clk(clk),.d(d[582:544]),.q(tail));
assign got[582:544]=MUT==1?{1'b0,tail[37:0]}:tail;
reg [582:0] hist[0:4];integer c,j,k,checks=0;time last_pos=0;realtime last_rt=0;
always @(posedge clk)begin
 for(integer n=4;n>0;n=n-1)hist[n]<=hist[n-1];hist[0]<=d;
end
initial begin
 for(c=0;c<1024;c=c+1)begin
  @(negedge clk);
  for(j=0;j<583;j=j+1)d[j]=$random;
  // Exercise asserted/released reset carried as data and all query modes.
  d[582]=(c%17<8);d[581:580]=c%4;
  @(posedge clk);#0.001;
  if(c>0 && ($realtime-last_rt < 833.3325 || $realtime-last_rt>833.3335))$fatal(1,"clock period");
  last_rt=$realtime;
  if(c>=4)begin
   if(got!==orig || got!==hist[4])$fatal(1,"QTAIL mismatch cycle=%0d mut=%0d",c,MUT);
   checks=checks+583;
  end
 end
 $display("PASS_ATTN_QTAIL full_bits=583 tail_bits=39 stages=5 FF=195 period_ps=833.333 cycles=1024 bit_checks=%0d",checks);$finish;
end
initial begin #2000000;$fatal(1,"watchdog");end
endmodule
