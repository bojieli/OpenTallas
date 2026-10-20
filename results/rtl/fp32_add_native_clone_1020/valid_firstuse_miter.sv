module fan32_valid_miter(input wire clk,rst_n,valid_in,input wire[31:0]a,b,output wire bad);
 wire vg,vn; wire [31:0] yg,yn;wire [1:0]eg,en;
 fan32_graph_input gold(.clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(yg),.err(eg),.valid_out(vg));
 ot_hdc_fp32_add_lat7_fan32_native dut(.clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(yn),.err(en),.valid_out(vn));
 reg [3:0] captures;
 always @(posedge clk) if(!rst_n) captures<=0; else if(captures<7) captures<=captures+1'b1;
 assign bad=(vg!=vn)||((captures<7)&&(vg||vn));
endmodule
