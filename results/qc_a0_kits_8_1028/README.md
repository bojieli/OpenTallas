# QC-A0-KITS-8 (2026-10-28): A0 node tree = symmetric lattice + one master per level

COORD 21:07 ruling on the QC-A0-KITS-7 a0k6s root cause (routed FF clock-pin spread 51 ps vs plan 11.4 ps; the plan
tree balanced unequal legs (level-3 4..103 um) with 5-6 different masters per level).

## Paper estimate (PLAN MODEL = the same R7 NLDM+Elmore chain core_family_slice uses; UNCHECKED until routed)
estimate_node_tree.json (est_uniform.py, census geo of the DIE-QC-18 a0k6 kit, 12102 sinks):
- A shipped a0k6s plan, its d1/uf3 masters: TT 254.3 w18.6 / FF 202.4 w22.0 (uf3 GRT model claimed FF w11.4).
- B same geometry, ONE master per level (size compensation removed): TT w32.2 / FF w30.0 -> the shipped plan relied on
  ~15 ps of size compensation.
- C symmetric lattice (legs y 108/54/27, H 25.4, H 12.7, y 3.4 from the centre entry; 256 leaves 11.88 x 6.75 um),
  one master per level: TT 250.8 w16.9 / FF 201.7 w15.9, 8 stages, leaf spread 9.2 um. The residual window is
  leaf LOAD spread (2..101 sinks/leaf; sink density is 2x higher on the W third), not wire geometry.

## Implementation (opt-in, shared tools/die_plan)
- core_family_slice.py family key `lattice` {levels: tip offsets per level}: lattice_build (refuses a level whose legs
  differ in length), nearest-leaf sinks, empty leaves pruned; lattice_masters = one master per level key, deterministic
  coordinate descent on TT+FF window (slew <= 60); no d1/uf3 per-driver sizing (run: --fit skipped, trunk/replan refused).
  Families without the key: unchanged code path. Tests: 3 new, test_core_family_slice + test_core_plan_to_infra 33 PASS.
- families_a0_lattice.json (family a0node_lat), slices_lat/ot_qwen_tile_node.json (converted by core_plan_to_infra,
  die/latency/master_plan_sha256 as slices_ilv), recipe ot_qwen_tile_node_lat (= _ilv + two_mode, suffix a0k8).
- Plan checks (lattice_checks.json): PASS; legs 429 worst 1.002x Manhattan; TT 253.45 w16.97 / FF 205.43 w15.95;
  slew 37.6; driver displacement max 1.57 um; PG clearance PASS; 685 cells; masters BUFx16f (root, L1-L3), BUFx24 (L4-L6, leaf).
- Kit a0k8 = gen_core_kit_qc --module ot_qwen_tile_node_lat --master-slice slices_lat --seam-hold 25,25; diff vs a0k6s
  kit: only the nickname, the tree (core_infra/master_slice/tap_balance) and freeze.
