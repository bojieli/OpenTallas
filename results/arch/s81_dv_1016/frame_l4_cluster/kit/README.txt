TW3-S81-FRAMEGATE 10-19 frame kit floorplans (tools/s81_dv/frame_kit.py; COORD 0jy option A landed frame).
Row-structured legalisation of the c26l GEN arrangement under the ref_tile rules (>= 20 um channels, 20 um pin-face /
core edge, 43.2 um child lattice), width = p4l slot 1,436.832 um, height = what the content needs:
  variant                                        col_h9 H     col_h10 H   (p4l slot h9 2,695.68 / h10 3,000.24)
  hard relays, 43.2 lattice                      3,801.6      -
  hard relays, 8.64 small-child lattice          3,672.0      -
  soft relays (dsfd_rly_* synthesised), 43.2     3,369.6      3,672.0     <- the kits s81frame_col_h{9,10}_sr
Floor of the row structure: 6 q rows (221.4) + 3 bf rows (198.72) = 1,924.6 um of rows + 9 ROM/station bands
(>= 63 um ROM + 2 x 20 um channels) -> >= ~2.9 mm for h9 before lattice snapping: the p4l slot cannot hold the compact199
frame under the channel rule (c26l itself was 2,805 tall with 8.6 um ROM gaps and abutting relays).  SLOT CHANGE:
h9 +674 um, h10 +672 um per frame (spec slot_change_request) -> die plan frame pitch (coordinator / S81 die lead).
Region centres (child-area centroid) h9 r0 (629,493) r1 (619,1589) r2 (602,2806) -> lp reset hops r1 3 / r2 6 (depth 7);
h10 depth 8 (r1 4 / r2 7).  Benches re-run on that RTL: compiler/bench_lp_fg_1019.
