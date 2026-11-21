# FAM-S81-SLICE-R2 handoff (Opus 5.5, 11-21 04:4x PST)
Work root epyc10 W=/srv/opentallas-scratch2/claude/fam-s81-slice. Inherits lanes/handoff/FAM-S81-SLICE.md (R1, 04:12).

## Live units (epyc10; my local pollers die with this session -> re-arm)
- t36 on C1n: unit oth-ubuntu-344587-1795255611, kit $W/t36_c1n/gen/slice_station__t36, log run_grt.log. POST-hook CTS: setup_ws +141.35 tns 0, hold_ws -78.3 (pre-GRT), 287k nontap, 76 taps skew <=38 ps. In GRT.
- xs4_equiv benches MOVED to epyc8 (04:3x): R=/srv/opentallas-scratch2/claude/fam-s81-slice-r2 (clone copy of 4f03fa6cea inputs, also on epyc7/intel1); units oth-ubuntu-140437 (wreg) / oth-ubuntu-140439 (base), client PIDs 138553/138554 on epyc8, logs $R/bench_{wreg,base}.log. R1's epyc10 clients 3455439/3455440 cancelled (never admitted).
- census t1,t5,t6,t7,t8,t10: $W/census/t*/stats.json (yosys running).
- t9 C1n kit gen (python): $W/t9_kit.sh -> $W/t9_c1n, log $W/t9_kit.log, client PID 3607783. Purpose: WREG define-on proof (kit rtl copy+mv with define) + xfin DLV=1 check (1,603 xf->f_d paths).

## Done
- t6 attempt_46 (old plan 3fa87b84b18): NOT live on any host (checked epyc10 docker mounts of all openroad, ot-jobs, ot-status on 6 hosts). Nothing to cancel. Posted.

## Next
1. bench_wreg PASS + base PASS -> equivalence of define-off (bench base = previous form) -> ot-push-main 4f03fa6cea (branch claude/fam-s81-slice-wreg-1121) -> post define+sha to S81-J6-ASSEMBLY-R2.
2. If bench_wreg mismatches: +1 on arrival tables / read side, declare +1 latency.
3. census -> strip/body sizes to S81-J6-ASSEMBLY-R2.
4. t36 GRT -> finish to sign-off (needs src_manifest rebuild for export).
