module decode_base #(parameter WRONG=0)(input clk,input [15:0] a_h,output q);
reg [31:0] ah_q,hr;
always @(posedge clk) begin ah_q <= {a_h,16'b0}; hr <= ah_q; end
wire [31:0] hd,hd2;
ot_s81sl_ve_ring #(.W(32),.D(5)) u(clk,hr,hd,hd2);
// Exact x_aman cone of ot_s81sl_ve_fadd: unconditional first decode capture.
wire [7:0] a_field=hd[30:23];
wire [23:0] a_man={(a_field!=0),hd[22:0]};
reg [23:0] x_aman;
always @(posedge clk) x_aman<=a_man;
assign q=WRONG ? x_aman[16] : x_aman[0];
endmodule
