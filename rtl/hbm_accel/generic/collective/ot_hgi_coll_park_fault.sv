module ot_hgi_coll_park_fault #(parameter integer N=16) (input wire clk,rst_n,input wire [N-1:0] bank_ovf,output reg ovf);
wire [0:0] rn;
ot_rst_relay #(.REGIONS(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
always @(posedge clk or negedge rn[0]) if (!rn[0]) ovf<=1'b0; else if (
`ifdef MUT_FAULT
1'b0
`else
|bank_ovf
`endif
) ovf<=1'b1;
endmodule
