# ot-run hub recovery (INFRA2, 2026-10-24)

The fleet job launcher `ot-run` runs on ONE hub: **epyc1 (= tender-ray, 84.32.71.203)**. Since 10-24 its root md0 is a
1-disk RAID1 (nvme0n1p2 only; nvme1n1 became /srv/opentallas-scratch2). If epyc1 dies, no new heavy job can be launched
until another host is made the hub. Standby = **epyc3** (eternal-dove, 96 threads, 1 TB, root 7.3 TB 19 %, scratch2 6.9 TB).

## What the hub consists of
| Item | Path on epyc1 | Notes |
|---|---|---|
| launcher | `~/.local/bin/ot-run` (+ `.bak-rtxpro-1024`, `.bak-split-1024`) | single python3 file; host tables at the top (HOSTS, HOST_ROLE, HOST_RESERVE, NO_AVX512, HOST_MAX_DIE); re-read from its own file every 120 s |
| fleet size table sync | `~/.local/bin/ot-sizes-sync`, cron `*/10` | pulls `/var/tmp/ot-heavy/sizes.json` from all hosts, writes `sizes.fleet.json` everywhere |
| admission (per host, identical on all 5) | `/usr/local/bin/{ot-heavy,ot-heavy-reconcile,ot-protect-die,ot-vl-jcap}`, `/etc/ot-heavy.conf`, `/etc/ot-oomadj-legacy-cutoff`, system unit `ot-die-protection.service`, user cron `*/2 ot-heavy-reconcile` | already installed on epyc3 (and epyc2/intel1/intel2) |
| launcher state | `~/.local/state/ot-run/{spill_pending/,signals.log,loadspill_no/}`, `~/.config/ot-run/held_hosts` (absent = none held), `~/.local/state/closure_loop/jobs` | spill_pending records = jobs whose outputs still sit on a spill host (`ot-run --spill-sweep` copies them back) |
| EDA tools on PATH for ot-heavy | `~/.local/opentallas-tools/bin` (yosys-0.68, opensta, verilator-5.050; 316 MB) | present on epyc3 |
| docker | `openroad/orfs:asap7lock` = `:latest` = 16470cea1d34 | present on epyc3 |
| ssh | `~/.ssh/config` aliases epyc2/epyc3/intel1/intel2 (IPs); private key `~/.ssh/id_ed25519` (ubuntu@epyc1) -- **never copied**; `ssh localhost` must work (own key in own authorized_keys) | workers do NOT call back to the hub (their ot-* tools use no ssh) |
| clients | agents on rtx-pro: `ssh epyc1 ~/.local/bin/ot-run ...` (rtx-pro key `~/.ssh/agidock_ot`, alias `epyc1`/`tender-ray`) | each running job's client is an ssh child of an ot-run process on the hub |

**"localhost" semantics:** in ot-run and ot-sizes-sync, `"localhost"` = the hub itself (reached by `ssh localhost`).
Moving the hub therefore SWAPS names: the new hub's alias becomes `"localhost"` (its HOST_ROLE and its NO_AVX512 Zen-3 flag
move with it -- epyc3 is Zen 3, so NO_AVX512 must contain "localhost" on an epyc3 hub), and the old `"localhost"` becomes
`"epyc1"` (plain worker; drop it if dead). HOST_RESERVE stays on "localhost" (the hub keeps 8 threads/16 GB for clients).
`lanes/otrun-hub-retarget.py SRC DST NEWHUB OLDHUB [--drop-old]` does exactly this and prints the diff.

## Backups (non-secret, nightly)
- epyc1 cron `15 2 * * *` `~/bin/otrun-hub-backup.sh` -> `epyc1:/srv/opentallas-scratch2/hub-backup/` (other disk):
  `files/<absolute path>` for everything in the table above, `meta/` = crontab, user units/timers, docker digests, ssh key
  file NAMES, mdstat/df, coord HEAD, `last-run.txt`. Log `~/.local/state/otrun-hub-backup.log`.
- rtx-pro cron `45 2 * * *` `~/bin/otrun-hub-archive.sh` (copy: `lanes/otrun-hub-archive.sh`; epyc1 script copy: `lanes/otrun-hub-backup.sh`) pulls that to `~/.cache/otrun-hub-mirror/` and pushes it to
  `155.103.253.53:/archive/otrun-hub/` (epyc1 has no archive key). Log `~/.cache/otrun-hub-archive.log`.
- Restore source, in order: epyc1 scratch2 (if the box lives) > rtx-pro `~/.cache/otrun-hub-mirror` > archive. The
  ot-run tools are also byte-identical on every worker's `/usr/local/bin`; ot-run itself exists ONLY in these backups
  (and on epyc3 as `ot-run-standby`).

## Standby state on epyc3 (installed + dry-run 2026-10-24 20:27 PDT)
- epyc3's own key (ubuntu@epyc3) appended to `authorized_keys` on epyc2, intel1, intel2, epyc3 (epyc1 already had it);
  backups `~/.ssh/authorized_keys.bak-infra2-1024`.
- epyc3 `~/.ssh/config`: aliases `epyc1 tender-ray`, `epyc2`, `intel1`, `intel2` appended (backup `config.bak-infra2-1024`);
  `ssh {epyc1,epyc2,intel1,intel2,localhost} hostname` all OK from epyc3.
- `~/.local/bin/ot-run-standby`, `~/.local/bin/ot-sizes-sync-standby` = epyc1 copies retargeted with
  `otrun-hub-retarget.py ... epyc3 epyc1` (HOSTS = epyc2, localhost, intel1, intel2, epyc1). No cron, no jobs submitted.
- Dry-run results: `ot-run-standby --status` rc 0, all 5 hosts reachable and admitting (same numbers as epyc1's live
  `ot-run --status`, with epyc3 shown as localhost and epyc1 as a worker); `ot-run-standby --selftest choose` PASS (29
  cases); `ot-sizes-sync-standby --print` reads the fleet table. NOTE: the standby copy is a snapshot of 2026-10-24 19:54;
  ALWAYS regenerate it from the newest backup at cutover (step 2).

## Cutover recipe (epyc1 dead or being retired)
1. Confirm: `ssh -o ControlPath=none epyc1 true` fails for >10 min (or the owner retires it). Post an OWNER/HANDOFF line.
2. Newest ot-run: take it from epyc1 `/srv/opentallas-scratch2/hub-backup/files/home/ubuntu/.local/bin/` if readable, else
   rtx-pro `~/.cache/otrun-hub-mirror/files/home/ubuntu/.local/bin/`, else the archive. On rtx-pro:
   ```
   B=~/.cache/otrun-hub-mirror/files/home/ubuntu/.local/bin
   python3 ~/coord/lanes/otrun-hub-retarget.py $B/ot-run /tmp/ot-run.hub epyc3 epyc1 --drop-old
   python3 ~/coord/lanes/otrun-hub-retarget.py $B/ot-sizes-sync /tmp/ot-sizes-sync.hub epyc3 epyc1 --drop-old
   scp /tmp/ot-run.hub epyc3:.local/bin/ot-run; scp /tmp/ot-sizes-sync.hub epyc3:.local/bin/ot-sizes-sync
   ssh epyc3 'chmod +x ~/.local/bin/ot-run ~/.local/bin/ot-sizes-sync'
   ```
   (Omit `--drop-old` if epyc1 is alive and should stay a worker.)
3. State: copy `files/home/ubuntu/.local/state/ot-run/` and `.config/ot-run/` from the backup to epyc3 `~/.local/state/ot-run/`,
   `~/.config/ot-run/` (spill_pending records point at src/dst hosts by alias; a record whose src is epyc1 cannot be swept
   back -- copy those outputs by hand from the dst host or drop the record).
4. Cron on epyc3: add `*/10 * * * * /home/ubuntu/.local/bin/ot-sizes-sync >/dev/null 2>&1` (ot-heavy-reconcile `*/2` is
   already there). Install `~/bin/otrun-hub-backup.sh` from the backup and its `15 2 * * *` line, and change
   rtx-pro `~/bin/otrun-hub-archive.sh` to pull from `epyc3:` (epyc3 also has /srv/opentallas-scratch2).
5. Verify on epyc3: `ot-run --status` (every host reachable, epyc3 listed as localhost), `ot-run --selftest choose` PASS,
   then `ot-run --selftest` (runs a tiny command on each host through ot-heavy; this IS a real submission, ok at cutover).
6. Clients switch: every agent uses `ssh epyc3 ~/.local/bin/ot-run ...` instead of `ssh epyc1 ...` (rtx-pro already has an
   `epyc3` alias + key). Update BRIEFING/_LANE_PREAMBLE ("ot-run lives on epyc3") and HANDOFF. Do NOT repoint the rtx-pro
   `epyc1` alias at epyc3 -- the name-swap in the host tables relies on aliases meaning the real hosts.
7. Jobs that were running when epyc1 died: their ot-run clients died with it, but the units (`oth-*` scopes) keep running
   on the workers; outputs land in the lane dirs on those workers. Lanes collect them there and must not relaunch into a
   live run dir (`systemctl --user list-units 'oth-*'` on each worker). Lane worktrees that lived on epyc1
   (`~/wt/<lane>`, `/srv/opentallas-scratch/claude/wt/<lane>`) are gone: re-create from the pushed branches on epyc3
   (sparse checkouts; `/srv/opentallas-scratch2/claude/wt/<lane>`).
8. Hub automation (re-enabled on epyc1 2026-10-24 by INFRA2): user timers die-ci-commit (hourly), die-ci-nightly (02:30),
   release-task-watch (:02/:32) + their `*.d/infra2-*.conf` drop-ins and `~/bin/hub-git-sync.sh` (copies:
   `lanes/hub-git-sync.sh`, backup `files/home/ubuntu/...`). On the new hub: `git clone` coord/state to `~/coord` (read
   mirror) and keep a clean `~/OpenTallas` on main (die_ci_cron.sh hard-codes both), copy `~/.local/state/die-ci/` and
   `/srv/opentallas-scratch/claude/die-ci/results` if reachable (previous-run deltas), install the units + drop-ins,
   `systemctl --user daemon-reload && systemctl --user enable --now die-ci-commit.timer die-ci-nightly.timer
   release-task-watch.timer`, and repoint the rtx-pro cron line that copies `TASKS_STALE.json`/`TASK_WATCH_SUMMARY.txt`
   (`epyc1:coord/...` -> `<newhub>:coord/...`). die_ci_cron.sh's run-host list (intel1 intel2 epyc2) is in the script.

## Known gaps / blockers
- Job-launch worktrees and run dirs on epyc1's root are NOT backed up (multi-TB); only pushed branches survive.
- ot-run references `~/bin/ot-reaper.py`, which does not exist on epyc1 (reaper silently skipped) -- same on epyc3.
- The standby `ot-run-standby` drifts whenever epyc1's ot-run is edited: step 2 always rebuilds from the latest backup.
- The nightly backup is up to 24 h old for spill_pending/held_hosts; run `~/bin/otrun-hub-backup.sh` by hand after editing ot-run.

## CODEX notes 2026-10-25 02:38 PDT
CODEX took over user-bus recovery (infrastructure-only, no source branch). PASS: epyc1 user manager PID11427 reexecuted in place with SIGRTMIN+25, restoring systemd/private without restarting user@1000 or cancelling any scope. Restarted only dbus.socket/service; both active. Two systemd-run --user --scope true smokes PASS. Removed only localhost user-bus-down line from held_hosts; all five hosts admit again (localhost 233 GB, run21 at 02:38). Existing 31 docker containers and30 oth scopes preserved (pre-reexec snapshot120 process IDs;93 still alive later, short compiler/sleep children naturally exited). The report-only STALLS epyc1 zero-scopes value was false because its bus was unavailable.
Runtime workaround: /run/user/1000/systemd/user/dbus.service.d/codex-runtime-recovery.conf sets Type=exec because the incident also deleted the manager notify socket; no user-manager restart until original scopes and Codex/tmux sessions are safely parked. Recovery evidence and held_hosts backup epyc1:/srv/opentallas-scratch2/claude/codex-infra/. Next: remove runtime override after eventual safe manager restart; this is not needed for scope-based ot-heavy work. Scratch status epyc1 root26%, scratch2 84%/559GB free; other workers above disk floor (epyc2 134GB at02:38).

2026-10-25 02:42 PDT CODEX: epyc3 standby refreshed from current epyc1 v14 (includes --stage), retargeted localhost<->epyc1 and NO_AVX512; choose selftest29 PASS, status all5 PASS. Standby only, no cutover/no jobs. Prior standby retained .pre-codex-20261025. Fresh STALLS shows127 jobs (before recovery89), QC qfd_dv_s8x_btab_adj10 idle1h43 delegated to QC owner; epyc1 inherited prune finished02:40 scratch264%/1.2TB free.
