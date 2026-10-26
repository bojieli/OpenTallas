module keep_probe(input clk,rst_n,input [3:0] d,output [7:0] q);
(* keep = 1 *) reg [3:0] a,b;
always @(posedge clk or negedge rst_n)
 if(!rst_n) begin a<=0;b<=0;end else begin a<=d;b<=d;end
assign q={b,a};
endmodule
