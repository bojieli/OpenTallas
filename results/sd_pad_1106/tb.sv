`timescale 1fs/1fs
module tb;
 reg clk=0,rst=0,pstart=0;
 always #416500 clk=~clk;
 wire [1:0] a,b,ad,bd;
 reg [1:0] da[2],dd[2];
 integer checks=0;
 for(genvar f=0;f<2;f=f+1)begin:g
  ot_dp_landing_origin_s #(.PADW(1)) gold(.clk(clk),.rst_raw_n(rst),.p_start(pstart),.strap_efall(1'(f)),.strap_pad(1'b0),.start(a[f]),.start_d(ad[f]));
  ot_dp_landing_origin_s #(.PADW(2)) gate(.clk(clk),.rst_raw_n(rst),.p_start(pstart),.strap_efall(1'(f)),.strap_pad(2'(`PAD)),.start(b[f]),.start_d(bd[f]));
  always @(posedge clk)begin
   if(!rst)begin da[f]<=0;dd[f]<=0;end
   else begin da[f]<={da[f][0],a[f]};dd[f]<={dd[f][0],ad[f]};end
   #1;
   if(b[f]!==da[f][1] || bd[f]!==dd[f][1])$fatal(1,"PAD_WRONG cycle%0d fall%0d got%b/%b exp%b/%b",checks,f,b[f],bd[f],da[f][1],dd[f][1]);
   checks=checks+1;
  end
 end
 initial begin
  for(integer seed=0;seed<20;seed=seed+1)begin
   rst=0;pstart=(seed&1);repeat(5)@(negedge clk);
   #39000;pstart=0;rst=1;
   repeat(3)@(negedge clk);#(1000+seed*17000);pstart=1;
   repeat(35)@(negedge clk);
  end
  $display("PAD2_EXACT_PASS checks%0d both_edge_choices repeated_reset start_and_start_d_plus2",checks);$finish;
 end
endmodule
