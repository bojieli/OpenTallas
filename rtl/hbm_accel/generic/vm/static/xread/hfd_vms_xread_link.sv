`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-10 2026-10-28 (COORD 09:30 ruling; plan C21 c21_side.json planned_links vmx_W2E / vmx_E2W):
// ONE-OWNER CROSSING READ of the HBM hub's half-local VM banks (DIE-HBM-9 (6), COORD 08:51 (6)).
// A shared tensor lives in ONE half's banks (the owner).  The far half never sends a request across the hub: the
// owner half issues the read on its own bank port with the record (static schedule, 10-14), and the response
// streams to the far half's clients over this fixed-latency register chain (LX edges, one register per relay
// site; plan regs_um = 3 relays + 1 capture = LX 4).  No queue, credit, ready, arbitration or runtime choice.
//   in  : owner-side bank responses rr (LANES x 257 b: [256] valid, [255:0] data), as the q0_faces bank drives them.
//   out : far-side response stations, exactly LX clk edges later (valid AND data), lane for lane.
// Dead-by-schedule ties that go with it (declared in xread_ties.json, 1.8 strap conditions): the far client's
// direct request station toward the owner bank is never scheduled once the read is owner-issued, so the parent
// ties that bank-request pin bundle to 17'b0 (TIELO); its response pin is left unconnected.  The bank master itself
// is unchanged (reuse), so the tie needs no new master and no type split.
// Reset: only the valid bits are reset (rst_n, synchronous release as the bank's pin flops); data bits are
// don't-care while valid is low, so they carry no reset (as the bank's pin registers).
// MUT (bench fail hooks only, default 0 = production): 1 one stage short, 2 lanes 0/1 swapped, 3 top data bit of the last lane inverted.
module hfd_vms_xread_link #(
    parameter integer LANES = 16,   // 16 x 256 b = 4096 b/cycle per direction (plan vmx_*: bits 4096)
    parameter integer LX    = 4,    // fixed crossing latency in edges (plan latency_cycles 4)
    parameter integer MUT   = 0
) (
    input  wire [LX-1:0]        clk_stage,  // stage s clock = the hub comb tap at relay site s (plan regs_um order)
    input  wire                 rst_n,
    input  wire [LANES*257-1:0] rr_owner,
    output wire [LANES*257-1:0] rr_far
);
    localparam integer N = (MUT == 1) ? LX - 1 : LX;
    initial if (LX < 1 || LANES < 1) $fatal(1, "hfd_vms_xread_link bounds");
    wire [LANES*257-1:0] q [0:LX];
    assign q[0] = rr_owner;
    genvar s, l;
    generate
        for (s = 0; s < LX; s = s + 1) begin : stage
            (* keep *) reg [LANES*257-1:0] r;
            integer i;
            always @(posedge clk_stage[s]) begin
                r <= q[s];
                if (!rst_n)
                    for (i = 0; i < LANES; i = i + 1) r[i*257 + 256] <= 1'b0;
            end
            assign q[s+1] = r;
        end
        for (l = 0; l < LANES; l = l + 1) begin : out
            localparam integer SRC = (MUT == 2 && LANES > 1 && l < 2) ? 1 - l : l;
            assign rr_far[l*257 +: 257] = q[N][SRC*257 +: 257] ^ ((MUT == 3 && l == LANES - 1) ? {1'b0, 1'b1, 255'd0} : 257'd0);
        end
    endgenerate
endmodule
`default_nettype wire
