KV-KITS-7/HUBC 2026-10-27 11:31 PDT
qkd_ahub kit: intel2:/srv/opentallas-scratch2/claude/kv-kits-7-hubc/kits/qkd_ahub__604.8x440.64 kit_hash e0bfe7ee388d53c8, plan hm_r26q3 256600e2 (ahub pins 5781bd2d = q2/r24),
source claude/kv-kits-7-hubc-1027 (ec613d58ef + ahub cut 80a104f8c0 + FLOW-RC-1 + PREFLIGHT-2 + keep hook + kit_contract hard-children parser).
gen: gen_core_kit_kv.py --core-json results/kv_ahub_r2_1027/rtl/qkd_ahub/qkd_ahub_core.json --plan hm_r26q3.json --kit-rtl kit_rtl(kv3_hub_C, hard_macros {})
     --am-g-drop --hard-children physical/die_plan/qwen_kvsys/cores/harden/qkd_ahub_hard_children.json; then results/kv_cores_r6/tools/pass1_reserve.py qkd_ahub_slice_used.json KIT
PREFLIGHT-2 (kit_preflight --contract): 9/10 PASS incl rc_calibration + macro_channels; FAIL clock_entry_clear:
  ck[0] entry (302.376,220.32) on the top edge of hard child ot_nhb_zh g_zh[1] [198.72,69.12,349.92,220.32].
PLAN STRUCTURAL: the KV-CORE-SLICE-1 ahub slice (12.8a centre entry + 8x4 core_tree grid) was made without the 5 hard children:
  entry island [298.08,216,306.72,224.64] and 18/32 core_tree islands overlap macro boxes (19/33 total, list in this commit msg / below).
  Fix (plan owner): entry in the free H channel y 220.32..263.52 (e.g. centre (302.4,241.92), on the 4.32 lattice, x clear of all macros),
  H-tree islands only in channels, the 5 macro ck pins as sinks with their signed insertion (insertion.json) balanced per 12.3 / v5.0 early taps.
Physical inputs of this kit == KV-CORES-PV kit 58a6fbd2 (io.tcl/pins/config/sdc/macro_place/pdn byte-identical; only dead text in ot_qkvd_kv_desc.sv
  and the FLOW-RC records differ), so its 3_place (epyc2 run, exit 0) is rendered here: ahub_placed.png (VIEWED): 5 macros, 15,225 cells / 3,556 FF,
  fill 1.9 % of free, pins on S+E faces only, pin->reg p90 6.7 um, max bin 0.54; std logic in the S band and between macro rows; entry dot on zh[1] top edge.
No place launched on the new kit (a GOAL=place unit was started 11:2x and stopped by me after 1 min: kit lacked FLOW-RC-1; regenerated instead).
kv3_astk: NOT kitted. Main carries only the ASTK5 transform set (route TT -85.91 / FF -13.22, known structural FAIL); ASTK6-8 (zq->sd fix, fence/ctl,
  face sub-root, storage enable) live only on codex/kv-astk-main-1026@bbf056027, COORD HOLD 10-26 05:55 (gen_core_kit_kv.py conflict at the
  strap_delta/hr_face hunk + island_ft/master-slice hunk; zone_members/strap_master/leaf_affinity not opt-in). Conflict probe on this branch: 2 hunks,
  both in gen_core_kit_kv.py. ASTK8 clock (face sub-root +~100 ps, 10,882 hold buffers) was not accepted; Codex early-feed diagnostic exit 0 at
  epyc2 codex-kv-astk-1026/early (bypass_*_ins/hold.tsv) uncollected.
islands over macros: entry[298.08, 216.0, 306.72, 224.64], core_tree_1[34.56, 159.84, 43.2, 168.48], core_tree_2[34.56, 272.16, 43.2, 280.8], core_tree_3[34.56, 380.16, 43.2, 388.8], core_tree_5[108.0, 159.84, 116.64, 168.48], core_tree_6[108.0, 272.16, 116.64, 280.8], core_tree_7[108.0, 380.16, 116.64, 388.8], core_tree_13[259.2, 159.84, 267.84, 168.48], core_tree_14[259.2, 272.16, 267.84, 280.8], core_tree_15[259.2, 380.16, 267.84, 388.8], core_tree_17[336.96, 159.84, 345.6, 168.48], core_tree_18[336.96, 272.16, 345.6, 280.8], core_tree_19[336.96, 380.16, 345.6, 388.8], core_tree_21[410.4, 159.84, 419.04, 168.48], core_tree_22[410.4, 272.16, 419.04, 280.8], core_tree_25[488.16, 159.84, 496.8, 168.48], core_tree_26[488.16, 272.16, 496.8, 280.8], core_tree_29[561.6, 159.84, 570.24, 168.48], core_tree_30[561.6, 272.16, 570.24, 280.8]
