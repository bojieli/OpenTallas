# S81-ALLFIX-MULTI handoff (Opus 5.5; started 11-23 16:28 PST). FAMILY lane multi/die rows -> S81-ALLFIX-INT.
Brief: localhost scratchpad allfix_brief.txt + resume_1123b/e.txt + rules.txt. Base B1 ae3101241d6b (E10 b1_tree/physical/die_plan/s81/plan_j9_b1_exact_1123_ae3101241d6b.json).
Work dir E10 /srv/opentallas-scratch2/claude/s81-allfix-multi/{rhi,rr,x13} (E10 scratch ~70 GB, DRAINING: only existing --dir works).
## Done
- RHI row 8c512474bcf6 (rhi/plan_rhi.json, RST 384 + HSK 402 + io_hold) PRE 0/178. ROW-REBASED posted 17:2x.
- ROW-MAP posted: umbrella rows mapped to base/family lanes; x14+GFLOCAL left to INT; misc data legs -> ALLFIX-SVC.
- x13 census (x13/census_ae31.json): 32 BIND_IGNORED all svc_hi; ROW-REBASED posted (env OT_BIND_TYPE_DEFINES=on).
## In progress
- RHI-RST-REACH: rr/rr_run.sh TAG TYPES --local-taps (bank_reset_delta.py rt 70b6f0430ea9). J8-RTL dry: eng 1303->381 (2 local taps), gunit 2285->112, iqf 968->194, seqhost 1356->292; serdes 0 banks on rst_n (already bank_taps). Final needs B1 bound RTL (j9_b1_exact_1123_out/rtl, EMIT in progress), then --second-pass for eng, then PRE, ROW-REBASED.
- Owed: rc67 hop re-scan + x13 census on INT combined plan.
## 17:5x
- RHI-RST-REACH v1 12cd5a01764b (rr/plan_v1.json) PRE 0/178, ROW-REBASED posted. Chain: seq0 (B1 RTL seqhost) -> v1a (J8 RTL eng,gunit,iqf --local-taps) -> v1 (eng --second-pass). Needs env OT_PLAN_ROOT=b1_tree/physical/die_plan/s81 OT_RT_CURRENT=b1_tree.
- v2 = same chain with B1 RTL once j9_b1_exact_1123_out/rtl has s81p_{eng,gunit,iqf}__t1.sv (waiter running). Then pre.sh plan_v2.json v2 and post.
- REPORT to COORD posted 17:5x.
