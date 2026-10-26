# PLAN-DELTA/HBM 2026-10-25: one master + one pin template per core group

Base: origin/main 394765394 `physical/die_plan/hbm/die_plan.json` (60 types / 187 partitions / 733 hard-core entries).
Why main: PATH-HBM's plan of record (codex/hbm-plan-0719 @ecfb97d718) changes nothing under `physical/die_plan/hbm`.
Its L74/L12/L13 work is analytic only (results/hbm_named_path_0719). claude/hbm-b2o-1025r @fcd78fa50f is NOT READY
(G0 FAIL 3 / G0C FAIL 6).
Tools: cherry-pick of bd29861376 (Codex strict `parent_id_straps` schema + helper; not on main yet). Only this
commit, not the binder commits 92cbb7e8f8 / 54fe4d66bb / bd2dea2e12 / af19a65ef3.

`delta_hbm.py` is deterministic and idempotent. It reads the base plan from git (BASE_SHA) and writes:
- `physical/die_plan/hbm/die_plan.json`
- the new pin tables in `physical/die_plan/hbm/cores/pins_plan_c1/` (old tables kept)
- `delta_groups.json` and `displacements_over_405.json`

`count.py` counts distinct designs the way `tools/autopilot/ownership.py plan_items()` keys them (RTL master +
outline + pin-table sha).

## Before -> after
| | before (main) | after |
|---|---|---|
| partition types | 60 | 60 |
| type designs (ownership) | 60 | 60 |
| **core designs (ownership)** | **154** | **123** |
| hard-core modules / pin files | 214 / 220 | 184 / 189 |
| G0 errors / warnings | 3667 / 3640 | 3667 / 3640 (identical findings) |
| G0C errors / warnings | 5586 / 1721 | 5586 / 1721 (identical findings) |

Both gates were already failing on main before the delta. The failures are base debt: stations 1815, hops 1811,
m89_signals 41, complete 1598, reach 201, core_faces 110, die_io_plan 10. The delta adds 0 findings, and its
hard_cores track check is clean. Note that the main HBM plan does not pass the current main G0 (b79be3518 reported
0 errors on an older tool).

## Groups applied (all outside the PATH-HBM types c0 and q_rc4*)
| group | entries | modules -> | pin tables -> | master module written | straps (option B, parent_id_straps) | max pin move |
|---|---|---|---|---|---|---|
| sfu lane (q_sfuc) | 16 | 16 -> 1 | 16 -> 1 | ot_hgi_sfu_split3_lane_core | map_lane_j[4] = lane j | 0 um (rename only) |
| su lane_exp1..14 + exp_l (q_su0/q_su1) | 30 | 15 -> 1 | 15 -> 1 | ot_hbm_su_pg_lane_exp_core | lane_lane_id[11] | 0 um (rename only) |
| idx score tail0/1 (q_os2) | 2 | 2 -> 1 | 2 -> 1 | ot_hbm_idx_tail_native | - | 0 um |
| pc_ctrl leaf_cfg_h9b (q_svc0..3, q_svc3_v1) | 20 | 1 | 2 -> 1 | (unchanged) | - | 0.141 um |

Pin names follow two rules:
- A cut pin that is a whole canonical master port keeps the canonical port name from
  `cores/harden/canonical_ports_split.json`.
- A cut pin that is a concatenation, or that the census leaves unmapped, gets a lane-neutral cut name
  (`g_bank_N_u_bank_read_addr_1`, ...). HBM-CORES owns the bit map for these, because the census has no per-cut lsb.

ID strap input pins are placed on the clock pin's face row (S, M5), right after the last pin at the row pitch. The
G0 track check passes for them.

pc_ctrl h9b uses the as-built published table (cores/pins, closed view used by q_svc3), not the plan-derived table.
All members take its track_offset [0.108, 0.012], so the closed core is not re-pinned.

Whole-instance orient: every member's best orient came out R0, because the tables were already one geometry once
renamed. No MX/MY/R180 was needed.

**Displacements > 405 um: none** (`displacements_over_405.json` = []).

## Deferred
| item | reason |
|---|---|
| tkm root + 32 tiles; every entry of type c0 (root partition) and q_rc4* (coll_q2 NW_hub ingress cores) | PATH-HBM exclusion: P4/P5/P1. hc_root tails (hc_tail_rest, sk_*) and hcp_sys live in c0, so they are excluded too. |
| su lanes4 / lanes_plain (12 -> 2) | Their straps are `lane0..3_lane_id`, which are not in the approved ID list of the parent_id_straps helper (tile_id, tile_tid, map_lane_j, lane_lane_id). They also have 85 concatenated cut pins with no bit map. Needs a helper-list extension (Codex owns it) plus the HBM-CORES bit map. |
| bankq hcp_lanes x3 (8 -> 3) | Their straps are `lg*_fst` (chain-first flags). These are control constants, not IDs, so option B does not cover them. **OWNER?** |
| q_sm0..3 -> 1 type | Needs type-frame windows with sm2/3 = MX of sm0/1 and the lanes re-windowed, which is a re-route step (HBM-ARCH 07:08). Not done in this delta. |
| sm_attn leafh_lx / native_col / tile_tp, vm_calendar_role, pretree | They have one table per outline (2 outlines each), so they are distinct designs already. |
| idx hcol HALF0/1 | Already 1 table per half on main (32 modules -> 1 design each by ownership). Nothing to do. |

## Files
- `templates.png`: the 4 new templates (strap pins marked with a red x).
- `die_after_g0.png`: the G0 render after the delta. It is identical to before, since no partition, window or
  origin moved.
- `cores_after.png`: the core render (render_cores_v2.py). Every core has pins.
- `*_g0*.summary.txt`: finding counts per check.
