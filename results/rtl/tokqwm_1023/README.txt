TOKe-QWM 10-23: Qwen ROM functional token record, ALL 9 stages on ONE assembly = main 92c2417f6 (git archive rtl tools configs
physical/asap7_memory_macros; driver tools = main tools/qwen_tokfunc). RUNROOT /srv/opentallas-scratch/claude/tokqwm-1023 on
gold1 (stg, head, attnret), gold2 (xt1), ep7 (tp8, ovl4u --release-masters, ctx4u, xdie), ep9 (kv --explicit-r17, chain).
Fixture reuse (model-derived, not RTL): stg --fx = tokqw4 stg3/fx; stg fx_res 115/115 == main; link fixtures 57/57 == 09a3eb64f staging.
Bound-source delta 09a3eb64f -> 92c2417f6: tt_ctlm/head RTL (head stage) + tb_qfd_dv2 xhead probe wires (stg tb); nothing else bound.
xhead = committed claude/tokd-qw-1022@299d1e880 per-consumer bench (tokqw4 tree, not re-run on this assembly).
Verdicts: stages/*.json; compose: compose/report.json (u1/u4, gaps, held reasons). run_scripts/ = exact staging/launch/compose.
