HBM-SFU9 10-17: SFU programme store r9c (column leaves) evidence.
r9 RTL bench (6f294ab02, run by SFU-STORE-9 07:52-08:00 on ot-epyc4): POSITIVE PASS edges=6683 (active 6515, D=4/status 2);
  mutants flip/skip/early/cfgdrop REJECTED. A duplicate r9 re-run by HBM-B (09:00, /srv/opentallas-scratch/claude/hbmb-1017/sfu9)
  was SIGTERMed (exit 143) during the Verilator build: no verdict, superseded.
r9 leaf2 gate (hbm_sfu_store_leaf2_r9_1017/gate_result.json, 6f294ab02, agidock128): WARN, CTS TT insertion 525.3 / spread 159.7,
  1,686 sinks; W face 834 pins over 189.8/194.4 um: REJECTED by the coordinator (HANDOFF 0db). Preserved.
r9c bench (this commit's RTL: leaf in_data split into in_data_lo[135:0] / in_data_hi[119:0], bit-identical; new mutant split):
  bench_r9c_pos.log PASS edges=6683; bench_r9c_split.log / _flip.log / _cfgdrop.log REJECTED (expected). ot-epyc4,
  /srv/opentallas-scratch/claude/hbm-sfu9-1017/bench_r9c.
