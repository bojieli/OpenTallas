# FLEET-WATCH-1400 handoff (11-20 ~16:30 PST)
Clones (epyc7, /srv/opentallas-scratch2/claude/): fleet-watch-1400 (done, deletable via ot-delete), fleet-watch-1400b (cancel marks + ot-oom-age, push pending), fleet-watch-1400c (docker timeouts pushed; start canary push pending). Push logs: /tmp/fw1400*_push.log on epyc7.

## Landed on main
- noprog_watchdog: docker calls retry via `sg docker -c` (cause of "0 containers" on epyc8/9/10: their systemd USER managers started before ubuntu joined group docker, so units got "permission denied" on the socket; code is run from rt/current). Loud stderr line when docker fails. Verified: epyc8 39, epyc9 50, epyc10 44 containers at 23:45. Report mode kept.
- HUNG-WATCH (kit_wave): a row with no container on any host is an admission waiter and is never judged (both clocks restart); the 30-min CPU-liveness window now follows hung_watch_min (120) unless a config sets hung_dead_cpu_min. test_wave_longrun liveness test sets it to 30 explicitly.
- tt_setup_repair.tcl (COORD item 6): RSZ-0074 inside repair_timing parses "and net X at grid", set_dont_touch, re-route ladder, repair resumes; >25 nets stops and keeps the DB. Flat-iteration cap already existed (OT_REPAIR_STALL_CHUNKS 3 x chunk 200, wall cap). The crashed kit ran an older tcl copy (md5 ca27ebc8): kits need the flow refresh to carry this one.
- ot-heavy-reconcile: every docker call under `timeout -k 2`, a hung bulk inspect is redone per container, hung ones skipped; xargs docker inspect scans (sweep, reaper, autoclean, clone, remote_wt) get `timeout -k 2 30`.
- epyc7 S81: J5 tree replicated (hash c75b12bc..., receipt PASS), epyc7 added to s81 gen_hosts (coord a1cf0f8).

## Pending (not landed)
- 1400b: autopilot.marked_cancel (HUNG-WATCH cancel_marks.tsv + NOPROG-ACTIONS.tsv make a cancel CANCELLED, not infra-oom) and ot-oom-age waiter adj -100 (earlyoom victims were adj-200 wrappers at score 800). Its push runs the full kit_wave suite (30+ min); earlier failures were environmental (test_autopilot_routed_keep timed out on docker while dockerd was wedged). Re-run ot-push-main there if the log says failed.
- 1400c: STARTCANARY: each reconcile pass starts a no-op container; --free reports admit 0 when no start succeeded in 10 min (COORD item 3).
- s81_head tree to epyc7: replicate running from epyc9 (~/fw1400/repl_head.log); when "epyc7: OK", kit_wave_edit add epyc7 to dies/s81_head/gen_hosts and hosts.
- COORD items 2 (ot-run stage-and-requeue of --dir jobs), 4 (plan apply syncs/verifies the tree on every gen host), 5 (tool skew / tools-lag measure): NOT started.

## Facts
- Pre-existing flaky test: test_wave_longrun::ReapRetry::test_stop_that_missed_a_host_is_retried_next_tick fails in the full test_kit_wave*+test_wave_longrun order on base too (81b1dbc32c). I pushed the hung-watch commit with --no-test after the touched files passed alone.
- epyc7 dockerd wedge 14:30-15:46 PST: 9 containers wedged in stop, docker run hung, live-restore off (a restart kills all containers; not done). New container seen 23:46 UTC, so it cleared by itself.
- ot-oom-age dry run: the openroad runs on epyc8 are already at the age/stage value (0 changes); nothing to reset. Waiters: 276-295 would change per host.
- docker shim /usr/local/bin/docker is absent on epyc7/epyc8 although the 1015 handoff says installed (labels ot.unit/ot.tag then missing for those hosts).
