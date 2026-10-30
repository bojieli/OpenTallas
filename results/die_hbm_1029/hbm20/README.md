# DIE-HBM-20 (2026-10-29 14:03-15:05 PDT) — hfd_ep_static (a) split / (b) wider slot, qcore_r13 SRAM arrangement, TOK check

Common root cause (CHECKED from the SRAM LEFs): ot_sram_1r1w_64x512 / 128x256 carry M4 pins on BOTH vertical edges
(W: rd_out + wd_in low half + clk/ce/addr; E: wd_in high half + w_mask + tied repair pins), OBS M1-M4, kit max M5:
nothing crosses a macro sideways, so every SRAM needs logic access on both edges and its heavy (rd_out) edge must face
the logic. A single SRAM column / stack with the heavy edge into a narrow strip is the GEOM-61 / qcore failure class.

## hfd_ep_static (COORD 13:38: (a) and (b) in parallel; first with G0C 0 EP core_faces + GRT0 wins)
- (b) wider slot, epB/README.md: B4 427.68x246.24 2x2 SRAMs, busy edges into a 50.5-um mid channel, S logic band,
  SerDes pins on S: core GRT 0 @50 it, AUTO-GEOM FAIL only channel_h 1.081 est (hard 1.0). Plan epB4 (intel1
  die-hbm-20/plan/epB4, sha bebf98c400a5): G0 PASS, G0C 8 = inherited q_hub set, 0 new, EP core_faces 2 -> 0.
  => meets the stated win criterion first (G0C EP core_faces 0 + GRT0).
- (a) tx/rx split, epA/README.md: opt-in RTL hfd_ep_static_tx/_rx (Verilator equivalence 0 errors over 10 runs, mod
  cal_fault status +2 edges); tx2 99.36x99.36 GRT 0 (fill 0.137 INFO-ish FAIL), rx3 263.52x397.44 GRT 0 (r2r 430.6/3);
  same-slot rx GRT 33. Plan delta written, NOT built, no G0/G0C.
## qcore_r13 (task b2), qcore/: same outline 267.84x250.56, synth reused, place-only + AUTO-GEOM GRT50
- V3a both MY, W column, separated (y 45/192): GRT 0 (V2 6,801), channel_h 1.004 est only FAIL, r2r 331/0.
- V3c one N row both MY: GRT 0, channel_h 1.093 est. Centre column refused (covers clock entry 133.9,125.3).
## TOK check of HBM-034 (+10/+7 pgp.command cycles), tok/: ds S2 schedule (DIE-HBM-10 basis), bound every SU record
  pays it: +7 = 1.172 %, +10 = 1.702 % -> 1874 tok/s from 1906 (CHECKED model run; replaces the <=0.5 % estimate).
