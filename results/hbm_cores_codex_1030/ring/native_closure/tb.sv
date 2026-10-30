`timescale 1ns/1ps
module tb;
parameter MUT=0;
reg clk=0, rst_n=1, v=0;
reg [31:0] a=0,b=0;
wire [31:0] yg,yn;
wire [31:0] yn_cmp = MUT ? {yn[31:1],~yn[0]} : yn;
wire vg,vn;
recipe_ot_hdc_fp32_add_lat #(.LAT(7),.DRST(0)) g(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(yg),.err(),.valid_out(vg));
native_ot_hdc_fp32_add_lat #(.LAT(7),.DRST(0)) n(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(yn),.err(),.valid_out(vn));
always #5 clk=~clk;
integer edge_count=0,i;
always @(posedge clk) begin
 #1; edge_count=edge_count+1;
 if ({yg,vg} !== {yn_cmp,vn}) begin
  $display("DIFF edge=%0d recipe=%h/%b native=%h/%b",edge_count,yg,vg,yn,vn);$fatal(1,"strict y/valid mismatch");
 end
end
initial begin
 #1;rst_n=0;
 for(i=0;i<2200;i=i+1) begin
  @(negedge clk);
  rst_n=(i>=8 && !(i>=600 && i<609) && !(i>=1300 && i<1309));
  a=$random;b=$random;v=(i%4!=0);
  if(i%19==0)a=0;
  if(i%23==0)b=32'h80000000;
  if(i%31==0)a=32'h7f800000;
  if(i%37==0)b=32'h7fc00001;
  if(i%41==0)a[i%32]=1'bx;
  if(i%67==0)b[(i+7)%32]=1'bz;
 end
 @(negedge clk);$display("PASS strict four-state y/valid edges=%0d masks=0 LAT=7 DRST=0",edge_count);$finish;
end
endmodule
