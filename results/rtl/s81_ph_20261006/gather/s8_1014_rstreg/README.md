Gather reset tree (claude/s81-gather-1014 @3a30f458b RTL), EPYC1 2026-10-14:
ROOT_S_GATE PASS 274 (RST_REG 0 root, unchanged); full 128-root / 32-leaf cluster (SSA2 LOCAL_BANKS DIE_CLOCKS CONTROL_STRIP) vs flat
dsfd_sp_gather_c: base real_L2 37,440 / real_L20 37,312 rows 0 mismatch, stress, orphan (reset with open partials) PASS, ovf fault
observed, refuse REFUSED; mutants lane/chain/nofwd/xgo/ovf/heap/decision/own_co/select/rstreg FAIL; early-start mutant FAIL in
startup mode (startup/mut_early*.log; its plain-stress run in cluster/verdicts.log is a runner case error, fixed in run_gather_cl.sh);
startup 6/6 PASS (early command 1/4 x reset phase 0/2/6, drained restart).
