# COLL safephys reset-copy successor (LH-SMATT 10-19), RTL 77a229559
Same ORFS synth recipe / image / config as mapped_sizing (Codex a3dafdb3d), only the two RTL files changed.
- Reset: the single core rst_l (155 n1s0 / 164 n2s1 loads) is now 9 KEPT keep_hierarchy D1 copies (g_rst[0..7].u_rst + u_rst8).
  Actual mapped loads per copy (actual_fanout.tsv lists nets >16): n1s0 max 32 (rst_v[1] = cycles), n2s1 max 32; all others <=28.
  SAFE items 1/3 reset: PASS (<=32). Copies survive synthesis (distinct g_rst[k].u_rst drivers).
- Tie nets (921 HIGH / 580 LOW) are the async-set/unused macro constants: per-sink repair_tie_fanout at floorplan, not functional fanout.
- Chip area incl. 4 macros (19,369.9 um2): n1s0 23,583.5 / n2s1 23,740.9 um2 (generic pin-reg wrapper, conservative).
- Proofs (proofs.log, Verilator 5.050 on fleet): iter 512 PASS, fixed-delay 39,824 checks PASS, n1s0/n2s1 production 1792 + dense 8192 PASS,
  every mutant FAIL (script exits non-zero on a surviving mutant; PROOFS_RC=0).
