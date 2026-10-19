# qfd_d2d_static_sf7 — SF7 compute D2D end (primary, QW-D2D3 2026-10-19)

CRITICAL prefix (`qfd_d2d_static`): gate + review packet only, no REVIEW.json, no submit.

Top `qfd_d2d_static_ovl_sf7` (`rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies_ovl_sf7.sv`, core `qfd_d2d_static_core_s7` in `ot_qwen_d2d_safe7.sv`): same ports, TXDP 0x0a010308 = [8,3,1,10], cycle-identical outputs to `qfd_d2d_static_ovl`.

sf7 (QW-D2D3 10-19): RTL successor qfd_d2d_static_ovl_sf7 (ot_qwen_d2d_safe7.sv): every native root <= 32 loads in source (SF6S 221 unsafe -> 0 non-tie), cycle-identical to qfd_d2d_static_ovl. Outline re-sized 345.6 x 216 -> 259.2 x 216 (-25%, fill 22% -> 29.8%), macros 2 x 2 (43.2|172.8, 43.2|129.6), prog_* ports N -> E so N fits.

Evidence: `results/arch/qw_d2d_safe7_1019/` (native census `native_summary.json`, receipts: 200k lockstep PASS + SFMUT 1-5 FAIL, 35-layer pair PASS + 3 pair mutants FAIL; Verilator 5.050).

Fill: pin-bound: 3,668 functional ports (548-bit native/program/RX payloads, 583-bit FDI flits, 524-bit x3) at the 0.192 um legal pin pitch (5.2/um, rule <= 6/um) need 704 um of face; qfd_d2d_static_sf7 259.2 x 216.0 gives fill 29.8% (macros 10580 + synth std 6085 um2); per face N 1121 pins over 215.04/259.2 um (83%), S 1170 pins over 224.448/259.2 um (87%), W 758 pins over 145.344/216.0 um (67%), E 619 pins over 118.656/216.0 um (55%). A 35-40% outline (<= 47.6k um2, perimeter <= ~870 um) would need >= 81% of the whole perimeter and every face >= 90% full, and the 2 x 2 lattice macros need >= 186 um height.

## SAFE-DESIGN checklist (owner 10-19)

- 1_pins: PASS: every functional port has its own pin flop (PR=1), KEPT pin-flop copies for cfg_data, cal_start[_rx] (7), cal_seg[_rx] (6), result_v (22); reset lands in the RTL 2-flop face capture (u_reset_regions / u_por_region s0/s1, FIRM at the E rst_n/por_n pins by local_reset_capture.tcl); kit reset_landing opt-out (RTL lands it).
- 2_reach: PASS by construction: 259.2 x 216.0 outline, pin flop to farthest macro pin < 405 um Manhattan; gate timing confirms.
- 3_fanout: FIXED in source (SF7, ot_qwen_d2d_safe7.sv): whole-block native census 0 non-tie roots > 32 (max FF 32, comb 32, input 22, macro 1; SF6S 221 unsafe) with KEPT non-parametric leaf copies (synth_keep_modules): 36-copy equal-depth reset tree, 25 epoch-begin copies, per-group halt/start/segment/advance/write-enable copies, one-hot twins, 2-level table-write decode; tie nets split by ORFS repair_tie_fanout. No ODB copy hooks.
- 4_depth: PASS: logic depth unchanged or shallower (copies only); gate confirms.
- 5_storage: PASS: slot store = 4 x 64x137 SRAM macros; calendar tables 2 x 1 kb flops (<2 kb) written by a kept decode, read by registered one-hot twins; TXD 1-bit capture delays <= 10 deep (waived: a ring costs more).
- 6_floorplan: macros 2 x 2 / row on the 43.2 lattice [(43.2, 43.2), (172.8, 43.2), (43.2, 129.6), (172.8, 129.6)], 10.8 um halos, full-width std band; pins 0.192 um on full faces (N 1121 pins over 215.04/259.2 um (83%), S 1170 pins over 224.448/259.2 um (87%), W 758 pins over 145.344/216.0 um (67%), E 619 pins over 118.656/216.0 um (55%)); aspect 1.20. Fill 29.8%: pin-bound (fill_reason.pin_bound, measured demand), the 40-60% synthesis-area target is infeasible for 3,668 ports at the legal pitch.
- 7_clock: Centre-fed: ck on the N centre track (129.612), CTS sink clustering 20/40; io_hold_margin 0.03; gate measures spread <= 80 TT+FF.
- 8_schedule: PASS: 0 added edges (200k lockstep vs qfd_d2d_static_ovl; 35-layer pair bit-exact at TXDP [8,3,1,10] = compiled_L1 dv2f18dh2). Static calendars, no credits/backpressure.
