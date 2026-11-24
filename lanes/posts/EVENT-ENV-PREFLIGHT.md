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
