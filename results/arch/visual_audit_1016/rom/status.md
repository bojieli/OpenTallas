# VIS-ROM: closure-blocking (severity-1) findings, status

Updated 2026-10-16 ~10:00 PT (round 3). Maintained by VIS-ROM. Evidence: verdict batches 04:15-09:50 (verdict-watch/codex_batches), daemon job records, and layouts rendered and LOOKED at this round (`img_r3/`, `sheets/contact_r3_dies.png`, `sheets/contact_r3_tiles.png`). Full evidence is in `findings.json` (`round3` block holds the scores).
State values: **fixed-routed** (fixed and the route closed or improved on the cited metric) · **fix-in-gate** (fix built; gate or route running, or improved but not closed) · **not-started** · **failing** (fix tried, route failed again) · **superseded** / **refuted**.

| finding | die | master | owner | state | evidence (before -> after, job) |
|---|---|---|---|---|---|
| QC-01 | Qwen compute | qfd_tile_nk rp2 | Q-COMPUTE-DIE | fix-in-gate | r3 fences: DPL illegal 170 -> 92. Successor qfd_tile_nk_rp2_g4t-g4t-9d426ea6d (ten ROM capture pipelines fenced in their read-facing gutters) RUNNING on E4, no odb yet. |
| QC-02 | Qwen compute | qfd_tile_nl rp2 | Q-COMPUTE-DIE | fix-in-gate | r3: illegal 96 -> 53. qfd_tile_nl_rp2_g4t-g4t-9d426ea6d QUEUED. |
| QC-05 | Qwen compute | qfd_xs_tap | Q-DVM+LINK | **fixed-routed** | xt10 CLOSED 05:04 TT +64.59 / FF +12.14; xt11 CLOSED 08:08 TT +112.06 / FF +9.87. aw S face 20.9 -> 3.5 pins/um. Residual (sev3): fill 0.199 and an E-face/NE congestion knot in the xt11 final image (he_d 1,567 + gi 380 at 10.4 pins/um). |
| D-QC-02 | Qwen compute | die n_rst_field | Q-COMPUTE-DIE | refuted (pending measure) | r2h2 full chain shows the reset fan-out still dominant (n_rst_field 1,584 / 47.5 mm, TT -3.96 us); partial-reset fix 9c7f27fdb is on main and in r2h5 (GEN running). Final when r2h5 GEN reports reset_over_500 = 0. |
| D-QC-03 (r3, sev2) | Qwen compute | die r2h5 | Q-COMPUTE-DIE | not-started | Centre column 55.6 of 125.4 mm2 empty, vacant tile row 20.5 mm2; all 6 port tiles W of SFU/VM so the E array crosses the centre (b2 remap approved, in r2h6 staging only). |
| QKV-01 | Qwen KV | qkd_pv | Q-KVSYS-DIE | superseded | PV16 approved (owner 10-15); qkd_pv16_vport CLOSED r1/r2/r3/r5. v1.4.4 spine-PV plan not yet in any die trial: kvs12a/kvs12b contain no PV and the spine is empty (26.5 mm2; D-QK-03). |
| QKV-02 | Qwen KV | qkd_ectl_a_tp8_epoch_direct | Q-ELEM | **fixed-routed** | pg16 CLOSED 06:43 TT +155.24 / FF +9.50 (was stuck at 4 DRT shorts); pg16s image clean, rs 1,025 on M4+M6 at 8.7 pins/um. |
| QKV-03 | Qwen KV | qkd_d2d_static | Q-KVSYS-DIE | not-started | No new route since r1sp-r3sp (45 GRT overflows in the 20 um SRAM channel). |
| QKV-04 | Qwen KV | qkd_rly_* relays | Q-KVSYS-DIE | fix-in-gate | kvs12b (RLY_STD) replaces rly_2089 (52.7x105.8, 20.9 pins/um, 61 inst) with rlys_528/296/36/1 (528 bits on an 82.1 um face). kvs12b is in PDN; fixed-routed when its GRT shows no relay-face hot spots. kvs12a still carries the old relays. |
| QKV-13 | Qwen KV | return_slots mc_r3 | Q-KVSYS-DIE | **fixed-routed** | mc3b CLOSED 05:04 TT +68.38 / FF +25.64; pins <= 1.8/um. |
| S81F-01 | S81 | relay faces | S-DIE | fix-in-gate | c26b (--rly-face-pins) placed as c26b_r (GRT extra 5/12, E4). New relay views closed: rly_283_EW/SN/WE r4, 283_WN/WW rfp1, rly_1_NN/WW/NW/NS, rly_536_SN/SW/WS, rly4. relay_face_audit score pending the GRT. |
| S81F-02 | S81 | dsfd_cfifo x2 | S-ELEM-PQ | **failing** | Grown kit g69 (280.8x69.1) EARLY_FAIL_CONGESTION 09:17: xd 566 bits in 27 um (20.9 pins/um), xa/xb 21 pins/um, M5 only, GRT congestion 677 all at the xd wall. The die slot is 432x95. c26b_r still omits 68,864 xd2 + 128 xf2 bits (S-DIE LEF audit). New detail: S81F-02b. |
| S81F-16 (r3) | S81 | dsfd_sstn_*_x2 (5 masters) | S-NET+FILL | **failing** | 10 routes (x1 + x2nh) all EARLY_FAIL_CONGESTION 08:08-08:35. Gate: 1,102 flops in a 6 um band under N, util 9.9%. Closed split base566/payload536 (09:05) not yet bound; c26b_r binds 936+ x2 instances. |
| S81H-01 | S81 | dsfd_host_c | S-ELEM-PQ | not-started | Last route n1 EARLY_FAIL_HOLD on EPYC1 (terminated); no new job. |
| S81H-02 | S81 | dsfd_stage_seq_static c9 | S-ELEM-PQ | failing | n5-scanpipe EARLY_FAIL_CONGESTION 04:27 (markers 20,000 flat over iterations 10-25). |
| S81H-14 | S81 | VM WFC split | S-VM | **fixed-routed** | Return leaf CLOSED 07:58 TT +217.81; wfc_return256 r2 CLOSED 09:29 TT +282.37 (r1 FLOORPLAN_MARGIN pin_track fixed). Every r6 leaf closed. |
| S81V-01 | S81 | dsfd_vm_xio_return | S-VM | **fixed-routed** | r3 CLOSED 07:01 TT +196.13 / FF +20.91 (was native capture 220.0 ps). 54x324 um, e_d 2,048 pins at 6.7/um. |
| S81V-02 | S81 | x34_s W1026 | S-VM | fix-in-gate | fault x34/x43 W1 transports CLOSED 04:45-04:49; the W514 split parent gate is not yet in a batch. |
| S81H-15 (r3) | S81 | ot_s81_hc_ccf_bankpipe_bank / bank128 | S-ENGRAM+NORM (HC-COMB) | **failing** | v1 NEEDS_RTL TT -34.99 / DRC 2; bank128 g128edge24 EARLY_FAIL_CONGESTION 09:32 (GRT congestion 49,847). The SRAM's pins are on its W/E faces, the buses run N->S through 20/25 um side channels. |

**Summary:** 19 rows. Fixed-routed 6 (QC-05, QKV-02, QKV-13, S81H-14, S81V-01, and QKV-07 / QC-03 / S81H-03 at sev2 in `findings.json`). Failing 4: S81F-02 cfifo, S81F-16 sstn x2, S81H-02 stage_seq, S81H-15 HC bank. Fix-in-gate 5, not-started 3, superseded 1, refuted-pending 1.
Hit rate (confirmed / (confirmed + refuted)) after round 3: 16 / 19 = 0.84.
Largest open levers: (1) cfifo onto its full 432x95 die slot at 2-track pitch; (2) bind the closed sstn split and stop re-routing the x2 kits; (3) HC bank: line the bus faces up with the SRAM pin faces; (4) S81 hub compaction, keeping the ~100 mm2 the candidate frees in the south.
