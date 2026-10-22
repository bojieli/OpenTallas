module dut(input clk,rst_n,a, output reg [1:0] q, output reg z);
 always @(posedge clk or negedge rst_n) if(!rst_n) begin q<=0; z<=1; end else begin q<=q+{1'b0,a}; z<=~z; end
endmodule
