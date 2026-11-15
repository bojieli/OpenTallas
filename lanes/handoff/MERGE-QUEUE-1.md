# MERGE-QUEUE-1 handoff (successor, updated 2026-11-14 21:20 PST)

Task (OWNER 11-14): automatic merge queue for sha-pinned COORD approvals + kit wave on a pinned main tree. DONE, in operation.

## Live
- Queue: intel2 ot-merge-queue.timer (5 min). The service is TEMPORARILY pinned to the bootstrap copy ~/merge-queue/bin/ot-merge-queue
  (VERSION file), see the comment in ~/.config/systemd/user/ot-merge-queue.service. After 7fff3a1e0b1 lands, restore the ExecStart
  to the repo form (tools/fleet/systemd/ot-merge-queue.service: rt/current copy, bootstrap fallback) and daemon-reload.
- Log ~/merge-queue/log, state ~/merge-queue/state.json (re-queued false REDs listed under "requeued"); `ot-merge-queue status|parse`.
- Only COORD/OWNER-authored lines approve. Conditional rulings: proposed 'COORD APPROVED-IF:' (the queue ignores it).
- Gate: touched-path test selection under xdist; a new failure must also fail on a serial rerun of the branch and must not fail when the
  whole file runs on main (per-item base tree, same sparse set). Sparse: tools/, physical/common_flow, rtl/lib, rtl/common.
- Wave: autopilot.service drop-in zz-kw38-picker-runtime.conf + autopilot-aux.service run rt/current (backups ~/merge-queue/*.bak-mq1-1114).
  First tick on rt/76537ad08a5b 21:02-21:09 ok, run-items from rt/<sha>. kw38/rt is kept only for units still running from it.
- ot-tools-sync flips rt/current on hub + intel1 epyc2 epyc7 epyc8 epyc9 epyc10 after every push; ot-tools-drift.timer every 15 min.
- Per-host ot-run backends still differ from main (ADMIT-TUNE-1 owns them); drift lines list them.

## Open
- READY 7fff3a1e0b1 (whole-file baseline) waits for the COORD token.
- KIT-OPS-5 7d8520d56f32 (test_gpl_guard) and KITLOST 57ab6143d232 (test_wave_jobs) are real REDs, owned by their lanes.
- Local clone on rtx-pro: /home/ubuntu/wt/merge-queue-1-1114. Debug worktree intel2 mq1/wt/dbg-pga (can be removed).
