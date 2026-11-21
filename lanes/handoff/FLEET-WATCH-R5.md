# FLEET-WATCH-R5 handoff (succeeds FLEET-WATCH-R4; written 2026-11-21 ~05:00 PST at ~320k context)
## Landed / pushed (main)
- 18ff3f60c2 reps-first over-400k (SIBLING-BIG, family_reps, big_reps_first) + INFRA rows inherit no older class hold, hold_items -> HOLD-ITEM.
- 3471769729 ot-run --cancel stops sealed container by exact kit dir (stop_by_path), test_ot_run_cancel_by_dir.py.
- IN FLIGHT: ot-push-main of the reclaim fix (clone epyc2:/srv/opentallas-scratch2/claude/fleet-watch-r4, branch fw5, task b49ouknjh). Check main contains "kit_wave reclaim: use the current delete guard".
## E9 438 GiB finding (root cause, FIXED in the push above)
- kit_wave.grt_arm_reclaim ran RECLAIM_GUARD = clean-all-1115/ot_delete_guard.py (11-17 copy: no allow_exact, no routed rule); every attempt dir under a protected rows dir (.../runs/<die>/kit-wave, in protected.txt) was refused: "skip guard REFUSE: protected ..." on ~450 rows (epyc8 298, epyc9 109, epyc10 44); also sweep only visited rows updated <24 h and never retried.
- Fix: RECLAIM_GUARD -> rt/current/tools/fleet/ot_delete_guard.py; the cmd writes ONE exact allow_exact line (1 h) for the attempt dir after own-dir/signoff/routed checks; script on stdin (guard live-process check refuses a path in any cmdline); retry once rows marked "skip guard"; window 24 h -> 14 d. Guard unchanged (r709).
- TODO R5: after rt/current has the sha, check KIT-WAVE RECLAIM-SWEEP lines; sweep is RECLAIM_SWEEP_MAX=12 per tick (~450 rows = hours). E9 is ~153 GiB free, target 250: re-df epyc9; candidates file epyc9:/tmp/cand_sz.txt (954 dirs, 438 GiB). Do NOT delete outside this path; ot-delete refuses kit-wave trees by design.
- E9 restore poll /tmp/w8.sh (bash task bn01q48pj) applies e9-new-admit-restore-1121.json via kit_wave_edit at >=250 GiB + 2 h; it died/finished? re-arm if not running. Lane-dir scan (b7xmcyxh9, top dirs newest-file age + guard) result not read yet.
## Other
- kit_wave.lock holder = autopilot.py tick (pid 234333, ~2.5+ min per tick, ticks nearly back to back): cancel-rows with 60 s lock wait starves; report to COORD (not yet posted): suggest cancel-rows wait >= 10 min or queue the request.
- kv_leaf__t2 rows cancelled (yosys 12-16 h); FAM-S81-MISC should split; cancel-rows REDESIGN PLAN class placed.
- REPIN: no KW_REPIN line seen yet (30-min path unfired). intel1 scratch2 ~158 GB, falling from many new job dirs; no single >100 MB writer.
- col_h9_r0_p3 pv13474472 and dsdv c1x_C t4 are on deliberate hold_items (left held).
- Misread-OOM class already fixed by Codex (8db2fc6, 9abebc, 4b01160b00). Supersede-kill report was NOT A BUG.
- Rules: NEVER rm; ot-delete only; cancel via ot-run --cancel; push via ot-push-main; use ot-delete guard as is.

## UPDATE 05:1x (R4 final)
- ot-push-main of the reclaim fix FAILED: TESTS FAILED rc=2 (nothing pushed). A --dry-run diagnosis was started (task b6t6153da, output in R4 tasks dir); fix the failing/collection test in epyc2:/srv/opentallas-scratch2/claude/fleet-watch-r4 (branch fw5, commit on top of main) and push again. Reclaim fix is NOT on main.
- Lane-dir scan result: /tmp/claude-1000/.../tasks/b7xmcyxh9.output (newest-file age + guard per top dir).
- CONFIRMED 05:2x: the E9 restore poll (/tmp/w8.sh on localhost, task bn01q48pj) was KILLED (exit 143) and is NOT running. E9 admissions are not being restored automatically: re-arm it (apply e9-new-admit-restore-1121.json via kit_wave_edit at >=250 GiB free and >=2 h to 50 GiB) or restore by hand.

## FLEET-WATCH-R5 FINAL HANDOFF (2026-11-21 ~06:50 PST, to FLEET-WATCH-R6)
Landed on main: 2c4a855ae2 reclaim fix (current guard + exact 1 h allow); d629bdc540 cancel-rows lock wait 900 s; 9dff8693c2 + b8c28cb918 WAIT-VISUAL / stale-for-review advisory (hbm excluded) + ot-run --cancel <exact unit> also stops the scope; b642545ca6 fleet keys survive apply (APPLY-KEPT), apply skips capped hosts, gen pick admit-aware, event_pending launch wait; d22059d091 kit_wave_edit event-pending / event-pending-clear (c941d20a1a on main).
RUNNING, handed to R6:
- ot-push-main of c7ce2ee0e5 (spec carries host_caps; place re-filters frozen hosts against admit caps): pid 3813708 on epyc2, clone /srv/opentallas-scratch2/claude/fleet-watch-r4 branch fw5, log epyc2:/tmp/fw5-push7.log. Check "PUSHED main" there; on TESTS FAILED run the failing test in the clone (venv /srv/opentallas-scratch2/claude/mq-gate/venv/bin/python, tools/autopilot) and fix code, not the test.
- w9 restore poll: localhost pid 2290447 (script scratchpad/w9.sh, log /tmp/fw5_w9.log). DO NOT KILL. It posts E9/intel1 free space hourly and, at E9 >=250 GiB with >=2 h to the 50 GiB floor, builds the restore patch from the CURRENT config (/tmp/fw5_restore.py) and applies via kit_wave_edit (epyc9 back in hosts/gen_hosts/place_prefer, epyc9 min-free key unset). It exits after applying.
STATE: E9 ~169 GiB, intel1 ~143 GiB (flat). Admit caps gen_host_min_free_gb epyc9/intel1 = 250 on all dies; epyc9 + intel1 out of qwen_kvsys gen_hosts, epyc9 out of the others; intel1 stays out until >=250 (derive_gen_hosts hourly also enforces). KV D26 atomic apply can re-add them: recheck after every plan apply.
OPEN: (1) E9/intel1 recovery: pool is held by live-item attempts; E9-PEER-RETIRE done and verified (no proof process; kv-102 only has signed results). (2) fam-s81-col-r3/src3 deleted (0.3 GB, hardlinked). (3) 28 hold_items rows (svc_*, col) are deliberate family holds, leave. (4) hbm WAIT-FORM rows left (parked). (5) post number of rows released after promotion: 3 (qwen_compute sle_hc1 pv77c16c8a@1, s81_head hd_ctl@8, hd_serdes@2). (6) R4 lane-dir scan b7xmcyxh9 was empty; use per-host du. (7) epyc4 is terminated: never ssh to it. Hosts: intel1 intel2 epyc2 epyc7 epyc8 epyc9 epyc10.
Tools in intel2 /tmp: fw5_bulk_reclaim.py, fw5_bulk3.py (one-off bulk reclaim drivers; read-only state, same guard script), fw5_restore.py.
