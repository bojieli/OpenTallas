(* blackbox *) module ot_dsrom_su_hcpost_lane #(parameter integer ML=5, parameter integer AL=4, parameter integer FDUP=0) (
  input wire clk, input wire rst_n, input wire v, input wire [31:0] r0,r1,r2,r3,y,c0,c1,c2,c3,p, output wire vo, output wire [31:0] o, output wire fault);
endmodule
module gold(input wire clk, rst_n, v, input wire [15:0] a0,a1,a2,a3, input wire [31:0] y,c0,c1,c2,c3,p,
  output wire vo, output wire [31:16] o, output wire fault);
  pr_old #(.ML(7),.AL(6)) u(.clk(clk),.rst_n(rst_n),.v(v),.r0({a0,16'd0}),.r1({a1,16'd0}),.r2({a2,16'd0}),.r3({a3,16'd0}),.y(y),.c0(c0),.c1(c1),.c2(c2),.c3(c3),.p(p),.vo(vo),.o(o),.fault(fault));
endmodule
module gate(input wire clk, rst_n, v, input wire [15:0] a0,a1,a2,a3, input wire [31:0] y,c0,c1,c2,c3,p,
  output wire vo, output wire [31:16] o, output wire fault);
  pr_new #(.ML(7),.AL(6)) u(.clk(clk),.rst_n(rst_n),.v(v),.r0(a0),.r1(a1),.r2(a2),.r3(a3),.y(y),.c0(c0),.c1(c1),.c2(c2),.c3(c3),.p(p),.vo(vo),.o(o),.fault(fault));
endmodule
