# dscoll_lane_w_s4 -- S81-COLL safe4 lane tile on the 43.2 lattice (S81-COLL3, S81.STA.LKTO.2, 10-19)

Top `dsfd_coll_lane_w_safe4` (safe4 f5f105399: 10 same-edge UNA copies, split sender/ready rewind cones), CH_BOARD 700.
Spec from results/rtl/s81_coll_safe4_1019/kit/gen_s4_specs.py; geometry proof results/rtl/s81_coll_safe4_1019/kit/geom_proof_s4.json.
Successor of s3 (475.2x421.2): both s3 gates FAIL trial GRT (89 negotiation iterations from ~3,600 overflow, then the
post-repair incremental re-route stalled > 4 h; 52 channels < 20 um between abutted stacks).

Geometry 540.0 x 712.8 (aspect 1.32). S strip: RX FIFO 18 x 256x64 + credit-rx landing 9 x 32x64 at the core face;
N strip: gearbox slot store 10 x 32x64 at the link face + replay 18 x 256x64. 4 big rows per strip at 86.4 pitch, 6
columns at 86.4 pitch (origins 43.2 + 86.4 k). ONE full-width band y 345.6..385.2; rows outside are removed before
tapcell (physical/dscoll_cx/coll_s4_cell_band.tcl). E = column mirror of W (still on the lattice).

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS (RTL) -- every data pin registered in the safe4 RTL (same as safe3); reset_landing 2 stages.
2 Reach: PASS by construction, to confirm at the gate -- macro->band <= 302 um, pin->band <= 343 um (< 405).
3 Fanout: fixed in RTL (safe4 UNA copies, split rewind cones; kept modules kp4_20/kff4_1/kff4_10/rewind4). Gate textbook confirms.
4 Depth: s3 658 ps una->ready_r is the stage safe4 splits; gate textbook confirms.
5 Storage: PASS -- all storage in 55 bank64 SRAMs.
6 Floorplan: PASS -- lattice_band_errors() = [] (every origin on 43.2, min macro gap 25.9 um, core edge >= 21.3 um,
  no macro in the band, band density 44.5% of synthesis std 9,445 um2); pin-face channels 51.8 um, 1,690..2,090
  macro contacts each = 67..83% of the channel-only M3+M5 tracks (M5 over the macros adds ~ the same again);
  bus pins <= 1.7/um over full faces. Fill 19% is lattice/channel area (ROOT lattice_channel_bound approval requested).
7 Clock: spine clock, io_hold_margin 0.03; pin-flop spread judged by the --cts gate (TT/FF <= 80 ps).
8 Schedule: PASS -- static, 0 added cycles; safe4 lane miter m0 PASS 79,994 checks; m1-m4 FAIL witnesses in
  results/rtl/s81_coll_safe4_1019/bench/.
