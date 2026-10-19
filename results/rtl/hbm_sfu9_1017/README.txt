HBM-SFU9 10-17: SFU programme store r9c (column leaves) evidence.
r9 RTL bench (6f294ab02, run by SFU-STORE-9 07:52-08:00 on ot-epyc4): POSITIVE PASS edges=6683 (active 6515, D=4/status 2);
  mutants flip/skip/early/cfgdrop REJECTED. A duplicate r9 re-run by HBM-B (09:00, /srv/opentallas-scratch/claude/hbmb-1017/sfu9)
  was SIGTERMed (exit 143) during the Verilator build: no verdict, superseded.
r9 leaf2 gate (hbm_sfu_store_leaf2_r9_1017/gate_result.json, 6f294ab02, agidock128): WARN, CTS TT insertion 525.3 / spread 159.7,
  1,686 sinks; W face 834 pins over 189.8/194.4 um: REJECTED by the coordinator (HANDOFF 0db). Preserved.
r9c bench (this commit's RTL: leaf in_data split into in_data_lo[135:0] / in_data_hi[119:0], bit-identical; new mutant split):
  bench_r9c_pos.log PASS edges=6683; bench_r9c_split.log / _flip.log / _cfgdrop.log REJECTED (expected). ot-epyc4,
  /srv/opentallas-scratch/claude/hbm-sfu9-1017/bench_r9c.
r9 leaf3 gate (6f294ab02): WARN, CTS TT insertion 590.8 / spread 240.9, 2,359 sinks, W face 1,078 pins over 276.5/280.8 um: same defect as leaf2, superseded by r9c. Preserved.
r9c gates (HBM-TILES-B 10-17 12:04, re-launched: the 10:11 launch died at once, ot-run not on PATH): BOTH FAIL trial GRT,
  M4 (horizontal) overflow leaf2 307 / leaf3 921; CTS TT insertion 448.6/spread 203.9 (1,686 sinks) and 506.9/155.9 (2,359).
  Cause: the fully abutted R0 stack leaves no horizontal crossing under the M5 cap, so the E band (in_data_hi flops) gets
  clock/control round the stack. Preserved (gate_result.json + gate_layout).
r9d (mkspec_r9d.py): same RTL/pins; the stack is split into two halves with ONE 21.6 um W->E crossing channel at mid-height,
  where clk + control enter. leaf2d 280.8x349.92 (1.25:1), leaf3d 298.08x492.48 (1.65:1).
r9d gates (12:2x, cdf3f4995): leaf2d WARN (fill 51%, 2 zero-um abutment channels): trial GRT overflow 0, CTS TT insertion
  407.7 / spread 131.3 (1,686 sinks) -> CRITICAL (hbm_sfu_programme_store family): coordinator reviews
  physical/ref_tile/hbm_sfu_store_leaf2_r9d_1017/gate_layout/{floorplan,density,congestion}.png before any submit.
  leaf3d FAIL: M4 overflow 307 at the W/E edges of the 2nd macro of the upper half (pin-access row, Max H 1), CTS 616.9/261.3
  (2,359 sinks). Next for leaf3: not more height; try 2 columns x 3 (centre crossing channel both ways) or 2 leaf2-like
  halves, and find why insertion grows with height (E-band sinks reach the W clock entry only through the channel).
