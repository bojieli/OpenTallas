TOK-QWEN-6 2026-10-29: HEAD reservation token price (estimate before build, COMPILED_NOT_QUALIFIED)

Branch claude/tok-qwen-6-1029 = main 2b90210bd + Codex READY cherry-picks (565a9d295 9fee7b587 b5e1e322d befa24db0
c5529a41b 21129bc44 1577387ae 6dc0d4529). 6dc0d4529 lets run_mu833.sh take CST and OT_KV_HEAD_PREP_EDGES instead of the
hard HP=12 / 2,2,2,3,2,2 literals.

probe.sh/dock.sh rerun the Codex native7_currentqc recipe (bind7, KST 90,90,88,88,88,78,78, CST 5,5,5,6,4,4, F2) with
HEAD_PREP 12/21/37/40 (12 = old disproved slot; 21 = user0 prepare-only min; 37/40 = HOST-late held / filler-priority wire
slot from qc_head_schedule_1029). hp12 reproduces Codex targets.sha256 16/16 IDENTICAL.

Result: recurring_head_O61 moves cyc 12->40 (rx_out 29->57); token_period 293376, compiled token 290059, service pad 91,
emb_fill margin 1123 are UNCHANGED for all four; only boot_bundle, pair image and target11 differ. HEAD reservation costs
0 token edges up to 40. Not a qualification: actual GEN prepare dates/HOST interval/outgoing face mapping still decide
the value; physical phase/G5 not claimed.
