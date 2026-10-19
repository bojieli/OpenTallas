# MU-QW-AMIX (10-19): "one token per user at the root at a time" is CHECKED, compiler and RTL

Before: qfd_dv_scalar2 (fix a540f1f9f) restarts the root argmax merge on each token edge at MU_NU > 1, and the AMI words
carried no user, so a merge holding two users' candidates was schedule-guaranteed but not checked. Now both sides check it.

## 1. Compiler (tools/qwen_static_schedule)
- `mu_calendar.am_root_window(n_slices=12)` derives the root-merge window from the RTL. The reference edge e is the edge the
  AMAX emit (one broadcast, dst 15) enters slice 0's (W5's) cmd_q.
  - Command chain: `cmd_o <= cmd_q` and the next slice's `cmd_q <= cmd_i` give 2 edges per hop. Slice k decodes the emit at e + 2k.
  - Slice: `am_emit` register +1. The AMI beat goes into the scalar out register dn_o / up_o +1. The AMV beat follows one edge later (am2) +1.
  - Scalar chain hop: the neighbour's pin register scd_q / scu_q +1, then its pass register +1.
  - Root: the AMV beat merges on the edge after it reaches the pin register, +1. The root's own candidate merges at e + 2r + 2.
  - Result: a candidate from slice k reaches root r at e + 2k + 2|k-r| + 3. With 12 slices and the worst root position
    (r = W5 = 0), merges fall on [e+2, e+48). Two users' emits must therefore be at least 46 edges apart.
  - mu_opcal.AM_ROOT_SPAN = 48 covers this (48 >= 46; checked by test_mu_opcal).
- `mu_calendar.check_root_merge(sched)` checks every user's token-start ("head") block, which emits at t0 + AM_EMIT_T (8)
  and holds [emit+2, emit+48). If two users' windows overlap it raises ScheduleError naming the users, the emit cycles and
  the windows. `compile_calendar` calls it and records `root_merge` {window, emits_checked, mixed 0}. The calendar of
  record passes.
- Tests: test_mu_calendar (derivation, of-record passes, a forced mix one edge inside the window raises, a moved filler
  head raises) and the new test_mu_opcal (mu_opcal.check_root_merge: legal passes, forced mix raises, cyclic mix across
  the frame edge raises, span >= derived). 18/18 pass locally (pure Python).

## 2. RTL (MU_NU > 1 only; at MU_NU 1 every changed word / status bit is the old constant)
- qfd_dv_amax_mu: new output `am_u` = the AMAX emit's user cmd[9:8] (0 at NU 1).
- qfd_dv_scalar2:
  - The user rides in tag[1:0] (word[33:32]) of the AMI and AMV beats. It was 0 before.
  - The root latches the merge user on the first candidate after a token / ROOT cfg. A candidate of another user while
    the merge is open, or two users on one edge, sets the sticky `fault` (slice sc_fault, status bit 65 / any_fault 69).
  - `tok_user` is the merge's user. The TOK broadcast carries it in tag[1:0], and non-root slices latch it.
  - MU_MUT 2 drops the check.
- qfd_dv_slice2:
  - **st[27:26] (= ss5[27:26] at W5, contract with MU-QW-B1-RTL) = the user of st[23:0] on every edge with st[24] (tok_v) set.**
    For the scalar-tree token this is the root merge user. For the cross-die gather token it is the gather AMAX cmd[9:8].
  - On other edges st[27:26] = ar_rank[1:0] as before. ar_rank[2] stays at [28]. At MU_NU 1, st is unchanged.
  - Bench-only `OT_DV_AMAX_MUT=7` selects the mutant (scalar2 MU_MUT 2).
  - The faces (generated wrappers) need no regeneration: the port lists are unchanged.
- Open hole, outside this lane's scope: at a non-root slice, an AMAX emit on the edge right after another emit lets am_v
  displace the pending AMV beat with no fault. The calendar spaces emits >= 46 edges apart.

## 3. Witnesses (runs/, fleet ot-epyc8, Verilator 5.050, RTL 95074c8a3, one build per ot-run job, 24 GB units)
Script: `run_group.sh`. These were run on master (0), the W face (1) and the E face (2):

| case | result |
|---|---|
| F{0,1,2}_nu1_ag: a-g, i, j at MU_NU 1 (identity) | PASS all |
| F{0,1,2}_nu4_ag: a-g, i, j at MU_NU 4 | PASS all |
| F{0,1,2}_nu4_m_s21 / s22: 4 users, token idx AND token user (status [27:26], TOK tag, slice-1 status) | PASS 8/8 each |
| F{0,1,2}_nu4_n: mixed merge must fault (sc 1, port 0, slice 1 clean) + legal tokens / users | PASS 2/2 each |
| NEG_n_am7_f{0,1,2}: check dropped (AM_MUT 7) | FAIL 1/2 as wanted |
| FACES_mut0_nu1 / nu4 (W1 W0 E0 E1 chain) | PASS |
| lint MU_NU 1 / 4 | clean |

Mutant fail regex (AM_MUT 7, bench n): `mixed: root sc fault 0 \(want 1\)`. The witness logs are NEG_n_am7_f*.out.
Bench o is not affected; its files are unchanged.
Bench h (12-slice SETID, MU_NU 1 / 4, 96 GB units) was still running at commit time: see pending_results.

## 4. SLICE-E / slice2_w
Not carried. The _e branch re-cut (qfd_dv_slice2_lpf_parts lpc) has to be regenerated and re-benched by SLICE-E. The
instructions are in lanes/OWN-QWEN-SLICEE.md and lanes/Q-KITS.md.
