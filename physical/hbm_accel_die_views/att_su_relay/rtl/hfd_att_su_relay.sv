`timescale 1ps/1fs
`default_nettype none
// hbm-phys-1010 [idx] (lead decision 10-10, R25GQ): one registered relay station of the attention-root -> SU lane die
// bus (529 b = {data528, valid}), replacing the interim hfd_index_q b0..b5 transport band stack.  A chain of these
// (tools/hbm_att_su_relay.py places them, die segment <= 480 um) carries at_<q>_<r>3_hi.o to hb_su_<q>.a lane r.
// The bus is a valid-only stream into an always-accepting sink (hfd_su registers `a` every cycle, the attention root
// has no ready), so the relay is one register: input pin -> flop -> output pin (pin flop at both faces, no logic).
// The valid bit is reset (die reset, synchronised here); the payload is not.
module hfd_att_su_relay (
  input  wire [0:0]   ck,
  input  wire [0:0]   rst,
  input  wire [528:0] i,
  output wire [528:0] o
);
  wire c = ck[0];
`ifndef SYNTHESIS
  reg mut;   // negative control for the chain bench: corrupt payload bit 1 of every 7th valid beat
  integer nv = 0;
  initial mut = $test$plusargs("MUT_RELAY");
`endif
  reg [1:0] rst_s;
  always @(posedge c or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
  wire rn = rst_s[1];
  reg v; reg [527:0] d;
  always @(posedge c or negedge rn) if (!rn) v <= 1'b0; else v <= i[0];
  always @(posedge c) begin
    d <= i[528:1];
`ifndef SYNTHESIS
    if (i[0]) begin nv = nv + 1; if (mut && nv % 7 == 0) d[0] <= ~i[1]; end
`endif
  end
  assign o = {d, v};
endmodule
`default_nettype wire
