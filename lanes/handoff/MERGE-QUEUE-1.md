# MERGE-QUEUE-1 handoff (successor, updated 2026-11-14 ~20:05 PST)

Task (OWNER 11-14): automatic merge queue for sha-pinned COORD approvals + the kit wave running on a pinned main tree.

## State
- Branch claude/merge-queue-1-1114 head 54d5fd4ca78 (02e3ea1a719 + basetemp-parent fix). Local clone (rtx-pro): /home/ubuntu/wt/merge-queue-1-1114.
- Queue on intel2: bootstrap ~/merge-queue/bin (ot-merge-queue, ot-tools-sync), venv ~/merge-queue/venv, clone /srv/opentallas-scratch2/claude/mq1/repo,
  worktrees mq1/wt, log ~/merge-queue/log, state ~/merge-queue/state.json. `ot-merge-queue status|parse`.
- ot-merge-queue.timer ENABLED 19:4x (5 min). ot-tools-drift.timer NOT installed yet.
- READY posted (queue line ~11687) asking COORD for: COORD APPROVED: claude/merge-queue-1-1114 @54d5fd4ca78
- Wave still on kw38/rt (drop-in ~/.config/systemd/user/autopilot.service.d/zz-kw38-picker-runtime.conf + autopilot-aux.service).
- kw38/rt live-vs-main 3-way residual: /srv/opentallas-scratch2/claude/mq1/tmp/resid.out (+ first 8 in the STATE post). So far every residual is older live text that main superseded.

## Next
1. Approval lands -> queue merges, ot-tools-sync makes rt/<sha12>, rt/current.
2. Switch wave: drop-in ExecStart -> /srv/opentallas-scratch2/claude/rt/current/tools/autopilot/autopilot.py (fallback kw38), same for autopilot-aux; daemon-reload. Running units keep kw38/rt.
3. Install ot-tools-drift.timer. Tell ROOT-MERGE-63 to stop after first MERGED.
