TW3-S81/FRAME 10-19: native landed-frame (FRAME_LP=1, 3-region compiler re-schedule) benches, Verilator 5.050, ot-epyc7,
source claude/tw3-frame-1019 a522c213c (staged as .../claude/tw3-frame-1019/src2). Build ~8 min, RSS 6.1 GB.
  col_h9  MUT0: plan K2048/nseg4 all-12-Q PASS cycle-exact vs compiler calendar (14 ret words, fault 0); each 12/12 PASS
  col_h9  unland / landread / reset(u_e0 held 400): plan FAIL as expected (NEGATIVE_CONTROL_FAILED_AS_EXPECTED)
  col_h10 MUT0: plan PASS (10 ret words, fault 0); each 12/12 PASS; unland / landread / reset FAIL as expected
codex_h9_k2_fail_1018/: the Codex FAIL (PLAN_MISMATCH 6 vs 12, FAULT 323-326). Root cause: frame_schedule.py dropped the
r1 leaves (sk_n skew-relay nets not matched -> node b = 'zero'). replay_on_fixed_topology.txt: Codex's placement on the
corrected topology predicts the bench's 12 ret edges exactly + F1 faults (generator bug, not calendar/RTL).
