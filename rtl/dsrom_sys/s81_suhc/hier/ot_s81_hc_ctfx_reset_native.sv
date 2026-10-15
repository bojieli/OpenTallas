// Serial HC broadcast: same one-edge data/valid path after initialization.
// Reset assertion is asynchronous; release takes three edges (old rr: one).
// Production initialization must hold fv_in zero until three rising edges after
// rst_in rises. This adds two initialization edges, zero token/data edges.
module ot_s81_hc_ctfx_reset_native #(parameter integer S_RD=2)(
 input wire clk,rst_in,
 input wire [S_RD+4:0] fv_in,
 input wire [FXW-1:0] fd_in,
 output reg [S_RD+4:0] fv,
 output reg [FXW-1:0] fdx
);
 localparam integer O_D=5+S_RD*16+20+6+8+32+1, FXW=O_D+S_RD*512;
 wire [0:0] rst_local;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr
  (.clk(clk),.rst_n_in(rst_in),.rst_n(rst_local));
 always @(posedge clk or negedge rst_local[0])
  if(!rst_local[0]) fv<='0; else fv<=fv_in;
 always @(posedge clk) fdx<=fd_in;
endmodule
