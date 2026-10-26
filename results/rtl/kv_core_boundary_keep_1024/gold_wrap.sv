module observe(input clk,rst_n,input[15:0]d,output[11:0]q);wire[15:0]z;G #(.W(16),.D(2),.RST(1)) r(.clk(clk),.rst_n(rst_n),.d(d),.q(z));assign q={z[15:13],z[8:0]};endmodule
