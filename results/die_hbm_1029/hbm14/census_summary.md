# HBM 12.18 kit census (DIE-HBM-14, 2026-10-29 06:2x PDT)

Sources (all copied read-only into this dir): intel2 ~/coord/autopilot/OWNERS.tsv (tick 05:53), state.json/queue/signed,
~/.local/state/fleet-viz/release_tree_plan_cache.json (provenance v1), main tools/autopilot/ownership.py (plan_items/signed_items
re-run here), plan c25c_d14 (localhost:/srv/opentallas-scratch/claude/die-hbm-13/c25c_d14) and main physical/die_plan/hbm_arch/B2n.

## Reconciliation (CHECKED: recomputed with ownership.plan_items)
- "49 types + 210 cores" = plan hbm_arch/B2n (10-25), which ownership.py DIES still names for hbm: 49 types, 88 partitions,
  210 core modules = 226 core designs (master+outline+pin table; e.g. vms_bank_native_q0_faces 8 tables, sm_xcal_rel_t 4),
  819 placed replicas. OWNERS.tsv's 49+226 rows reproduce exactly. 54 of 226 are RETIRED (OWNERS-RETIRED.tsv: TKM tiles,
  bankq*, qhub_static, q2 body) -> 172 live B2n core designs.
- The current plan c25c_d14 is different: 81 types / 90 partitions, 78 core modules = 80 core designs, 1197 placed replicas.
  Only 48 of the 78 modules exist in B2n and every one has a new pin table (28 same outline, 20 new outline): 0 of 80 current
  core designs equal a B2n design; 32 modules are new (no OWNERS row at all). Types: 1 exact (q_mca), 49 changed, 28
  __physical_v1 variants, 3 new (PHY_NW/NC/NE). 151 B2n rows are not in the current plan (54 RETIRED + 93 NEEDS-KIT + 4 others).
- So the autopilot census, UNOWNED-ITEM gaps and kit gating for HBM are against a superseded plan.

## Current plan, grouped (state = autopilot state of the same module/type name on B2n; new designs = NEEDS-KIT)
| kind | state | designs | replicas |
|---|---|---|---|
| type | PLAN-STRUCTURAL | 54 | 57 |
| type | NEEDS-KIT | 23 | 29 |
| type | FIX | 4 | 4 |
| core | NEEDS-KIT | 49 (32 new modules) | 1076 |
| core | FIX | 8 | 35 |
| core | GEOM-REQ | 14 | 55 |
| core | REVIEW | 4 | 16 |
| core | KIT-PLACED | 4 | 14 |
| core | SIGNED-UNVERSIONED | 1 (collar_idx256r) | 1 |
| core | SIGNED | 0 | 0 |
Every non-NEEDS-KIT core state refers to a kit on the B2n pin table, so strictly none is valid for c25c pins until re-pinned.

## Owners
Default owners HBM-PLAN, HBM-CORES, CORE-VIEWS have no live agent today (Codex parked 05:0x, out until 11-01).
Live: DIE-HBM-14 (PATH-HBM/DIE-HBM rows: 14), HBM-BIND-1 (bind only). HBM-CORES-KITS-10 (ring_ag, hnx) PARKED 06:06, successor pending.
=> 147 of 161 current items have no live owner.
