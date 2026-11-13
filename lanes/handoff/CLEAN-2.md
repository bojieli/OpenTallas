# CLEAN-2 lane handoff (updated 2026-11-12 19:3x PST)

## 1 Scope
Fleet disk cleanup rules (COORD task 11-12). Dry runs done and reviewed. COORD APPROVED (19:0x) real use of classes a and c under --live-refs-only --aggressive (unsigned superseded, failed, cancelled/withdrawn, trims; signed only with verified ARCHIVED.json re-checked at delete). Stop + post on any ALERT, any path under closed_archive or /archive, or a symlinked target.

## 2 Branch
localhost:/home/ubuntu/wt/clean2 (sparse clone), claude/clean-2-1112@cf818e05ae, pushed. READY posted 19:1x (merge lane train 24). Merges clean on main (main has no tools/fleet change since base).

## 2b OWNER ORDER 19:2x (via COORD): old hourly cleanup STOPPED + DISABLED by COORD on all 8 hosts (ot-autoclean.timer; localhost also ot-autoclean-push + ot-autoclean-drive timers). Do NOT re-enable old timers/config. After MERGED: unit runs only main's code with --live-refs-only --aggressive --classes abc as FIXED unit args (not the old env), then enable. If train 24 not MERGED by ~20:25: real pass by hand from cf818e05ae, epyc4 first: fresh snapshot via scratchpad clean2/build_snap.py <branch ot-autoclean.py> <dir> (tested 19:3x: 9600 live attempts, 619 live keep, 515 open READY/ASK paths, 1755 stale rows), scp to host state dir ~/.local/state/ot-autoclean-clean2/snapshot-real, run ~/.local/share/ot-autoclean-clean2/ot-autoclean.py (= branch tip) run <args> --apply --live-refs-only --aggressive --classes abc --state ~/.local/state/ot-autoclean-clean2/real.
Reapers left running by COORD (job reapers, not disk cleanup): intel2 */15 released-reaper, localhost */30 ~/bin/ot-reaper.py, localhost ot-orphan-reaper timer. Assessed + told COORD 19:3x: no direct conflict; ot-reaper HAND/UMBRELLA (idle>48 h lane dirs) honours lanes/PROTECTED-DBS + signed only, looser than the new rules; follow-up idea: make it read the autoclean union.

## 3 Approved steps (do in order)
1. DONE: READY posted.
2. (timers: see 2b) After MERGED (check: git -C ~/wt/clean2 fetch origin main; git branch -r --contains cf818e05ae): deploy main's tools/fleet/ot-autoclean.py + wt-reaper.py on all 8 hosts KW-FIX-46 way: systemctl --user stop ot-autoclean.timer (localhost also ot-autoclean-push.timer), cp -p live file to .bak-clean2-1112, copy main file to .new in same dir, mv over (new inode), md5 == main, start timer. Localhost FIRST (its hourly push at :10 copies tools + builds the snapshot; snapshot needs live_attempts/live_keep, queue_open.json, protected_stale.txt for --live-refs-only, else the host refuses = safe).
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
