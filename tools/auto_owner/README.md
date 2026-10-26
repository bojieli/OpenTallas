# AUTO-OWNER (owner 2026-10-18)

Every open element of the current dies must have a live job or a live owner, without a human noticing.

- `element_owner_watch.py`: computes ACTIVE / STALE / UNOWNED for every open current-die element (fleet-viz `/api/elements`), takes the automatic actions (main's `submit_exact` for passing non-critical kits, gate-and-submit for kits without a gate, `flow_failure` resubmits of admitted re-routes, critical tiles to `lanes/COORD-REVIEW-QUEUE.md`) and writes `UNOWNED.json`, the input contract for the coordinator's hourly check: every element with `needs_agent: true` gets a fresh family agent.
- `release_task_watch.py` (TASK-WATCH, owner 10-19): liveness of EVERY open `RELEASE_TREE.md` task from evidence, never from the status text: live processes in named run dirs (one probe per fleet host + localhost), exit markers of die-chain run dirs, closure-daemon jobs, fleet-viz jobs, owner lane files and HANDOFF lines. Classes LIVE / WAITS-OK / BLOCKED-ON-OWNER / STALE (no evidence for 60 min) / DEAD (the newest named run failed and nothing named is live). Writes `TASKS_STALE.json` + `TASK_WATCH_SUMMARY.txt`; the coordinator's hourly check (Claude or Codex) launches a fresh agent for every task with `needs_agent: true`. Tests: `test_release_task_watch.py`.
- `release_tree_render.py`: the release-tree renderer (fleet-viz `/release`) with the "tasks LIVE / STALE / DEAD" banner (+ DEAD/STALE list) and the ACTIVE / STALE / UNOWNED element banner.
- `systemd/`: `element-owner-watch.{service,timer}` (user units, every 30 min): element watch, then task watch, then re-render.

Deployed copies run from `~/claude-takeover-20261007/tools/`; this directory is the version-controlled source.

## stall_watch.py (report only, 2026-10-25)

`stall_watch.py` runs on the ot-run hub (epyc1) from `systemd/stall-watch.timer` (every 15 min, :05/:20/:35/:50) and
writes exactly one file, `~/coord/STALLS.txt`; the rtx-pro crontab rsync (7,22,37,52) copies it next to
TASK_WATCH_SUMMARY.txt. It probes every fleet host (ssh, read only) for running `oth-*` ot-heavy scopes and docker
containers, finds each job's log (ORFS logs under the RW bind mounts, else files the job holds open for writing, else
the newest file under its cwd) and lists:
- STALLED: log not grown for > 90 min (> 180 min while in detailed route);
- RUNAWAY (info): log still grows but one ORFS stage has run > 6 h (e.g. GRT FF-hold repair loops).
Lane/owner is guessed from the `/srv/opentallas-scratch*/claude/<dir>/` path. It never kills or submits anything.
`--stdout` prints instead of writing; `--json FILE` dumps the rows.
Install: copy `systemd/stall-watch.{service,timer}` to `~/.config/systemd/user/`, `systemctl --user enable --now stall-watch.timer`.
