module forest_child #(parameter integer W=1073)(input wire clk,rst_n,input wire[W-1:0] i,output reg[W-1:0] o);
reg[3:0] c;
always @(posedge clk or negedge rst_n) if(!rst_n)begin o<=0;c<=0;end else begin o<=i+c;c<=c+1'b1;end
endmodule
