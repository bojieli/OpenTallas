# KV-PC-HGI-1119 handoff (11-19)
Scope: 4 qkd_kvs_pc* rows + 13 kv3_hgi_v1/v2 cl* and kv3_hgi_v3 rows (OWNERS-SWEEP 44de87ca). Source: kit_wave_state items (all 9 distinct names reviewed).
## Classification (every last attempt is class SUPERSEDED/VOLUME, reaped by the wave, none a live design failure)
- qkd_kvs_pc, __v4128d4b721bf, __vc499977aa713, qkd_kvs_pc_h_head_p: OLD PLAN. "not an item of current plan (2433b9c21c26); plan block 310511289bc3; relaunches under its current name" (qkd_kvs_pc: gen on superseded block). No relaunch of these names: current names are qkd_kvs_pcc/pcf (separate view-rows lane). Retire from sweep.
- kv3_hgi_v1__cl141fc26e / cl42bc8b12, kv3_hgi_v2__cl2862d491 / cle0015330 (cl* rows): OLD PLAN/STALE BIND. Last attempts KV-HG6/KV-D22 "die switched to KV-D23H". Earlier fails event28w_c: PDN-0006 VSS M5 blocked (head2_e0), PORT_BIND extra 48 strap_head2_e0 (fixed by later plans), KV-HG1 contract metadata kvhg1_views missing. All on dead plans. Relaunch once D25d applied only if the item exists in D25d plan (parents kv3_hgi_v1/v2 clusters); else retire.
- kv3_hgi_v3: last live attempt b642f2409845e KV-D23H = INFRA/stale bind: OT_VIEW_LEF kvhg1_views_1116/kv_cland_w523_ns_23deb missing (pruned worktree) -> superseded by KV-D24. Relaunch on D25d through wave. Known open design item from FABLE-FIX-KV-HG: R-CAP 3.11M cells at kv101ns plan (split already in D24 hub_C/hg rows); HG7 ECTL ring->bin >405um (all-frame RESPONSE_LAT 29/QK 40).
- Live (not mine): kv3_hgi, v4..v8 RUNNING route (PRECHECK/CBC owners).
## Next
1. After D25d apply (KV-D23-COMPOSE): wave retry kv3_hgi_v3 + any cl* item present in plan; list verdicts.
2. If kv3_hgi_v3 on D25d fails design: fix row for D25e / private proof kit (ot-run --priority proof).
