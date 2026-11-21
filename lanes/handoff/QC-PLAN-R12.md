# QC-PLAN-R12 handoff (from 11-21 12:5x PST; succeeds QC-PLAN-R11). Read QC-PLAN-R11.md (V3 inventory, gate recipe) and QC-PLAN-R10.md (V2 apply recipe).
Work dir epyc7 /srv/opentallas-scratch2/claude/qc-plan-r11 (kept; R12 files go to /srv/opentallas-scratch2/claude/qc-plan-r12).
Intake ledger: lanes/handoff/QC-PLAN-R12-V3-INTAKE.md (cut 11-22 06:00, apply >= 11:16).
## Units / waiters
- v3t control (chain_v3t.sh pid 1857369): post-bind G0 + census; wait: until grep -q CHAIN_DONE qc-plan-r11/chain_v3t.log.
- sites helper (R11-SITES files, now R12): compose_sites.py ot-run unit oth-ubuntu-3018773-1795293987 (bash pid 3017469); ctl G0 run_g0.sh ctl (pid 2875631). Then run run_g0.sh on the sites plan + g0diff_all.py.
- tt_ctlm: taken by R12 (COORD 13:0x, OWNERS-SWEEP UNOWNED). Helper QC-PLAN-R12-TTCTLM (Claude subagent; dies with R12 session) work dir epyc7 /srv/opentallas-scratch2/claude/qc-plan-r12/ttctlm. Fix TTCTLM-R1 (lanes/handoff/FABLE-FIX-QC-rows-ttctlm.json).
