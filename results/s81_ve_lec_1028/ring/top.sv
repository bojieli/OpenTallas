module ring_base(input clk,input [15:0] d,output [1:0] q);
reg [31:0] hr;
always @(posedge clk) hr <= {d,16'b0};
wire [31:0] a,b;
ot_s81sl_ve_ring #(.W(32),.D(5)) u(clk,hr,a,b);
assign q={a[0],b[0]};
endmodule
