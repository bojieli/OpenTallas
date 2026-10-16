`timescale 1ps/1fs
`default_nettype none
// Additive candidate only. Local programme starts two serial edges earlier;
// these actual two flops restore the original release leaf's busy observation.
// Clock/reset physical qualification remains OPEN. Canonical leaf unchanged.
module ot_hbm_su_bridge_release_local_candidate #(parameter integer DELAY=2)(
 input wire clk_serial,clk_stream,rst_n,rst_stream_n,prog_busy,
 output wire bridge_rst_n,fault);
 wire busy;
 generate if(DELAY==0)begin:bypass
  assign busy=prog_busy;
 end else begin:rung
  reg [DELAY-1:0] pipe;
  for(genvar k=0;k<DELAY;k=k+1)begin:g
   always @(posedge clk_serial or negedge rst_n)
    if(!rst_n)pipe[k]<=0;else if(k==0)pipe[k]<=prog_busy;else pipe[k]<=pipe[k-1];
  end
  assign busy=pipe[DELAY-1];
 end endgenerate
 ot_hbm_su_bridge_release release_leaf(.clk_serial(clk_serial),.clk_stream(clk_stream),
  .rst_n(rst_n),.rst_stream_n(rst_stream_n),.prog_busy(busy),.bridge_rst_n(bridge_rst_n),.fault(fault));
endmodule
`default_nettype wire
