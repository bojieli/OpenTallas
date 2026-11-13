// FORMAL CONTRACT ONLY: existing macro's synchronous read-before-write/mask
// semantics. Primary lockstep runs use the unmodified physical macro RTL.
module ot_sram_1r1w_32x64_m1 (
 input wire clk,r_ce_in,w_ce_in,input wire [4:0] r_addr_in,w_addr_in,
 output reg [63:0] rd_out,input wire [63:0] wd_in,w_mask_in
);
 reg [63:0] mem[0:31];
 always @(posedge clk) begin
  if (r_ce_in && w_ce_in) assert(r_addr_in != w_addr_in);
  if (r_ce_in) rd_out <= mem[r_addr_in];
  if (w_ce_in) mem[w_addr_in] <= (wd_in & w_mask_in) | (mem[w_addr_in] & ~w_mask_in);
 end
endmodule
