# Nightly wave-source rebuild 20261112 (WAVE-OPS-1)

main 83e9f033ecb0; composed base 386428f6af2e; train line:     1. Compose on epyc8 (own clone; GitHub-only shas are relayed through a localhost bundle): main + the latest "ROOT-MERGE-57 UNLANDED" train in landing order + KW-FIX-44 "claude/<b> @ <sha>" posts of the last 48 h + each die's wave branch (src_sha). Merges are plain; a conflict is aborted and repo

- overlays on main (3): claude/kw-fix-44-script-inputs-1110 ad59b36619cb; claude/kw-fix-44-grt-early-1110 b6d8a28df457; claude/kw-fix-44-macro-grid-1110 a1583449d1cd
- overlays conflict (not applied) (2): claude/kw-fix-44-loadgate-1110 2129acf2d0e2; wave-ovl/grt-patch-1-genphys-1111 aef743c06d75
- overlays merged (1): claude/kw-fix-44-pingrid-1111 0bd2b6f0b13f

## s81 -> /srv/opentallas-scratch2/claude/wave-src/20261112/s81 (new 386428f6af2e; die branch c6c0f5cf65d2 on main/overlays)
- live /srv/opentallas-scratch2/claude/s87bind/bsrc3_r11r on epyc9; manifests: epyc7 be018651e85b, epyc8 dbaa43eb9941, epyc9 be018651e85b
- paths: sparse (absent live, kept absent) 179119, same 140980, restored (in the commit, absent live) 3410, new file (main/overlay) 742, carry live-only (not in git) 100, take new (main/overlay changed) 54, carry live overlay (not in git) 39, conflict: both changed (kept live) 3
- carried live overlays (not in git), top dirs: tools/die_plan/__pycache__ 74, physical/die_plan/s81 10, physical/die_plan/qwen_kvsys 4, physical/die_plan/hbm 3, results/token_pass/s81_dead_inputs_2148 2, .gitattributes 1, .github 1, .gitignore 1, .qscratch 1, .s81-scratch 1, .selt_lint 1, AGENTS.md 1, ARCHITECTURE_EXECUTION_CONTRACT.md 1, CITATION.cff 1, CLAUDE.md 1
- conflicts (live kept): physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py tools/die_plan/gen_phys.py
- re-bind: strict bind of record (asbuilt /srv/opentallas-scratch2/claude/s87bind/asbuilt_f_s87d.json, old bind /srv/opentallas-scratch2/claude/s87bind/out_r11r) -> /srv/opentallas-scratch2/claude/wave-src/20261112/s81.bind
- item_inputs pinned (own plan/kit_rtl, not re-bound): 74

## s81_head -> /srv/opentallas-scratch2/claude/wave-src/20261112/s81_head (new 386428f6af2e; die branch 7b84010b1c6e on main/overlays)
- live /srv/opentallas-scratch2/claude/kw45/src_head_main_m8w1_7b84010b1c on epyc9; manifests: epyc7 95db8a40851f, epyc9 95db8a40851f, epyc8 95db8a40851f
- paths: same 225306, sparse (absent live, kept absent) 98434, new file (main/overlay) 269, restored (in the commit, absent live) 256, carry live-only (not in git) 108, stale old git copy -> take commit 34, take new (main/overlay changed) 31, carry live overlay (not in git) 11, 3-way merged (live overlay + main) 5, conflict: both changed, merge conflict (kept live) 1
- carried live overlays (not in git), top dirs: tools/die_plan/__pycache__ 61, physical/die_plan/s81 8, physical/die_plan/qwen_kvsys 4, tools/s81_head/__pycache__ 4, physical/die_plan/hbm 3, .m8wave_src.json 1, assets/sink_bins_0.json 1, assets/sink_bins_1.json 1, assets/sink_bins_2.json 1, assets/sink_bins_3.json 1, assets/sink_bins_4.json 1, assets/sink_bins_5.json 1, assets/sink_bins_6.json 1, assets/sink_bins_7.json 1, assets/sink_bins_8.json 1
- 3-way merged: physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py tools/die_plan/die_plan.schema.json tools/die_plan/gen_phys.py tools/die_plan/schema.py
- stale old git copies -> commit (34): physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x.sv physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_cap5_lp.sv physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_cap5r_lp.sv physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_lp.sv physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_lp.sv physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c3x.sv physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c3x_lp.sv rtl/common/ot_dp_clk_landing.sv rtl/common/ot_dp_clk_landing_ca.sv rtl/dsrom_sys/s81_dv/slice/landed/c1x/ot_s81sl_slice_c1x_lp.sv rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8/ot_s81sl_slice_c1x_k8_lp.sv rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5/ot_s81sl_slice_c1x_k8_cap5_lp.sv rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp.sv rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp_e6.sv rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp_w3.sv rtl/dsrom_sys/s81_dv/slice/landed/c3x/ot_s81sl_slice_c3x_lp.sv rtl/dsrom_sys/s81_dv/slice/landed/c3x_k8_cap5r/ot_s81sl_slice_c3x_k8_cap5r_lp.sv rtl/dsrom_sys/s81_dv/slice/landed/c3x_k8_cap5r/ot_s81sl_slice_c3x_k8_cap5r_lp_w3.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_c1x.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_c3x.sv tools/die_plan/bind.py tools/die_plan/bind_verify.py tools/die_plan/clock_landings.py tools/die_plan/count_align_bind.py tools/die_plan/test_core_input_lockup.py tools/die_plan/test_core_out_land.py tools/die_plan/test_ring_wreg.py tools/die_plan/test_ring_wreg_chunks.py tools/hbm_idx_topk_static_vectors.py tools/hbm_layer_vehicle/cx_layer_1021.py tools/hbm_layer_vehicle/idx_images.py tools/hbm_vm_static_calendar.py tools/s81_dv/layer_prog/test_vp_local_forms.py tools/s81_dv/vp_local_1026/forms.py
- conflicts (live kept): tools/autopilot/kit_wave.py
- re-bind: no strict bind of record in kit_rtl (script mode, script export): bind-diff not applicable; the new tree is built and byte-checked only

## qwen_compute -> /srv/opentallas-scratch2/claude/wave-src/20261112/qwen_compute (new 69c2982913fb; die branch 9024de9d66 merged)
- live /srv/opentallas-scratch2/claude/kw45/src_qc_s27_9024de9d66 on epyc9; manifests: epyc7 e3b0c44298fc, epyc9 f51b0b12ea6e, epyc8 c987b0afc7d8
- paths: same 324289, new file (main/overlay) 52, carry live-only (not in git) 34, restored (in the commit, absent live) 32, take new (main/overlay changed) 9, stale old git copy -> take commit 7, carry live overlay (not in git) 4
- carried live overlays (not in git), top dirs: tools/die_plan/__pycache__ 28, physical/die_plan/qwen_compute 10
- stale old git copies -> commit (7): tools/die_plan/gen_phys.py tools/die_plan/route_supply.py tools/die_plan/test_wide_chain_float.py tools/die_plan/wide_chain_float_event.py tools/fleet/ot-autoclean.py tools/fleet/test_ot_autoclean_auto.py tools/fleet/test_ot_autoclean_dx.py
- re-bind: strict bind of record (asbuilt /srv/opentallas-scratch2/claude/kw45/src_qc_s27_9024de9d66/physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_sw2_pv.json, old bind /srv/opentallas-scratch2/claude/kw45/qcs27in/bind_plan_qc99_s27) -> /srv/opentallas-scratch2/claude/wave-src/20261112/qwen_compute.bind

## qwen_kvsys -> /srv/opentallas-scratch2/claude/wave-src/20261112/qwen_kvsys (new 386428f6af2e; die branch 9446d18f5d9a on main/overlays)
- live /srv/opentallas-scratch2/claude/kw45/src_kv_main_40e22dd1d2 on epyc9; manifests: epyc7 12205103b101, epyc8 e1503cd5adc3, epyc9 7cadeca203e5
- paths: same 323855, new file (main/overlay) 438, carry live-only (not in git) 98, take new (main/overlay changed) 43, stale old git copy -> take commit 7, carry live overlay (not in git) 3, conflict: both changed (kept live) 1
- carried live overlays (not in git), top dirs: tools/die_plan/__pycache__ 96, physical/die_plan/qwen_kvsys 3, tools/__pycache__/die_port_bind.cpython-314.pyc 1, tools/hbm_die_v16/__pycache__ 1
- stale old git copies -> commit (7): physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py tools/die_plan/check.py tools/die_plan/clock_landing_plan.py tools/die_plan/die_plan.schema.json tools/die_plan/gen_phys.py tools/die_plan/route_supply.py tools/die_plan/schema.py
- conflicts (live kept): tools/die_plan/landing_place.py
- re-bind: strict bind of record (asbuilt /srv/opentallas-scratch2/claude/dkv98/asbuilt_rel.json, old bind /srv/opentallas-scratch2/claude/dkv98/bind_vF2) -> /srv/opentallas-scratch2/claude/wave-src/20261112/qwen_kvsys.bind
- item_inputs pinned (own plan/kit_rtl, not re-bound): 29

## hbm -> /srv/opentallas-scratch2/claude/wave-src/20261112/hbm (new 386428f6af2e; die branch 7b84010b1c6e on main/overlays)
- live /srv/opentallas-scratch2/claude/kw45/src_hbm_main_m8w1_7b84010b1c on epyc9; manifests: epyc7 615c611371ca, epyc9 f9c682440c79, epyc8 92fb66bf56c9
- paths: same 324031, new file (main/overlay) 268, carry live-only (not in git) 112, take new (main/overlay changed) 35, carry live overlay (not in git) 10, conflict: both changed (kept live) 3
- carried live overlays (not in git), top dirs: tools/die_plan/__pycache__ 97, physical/die_plan/s81 8, physical/die_plan/qwen_kvsys 4, physical/die_plan/hbm 3, physical/die_plan/hbm_arch_cores 3, .m8wave_src.json 1, physical/die_plan/qwen_compute 1, tools/__pycache__/die_port_bind.cpython-314.pyc 1, tools/autopilot/__pycache__ 1, tools/die_plan/macro_skip_rtlmp.tcl 1, tools/die_plan/test_gen_phys_phy_core_area.py 1, tools/die_trial/__pycache__ 1
- conflicts (live kept): physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py tools/die_plan/gen_phys.py
- re-bind: strict bind of record (asbuilt /srv/opentallas-scratch2/claude/hbm-cut-1111/bind/asbuilt_t20io.json, old bind /srv/opentallas-scratch2/claude/hbm-cut-1111/bind/bind_t20io) -> /srv/opentallas-scratch2/claude/wave-src/20261112/hbm.bind
- item_inputs pinned (own plan/kit_rtl, not re-bound): 86
