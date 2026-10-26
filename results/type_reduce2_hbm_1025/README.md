# TYPE-REDUCE-2/HBM 2026-10-25: one pin template per (RTL master, outline) + ID straps (B2n HBM plan)

Base: origin/main 190ebb428 `physical/die_plan/hbm_arch/B2n` (the plan autopilot OWNERS.tsv keys: 49 types + 226 core
designs = 275 items). The earlier delta claude/plan-delta-hbm-1025@3b89ef2ea3 (merged) changed `physical/die_plan/hbm`,
not B2n, so nothing of it is redone here.

Step: `python3 physical/die_plan/hbm_arch/core_templates.py` (deterministic, reads the base from git, writes
B2n/die_plan.json, B2n/core_conns.json, B2n/cores_tmpl/*.json, the `*_strap.sv` wrappers and groups.json /
displacements.tsv here).

## Result
| | before | after |
|---|---|---|
| core designs (ownership.py plan_items) | 226 | **186** |
| type designs | 49 | 49 |
| G0 | PASS 0 E / 366 W | PASS 0 E / 366 W (0 new, 0 gone findings) |
| G0C | PASS 0 E / 366 W | PASS 0 E / 366 W (0 new, 0 gone findings) |
| applied pins moved > 405 um | - | **0** |

Per master: sfu lane 16 -> 8, su pg lane_exp 29 -> 10, su pg lanes4 (440.64x457.92) 6 -> 4, idx score hcol h0 6 -> 1,
h1 6 -> 1, idx score tail 2 -> 1, bankq lanes3 (fst=0 pieces) merged by identical table. (sfu/lane_exp/lanes4 keep one
template per FACE CLASS: the replicas whose ports all face the same neighbours; ID straps take the rest.)

## ID straps (owner option B) -- new declared strap_* input pins
| master (wrapper module) | strap port | width | replicas |
|---|---|---|---|
| ot_hgi_sfu_split3_lane_core (ot_hgi_sfu_split3_lane_core_strap) | strap_map_lane_j | 4 | 16 entries |
| ot_hbm_su_pg_lane_exp_core (ot_hbm_su_pg_lane_exp_core_strap) | strap_lane_lane_id | 11 | 30 entries |
| ot_hbm_su_pg_lanes4_core (ot_hbm_su_pg_lanes4_core_strap) | strap_lane0..3_lane_id | 4 x 11 | 8 entries (440.64x457.92) |
Whitelist extended: tools/die_plan/parent_id_straps.py HBM_ID_WIDTHS + schema.py _physical_id_widths (core strap
schema now one if/then per port) + die_plan.schema.json regenerated + tests (test_hbm_identity_straps.py).
Strap pins sit on free lattice slots of the clock pin's row (nearest the clock pin). Wrappers are pure port renames of
the canonical master (no logic).

## Not applied (recorded in hbm_census.tsv, face_defer.json, displacements.tsv)
One table per (master, outline) for these would stretch pins past 405 um or turn ports away from their partners
(G0C core_faces); the structural fix is a parent re-place so every replica sees the same neighbour directions:
hfd_ep_static 389 pins >405, vms_bank_native 874, bankq_ft lanes6_7 1402, bankq lanes6_7 10197, sm_group_rel_id 8481,
sm_xcal_rel_t 33, vm_kshare 5927, xload_bfqg 801, pg_pretree 79, pg_lanes4 (440x458 whole group) 176 (listed);
pc_ctrl h9b / vmdel / bdring / xq_pegress / aq_tree13: 0 pins >405 but new G0C core_faces findings.
pg_lanes4 760.32x725.76 (15 designs): cut-pin name sets differ between pieces (needs the HBM-CORES bit map).
PATH-HBM root partition excluded: TKM tiles (32, tile_tid; PATH lead's no-ID common/terminal templates), hc tails.

## LEC (lec_wrap/, run from the repo root: `yosys -q lec_wrap/<case>.ys`; repo-relative paths)
For each strap wrapper, 2 IDs (first and last variant in the plan): gold = canonical master with the ID input tied to
the old variant's constant, gate = new `*_strap` wrapper with strap_* tied to the same constant (master kept as one
blackbox cell on both sides, merged by equiv_struct; equiv_simple + equiv_induct + equiv_status -assert).
6/6 EQUIVALENT (sfu lane j=0/15, lane_exp id 2/15, lanes4 ids 64-67/76-79). Mutant (sfu strap 4'b0000 -> 4'b0001 on
the gate side) is caught: 1 unproven $equiv. The old per-replica piece = master with the ID tied is the census
definition (canonical_ports_split.json type_ids[*].check = PASS, split tops wired bit-exactly from the as-built
master); a gate-level kit LEC of the new strap master per ID belongs to the kit step (tools/die_plan/lec.py).
