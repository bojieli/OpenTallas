module ring_lockstep #(parameter MUT=0)(input clk,input [31:0] d,output mismatch);
reg [31:0] hr;
always @(posedge clk) hr<=d;
wire [31:0] a,b;
ot_s81sl_ve_ring #(.W(32),.D(5),.MUT(MUT)) u(clk,hr,a,b);
reg [159:0] shift;
always @(posedge clk) shift <= {shift[127:0],hr};
assign mismatch=(a!=shift[159:128]) || (b!=shift[159:128]);
endmodule
