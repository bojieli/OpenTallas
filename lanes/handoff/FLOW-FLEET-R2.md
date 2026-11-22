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
