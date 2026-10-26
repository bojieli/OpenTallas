# Auxiliary infrastructure coverage 2026-10-26 02:09 PDT

| Lane | Current / jobs | Next / failure disposition |
|---|---|---|
| INFRA | Live four-host admissions: epyc2 551GB, intel1 628GB, intel2 669GB; hub-local -32GB,37 running scopes. Scratch free 200/2045/2191/708GB; roots4/6/11/18%. | No disk guard or bus outage. Use bounded --stage for new jobs; KV bind30 without --stage notified KV owner. No inherited cancellation. |
| INFRA2 | autopilot,flow-canary,release-task-watch,stall-watch,wt-reaper timers active and last results0; element-owner-watch already inactive. Backup last20:33, next02:15; archive next02:45. | No duplicate service/probe run. Standby intel2; epyc3 retired, old five-host requirements superseded. |
| DIE-CI | Hub service3819714 alive37.6h with global lock, pinned da5213b0b3. Intel2 scope oth-ubuntu-2466333-1792870320; g2part-162124 OpenROAD162242 at100%CPU/33GB, retired d4g q_sfuc route. Four completed dies previously harvested; latest summary remains9f6cbf. | Historical job still computes, not stale-lock cleanup candidate; preserve under no-kill rule. No current die inferred FAIL. Current paths own release GRT/STA; do not rerun obsolete CI. Latest scheduler already has per-die immediate harvesting. |
| FLEET-DISK / FLEET-NEW3 | Tools merged, current root/scratch floors safe; no new destructive cleanup. | Old nvme recovery closed by owner wipe. No mover/reformat action needed. |
| OTRUN-HUB-RECOVERY | Active hub healthy, standby intel2 and non-secret backup installed;14 live spill records, --spill-sweep --dry-run found no recoverable orphan outputs. | No cutover needed. Runtime dbus override stays until safe manager restart; never restart user@1000 while scopes live. |

Concrete inherited failures passed to physical owners: HBM intel1 link_mem128 synth idle21h; intel2 old idx_topk synth idle20h; HBM SerDes/idx_topk placement18h/15h activeCPU. They remain lane-owned; no generic retry. No new heavy job, source change, deletion or OWNER question.
