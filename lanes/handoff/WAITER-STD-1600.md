# WAITER-STD-1600 handoff (2026-11-20 ~16:15 PST)

Built and pushed to main (2c5b84faf6, deployed by the merge-queue sync to rt/current on all 6 build hosts + hub; ot-wait symlinked on
PATH of all 7 hosts with tools/fleet/install_path_tools.sh):
- tools/fleet/ot_status.py: status file per ot-run client (otrun-<host>-<pid>) and per ot-push-main (otpush-<host>-<pid>) in
  ~/.local/state/ot-status/<name>.json {rc, t_end, log, unit, lane, pid, pid_start}; DONE/DIED posted via ~/coord/bin/post.sh
  (hub direct, other hosts via ssh intel2) under the lane: ot-run only when the submitting shell exports OT_LANE=<LANE> (DONE only when run >= 120 s,
  OT_STATUS_DONE_MIN_S); ot-push-main also falls back to the clone dir name. OT_STATUS=0 / OT_STATUS_POST=0 switch off. Tests of other
  files that run ot-run/ot-push-main under pytest write nothing.
- tools/fleet/ot-wait <name|oth-unit|pid> [--timeout S] [--cmdline TEXT]: exits with the job rc; 66 not found, 70 plain pid ended
  (rc unknown), 71 client died with no status, 124 timeout. Exact pid mode checks starttime + /proc cmdline.
- Rule line in AGENTS.md and lanes/_CORE_LANE_RULES.md.
- tools/fleet/test_ot_wait.py (15 tests).
Not done / open: status files are never pruned (300 B each; prune via ot-delete later); ot-wait waits only for records on its own host;
the autopilot's ot-run launches write status files but never post (no OT_LANE).
Waiters: lanes/STALE-WAITERS.tsv. 68 pure >24 h waiters killed (exact pid, cmdline re-checked). 'pgrep-waiter-with-work' (64), other forms
(47) and the live Claude tool shells (53, localhost) were NOT touched: lanes should replace them with ot-wait when they next look.
