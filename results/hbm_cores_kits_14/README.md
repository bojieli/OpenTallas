# HBM-CORES-KITS-14 (2026-10-29): K5 SU + K8 HNX/PHY core kits on plan c25c_d16

Plan c25c_d16 die_plan.json sha256 6ba9f877d23f (DIE-HBM-15). Source main a4453d4004 (no edits). Generator results/die_hbm_kits_1027/mk_c20.py
(views_b2r2 + gen_core_kit_hbm.py, FF hold margin 10 ps default = 12.19), gate tools/die_plan/kit_preflight.py --contract.
Macro placements: results/hbm_cores_kits_3/mp_rule_c.py (R-SRAM-ENTRY) on the k1 kits + yosys instance lists (inst/inst.sh;
k = path below the face shell) -> mp/*.json, then mk_c20 --avoid-macros (k2). islchk (results/hbm_cores_kits_4/k11/islchk.py) 0 overlaps.

| type | kit | preflight | state |
|---|---|---|---|
| su_static_pgslice_lg__pretree | k1 _k14 | PASS 0 | AP 15df583662e5 AUTO, place-only running intel1 |
| hfd_ep_static | k2 _k14m (C=1, escape bound 2.45 UNCHECKED) | PASS 0 | AP a9bc2955f067 AUTO, place-only running intel1 |
| host_cp_rxs (434.808x480) | k2 _k14m (C=1, esc 0.67) | PASS 0 | AP 1de6f212e672 AUTO, place-only running intel1 |
| pdie_serdes | k1 _k14 | PASS 0 | not launched: ADOPTED KITS-4 _k11 (same pins d62659dbe46a) place-only, epyc2 container in kit LEC |
| su_static_cxport_ij_q | k1 _k14 | PASS 0 | not launched: same view measured AUTO-GEOM FAIL 30c598db1e6d (fill 0.061, empty 0.80, r2r 488) -> outline (plan) |
| su_static_qcore_r13 | k1 _k14 (mp v6) | PASS 0 | not launched: same view AUTO-GEOM FAIL 3bf08fc6bb53 (GRT ov 1141, channel_h 1.275) + Codex M7 GRT-0116 -> outline (plan) |
| su_static_sfustore_hw (336.96x328.32) | k1 | FAIL (no macro placement) | mp_rule_c INFEASIBLE: 16 SRAM+halo 82.3k of 105.0k um2 core -> outline (plan) |
| su_programme_pslice_c5 (939.6x760.32) | k1 | FAIL (no macro placement) | 100 SRAMs, macro+halo 514k of 700k um2; C=8 escape bound 18.4 -> plan restructure |
| su_static_pgslice_lg__lanes8_11 | k2 _k14m (C=2 FEASIBLE) | FAIL 8 | plan clock pins clk_bank/clk_bank_macro/clk_insert/clk_lane on M4 0.192x0.024 (GEOM-21) |
| su_static_pgslice_lg__lane_exp0 | k1 _k14 (B2n exp_lane.json) | FAIL 10 | clock pins 0.024x0.192 (GEOM-21) + family placement channels 8.856/9.048 < 10.8 |
| lane_exp/lanes/lanes_plain canon (3) | - | NO_RECIPE | canonical strap types (lane*_lane_id) need a recipe (member split recipe + strap ports) |
| hnx_fused_lane/tnode/hub_n4ext/host_program | - | NO_RECIPE | RTL rtl/hbm_next/fused/*.sv, no recipes_b2 entry |
| hnx_rp3lp3h_n/_s | k2 _k14m PASS 0 (flat) | NOT LAUNCHED | c24_side: hard-child parent (3 x hnx_lane_x, 226.6k cells each); a flat kit breaks the 400k cap and the plan view -> needs hnx_lane_x signed view + hard-child kit |
