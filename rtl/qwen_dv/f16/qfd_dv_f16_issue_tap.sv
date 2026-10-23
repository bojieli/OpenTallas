`timescale 1ns/1ps
// The selected slice PROG read request/actual selected row are the event.
// This leaf does not produce a completion, final-read receipt or auth signal.
module qfd_dv_f16_issue_tap (
 input wire ck,rst_n,program_re,
 input wire [8:0] program_pidx,
 input wire [3:0] slice_id,
 // Source-context travels at precisely the command's registered hop age.
 input wire [21:0] command_context,
 output reg [37:0] observation
);
 always @(posedge ck or negedge rst_n)
  if(!rst_n) observation<=38'd0;
  else observation<={program_re,program_pidx[8:7],slice_id,program_pidx,command_context};
endmodule
