module fan32_miter(input wire clk,rst_n,valid_in,input wire[31:0]a,b,output wire bad,output wire vg,vn);
 wire[31:0]yg,yn;wire[1:0]eg,en;
 fan32_graph_input gold(.clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(yg),.err(eg),.valid_out(vg));
 ot_hdc_fp32_add_lat7_fan32_native dut(.clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(yn),.err(en),.valid_out(vn));
 assign bad=(vg!=vn)||((vg||vn)&&({yg,eg}!={yn,en}));
endmodule
