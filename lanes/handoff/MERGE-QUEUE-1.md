# MERGE-QUEUE-1 handoff (successor, updated 2026-11-14 ~20:25 PST)

Task (OWNER 11-14): automatic merge queue for sha-pinned COORD approvals + the kit wave running on a pinned main tree.

## State
- Queue LIVE on intel2: ot-merge-queue.timer (5 min) runs ~/merge-queue/bin/ot-merge-queue (bootstrap, VERSION file) until
  rt/current/tools/fleet/ot-merge-queue exists. Log ~/merge-queue/log, state ~/merge-queue/state.json; `ot-merge-queue status|parse`.
- First MERGED 20:10 repo-state-1 -> main 243b6b4a4d5; ot-tools-sync made rt/243b6b4a4d5c = rt/current on hub + 6 hosts.
- MERGE-FAIL 20:10 wave-recipe-1 3d69f0eb0c5 (xdist isolation: test_m8_grant + form_wait_arm), 20:16 pg-aware-1 288ada0041 (97 test_bind).
- Parser: only COORD/OWNER-authored lines approve (fixed 20:00 after my own STATE quote nearly self-approved; a 20:00:00 run was stopped, nothing pushed).
- Own branch claude/merge-queue-1-1114 head 4b9ede660cd, dry-run GREEN on 243b6b4a4d5; READY posted, waiting for COORD token
  `COORD APPROVED: claude/merge-queue-1-1114 @4b9ede660cd`. Local clone /home/ubuntu/wt/merge-queue-1-1114 (rtx-pro).
- ASK posted: conditional approvals should use 'COORD APPROVED-IF:' (ignored by the queue) until the condition is met.
- kw38/rt residual (mq1/tmp/resid.out): 48 live-modified files, every residual is older live text superseded by main (runtime files); only old-semantics test hunks are live-only. Safe to move the wave.

## Next
1. Own branch lands -> rt/current at that sha (has content rt_tools digest).
2. Switch wave: replace (copy+mv) ~/.config/systemd/user/autopilot.service.d/zz-kw38-picker-runtime.conf ExecStart -> /srv/opentallas-scratch2/claude/rt/current/tools/autopilot/autopilot.py (fallback kw38), same for autopilot-aux.service; daemon-reload. Running units keep kw38/rt. Backups *.bak-mq1-1114.
3. Install ot-tools-drift.service/.timer. Post RESULT.
