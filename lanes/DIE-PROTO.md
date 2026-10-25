# DIE-PROTO (owner-approved 10-25 ~06:29): industry-style die prototype on the CURRENT plans
Goal: die-top GRT on partition abstracts (signals <= M7, dec. 12) + die STA with real signed views where they exist
(stand-ins + 40 ps contract elsewhere), per release die: s81, s81_head, qwen_compute, qwen_kvsys, HBM (B2n on main if G0C).
Branch claude/die-proto-1025 (worktree epyc1:/srv/opentallas-scratch2/claude/wt/die-proto-1025); fleet data
<host>:/srv/opentallas-scratch2/claude/die-proto/<die>/; results results/die_proto_1025/<die>/.
## Log
2026-10-25 06:32 PDT DIE-PROTO: started. Tools: die_trial.py kit/grt (abstracts, ft crossings + reset, M4-M7 signals,
  M8/M9 clock/PG obs) + die_sta.py/die_ci.py ILM with signed views. Signed partition types on current plans (release cache):
  S81 slice_station t12/t17/t20/t21, KV kv3_head_eighth e1/e3/e5/e7 (plan match to verify); QC/head none (cores only).
