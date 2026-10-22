# hcoll_v5_fj3_r256 — d4g SW programme-target / fault-join leaf at ROWS 256 (ot_hgi_coll_fj_n2s1 #(ROWS 256))

HBM-COLL256-KITS 10-19, coordinator HANDOFF 0ky (3). Same leaf as hcoll_v5_fj3 / _r128 (the q3 LP fj view) with the
8-bit programme target. ROWS 64/128 elaborate unchanged.

## SAFE-DESIGN checklist (owner 10-19)
1. Pins: PASS. fj_core registers every input at its pin in RTL and every output is flop Q (as hcoll_v5_fj3);
   reset_landing 2 stages.
2. Reach: PASS. Tile 136 x 86 um.
3. Fanout: WAIVED with reason: the synchronous rst_q of fj_core drives ~300 flops (textbook WARN on hcoll_v5_fj3_r128,
   gate WARN only); it is a reset distribution net buffered by the flow, not a data cone. No data register > 32 loads.
4. Depth: PASS. Scan check = flow macro Q (~340 ps TT) -> row_bad compares (8-b) -> check_bad/fault flop; no in->out path.
5. Storage: FIXED. The 256 x 18-b flow store is ONE ot_sram_1rw_256x64 (u.u_program.g_fsram.u_flow); the macro read is
   the scan lookahead (frames and descriptor scans never overlap: one 1RW port). r128 kept 2 kb of flow flops. The
   1,536-b programme assembly register (segment-slot writes, 48:1 x 32-b drain read) is unchanged from the closed leaf.
6. Floorplan: macro origin (43.2,43.2) on the lattice, >= 20 um channel on both pin faces (inputs W / outputs E) and to
   every core edge; pin faces as the closed fj3 (N host frames, S issuer, E faults); one connected band.
7. Clock: one clock; spread from the gate; route io_hold_margin 0.03.
8. Schedule: no edge changes for the compiler: issuer_start_pc is set at descriptor accept (>= ROWS+2 edges before
   launch) instead of at launch; the launch / configured / fault edges are unchanged.

## Gate
(see gate_result.json; summary appended by the lane after the --cts gate)
