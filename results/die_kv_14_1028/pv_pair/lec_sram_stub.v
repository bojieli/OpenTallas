// DIE-KV-14b proof-only stand-in for the ot_sram_1r1w_32x128_m1 black box (identical on both sides): every input pin
// is captured by a named register (a compare point after equiv_make) and the read data is a registered function of
// all inputs, so a difference on any SRAM pin propagates. Not a memory model; used only by lec_slice_lc.sh.
module ot_sram_1r1w_32x128_m1 (input wire clk,input wire r_ce_in,input wire [4:0] r_addr_in,output reg [127:0] rd_out,
 input wire w_ce_in,input wire [4:0] w_addr_in,input wire [127:0] wd_in,input wire [127:0] w_mask_in);
 (* keep *) reg [267:0] pin_q;
 always @(posedge clk) begin
  pin_q <= {r_ce_in,r_addr_in,w_ce_in,w_addr_in,wd_in,w_mask_in};
  rd_out <= pin_q[255:128] ^ pin_q[127:0] ^ {116'd0,pin_q[267:256]};
 end
endmodule
