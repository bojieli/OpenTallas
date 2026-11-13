# CLEAN-2 lane handoff (updated 2026-11-12 22:02 PST): RESULT posted, lane STOPPED

## State now
- All 8 hosts run main b9c049d416 tools as new inodes: ot-autoclean.py 7033b99c, wt-reaper.py b41e676d. The old 96d3ada9/3a9cba07 files are kept as ~/.local/share/ot-autoclean-auto/*.bak-clean2-1112.
- Unit drop-in ~/.config/systemd/user/ot-autoclean.service.d/clean2.conf (epyc8/9: zz-clean2.conf, sorted after sg-docker.conf and wrapped in sg docker -c). It clears EnvironmentFile and OT_AUTOCLEAN_ARGS (the old env is not read) and sets fixed args: run --host H [--srccopy on localhost] --queuename-skip-superseded --queuename-skip-trim-c --c-old-keep-h 24 --union-real-sources-only --keep-expire-h 24 --classes ac --live-refs-only --aggressive --apply, plus the reaper setting.
- wt-reaper: OFF (--wt-reaper=) on localhost, epyc4, intel2, intel1, epyc2 and epyc7 since 21:4x (COORD: not approved for real use; idle 2 h too short). epyc8/9 drop-ins show --wt-reaper-idle-h 24, set by someone else before my change; COORD allows >= 24 h.
- Timers ENABLED: ot-autoclean.timer on all 8 hosts. Localhost: ot-autoclean-push.timer (:10, snapshot + tool push, main code) and ot-autoclean-drive.timer (:05, drive --no-run --apply --commit = signed export with sha256 + manifest collect, no deletes).
- Still running: old-code drive PID 1583582 (started 16:17 with old code in memory). It pushed a 16:17 snapshot to epyc4 at ~21:1x. The new code refused it ("4.9 h old"; nothing deleted). I refreshed it with a push at 21:39. The next push at :10 refreshes all hosts. DISK-1111 export drive PID 467773 (epyc4 scratch2) is still running. Do not kill either: they carry the signed export.

## Real pass results (first new-rules pass per host)
Columns: host | manifest DELETED rows / GB | df freed | worktrees removed by the reaper
- epyc4 | 301 / 214.6 | +204.6 (scratch2 96%->93%) | 0
- intel2 | 438 / 240.6 | +266.7 | 15
- epyc2 | 250 / 117.5 | +87.9 | 0
- epyc7 | 96 / 130.1 | +1529 | 58
- intel1 | 155 / 13.8 | +20.8 | 0
- epyc9 | 41 / 33.7 | +17.6 | 0
- epyc8 | 99 / 140.0 | +84.9 | 0 (reaper stopped)
- localhost | 0 / 0 | +108 | 5

0 ALERT, 0 /archive or closed_archive paths, 0 symlinked targets on every host. Signed attempts deleted only with export verified: epyc4 62, epyc7 11, epyc2 6, epyc9 6, intel2 4, epyc8 1.
Note: the first epyc8/9 passes ran DRY with no args because sg-docker.conf overrode clean2.conf; fixed (zz-clean2.conf) and rerun.

## Worktree removals (NOT reviewed by COORD; see lanes/handoff/CLEAN-2-wt-removed-1112.tsv)
- 78 removed for real (epyc7 58, intel2 15, localhost 5).
- All were clean or pycache-only, with at most 100 MB of ignored non-cache data (reaper rule). Each was an ~20 GB tracked checkout.
- 59 heads are on GitHub origin. 19 are not (15 not found, 4 on branches that have since moved). For all 19, the branch ref still exists in a host repo at the same head (listed in the tsv), so they are recoverable with git worktree add.
- The dry run showed epyc7 at 0 because my reaper-only dry replay used the old union. The real union released 3191 stale ARCHIVE-PROTECTED 11-06 rows.
- The second-pass reapers (timer catch-up at 21:14) were killed by exact PID before they removed anything new (removals.tsv shows nothing after 05:07Z).

## Gotchas
- A new drop-in must sort after any existing one (epyc8/9 have sg-docker.conf).
- Enabling a Persistent timer fires it at once.
- pgrep -f inside an ssh command string matches the ssh shell itself.
