module zero_ring_miter #(parameter MUT=0)(input clk,input [15:0] a_h,output mismatch);
reg [31:0] ah_q,hr;
always @(posedge clk) begin ah_q <= {a_h,16'b0};hr<=ah_q;end
wire[31:0] a,b,c,d;
ot_s81sl_ve_ring #(.W(32),.D(5)) gold(clk,hr,a,b);
ot_s81sl_ve_ring_zero #(.W(32),.D(5),.ZERO_LOW(MUT?17:16)) trial(clk,hr,c,d);
assign mismatch=({a,b}!={c,d});
endmodule
