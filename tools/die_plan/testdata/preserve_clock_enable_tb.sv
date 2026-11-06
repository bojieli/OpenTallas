module mid_ce_pair #(parameter MUT=0)(input clk,rst_n,ena,d, output reg old_q=1, output reg new_q=1);
reg held_ena=0;
always @* if(!clk) held_ena=ena;
wire gclk=clk & held_ena;
always @(posedge gclk or negedge rst_n) if(!rst_n) old_q<=1;else old_q<=d;
wire qn=~new_q;
wire n1=~(ena & d);
wire n2=ena | qn;
wire nx=~(n1 & n2);
wire bad=~(n1 & (ena | ~qn));
always @(posedge clk or negedge rst_n) if(!rst_n)new_q<=1;else new_q<=MUT?bad:nx;
endmodule
module tb;
reg clk=0,rst_n=0,ena=0,d=0;
wire a,b,ma,mb;
mid_ce_pair ok(clk,rst_n,ena,d,a,b);
mid_ce_pair #(.MUT(1)) mutant(clk,rst_n,ena,d,ma,mb);
integer i,seen=0,checks=0;
initial begin
 for(i=0;i<10000;i=i+1)begin
  clk=0; #2; rst_n=(i%113)!=0; ena=((i*7+i/13)%11)<6; d=((i*17+i/29)%7)<3;
  #3;clk=1;#2;
  if(a!==b)$fatal(1,"lockstep mismatch %0d old%0b new%0b",i,a,b);
  if(ma!==mb)seen=seen+1;
  checks=checks+1;
  #3;
 end
 if(seen==0)$fatal(1,"mutant not caught");
 $display("MID_CE PASS checks=%0d mutant_caught=%0d",checks,seen);$finish;
end
endmodule
