# qkd_d2d_static_r7w_sf: KV D2D safe fan-out master qkd_d2d_static_sf (claude/kv-d2d-1019)

Same 475.2 x 280.8 um outline, four 64x512 SRAMs at (43.2,43.2) (259.2,43.2) (43.2,172.8) (259.2,172.8), pin faces and
full-face pin plan as the root-approved safe geometry 353123a8d (`*_s1`); new source = SAFE FAN-OUT end
(results/rtl/kv_d2d_safe_fo_1019/README.md). PRIMARY clock: E-face root at the band centre, local 20-sink / 40 um clusters (as s1).

SAFE-DESIGN checklist (pre-gate; gate facts appended after review):
1. Pins: PASS. PR=1 pin flop on every functional port; start / seg / cfg have identical KEPT pin-flop copies (same pin,
   equal from the first edge). por_n / rst_n land in 2 registered stages at the face (reset_landing).
2. Reach: PASS structurally (pin flops FIRM at pins, no new data stage, copies placed by their loads); gate confirms.
3. Fanout: FIXED. Native transparent census max 32, 0 nets > 32 (as-built 555 / 1096 ABC). Copies take their master's D
   net (first-edge convergent from any state; OT_FO_CHECK random-init proof, MUTFO1 self-hold mutant caught). Reset:
   12-copy ot_rst_split families, OT_RST_COPIES_MAX 24 (max 19 per copy).
4. Depth: PASS. No new logic stage; calendar read muxes become one-hot AND-OR (shallower than 32:1); gate measures.
5. Storage: PASS. Payload in four SRAMs; calendar image 32 x 32 b per calendar (1 kb < 2 kb) one-hot selected; fixed
   TX capture delays 22/4/3 b are control-only (inherited s1 note).
6. Floorplan: PASS (s1 geometry: 43.2 lattice, 44.712 / 51.816 um channels, 20 um W/E halos, full-width std band, max
   4.72 pins/um, aspect 1.69).
7. Clock: single sub-mm root, io_hold_margin 0.030; gate must show TT/FF pin-flop spread <= 80 ps.
8. Schedule: PASS. Cycle-identical to the as-built end (lockstep miter 5,992 full-output comparisons; pair LOCK 1,192
   edges 0 mismatches): no added cycle, nothing to price.
