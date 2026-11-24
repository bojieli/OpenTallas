# QC-GLUE-IMAGES handoff (lane memory)
Job: QC baked-constant rows 1-5 + 7 (QC-BAKED-TRIAGE 05:44, FABLE-RC-QC 05:46 ACCEPT): glue sys_face_cfg ROM n59, CS_RXV/CS_X3S calendar,
d2d_cal_image_qc_pair TXDP (two calendars in one kit), native59 LAND_EDGES, tt_ctlm DEF_RELAY. Item 6 su_mem9 = SU owner (not mine).
Work dir: intel1 /srv/opentallas-scratch2/claude/QC-GLUE-IMAGES (copy intel2 same path). OT_LANE=QC-GLUE-IMAGES. Clone wt/ (origin/main c72e9ae815).

## 08:35 PST state
- Tool: gi/derive.py BIND OUT.json (LANEAGE-SWEEP bit-exact dr lineage qc_bind_consumer_ages_native.py):
  n59 = E5 rp_in + 1 CTL repair4 + E5 CTL->VM relay D + 1 leaf relay + 4 MIF0/SRAM capture; seam/TXDP from param_regen.json.
- gi/build.sh DERIVE PAIR_IMG SRC OUT: checks pair image die_stages/TXD == bound, qc_prog_roms for N/N-1/8, oracle, sys_face playback
  (exact RTL, N PASS / N-1 and 8 caught), native59 fence bench (n59bench/), overlay (2 RTL files) + MANIFEST.sha256.
- C1h result rows/c1h: N=532 (rp_in 501, relay 25), seam 7,7,7,8,8,8, TXDP 15011213 = pair img
  QC-ALLFIX/rows_j/pair_0635/out/img_bnd (Codex, KV D29 sel cand, KST 95,95,93,93,93,77,77). sys_face_cfg c26271b28f26 (= Codex), VIS 3278,
  KVSLOT 637..640. Overlay: d2d_cal_image_qc_pair.svh 14faef2260a2, qfd_native59_dv_headprep_obs1.sv LAND_EDGES=532 9e47f133745e.
- native59 cost: dr_landing pipe 1721 -> 36323 cells (65 b x 532 shift). FIFO form (32 x beat+timestamp, ~0.5k flops) is the fallback
  if native59 cannot close; not written.
- C1j: 12 dr lanes + latency identical to C1h; FW types changed only by defines OT_DLY_CPL/OT_ST_QNALT (cycle-equal delay form);
  rtl/qwen_* identical except tt_ctlm T20. Expect N=532. Waiter intel1 wait_c1j.sh (pid 2148188) reruns derive+build on cJ/bind when done, posts.
- Item 7 tt_ctlm: T20 core + 5 pads in C1j (QC-ALLFIX tt_t20_0642); LANEAGE 06:46: ctlm_image reads only R_CMD/R_HR/R_SS/R_AG,
  so dr_o/out_data/kv_x3_slot need nothing. LEC link 1 open with QC-F16-PRODUCER/QC-TTC-R2.
- Holds: V4 wave native59 (owner QC-GLUE) + glue (QC-V4) stay: V4 images are wrong. Release = event kit with this overlay signs (glue, native59).
- KV dependency: pair image K half from KV D29 selected candidate; if KV A5t3/A5t4 changes KS_* or TXDP K, recompile pair (compile_pair.sh on epyc9 rows_j/pair_0635) and rerun build.
- ROM GDS: sys_face_cfg + calendar_m0/m1 viamap from rows/<event>/rom_N go to ROM-WEIGHTS-1119 for the QC control-ROM content.
