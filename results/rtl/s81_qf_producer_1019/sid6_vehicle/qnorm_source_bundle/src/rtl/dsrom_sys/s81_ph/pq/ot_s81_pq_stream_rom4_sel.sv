`timescale 1ns/1ps
// Banked PQ stream program ROM select leaf (S-ELEM-B 10-15, answer to S-BIND port-bind ra2 14 vs 12 bits).
// The canonical PQ stream address rom_sa is 14 bits (16,384 rows); the die keeps its 4096x72 macro
// (ot_rom_4096x72_m8) and places FOUR of them. This leaf is the only logic between the core and the
// four macros, and keeps the core's "two-cycle synchronous ROM" contract (address launched at edge t,
// sampled by the macro at t+1, rd_out used by the core at t+2):
//   * a[11:0] = sa[11:0] to all four macros, ce[b] = (sa[13:12] == b): one decode level before the macro pins;
//   * the bank index is registered on the macro's sample edge (t+1) beside the macros, so the 4:1 response
//     mux selects the bank that produced rd_out on that same edge (0 added cycles).
// Only rd_out[47:0] is used (stream word); bits 71:48 of each macro are unconnected spare columns.
module ot_s81_pq_stream_rom4_sel (
  input  wire        clk,
  input  wire [13:0] sa,
  output wire [11:0] a,
  output wire [3:0]  ce,
  input  wire [47:0] rd0, rd1, rd2, rd3,
  output wire [47:0] sq
);
  assign a = sa[11:0];
  assign ce = 4'b0001 << sa[13:12];
  reg [1:0] bank_q;
`ifdef OT_S81_PQ_ROM4_MUT_SEL
  always @(*) bank_q = sa[13:12];          // mutant: select from the NEXT address (no sample-edge alignment)
`else
  always @(posedge clk) bank_q <= sa[13:12];
`endif
  assign sq = bank_q[1] ? (bank_q[0] ? rd3 : rd2) : (bank_q[0] ? rd1 : rd0);
endmodule
