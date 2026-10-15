// Native registered faces. Exactly +2 SIDE edges; all six clocks same PLL 1:1 phase0.
module ot_hbm_su_static_side_native6r2 #(parameter integer MUT=0)(input ck0,ck1,ck2,ck3,ck4,ck5,rst_n,v,input [2:0] fn,fn_out,input [31:0] x,output reg [31:0] y,output reg fault);
reg v_q; reg[2:0] fn_q,fn_out_q; reg[31:0] x_q;
always @(posedge ck0) begin v_q<=v; fn_q<=fn; fn_out_q<=fn_out; x_q<=x; end
wire[31:0] side_y;wire side_fault;
ot_hbm_su_static_side #(.MUT(MUT)) u_side(.clk({ck5,ck4,ck3,ck2,ck1,ck0}),.rst_n(rst_n),.v(v_q),.fn(fn_q),.fn_out(fn_out_q),.x(x_q),.y(side_y),.fault(side_fault));
always @(posedge ck0) begin y<=side_y; fault<=side_fault; end
endmodule
