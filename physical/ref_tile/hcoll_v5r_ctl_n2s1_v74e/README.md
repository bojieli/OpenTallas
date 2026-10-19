# hcoll_v5r_ctl_n2s1_v74e -- d4g COLL release leaf n2s1 (VM_RT 74), SAFE redesign after the v74s gate FAIL, variant E (macro stack moved east, wide W register band) (LH-COLLPVM 10-19)
RTL ot_hgi_coll_ctl_v5r_n2s1_safephys, unchanged from hcoll_v5r_ctl_n2s1_v74s (branch claude/hbm-coll-safephys-rst-1019 293d38e7c):
Codex COLL-SAFE fixed-delay SRAM pipes + 9 KEPT reset copies (mapped max 32). Same ABI/edges as v74.
Parallel twin kits: hcoll_v5r_ctl_n2s1_v74k (172.8 x 345.6, stack at x 43.2) and hcoll_v5r_ctl_n2s1_v74e (216 x 345.6, stack at x 86.4).
Bind whichever gates/closes first under the checklist; cancel the other.

Why (v74s n1s0 gate 293d38e7c FAIL): (a) clock pin-flop spread TT 102.7 / FF 90.4 ps from ONE root over 3,349 sinks split into
a W band and an E band around a 95 um macro column; (b) trial GRT overflow 184 (M2+M4 horizontal) in the gcell column at the
macro-stack W pin face. Root cause of (b): the kit's macro halo (MACRO_PLACE_HALO 5.4) only feeds the macro placer; tapcell cut
the rows at MACRO_ROWS_HALO_X = 2 um (platform default), so the 128 read-data AND gates per SRAM sat 2-5 um from the W pin face
and their local M2/M4 wiring shared the cap-0 straddling gcell with 410 SRAM pin escapes. Tile pins were also packed at the
2-track minimum (10.5 pins/um local clusters on W/E/S faces, 5.1/um average on W).

SAFE-DESIGN checklist (owner 10-19):
1 Pins: PASS (native) -- every input captured at its pin in RTL, every output a flop Q (pin_regs OFF as approved v74: a synthesis
  stage would add an unscheduled edge). Reset: 2-stage face landing then 9 kept D1 copies. FIXED pin pitch: pin_min_tracks 4
  (0.192 um) -> <= 5.2 pins/um everywhere on every face (was 10.5/um clusters); W face 1,661 pins need 319 um -> height 345.6.
2 Reach: PASS -- 216 x 345.6 outline, longest pin->flop Manhattan < 405 um; gate measures placed reach.
3 Fanout: PASS (fixed in v74s) -- reset copies max 32 (mapped census results/arch/hbm_coll_safephys_1019/mapped_sizing_rst).
4 Depth: WARN kept -- iter_mul pd->m_rgx_l ~655 ps / 19 levels estimate (v74s gate), TT setup >= 0 measured; unchanged V7 logic.
5 Storage: PASS -- delay pipes are 4 fixed-delay SRAMs (2x 128x256 p192_mir, 2x 32x128 p192_rc); no runtime-indexed flop arrays.
6 Floorplan: FIXED -- stack origin x 86.4 on the 43.2 lattice (y 43.2, abutted pitch = h + 0.024, on track, no N/S macro pins);
  REAL pin-face halo MACRO_ROWS_HALO_X 6.48 um (rows cut, > 11 gcells of 0.57 um free of cells on both W and E SRAM pin faces),
  W register band 2.16..79.9 um (~78 um, holds the 1,661-bit input capture mass away from the macro face), E band 187.7..213.8; aspect 1.6. WAIVED fill (pin-bound, spec fill_reason).
7 Clock: FIXED -- regional roots: clock_split_km.tcl K=8 on clk_control (8 k-means sink clusters, one BUFx24 local root at each
  cluster centroid beside its register mass, CTS balances the 8 roots under one top tree). Gate must show pin-flop spread <= 80
  ps TT and FF. io_hold_margin 0.03.
8 Schedule: PASS -- static, no added edge vs v74 (proofs production 1792 + dense 8192 PASS at LAT 74; mutants FAIL).
Parent impact: outline grows from 172.8 x 324 to 216 x 345.6 (slot change for the ctl_v5 parent, H.STA.BLK.16.4).
Critical prefix (ot_hgi_coll_ctl_v5): gate PNGs go to the coordinator review queue; no REVIEW.json / submit by this lane.
