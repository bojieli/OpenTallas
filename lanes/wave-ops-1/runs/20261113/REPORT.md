# Nightly wave-source rebuild 20261113 (WAVE-OPS-1)

main 3f11a4569d72; composed base ef623404397a; train line:     1. Compose on epyc8 (own clone; GitHub-only shas are relayed through a localhost bundle): main + the latest "ROOT-MERGE-57 UNLANDED" train in landing order + KW-FIX-44 "claude/<b> @ <sha>" posts of the last 48 h + each die's wave branch (src_sha). Merges are plain; a conflict is aborted and repo

- overlays merged (1): claude/kw-fix-44-pingrid-1111 0bd2b6f0b13f
- overlays conflict (not applied) (1): wave-ovl/grt-patch-1-genphys-1111 aef743c06d75

## s81 -> /srv/opentallas-scratch2/claude/wave-src/20261113/s81 (new ef623404397a; die branch 7073a6b4a599 on main/overlays)
- live /srv/opentallas-scratch2/claude/kw45/src_s81_main_7073a6b4a5 on epyc9; manifests: epyc7 e6efd59aaacc, epyc8 8c1392cbd7a0, epyc9 26256e9a14a0, epyc2 0cead6813f3c, intel1 0e0c3b2c4435
- paths: same 325058, carry live-only (not in git) 89, new file (main/overlay) 80, take new (main/overlay changed) 18, carry live overlay (not in git) 1, stale old git copy -> take commit 1
- carried live overlays (not in git), top dirs: tools/die_plan/__pycache__ 85, physical/die_plan/s81 2, KITOPS1_OVERLAY.txt 1, tools/autopilot/__pycache__ 1, tools/die_trial/__pycache__ 1
- stale old git copies -> commit (1): tools/die_plan/gen_phys.py
- re-bind: strict bind of record (asbuilt /srv/opentallas-scratch2/claude/kit-ops-1/s81_r12bA/asbuilt_kitops1_7073a6b4a5.json, old bind /srv/opentallas-scratch2/claude/kit-ops-1/s81_r12bA/out_main_7073a6b4a5_b) -> /srv/opentallas-scratch2/claude/wave-src/20261113/s81.bind
- item_inputs pinned (own plan/kit_rtl, not re-bound): 61

## s81_head -> /srv/opentallas-scratch2/claude/wave-src/20261113/s81_head (new ef623404397a; die branch 2dd0d8c9fd6c on main/overlays)
- live /srv/opentallas-scratch2/claude/kw45/src_head_main_2dd0d8c9fd on epyc9; manifests: epyc7 b0907987e2d7, epyc9 864c82ca63e2, epyc8 16ace1680c75, epyc2 1608950ebdd0, intel1 01e5a478a4a0
- paths: same 324897, new file (main/overlay) 210, carry live-only (not in git) 105, take new (main/overlay changed) 50, stale old git copy -> take commit 1
- carried live overlays (not in git), top dirs: tools/die_plan/__pycache__ 73, tools/s81_head/__pycache__ 5, KITOPS1_OVERLAY.txt 1, core_pins/elemA_pins.json 1, core_pins/elemB_pins.json 1, core_pins/kp4_276x138_pins.json 1, core_pins/lep_pair_pins.json 1, core_pins/lep_pair_pins_777.json 1, core_pins/lep_pair_pins_777r.json 1, core_pins/ot_s81hd_he_epc_pins.json 1, core_pins/ot_sram_1r1w2c_256x64_m1.json 1, core_pins/ot_sram_1r1w2c_32x64_m1.json 1, core_pins/ot_sram_1r1w2c_64x546_m1.json 1, core_pins/ot_sram_1r1w_128x256_m1_r0c0.json 1, core_pins/ot_sram_1r1w_32x128_m1_r0c0.json 1
- stale old git copies -> commit (1): tools/die_plan/gen_phys.py
- re-bind: no strict bind of record in kit_rtl (script mode, script export): bind-diff not applicable; the new tree is built and byte-checked only

## qwen_compute -> /srv/opentallas-scratch2/claude/wave-src/20261113/qwen_compute (new ef623404397a; die branch 88018018ef on main/overlays)
- live /srv/opentallas-scratch2/claude/kw45/src_qc_s28_88018018ef on epyc9; manifests: epyc4 34db5ebada4b, epyc7 2fbb64a070c2, epyc9 2fbb64a070c2, epyc8 b4d36b1288d1, epyc2 df0967b2a70a, intel1 9e4ac5d8a6c7
- paths: same 324173, new file (main/overlay) 772, take new (main/overlay changed) 139, restored (in the commit, absent live) 54, carry live-only (not in git) 23, stale old git copy -> take commit 17, conflict: both changed (kept live) 2, carry live overlay (not in git) 1
- carried live overlays (not in git), top dirs: tools/die_plan/__pycache__ 17, physical/die_plan/qwen_compute 3, KITOPS1_OVERLAY.txt 1, tools/die_plan/gp_noconverge_gate.tcl.pre_fanout 1, tools/die_plan/param_wrap.py 1, tools/die_plan/test_param_wrap_status_reg.py 1
- stale old git copies -> commit (17): physical/die_plan/hbm_arch_cores/recipes_b2.json tools/autopilot/autopilot.py tools/autopilot/kit_wave.py tools/autopilot/test_kit_wave.py tools/die_plan/check.py tools/die_plan/die_plan.schema.json tools/die_plan/kit_istations.py tools/die_plan/reset_tree.py tools/die_plan/route_supply.py tools/die_plan/schema.py tools/die_plan/test_wide_chain_float.py tools/die_plan/wide_chain_float_event.py tools/fleet/ot-autoclean.py tools/fleet/test_ot_autoclean_auto.py tools/fleet/test_ot_autoclean_dx.py tools/fleet_viz/design_dev_server.py tools/fleet_viz/explorer/dataflow/dataflow.js
- conflicts (live kept): tools/die_plan/bind.py tools/die_plan/gen_phys.py
- re-bind: strict bind of record (asbuilt /srv/opentallas-scratch2/claude/kw45/src_qc_s28_88018018ef/physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_sw2_pv_bound5ef1.json, old bind /srv/opentallas-scratch2/claude/kw45/qcs28in/bind_plan_qc99_s28) -> /srv/opentallas-scratch2/claude/wave-src/20261113/qwen_compute.bind

## qwen_kvsys -> /srv/opentallas-scratch2/claude/wave-src/20261113/qwen_kvsys (new ef623404397a; die branch 66e6607e3f0e on main/overlays)
- live /srv/opentallas-scratch2/claude/kw45/src_kv_main_66e6607e3f on epyc9; manifests: epyc7 ae888ad701e3, epyc8 7e147ed472de, epyc9 4905de557beb, epyc2 32d0f151d94e, intel1 7a41aefb7144
- paths: same 324838, new file (main/overlay) 269, carry live-only (not in git) 127, take new (main/overlay changed) 50, conflict: both changed (kept live) 1
- carried live overlays (not in git), top dirs: tools/die_plan/__pycache__ 106, physical/die_plan/qwen_kvsys 15, KITOPS1_OVERLAY.txt 1, tools/__pycache__/die_port_bind.cpython-314.pyc 1, tools/autopilot/__pycache__ 1, tools/die_plan/macro_skip_rtlmp.tcl 1, tools/die_trial/__pycache__ 1, tools/hbm_die_v16/__pycache__ 1
- conflicts (live kept): tools/die_plan/gen_phys.py
- re-bind: strict bind of record (asbuilt /srv/opentallas-scratch2/claude/kw45/src_kv_main_66e6607e3f/physical/die_plan/qwen_kvsys/plan_of_record/asbuilt_vN.json, old bind /srv/opentallas-scratch2/claude/kit-ops-1/kvbind_vN2i/out) -> /srv/opentallas-scratch2/claude/wave-src/20261113/qwen_kvsys.bind

## hbm -> /srv/opentallas-scratch2/claude/wave-src/20261113/hbm (new ef623404397a; die branch 7073a6b4a599 on main/overlays)
- live /srv/opentallas-scratch2/claude/kw45/src_hbm_main_7073a6b4a5 on epyc9; manifests: epyc7 bb181c067cf4, epyc9 3b0e323caae1, epyc8 ce413bb4f210, epyc2 6a6967ee7883, intel1 9707e942978a
- paths: same 325058, new file (main/overlay) 80, carry live-only (not in git) 78, take new (main/overlay changed) 19, conflict: both changed (kept live) 1
- carried live overlays (not in git), top dirs: tools/die_plan/__pycache__ 76, KITOPS1_OVERLAY.txt 1, tools/die_plan/macro_skip_rtlmp.tcl 1
- conflicts (live kept): tools/die_plan/gen_phys.py
- re-bind: strict bind of record (asbuilt /srv/opentallas-scratch2/claude/kit-ops-1/hbm_pEv10/asbuilt_kitops1w.json, old bind /srv/opentallas-scratch2/claude/kit-ops-1/hbm_pEv10/bind_w) -> /srv/opentallas-scratch2/claude/wave-src/20261113/hbm.bind
- item_inputs pinned (own plan/kit_rtl, not re-bound): 5
