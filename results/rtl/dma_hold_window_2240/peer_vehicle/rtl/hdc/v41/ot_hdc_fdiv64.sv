`timescale 1ns/1ps
// Candidate only, not selected by production parameters. Two unchanged DEPTH31
// cores on complementary real gated clocks; fast registered input and output.
module ot_hdc_fdiv64(input wire clk,rst_n,v,input wire [31:0] a,b,
 output reg [31:0] y,output reg vo,fault);
 reg ph,vr; reg [31:0] ar,br;
 always @(posedge clk or negedge rst_n)
   if(!rst_n) begin ph<=0;vr<=0;end else begin ph<=~ph;vr<=v;end
 always @(posedge clk) begin ar<=a;br<=b;end
 wire ca,cb;
 ot_hdc_cg ga(clk,!ph | !rst_n,ca);
 ot_hdc_cg gb(clk, ph | !rst_n,cb);
 wire [31:0] ya,yb; wire va,vb,fa,fb;
 ot_hdc_fdiv da(ca,rst_n,vr & ~ph,ar,br,ya,va,fa);
 ot_hdc_fdiv db(cb,rst_n,vr &  ph,ar,br,yb,vb,fb);
 reg [31:0] yr; reg vf,ff;
 always @(posedge clk) begin
`ifdef NEG_PHASE
   yr<=ph ? yb : ya;
`else
   yr<=ph ? ya : yb;
`endif
   y<=yr;
 end
 always @(posedge clk or negedge rst_n)
   if(!rst_n) begin vf<=0;ff<=0;vo<=0;fault<=0;end
   else begin vf<=ph ? va : vb;ff<=ph ? fa : fb;vo<=vf;fault<=ff;end
endmodule
