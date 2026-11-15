# CORES-NOROW-1 handoff (2026-11-15 00:55 PST)
Cores: S81 dsdv_gunit_l1f_bf, HEAD s81hd_elemA_cv / elemB_cv (all unsigned; archive INDEX NO-DB for elemA/B; gunit ba0/ba1 stale).
- gunit bf: owned by TYPE-GUNIT-L1F (g4 epyc10 fable-review-cores/gunit_g4/..._gf5g4 in GRT; g3f epyc7/8 type-gunit-l1f/g3f). On first signoff: AUTO-RESIGN row + archive (QC-W515 waiter wait.sh polls g4).
- HEAD: kits at /srv/opentallas-scratch2/claude/type-hdcore-elemab/runs2/{A1,A2,B1,B2}(+B1r,B2r). A1 epyc10 6_final done, LEC running; A2 epyc9 6_final done, FAIL_POSTROUTE pin_audit. B1r/B2r route running (LEC advisory). Waiters: QC-W515 wait.sh/wait2.sh (localhost) archive on SIGNED.
- Next: Fable verdict in lanes/FABLE-TRIAGE-HEADKV.md; then run_kit_hbm.sh . post (ot-run, offer hosts) on A1/A2 routed DBs, B after route; check DRC0, setup>=-42, hold>=0; archive to AGIdock+rtx-pro; AUTO-RESIGN rows.
