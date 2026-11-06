module ot_sram_small(input clk,we,input [1:0] addr,input [7:0] din,output reg [7:0] dout);
reg [7:0] mem[0:3];
always @(posedge clk) begin if(we) mem[addr]<=din; dout<=mem[addr]; end
endmodule
module fixture(input clk,rst,we0,we1,input [1:0] addr,input [7:0] din,output [7:0] q0,q1,output [7:0] combined);
wire [7:0] r0,r1;
ot_sram_small \u_x.u_body.g_link[0].u_link.u_sram (clk,we0,addr,din,r0);
ot_sram_small \u_x.u_body.g_link[1].u_link.u_sram (clk,we1,addr,din,r1);
reg [7:0] \u_x.u_body.g_link[0].u_link.q ;
reg [7:0] \u_x.u_body.g_link[1].u_link.q ;
always @(posedge clk) begin
 if(!rst) begin \u_x.u_body.g_link[0].u_link.q <=0; \u_x.u_body.g_link[1].u_link.q <=0; end
 else begin \u_x.u_body.g_link[0].u_link.q <=r0; \u_x.u_body.g_link[1].u_link.q <=r1; end
end
assign q0=\u_x.u_body.g_link[0].u_link.q ;
assign q1=\u_x.u_body.g_link[1].u_link.q ;
assign combined=q0^q1;
endmodule
