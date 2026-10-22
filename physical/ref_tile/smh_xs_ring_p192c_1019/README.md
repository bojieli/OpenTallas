# smh_xs_ring_p192c_1019 -- smh_xs (H.STA.BLK.14.1) SAFE successor of smh_xs_ring_c32k_1019 (L2H-SMATT 10-19)
Parallel twins smh_xs_ring_p192a_1019 / smh_xs_ring_p192b_1019 (same RTL, different floorplan). Bind the first to close; cancel the other.
Why: c32k gate WARN (TT +108.9 / FF +47.95, spread 39.6/38, GRT 0) but its native view FAILS the face rule: all 11 SRAM faces 9.52-9.99
contacts/um (macro LEF pitch, 199/410 pins over 20.8/41.0 um) and tile pins at 0.096 pitch (Codex packet 5b7cc8a06). A halo cannot
change a LEF face density, so the macros themselves change: OT_SMH_SRAM_P192 selects the same-port wide-pitch generator variants
ot_sram_1r1w_32x128_m1_p192_rc (51.4 x 40.0) and ot_sram_1r1w_128x256_m1_r2c2_p192_mir (94.8 x 80.5): 0.192 um pitch = 5.1 pins/um.
Geometry: 475.2 x 302.4 (aspect 1.57): ring 2 abutted N-S columns x 43.2 (4) / 129.6 (3); x store 2x2 cols x 216 / 345.6, rows y 43.2 / 172.8; 34.8-35 um std channels at every W/E pin face, 47 um N band.
SAFE-DESIGN checklist (owner 10-19):
1 Pins: PASS -- c32k pin regs / landed rst_a (2-stage) unchanged; FIXED tile pin pitch: pin_min_tracks 4 (0.192 um, <=5.2/um: S 2,089 / N 1,644 / W 831).
2 Reach: PASS -- longest pin->flop / flop->macro < 405 um Manhattan in this outline (gate measures placed reach).
3 Fanout: PASS -- OT_SMH_FAN32 + ring reset relay (OT_SMH_RING_RST2), leaf relay <= 32 (c32k census).
4 Depth: PASS -- c32k TT +108.9 ps at the same RTL; macro-local registered ring read/write addresses.
5 Storage: PASS -- ring on 7 SRAMs, x store on 4 SRAMs; no runtime-indexed flop arrays.
6 Floorplan: FIXED -- every SRAM face <=5.1 pins/um (p192), macros on the 43.2 lattice (N-S stacks abutted at h+0.024 with no N/S pins),
  >=34.8 um std channel at every W/E pin face (row halo 6.48), continuous std band, fill 41% WAIVED pin-bound (S/N pin faces need >=401 um).
7 Clock: PASS -- FIXED km32 regional roots (p192a km16: spread 125.6/122.9 FAIL, insertion 530-714 ps over 475 um); io_hold_margin 0.03.
8 Schedule: PASS -- 0 added edges (same registered-read SRAM semantics); bench variant C (run_xs_ring_safe.sh C) vs rg2 ring and legacy.
smh_* is not a critical prefix: submit after a clean gate + committed C mutant witnesses.
