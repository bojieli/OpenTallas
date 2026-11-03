module top0 #(parameter integer CB=5, parameter integer QW=5) (input wire clk, input wire [4*16*(CB+4)-1:0] gs, input wire [4*16*CB-1:0] bs, input wire [QW-1:0] q,
  output wire [3:0] g_out, output wire [7:0] res_b, output wire [CB+9:0] res_above, output wire res_ok, output wire [4*CB-1:0] res_eq);
  ot_s81ph_sel_su_pipe #(.Q(4),.CB(CB),.QW(QW),.XR(0),.SELOH(0)) u (.clk(clk),.gs(gs),.bs(bs),.q(q),.g_out(g_out),.res_b(res_b),.res_above(res_above),.res_ok(res_ok),.res_eq(res_eq));
endmodule
module top1 #(parameter integer CB=5, parameter integer QW=5) (input wire clk, input wire [4*16*(CB+4)-1:0] gs, input wire [4*16*CB-1:0] bs, input wire [QW-1:0] q,
  output wire [3:0] g_out, output wire [7:0] res_b, output wire [CB+9:0] res_above, output wire res_ok, output wire [4*CB-1:0] res_eq);
  ot_s81ph_sel_su_pipe #(.Q(4),.CB(CB),.QW(QW),.XR(0),.SELOH(1)) u (.clk(clk),.gs(gs),.bs(bs),.q(q),.g_out(g_out),.res_b(res_b),.res_above(res_above),.res_ok(res_ok),.res_eq(res_eq));
endmodule
