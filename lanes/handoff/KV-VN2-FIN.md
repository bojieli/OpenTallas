# KV-VN2-FIN handoff (narrow successor of DIE-KV-99; KV vN2 plan event only) -- 2026-11-12 16:44 PST
## Scope
Finish + post KV vN2: vN2i = vN2h (md5 22227437) with kv3_pv_v2n + kv3_pv_v6 reverted to p1b (pre-reach_fix; same as pv_v1n), sidecar, G0, strict bind, package, READY + plan event, stop.
## Scripts (epyc4 /srv/opentallas-scratch2/claude/kvfin)
- revert.py PLAN REF OUT TYPES.. (partition_types[T] := REF; vN2g->vN2h diff was exactly partition_types.kv3_pv_v1n == p1b).
- make_vN2i.sh (REVERT env overrides type list): tools /dev/shm/dkv99/m4 (main 614ab4a0dac0) -> dkv99/vN2i/{plan_c.json,eW_sidecar.json}, G0 dkv99/g0_vN2i, slot diff vN2i/work/g0_slot.txt, steps vN2i/work/steps.log.
## Bind
epyc8 bash /srv/opentallas-scratch2/claude/dkv99/bind_e.sh vN2i PLAN SIDECAR (tree wt/die-kv-99-e, flag ON, R8 = r8_rebased_vN2f.json md5 648c8f44 already in plan_of_record, --all-gaps). Lane check vs cleanbind/bind_vN2/bind_latency.json: vN2h bind differed only on the 6 known +1 lanes.
## State
- started vN2i build on epyc4 (pid 3067673).
## UPDATE 2026-11-12 17:00
- vN2i plan md5 dc4e1207, sidecar md5 95a405ba (epyc4 dkv99/vN2i; copy epyc8 dkv99/bindi). G0 PASS 0 errors, 0 NEW (g0_vN2i). lat_audit: 2404 lanes, 702 fixed-cycle, 0 mismatches.
- Bind running epyc8 dkv99/bind_vN2i (started 16:47 PST).
- COORD 17:0x (owner scope cut): post on bind RC 0; non-functional bind findings -> open list, post anyway; unexpected lane diffs -> post flag OFF + list.
- Packaging note: plan_package.py package refuses this folder (main already carries abs paths: bind9_asbuilt.json.gz 139887, plan_c.original 684, kv1200_cut, PLAN-ROUTE-1 receipts); plan: refresh PACKAGE.json entries for the 4 changed files + verify.
## UPDATE 2026-11-12 17:13
- vN2i bind RC 0 (only the 6 known +1 lanes differ; flag ON). Committed claude/kv-vn2-event-1112@3b18004662, pushed. READY + PLAN-EVENT posted. Lane DONE.
