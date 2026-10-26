`timescale 1ns/1ps
`default_nettype none
// H-NETLIST/COLL 1815 (H-DIE d4c locality, 2 mm rule): inject LOCAL COPY, one per quadrant. hb_coll_<Q>.hgi_inj_addr +
// inj_rd (162 b, fan-out to cij/su0..3/sucx) left a centre-island pocket on a 1,880-2,060 um hop and set the stream
// equal-age max depth. This leaf is a fixed-latency register copy placed at the pocket exit next to the sink row:
// hb_coll drives ONE short hop into it (inject pins moved to the hb_coll face toward the sinks) and every sink is fed
// from its Q. Compiler-visible latency: exactly INJ_COPY_EDGES = 1 edge, identical for every bit and every sink
// (addr and rd leave together); no ready/credit, no state beyond the copy. rd resets to 0 (no spurious inject).
module ot_hgi_coll_inj_copy(
 input wire clk,rst_n,
 input wire [159:0] inj_addr_i,input wire [1:0] inj_rd_i,
 output reg [159:0] inj_addr_o,output reg [1:0] inj_rd_o
);
 localparam integer INJ_COPY_EDGES=1;
 always @(posedge clk) inj_addr_o<=inj_addr_i;
`ifdef OT_COLL_INJCOPY_MUT_SKEW
 always @(*) inj_rd_o=inj_rd_i;                       // mutant: rd bypasses the copy (age 0 vs addr age 1)
`else
 always @(posedge clk or negedge rst_n) if(!rst_n) inj_rd_o<=2'b00; else inj_rd_o<=inj_rd_i;
`endif
endmodule
`default_nettype wire
