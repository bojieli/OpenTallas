`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81/PORTFIX-FLT (2026-10-25, S81 DECISION 4: each unit has ONE 1-bit sticky fault, the detailed status codes are
// dropped, the faults are reported to the host): ot_s81_frs -- the die-level FAULT RING STOP.
//
// The die carries two 1-bit fault rings that start and end at the sequencer/host unit (dsdv_hostb_seqhost_mux):
//   sid ring  seqhost sid_ro -> 16 C slice partitions -> seqhost sid_ri
//   vid ring  seqhost vid_ro -> 16 svc partitions     -> seqhost vid_ri
// Each ring partition holds one stop.  A stop latches the OR of its local unit faults f[NL-1:0] (each the unit's 1-bit
// sticky fault output, or a 1-bit feeder lane from a neighbouring unit) into its own sticky bit s, and forwards
//   fo <= fi | s
// one register a hop (the ring is a registered shift of OR-ed sticky bits: every hop is a flop, no combinational path
// crosses a partition).  A fault raised at a stop reaches the seqhost after (2 + hops downstream) edges and stays there:
// s is sticky, so fo stays 1 every edge after.  Static: no handshake, no valid -- a level on a flop chain.
// Reset (OWNER DECISION 13 wavefront, control state only): the async active-low rst_n clears s and fo; the sticky
// fault is control state.  The ring is not on any data path (0 cycles on every compiled schedule).
// ot_s81_frs0: the stop for a ring partition with no local fault source (forward only, fo <= fi), so that every ring
// partition carries a registered hop and no f input is tied.
// MUT (bench negative controls only): 1 = s not sticky (s <= |f), 2 = the ring OR dropped (fo <= s),
// 3 = the local fault dropped (fo <= fi).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_frs #(
    parameter integer NL  = 1,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [NL-1:0] f,     // local unit faults (each a 1-bit sticky unit output or feeder lane)
    input  wire          fi,    // ring in (previous stop / ring head)
    output reg           fo     // ring out (next stop / ring end)
);
    reg s;                      // this stop's sticky local fault
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin s <= 1'b0; fo <= 1'b0; end
        else begin
            s  <= (MUT == 1) ? (|f) : (s | (|f));
            fo <= (MUT == 2) ? s : (MUT == 3) ? fi : (fi | s);
        end
endmodule

module ot_s81_frs0 (
    input  wire ck,
    input  wire rst_n,
    input  wire fi,
    output reg  fo
);
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fo <= 1'b0; else fo <= fi;
endmodule
`default_nettype wire
