`timescale 1ps/1ps
// Reset-cycle effect of the spine relay. src = macro output; a = spine at sink; q = sink release.
module ot_dp_rrelay (input wire clk, input wire d, output reg q); always @(posedge clk) q <= d; endmodule
module ot_dp_rsync #(parameter integer W = 1, parameter integer S = 2) (input wire clk, input wire [W-1:0] a, output wire [W-1:0] q);
 genvar g; generate for (g = 0; g < W; g = g + 1) begin : b
  reg [S-1:0] r; always @(posedge clk or negedge a[g]) if (!a[g]) r <= {S{1'b0}}; else r <= {r[S-2:0], 1'b1};
  assign q[g] = r[S-1]; end endgenerate endmodule
module tb; reg clk=0, src=1; integer c=0, t_as=-1, t_rel=-1;
 always #416 clk=~clk;
 always @(posedge clk) c<=c+1;
 wire old_q, new_a, new_q;
 ot_dp_rsync #(.W(1),.S(2)) s_old(.clk(clk),.a(src),.q(old_q));
 ot_dp_rrelay r(.clk(clk),.d(src),.q(new_a));
 ot_dp_rsync #(.W(1),.S(2)) s_new(.clk(clk),.a(new_a),.q(new_q));
 integer oa=-1,na=-1,or_=-1,nr=-1,ca,cr;
 always @(negedge old_q) if(oa<0) oa=c-ca; always @(negedge new_q) if(na<0) na=c-ca;
 always @(posedge old_q) if(cr>0 && or_<0) or_=c-cr; always @(posedge new_q) if(cr>0 && nr<0) nr=c-cr;
 initial begin cr=0; ca=0; repeat(30) @(posedge clk); oa=-1; na=-1;
  // pulse widths under test: macro-register launch, just after the edge
  #10 src=0; ca=c; repeat(16) @(posedge clk); #10 src=1; cr=c; repeat(10) @(posedge clk);
  $display("sink assert after src fall  old=%0d new=%0d clocks",oa,na);
  $display("sink release after src rise old=%0d new=%0d clocks",or_,nr);
  $finish; end endmodule
