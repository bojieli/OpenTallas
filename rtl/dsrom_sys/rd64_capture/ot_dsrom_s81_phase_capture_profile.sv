`timescale 1ns/1ps
// Canonical S81 only: exact source compiler guarantees sr%128=root.
// No owner state, grant, tree, codec, FIFO or new ACK. Select only with the
// bound Popper PHROM/keys/CFG source; prospective combinational timing unclosed.
module ot_dsrom_s81_phase_capture_profile #(
 parameter integer ENABLE=0
)(
 input wire [15:0] phase_rows,
 input wire [2:0] phase_np,
 output wire [128*19-1:0] root_returns
);
 wire [3:0] positions={1'b0,phase_np}+4'd1;
 genvar r;generate for(r=0;r<128;r=r+1)begin:root_profile
  wire [9:0] base_rows={1'b0,phase_rows[15:8],1'b0};
  wire [9:0] rows=base_rows+10'(phase_rows[7:0]>8'(2*r))+10'(phase_rows[7:0]>8'(2*r+1));
  wire [13:0] quota=rows*positions;
  assign root_returns[r*19 +:19]=(ENABLE!=0)?{5'b0,quota}:19'b0;
 end endgenerate
endmodule
