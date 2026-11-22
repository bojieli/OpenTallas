# FLOW-FLEET-R2 handoff (Sonnet 5.5, lane for COORD; source lanes/FABLE-FLOW-0350.md S1, P1, T1)

Lane clone: epyc9 /srv/opentallas-scratch2/claude/FLOW-FLEET-R2/repo (cone tools,bin,tests). Scratch tmp: .../FLOW-FLEET-R2/tmp.

## S1 UTF-8 guard: DONE
- (a) main main c9b8d5f226ca (lane commit 9b60997964): autopilot.read_coord decodes with errors=replace on the git-show path too (it was strict) + one WARN per file per process; test_read_coord_utf8.py.
- (b) coord/state e22d85406d: bin/utf8_guard.py; post.sh refuses invalid UTF-8 text; coord-commit.sh refuses invalid UTF-8 in the LINES IT ADDS to named text files (old bad bytes never block). COORD_UTF8_GUARD=off skips. tools/tests/test_utf8_guard.py.
- Note: tools/tests/test_coord_commit.py::test_nothing_to_commit_but_origin_has_head_is_pushed_status already fails without my change (NOTHING-COMMITTED rule 11-19).

## P1 private run-item under systemd: DONE (kit_wave.py runitem_unit_argv / runitem_reexec)
- private spec + not under systemd (INVOCATION_ID / .service cgroup / ot-run env) -> exec systemd-run --user --wait --unit=runitem-<item> with same args, env OT_/KW_/AP_/PATH/HOME, stdout+stderr to caller's log file (else <spec dir>/run-item.log); prints the unit name. Opt-out KW_RUNITEM_NO_UNIT=1. Existing 47 drivers are not restarted. test_runitem_unit.py.

## T1 min_rt for plan binds: DONE (ot-run plan_job_rt_floor)
- ot-run --plan-job bind refuses an rt (named /claude/rt/<sha12>/ in the command, else the client's own) below min_rt (kit_wave.json, $OT_MIN_RT, rt/MIN_RT) unless --rt-floor-exempt "WHY" (logged). test_ot_run_plan_rt_floor.py.

## 11-22 COORD add-on: interim result.json: DONE main 91ac256152b6
- run-item seal record now verdict RUNNING (stage kept); an ended unit left at RUNNING is collected as FAIL at that stage; FAIL only from fail(). test_interim_result.py.

## 11-22 COORD F1 / C1 / X1
- F1: LOAD_CAP_FACTOR=1.2 (tagged #@cap owner=FLOW-FLEET-R2 expires 2026-12-06, backup /etc/ot-heavy.conf.bak-fleetr2-f1-1122) on intel1 intel2 epyc2 epyc8 epyc9 epyc10 (epyc7 already). THREAD_CAP_FACTOR stays 0 everywhere: epyc7 current config is thread cap 0 (R1 reverted 1.0 after 31 refusals at load 50/96); say so if you want it back. Reps first: kit_wave family_plan SIBLING-WAIT while >= half the fleet is at load >= cores (opt-out reps_launch_first false); over_load_cap uses the hosts own factor

## 11-22 COORD F1 / C1 / X1
- F1: LOAD_CAP_FACTOR=1.2 (tagged #@cap owner=FLOW-FLEET-R2 expires 2026-12-06, backup /etc/ot-heavy.conf.bak-fleetr2-f1-1122) on intel1 intel2 epyc2 epyc8 epyc9 epyc10 (epyc7 already). THREAD_CAP_FACTOR stays 0 everywhere: epyc7's current config is thread cap 0 (R1 reverted 1.0 after 31 refusals at load 50/96); say so if COORD wants it back. Reps first: kit_wave family_plan SIBLING-WAIT while >= half the fleet is at load >= cores (opt-out reps_launch_first false); over_load_cap uses the host's own factor; install_fleet_host.sh 1.2. main 149a58c42d08.
- C1: tools/autopilot/goal_table.py is the one table; kit_wave PRIVATE_GOALS/CHAIN_STAGES/resolve_chain_goal and gen_phys RUN_KIT resume goal lines read it; test_goal_table.py. Not done: run-item re-exec from rt/current, brief text from --help.
- X1: cause = the 10 prov_1119 signed-store entries were ingested with pins None (no routed_db yet); the counter reads the store and nothing backfilled pins later. tools/signed_store_ingest.py pins_backfill (+ --backfill-pins, hooked into the hourly ingest, 40/run, 6 h retry) coord 895d2230668a; ran it: 12 entries set (the 10 + 2), coord 92c9058df96. Cache 06:15: S81 designs signed 68/72 (was 62).

## 11-22 COORD FABLE-FLOW-0800 items: main b37b5e52d791
- F1: ot-heavy-reconcile samples every unit scope + containers cpu.stat, writes the class p90 cores to /var/tmp/ot-heavy/cpu-peaks.tsv; SIMPLE_PEAK admission adds CPU_CHARGE (committed expected cores of running units + this job <= CPU_FACTOR x nproc, only while load1 >= CPU_MIN_LOAD(0.6) x nproc; no history -> 0.5 x declared threads). THREAD_CAP stays 0. Opt-out CPU_CHARGE=0 in /etc/ot-heavy.conf. Live on a host once its ot-heavy-reconcile is the new copy (rt/current follows; the installed /usr/local/bin copy is the one the gate runs: check TOOL-COPY).
- P1 (admission part): probes (<= SMALL_THREADS=4 threads, <= SMALL_PROBE_GB=40 GB) take the small-job line (SMALL_PROBE_MAX=8 per host) and the plan drain / plan queue no longer hold them (needs SMALL_JOB_GB>0, set on the gen hosts). NOT done: one fleet ticket that keeps its age across hosts and stages only after a host admits (ot-run spill/ETA-STAGE rework) and "a waiter that never started is not an attempt" (WAVE-OPS-R1).
- C2: ot-run submit ledger ~/.local/state/ot-run/submit.jsonl on the submitting machine; --cancel with no live client resolves dir / otrun tag / client pid / lane:NAME from it (96 h), stops the tag on every host + the exact dir's containers. Ledger starts empty: only jobs submitted after rt/current follows are covered.
- K2: disk_rate.py alert (every state change) adds TOP-WRITERS: top 5 lanes by GB written in the last hour + the running oth units whose cwd is under each. Admission on projected free space already existed (disk-ETA hold: free - fall rate x 1 h - job writes < floor); it is fed by the same disk_rate samples at every state.
- ot-tree-fork: --src-host fetch first asks the other fleet hosts' tree index for a same-manifest tree (find_holder), then fetches with 4 size-balanced parallel tar streams over aes128-gcm, no compression (was one stream); OT_TREE_FORK_STREAMS=1 restores the old path.
- test_ot_run_spill_floor.py was flaky in the push gate on a 100-container host (docker inspect fails closed): hermetic fake docker.
