module svc7_valid_miter(input clk,rst_n,v,input[31:0]a,b,output bad,early);
 wire vg,vn;wire[31:0]yg,yn;wire[1:0]eg,en;
 ot_s81svc7_add_graph_input gold(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(yg),.err(eg),.valid_out(vg));
 ot_s81svc7_add_native dut(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(yn),.err(en),.valid_out(vn));
 assign bad=vg!=vn;
 assign early=vg||vn;
endmodule
