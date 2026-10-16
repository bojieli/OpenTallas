`timescale 1ns/1ps
module tb;
 reg clk=0,rst_n=0,v=0; reg [31:0] a=0,b=0; wire [31:0] y0,y1; wire v0,v1; integer i,err=0,nv=0;
 ot_hgi_coll_pring_add_lane #(.LAT(8)) g(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(y0),.valid_out(v0));
 ot_hgi_coll_pring_static_add_lane #(.LAT(8)) s(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(y1),.valid_out(v1));
 always #1 clk=~clk;
 function [31:0] rnd; input integer k; reg [31:0] r; begin r=$random;
   case(k%6) 0: rnd=r; 1: rnd={r[31],8'hff,r[22:0]&{23{r[3]}}}; 2: rnd={r[31],8'h00,r[22:0]}; 3: rnd={r[31],8'd127+r[4:0],r[22:0]};
   4: rnd=32'h0; default: rnd={r[31],8'd150,r[22:0]}; endcase end endfunction
 initial begin
  repeat(3) @(negedge clk); rst_n=1;
  for(i=0;i<2000000;i=i+1) begin @(negedge clk); v=$random; a=rnd($random); b=(i%7==0)? {~a[31],a[30:0]} : rnd($random);
    if(i==700000) rst_n=0; if(i==700003) rst_n=1;
    if(v0!==v1 || (v0 && y0!==y1)) begin err=err+1; if(err<5) $display("MISMATCH i=%0d v %b %b y %h %h",i,v0,v1,y0,y1); end
    if(v0) nv=nv+1; end
  if(err==0 && nv>100000) $display("ADD_LANE_LOCKSTEP_PASS checks%0d",nv); else $display("ADD_LANE_LOCKSTEP_FAIL err%0d nv%0d",err,nv);
  $finish; end
endmodule
