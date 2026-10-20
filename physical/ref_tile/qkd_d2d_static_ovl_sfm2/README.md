# qkd_d2d_static_ovl_sfm2: KV D2D link end qkd_d2d_static_ovl_sfm (claude/kv-sram-d2d-1019, lane KV-SRAM-D2D)

PARALLEL FALLBACK of qkd_d2d_static_ovl_sfm (taller p288 pin face, s1 2x2 lattice slots); bind whichever closes first.

Right-sized-storage successor of qkd_d2d_static_ovl_sf (safe fan-out, census max 32): same 475.2 x 280.8 um outline, pin
faces and pin plan (S face re-spread in order with the 17 `rx_zero17` pins after `rx_payload`, 0.192 / 0.240 um, 4.75/um);
TXDP_K 0x03030416, NTX 3, SAFE_RC 1, SRAMV 2, FEG 1.  Source / evidence: results/rtl/kv_sram_d2d_1019/README.md.
Slot store: 4 x `d2d_sram_1r1w_64x137_m1_r2c2_p288` (57.912 x 67.512, W/E 229 pins at 0.288 um = 3.49/um (max 4 in 1 um)) at (43.2,43.2) (259.2,43.2) (43.2,172.8) (259.2,172.8); was 4 x 64x512 (137/512 columns, 10.2 pins/um).

## SAFE-DESIGN checklist (owner 10-19) -- pre-gate review; gate facts appended below after PNG inspection

1. Pins: PASS. PR=1 pin flop on every functional port incl. the 17 rx_zero17 flops (same edge as q_rx_payload);
   start / seg / cfg KEPT pin-flop copies (sf). por_n / rst_n land in 2 registered stages at the face (reset_landing +
   local_reset_capture FIRM at the pins), then ot_rst_pipe regions.
2. Reach: PASS by construction: pin flops FIRM at their pins (io_flop_at_pins), no new data stage; the CRC tree now sits
   between the fdi_rx pin flops and rx_crc (same span the rf -> CRC path had); gate textbook reach confirms.
3. Fanout: PASS (inherited sf census max 32; new: guard receipt shares the image write decode, 4 KEPT authorisation
   copies, POR copy +66 loads spread by OT_RST_COPIES_MAX 24, Z17 +1..2 loads per rx bit); gate high_fanout confirms.
4. Depth: FIXED. RX CRC registered beside rf (sf gates: ovl -95.5 / -100.7 ps at u_ctl.abc), recovery counter 5 b
   (r7w -16.1 / -23.4 ps at u_rec.n[15]); guard adds one AND on the start copies (registered authorisation).
5. Storage: FIXED. Slot payload 64 x 548 b in 4 right-sized SRAMs (all 137 columns live, no tied endpoints); calendar
   images 32 x 32 b per calendar (1 kb) one-hot selected; guard receipt 33 b per calendar.
6. Floorplan: macros on the 43.2 lattice (the s1 / sf lattice slots: channels 158 um (x) / 62 um (y), every pin face opens onto std-cell area); macro faces 3.49 pins/um <= 6; halos 20 um (x) / 5.4 um;
   full-width std-cell band; aspect 1.69; outline pin-limited (S 2,236+ pins at 4.75/um), utilisation waived for that reason
   (std ~6k um2 in 133k um2, as the reviewed sf kits).
7. Clock: s1 recipe (E-face root at the band centre, 20-sink / 40 um clusters); io_hold_margin 0.030; gate must show
   TT / FF pin-flop spread <= 80 ps.
8. Schedule: PASS. 0 added cycles (lockstep miter vs the as-built end, every output every edge); the guard only acts on
   an illegal boot (fail-stop); Z17 on the existing q_rx_payload edge; static calendars, no credits / backpressure.

## Gate facts (KV-D2D-COLLECT 10-19 18:45, CTS gate 0d832f6ba -> c2df6a4d7, PNGs floorplan.png / density.png personally inspected)

1. Pins: PASS (unchanged; reset_landing max 2 sinks on por_n / rst_n).
2. Reach: PASS, textbook reach 102.5 um max (<= 405).
3. Fanout: PASS, textbook PASS (census max 32).
4. Depth: PASS, textbook depth 350.1 ps; TT placement RC reg->reg +102.5 ps, reg->out +217.4; hold +34.8 ps.
5. Storage: PASS (right-sized 64x137 SRAMs, as above).
6. Floorplan: PASS. 4 x p288 57.912x67.512 at (43.2,43.2)(259.2,43.2)(43.2,172.8)(259.2,172.8), s1 2x2 slots on the 43.2 lattice; macro pin faces 3.49/um; full-width std-cell band, no islands; top-level
   faces S 4.9/um, W 4.5/um, N 2.5/um (<= 6). Fill 16% (< 35%) was the gate's only FAIL: the outline is pin-bound (every face
   98-99% occupied) and right-sizing removed ~37k um2 of macro, so spec.json now records fill_reason.pin_bound (no geometry change).
7. Clock: PASS. E-face centre root; TT/FF pin-flop spread 45.8/43.6 ps (<= 80); insertion 508.6/414.1 ps
   (guidance); io_hold_margin 0.030; trial GRT overflow 0 (M2 25.81%).
8. Schedule: PASS (0 added cycles).
Verdict: APPROVED (gate_layout/REVIEW.json); re-gated with fill_reason, then submit_exact.
