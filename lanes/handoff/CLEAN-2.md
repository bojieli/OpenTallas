# CLEAN-2 lane handoff (updated 2026-11-12 19:1x PST)

## 1 Scope
Fleet disk cleanup rules (COORD task 11-12). Dry runs done and reviewed. COORD APPROVED (19:0x) real use of classes a and c under --live-refs-only --aggressive (unsigned superseded, failed, cancelled/withdrawn, trims; signed only with verified ARCHIVED.json re-checked at delete). Stop + post on any ALERT, any path under closed_archive or /archive, or a symlinked target.

## 2 Branch
localhost:/home/ubuntu/wt/clean2 (sparse clone), claude/clean-2-1112@cf818e05ae, pushed. READY posted 19:1x (merge lane train 24). Merges clean on main (main has no tools/fleet change since base).

## 3 Approved steps (do in order)
1. DONE: READY posted.
2. After MERGED (check: git -C ~/wt/clean2 fetch origin main; git branch -r --contains cf818e05ae): deploy main's tools/fleet/ot-autoclean.py + wt-reaper.py on all 8 hosts KW-FIX-46 way: systemctl --user stop ot-autoclean.timer (localhost also ot-autoclean-push.timer), cp -p live file to .bak-clean2-1112, copy main file to .new in same dir, mv over (new inode), md5 == main, start timer. Localhost FIRST (its hourly push at :10 copies tools + builds the snapshot; snapshot needs live_attempts/live_keep, queue_open.json, protected_stale.txt for --live-refs-only, else the host refuses = safe).
3. Env: add " --live-refs-only --aggressive" to ~/.config/ot-autoclean-auto/env OT_AUTOCLEAN_ARGS (backup env.bak-clean2-1112); keep --classes abc (no d). Then run the push once (systemctl --user start ot-autoclean-push.service on localhost) so snapshots carry the new fields.
4. Real pass epyc4 first (scratch2 96%): df before; systemctl --user start ot-autoclean.service; df after; check manifest: 0 ALERT, no /archive or closed_archive paths, no symlinked targets. Then other hosts. Leave hourly timers on.
5. Signed export backlog: the export already runs: DISK-1111's epyc4 drive pid 467773 (log scratchpad kw46/drive_apply_epyc4_s2.log, ARCHIVED ... sha256 all match lines; FAIL lines are mostly epyc4 sshd resets, retried) and the hourly localhost drive (drive --no-run --apply --commit). epyc4 dry count: 1805 signed units in held attempts, 1669 already ARCHIVED.json. Do not kill those drives.
6. RESULT to COORD: GB freed per host (df before/after + manifest DELETED sums), then STOP.

## 4 Dry-run evidence
Per host results: scratchpad clean2/res-<host>.txt (summ3.py). Dry state on hosts: ~/.local/state/ot-autoclean-clean2 (A), .../aggr3 (B3 aggressive). Reaper-only dry rerun with marker fix: in/clean2_wt.sh, log wt2.log (running 19:0x).

## 5 Gotchas
- pgrep -f inside an ssh command string matches the ssh bash itself (I killed my own ssh shell once): put pgrep in a script file.
- argparse: --wt-reaper-args=--no-rescue (with =); empty --protected-dbs-repo needs '=' when replayed.
- localhost ~/coord is current (19:01) despite FLEET-2's note.
