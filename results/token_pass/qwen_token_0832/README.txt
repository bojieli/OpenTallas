Qwen token takeover 2026-10-29 08:25 PDT

Inherited TOK-QWEN-7/8 HOST local-install deadlock fix remains under native proof:
intel1:/srv/opentallas-scratch2/claude/tok-qwen-7-1029/kvl/lr_nominal
unit oth-ubuntu-121042-1793282217. At takeover target7 accepted cycle17751;
no FAR_CAL expected until target0, setup and START around cycle38214.
No proof verdict yet. No predecessor job restarted or modified.

Actual completed old m3_kswap is INVALID as a token control: boot passes,
36 failed layer summaries all have cal_start -1 and no results. The previous
kv_verdict printed CAUGHT merely because a FAIL summary existed. New classifier
requires boot PASS plus a failed requested layer with a nonnegative calendar
start when --layers is used. Boot controls retain their explicit boot-failure
semantics. Original run untouched; copied log/exit now classify FAIL, not CAUGHT.
Seven focused tests pass, including actual stalled summary shape, genuine
started-layer mismatch, boot controls and infrastructure failure cases.

Current native successor cannot yet rebase: KV event27f bind is elaborating;
QC provider imported but not strict-bound, no adopted HEAD_CONTEXT/ROPE profile
or selected GEN/HOST publication timeline supplied yet. Continue those die gates
while inherited positive proof advances; do not launch another stalled long run.
