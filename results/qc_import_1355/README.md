# QC physical import continuation, 2026-10-29 13:55

Base: exact DIE-QC-36 6ea044ed3cb7e4cd4a9103a03d5ba8f1b07ec10b. Own source worktree codex-qc-import-1355; own run root intel2 `/srv/opentallas-scratch2/claude/codex-qc-import-1355`.

Collected BB1 terminal FAIL: 88,801/89,180 clock pin backbones placed, 379 unresolved. Accepted shapes remain untouched. The residual solver imports every accepted record/reservation and retries only these 379 pins inside the same declared islands, max M6 jog 2.0um versus the prior 1.5um. Each still-failing pin gets island/M6-M7-obstacle/M8-track diagnostic counts. It is a geometry construction, not P&R or qualification. Own `residual.otrun.log` records admission and final status; `backbone_residual/summary.json` governs the remaining open count. Do not adopt partial reservations as complete.

The inherited A/B PG chain failed before construction: `NameError: name w is not defined` from nested shell/Python quoting (`paA.otrun.log`, unit390270). The corrected own runner passes paths through Python argv/heredoc, preserves upstream status and unresolved count, and labels partial inputs diagnostic. It does not change or kill predecessor jobs. PG construction is not a die GRT/STA/freeze result.

PROG source contract finding: strict-bind23ef9f36b1 reused elaboration epyc2 `die-qc33-bind/elab/asbuilt.json`; `$paramod\\qfd_dv_s8_vm8q_rp1\\MIF=0` cell `u_pg` explicitly has MIF=0, and qfd_dv_s8x_prog defaults0. The newly signed MIF1 physical view therefore is not qualified by that current native functional bind. Reported to QC owner; no source/contract edit here.
