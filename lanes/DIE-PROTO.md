# DIE-PROTO (owner-approved 10-25 ~06:29): industry-style die prototype on the CURRENT plans
Goal: die-top GRT on partition abstracts (signals <= M7, dec. 12) + die STA with real signed views where they exist
(stand-ins + 40 ps contract elsewhere), per release die: s81, s81_head, qwen_compute, qwen_kvsys, HBM (B2n on main if G0C).
Branch claude/die-proto-1025 (worktree epyc1:/srv/opentallas-scratch2/claude/wt/die-proto-1025); fleet data
<host>:/srv/opentallas-scratch2/claude/die-proto/<die>/; results results/die_proto_1025/<die>/.
## Log
2026-10-25 06:32 PDT DIE-PROTO: started. Tools: die_trial.py kit/grt (abstracts, ft crossings + reset, M4-M7 signals,
  M8/M9 clock/PG obs) + die_sta.py/die_ci.py ILM with signed views. Signed partition types on current plans (release cache):
  S81 slice_station t12/t17/t20/t21, KV kv3_head_eighth e1/e3/e5/e7 (plan match to verify); QC/head none (cores only).
2026-10-25 06:35 PDT DIE-PROTO: branch claude/die-proto-1025 pushed (=main 6a6fc12dd). 4 sub-agents launched: S81; s81_head+qwen_kvsys; qwen_compute; HBM (B2n on main G0C check first, B2o if it passes). Each: die_trial kit + die GRT (M4-M7) via ot-run, hop check vs 405, die_sta ILM with contract stand-ins + matching signed views, renders viewed. Fleet data epyc1:/srv/opentallas-scratch2/claude/die-proto/<die>/.
## PARKED 2026-10-25 08:11 PDT (FLOW-INFRA/DIE-PROTO-COLLECT)
Branch claude/die-proto-1025@bd51e6310 (results/die_proto_1025/SUMMARY.md + small logs/json/png). All 5 plans = main 394765394 plan sha.
Results: s81_head GRT ovf 0 (STA ideal PASS, tree no-PHY FAIL hold -154.6/skew 213.65); qwen_kvsys GRT ovf 0 but render peak 1.86 vs 25% FT share + 240 hops >405;
 qwen_compute it5 GRT ovf 1,659,581 (M6 407k H, M7 1.25M V) in SU FT band y10-11mm; s81 + hbm GRT pending.
Live jobs (do not duplicate): epyc1 dtrial-grt-3950895 (s81 GRT, 50 iters, ot-run client 3768013); epyc1 dtrial-grt-3616206 (hbm GRT, client 3450983);
 intel2 dtrial-grt-134732 (qwen_compute GRT 50 iters, client epyc1 2328984); epyc1 s81 sta_ideal (oth-ubuntu-3870481), kvsys sta_tree/sta_ideal (oth-ubuntu-3968450/3969990);
 intel1 qwen_compute kit2 STA TT/FF (oth-ubuntu-1542297/1542814); intel2 hbm die_sta (oth-ubuntu-296097); waiting clients: kvsys run_sta_branch (epyc1 429300), s81_head run_sta_branch_nophy chain (epyc1 431301).
Next: collect s81/hbm GRT by-layer overflow when they finish (50 iters is >20 min/iter; consider 5-iter variant only if they stall); collect die STA verdicts; QC: SU FT band structural fix (PATH-QC); KV: per-bit lattice (PATH-KV); head: clock load contract (CLOCK).
2026-10-25 08:38 PDT PATH-QC-PLAN: DIE GRT on delta plan claude/path-qc-plan-1025@f8e1f8c624 (die_trial kit, same grt.tcl as DIE-PROTO kit_it5: signal M4-M7, M8/M9 0.4, 5 congestion iters): TOTAL OVERFLOW 0 (H 0/V 0), usage 6.66%, WL 640 m, 494k nets, 2m26s on epyc3 -- vs START it5 1,659,581 (M7 1.25M, M6 407k). Cost: die 787.55 -> 819.92 mm2 (+32.4, SU rows 1339.2 um), ports 3410->3065, lanes 2207->1933. Kit+log epyc1:/srv/opentallas-scratch2/claude/path-qc-plan/dgrt/kit. G2 x13 path types: 7 CLEAN ov=0 so far (cbn_q00/q01, coll_ftc, fw_v3, st_a_v2, st_b_v2 + ctl/fe pending exit); sc_v3/stm_v3/su_* still running.
