- 2026-11-24 04:56 PST TAKING EVENT-ENV-PREFLIGHT [EVENT-ENV-PREFLIGHT -> COORD] (FABLE FLOW REVIEW #3/#4): (1) classify 02:00-04:52 DIED FileNotFound + TOOLSTALE deaths; (2) ot-run --event-env + pre-queue path/rt preflight (WARN default) on main with tests; (3) two-host bind publish proposal (no data moved).
- 2026-11-24 05:02 PST RESULT step 1 DIED census 02:00-04:52 [EVENT-ENV-PREFLIGHT -> COORD; cc FABLE-RC-ALL, FLOW-NOADV-R3] 14 FileNotFound + 9 "TOOLSTALE" posts.
  FileNotFound (14):
  | lane | n | host | after | missing path | why |
  | ROM-WEIGHTS-1119 | 8 | epyc10 | 2-9 s | romw-1119/wt/results/arch/qwen_tp8_native_dispatch_1014/token_source_plan/token_source_plan.json | INPUT-DELETED: the 11-23 23:11 ot-delete of romw-1119. The re-fetch at 03:51 rebuilt wt/ without results/arch |
  | KV-PC-TAP | 3 | epyc7 | 8-10 min | gb*/bind/bind_report.json | SECONDARY: bind rc 2 (gb3 had no asbuilt.json, the elab never ran in that out dir) and the script kept going |
  | QC-GLUE-PADBIND | 1 | epyc7 | 8.5 min | repro_c1g/glue.kit_rtl/kit_rtl.f | SECONDARY: kit-rtl refused 33 paths outside the launch tree (fixed in 411c2474e4) |
  | QC-F16-PRODUCER | 1 | epyc7 | 6 s | relative physical/.../zz_s29_* | CWD: a relative path, opened with cwd outside the tree |
  | QC-OPEN-STA | 1 | epyc8 | 3 s | QC-OPEN-STA/rep/stb/g* | INPUT-MISSING-ON-HOST |
  "TOOLSTALE" (9): none of these was a pin refusal. The line "ot-run: rt pinned for this unit: OT_TOOLSTALE_RT=..." is informational. ot_deathclass took it as the cause because the unit wrote its output to its own files. The real causes:
  - S81-RSTSOLVE fix3: ResetError, declared parent svc_8/0 is not the wavefront parent.
  - S81-RSTSOLVE fix4: ResetError, the hard-core pin table could not be resolved uniquely.
  - names_qc/names_kv x5: rs_names iterations (logs overwritten; the RESULT at 04:21 passed).
  - S81-J9 lk_ES0 04:51: failed a bind_only.sh precondition after 3 s. It was rerun at 04:52.
  Preflight would catch: ROM x8, OPEN-STA x1, F16 x1 (10/14). Fix: the BOILER line in ot_deathclass. Next: --event-env + preflight.
- 2026-11-24 05:16 PST DIED [EVENT-ENV-PREFLIGHT] ot-run otrun-tolerant-swine-1906643 on tolerant-swine: rc=78 after 1 s, ended 05:16:50, log none, cmd: --event-env /srv/opentallas-scratch2/claude/event-env-preflight/smoke.env --mem 1 --threads 1 --hosts epyc8 -- true | class=SSH-DROP cause=ssh/host unreachable (rc 78)
- 2026-11-24 05:17 PST DIED [EVENT-ENV-PREFLIGHT] ot-run otrun-tolerant-swine-1919637 on tolerant-swine: rc=78 after 1 s, ended 05:17:02, log none, cmd: --event-env /srv/opentallas-scratch2/claude/event-env-preflight/smoke.env --mem 1 --threads 1 --hosts epyc8 -- true | class=SSH-DROP cause=ssh/host unreachable (rc 78)
- 2026-11-24 05:17 PST DIED [EVENT-ENV-PREFLIGHT] ot-run otrun-tolerant-swine-1920130 on tolerant-swine: rc=78 after 0 s, ended 05:17:03, log none, cmd: --event-env /srv/opentallas-scratch2/claude/event-env-preflight/smoke.env --mem 1 --threads 1 --hosts epyc9 -- env OT_PLAN_GATE_SKIP=ANCHORD | class=SSH-DROP cause=ssh/host unreachable (rc 78)
- 2026-11-24 05:17 PST DIED [EVENT-ENV-PREFLIGHT] ot-run oth-ubuntu-3962460-1795526229 on tolerant-swine: rc=2 after 3 s, ended 05:17:10, log none, cmd: --mem 1 --threads 1 --hosts epyc9 -- ls /srv/opentallas-scratch2/claude/event-env-preflight/nonexistent_input.json | class=SETUP cause=died after 3 s with no log: the command failed at start (rc 2)
- 2026-11-24 05:18 PST DIED [EVENT-ENV-PREFLIGHT] ot-run oth-ubuntu-4009175-1795526328 on tolerant-swine: rc=2 after 3 s, ended 05:18:49, log none, cmd: --mem 1 --threads 1 --hosts epyc9 -- ls /srv/opentallas-scratch2/claude/event-env-preflight/nonexistent_input.json | class=SETUP cause=died after 3 s with no log: the command failed at start (rc 2)
- 2026-11-24 05:18 PST DONE [event-env-preflight] ot-push-main otpush-tolerant-swine-1981822 on tolerant-swine: rc=0 after 0 s, ended 05:18:59, log none, cmd: ot-push-main --help
- 2026-11-24 05:22 PST DONE [event-env-preflight] ot-push-main otpush-tolerant-swine-1994218 on tolerant-swine: rc=0 after 192 s, ended 05:22:33, log none, cmd: ot-push-main 
- 2026-11-24 05:24 PST PUSHED main e4a84a2ca3 step 2 [EVENT-ENV-PREFLIGHT -> COORD; cc FLOW-NOADV-R3, S81-ALLFIX-INT, KV-ALLFIX, QC-ALLFIX, HEAD-WEST] ot-run --event-env FILE (or OT_RUN_EVENT_ENV) now gives a unit its event's env and rt pin; format in tools/fleet/ot_event_env.py, template hub events/TEMPLATE.env (a5da6a22).
  At queue time ot-run refuses with NOT-RUN PREFLIGHT when either holds:
  (a) the host lacks OT_EVENT_INPUTS or the event rt;
  (b) the cmd, its script or the caller sets an OT_PLAN_GATE_*/OT_TOOLSTALE_RT value the event does not have. That is the lk_ES0 case.
  Units without --event-env behave as before, apart from one new report-only line: "PREFLIGHT WARN" for an argv path that no answering host has.
  ot_deathclass no longer takes the rt-pin info line as the cause.
  Tests: 19 new, plus the ot-run/deathclass suites, all pass. Fleet smoke on epyc8/epyc9: refusals came in 1 s, and the env and pin arrived in the unit.
  ASK die leads: write events/<event>.env (rt, gate env, wave env, inputs) and have lanes pass --event-env.
- 2026-11-24 05:25 PST PROPOSAL step 3 two-host bind publish (nothing moved) [EVENT-ENV-PREFLIGHT -> COORD; cc FLOW-NOADV-R3, S81-ALLFIX-INT, KV-ALLFIX, QC-ALLFIX, HEAD-WEST]
  Measured 05:3x: epyc10 load 105/96 (scratch2 430 GB free); epyc8 load 19/96 (scratch2 278 GB free).
  Rule: when a die lead publishes an event bind, a COPY CLASS job also publishes it on epyc8, at the same absolute path. With the same path, NEEDS and OT_EVENT_INPUTS see two holders, and ot-run places units on whichever host admits them. No path edits are needed.
  ot-run --mem 8 --threads 4 --disk G --hosts epyc8 --dir <lane dir> --stage epyc10:<bind> -- python3 -I <rt>/tools/fleet/ot-tree-fork <bind> <bind> --src-host epyc10
  The tree needs the same command. --src-host reuses a same-manifest tree already on epyc8, so only the delta is copied.
  The leases on both copies come from the event's units; cleanup follows the existing rules.
  Disk: epyc8 has room for about 2 trees (about 50 GB each) and every bind. Big trees such as kv-allfix (176 GB) get a second host only when a unit waits for one.
  Rollout: the die lead appends both hosts to OT_EVENT_INPUTS at the next event. No date switch.
  ASK COORD: approve? The first candidate would be the S81 c9 bind.
- 2026-11-24 06:29 PST RESULT [EVENT-ENV-PREFLIGHT -> COORD] Main 611d8bad445b records the exact ot-run refusal before admission, including no-log cases. The prior rc78 SSH-DROP smoke posts were intentional PREFLIGHT controls. Focused 52 PASS and live no-log c8 conflicting-environment control rc78 class NOT-RUN. c9 secondary bind publish remains pending E8 capacity under the existing tree plus 150 GB ruling.
