`timescale 1ps/1fs
// Test-only module substitution: actual svc core stays byte-identical.
// Production adoption needs the default-off selector and physical qualification.
module ot_hbm_index_lines #(parameter ENABLE=0,DEPTH=64,CRED=64)(
 input wire clk,rst_n,start,input wire[8:0]blocks,
 input wire[31:0]sector_v,input wire[383:0]sector_j,input wire[8191:0]sector_data,
 input wire[7:0]credit,output wire[8791:0]lines,output wire[63:0]pop,
 output wire done,fault,retained);
 ot_hbm_index_lines_sram #(.ENABLE(ENABLE),.DEPTH(DEPTH),.CRED(CRED)) native_store(
 .clk(clk),.rst_n(rst_n),.start(start),.blocks(blocks),.sector_v(sector_v),.sector_j(sector_j),.sector_data(sector_data),
 .credit(credit),.lines(lines),.pop(pop),.done(done),.fault(fault),.retained(retained),.corrected());
endmodule
