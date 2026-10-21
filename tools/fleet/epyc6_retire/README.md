# EPYC6 retirement deadline

Owner instruction (2026-10-21 08:19 PT): drain ot-epyc6 until 14:15 PT, preserve partial results, stop remaining jobs by exact unit/container/PID and record their lanes for relaunch, then terminate only after final archival verification.

This directory versions the existing operational watcher and its six helper scripts. The deployed location remains `/home/ubuntu/claude-takeover-20261007/lanes/epyc6-retire`; existing state and archive destinations remain there.

The archive pass can hold `state/watch.lock` for hours. `epyc6_retire.py --deadline-only` instead uses `state/deadline.lock`, performs no action before 14:15, verifies the provider/SSH identity, saves the current archive roots and fresh job inventory in `state/deadline_partial_snapshot.json`, then invokes the existing exact cancellation path. Source directories remain available for final copying. C3 merges the snapshot's observed directories so a killed job cannot disappear from archival scope. The enforcer never calls DELETE. It records `state/deadline_complete.json` only after a fresh inventory shows no remaining jobs; errors retry on the next timer tick. Retirement's own rsync processes are excluded from the job inventory.

New archive passes check the deadline between roots and every 15 seconds during a copy, preserving the copy's original timeout and exact transport process. An already-running older pass can finish without interruption because the independent timer does not need its lock. Final C3 manifests now compare SHA256 of every preserved regular file and symlink target; same-size corruption blocks deletion. C2's existing checks and the final provider identity check remain in place.

Deployed timers:

```
*/15 * * * * cd /tmp && python3 -I <lane>/epyc6_retire.py
* * * * * cd /tmp && python3 -I <lane>/epyc6_retire.py --deadline-only
15 14 21 10 * cd /tmp && python3 -I <lane>/epyc6_retire.py --deadline-only
```

The per-minute enforcer is cheap before the deadline (no SSH/API calls) and retries incomplete cancellation afterward. `finish()` removes all watcher/enforcer cron entries after successful retirement. `--dry-run --deadline-only` never cancels jobs.

Focused tests (no SSH/API requests or actual cancellation):

```
python3 -m unittest discover -s tools/fleet/epyc6_retire -p test_deadline.py -v
```

They cover the exact clock boundary, a busy archive lock, concurrent enforcers, retries, wrong identity, missing inventory, continued archive transport, final-copy scope, and same-size/symlink corruption.
