# SRC-AUDIT-1111 (lane SRC-AUDIT-1, read-only, 2026-11-11 PST / host clocks 11-12 05:0x UTC)

Scope: pinned src snapshots used by kit_wave (autopilot/kit_wave.json read 11-11 ~20:30 PST) vs origin/main 9446d18f5d (11-11 19:17 PST). Own clone: epyc8:/srv/opentallas-scratch2/claude/src-audit-1/repo (plain clone via hub, --filter unsupported by the hub; --reference of an existing local clone). Compare = git blob sha1 of every snapshot file under tracked top dirs (results/ and untracked physical/ data skipped) vs main tree and vs the snapshot base commit. `__pycache__`/.pyc excluded from all counts. Raw JSON: epyc8 src-audit-1/out/*.json.

## Headline findings

1. The premise "HBM snapshot is from 11-09" is stale: kit_wave.json already pins HBM to kw45/src_hbm_main_fe0002fac6 (main fe0002fac6cc, 11-11 10:08 PST) and every die snapshot is main-based and contains CLK-ROOT-CROSS e425162438 (git ancestor of every base, checked). The HBM snapshot is 213 commits (126 non-merge touching tools/ die_plan/ rtl/) behind main, so it MISSES everything merged after 11-11 10:08, not CLK-ROOT-CROSS.
2. (a) snapshot-only RTL that main lacks: none in any current die src (0 / 0 / 0 / 0 / 0). hfd_vms_bank_native_q0_faces.sv, ot_vms_bank_q0_faces_core.sv and ot_vms_ce_counter_pipe.sv are on main now (rtl/hbm_accel/generic/vm/static/..., rd1 merge 52216309aa); the epyc9-only item src src_hbm_rd1_nph has (a)=0. Only (a) hits: head 3 stray macro_rects_hd_*.json at tree root, qc 1 file physical/die_plan/qwen_compute/qc_start_1106/runtime/sidecar_pv.json (untracked runtime data, not RTL).
3. Unmerged local patches ((c)) are tiny and all identified: tools/die_plan/gen_phys.py in HBM/KV (+hbm opsg, s81) = VISLAYOUT2-QC 31b4aa4824 "copy flow_tag + grt_transition_mode into every kit dir" deployed ahead of merge by KW-FIX-45, branch claude/vislayout2-qc-1111, NOT on main; QC gen_phys.py = QC-NK-HOLD A+P hooks (core_input_place; commits 63ee76574e/d95f7cc25e ARE on main since 11-12 00:49, snapshot carries the pre-merge branch form via claude/kw-fix-45-qc-cut-comp-1111); gen_core_kit_hbm.py (hbm, hbm_opsg) = local edit with no matching commit (main has 86cebb38d2 --pre-gpl-extra / ef585c8b2f --grt-nonport-hold); run_kit_hbm.sh = claude/kw-fix-45-core-grtm-1111 2713b2eb62 (unmerged); kv/qc landing_place.py = claude/cland-facewin-1111 054e07a4c1 (unmerged); kv plan_c.json = local plan data; s81 plan_h2_2249.json = local plan data. Land 31b4aa4824, 2713b2eb62, 054e07a4c1 and the gen_core_kit_hbm.py edit to let main replace the snapshots.
4. HEAD snapshot (src_head_freg_58a264ab1e) holds 37 STALE older-than-base versions of main files (S81 portfix178 slice RTL, rtl/common/ot_dp_clk_landing*.sv from 11-09/11-11 20:39 commits, rtl/dsrom_sys/s81_dv/slice/landed/*): the head tree is a sparse overlay on an older base, so these are (b)-type stale, not new patches.
5. COPY PROBLEM: epyc9:s87bind/bsrc3_r7b (S81 src, config src) is a symlink farm: 45 top-level entries point to /srv/opentallas-scratch2/claude/kw43/src_s81_main_e5cc5a2, which does NOT exist on epyc9 (and is absent on epyc7, epyc2, intel1, intel2). All 45 are dangling on epyc9 (compiler, configs, data, docs, jobs, opentools, reports, runtime, schemas, site, spec, spice, src, tb, testdata, tests, root *.md). On epyc8 the target exists (works, but the src depends on the kw43 tree, never delete it). S81 hosts per config are epyc7/epyc9/intel2/epyc2; none of epyc7/epyc2/intel2 holds bsrc3_r7b at all; only epyc8 (not in S81 hosts list, only gen_hosts) is complete. Whether kits stage inputs via kit_store instead is not verified here.
6. HBM per-item src (14 bitgrp items, nph item, rd1_nph item) live on epyc9 only; HBM hosts are epyc8+epyc9 and epyc8 lacks src_hbm_bitgrp_*, src_hbm_nph_*, src_hbm_rd1_nph (opsg is on both). Items placed on epyc8 would find no src.
7. Copies on epyc8 vs epyc9 are otherwise equal: identical sha1 lists for tools/ ignoring __pycache__ (0 diffs in all 5 pairs); file counts per top dir identical; 0 empty subdirs in every current src. epyc7/epyc2/epyc4/intel1 hold none of the current kw45/s87bind srcs (only older c90382b467/cd03a1f33f HBM/HEAD/KV srcs on epyc7 and epyc8). /srv/opentallas-scratch and /srv/opentallas-scratch2 are the same filesystem on epyc8/epyc9 (same inode), so one copy per host.
8. kw32/src_27db6 (old KV src, retry note): epyc8 62489 files / 2089 empty dirs vs epyc9 and epyc7 81628 files / 2078 empty dirs vs intel1 320869 files; epyc2 and epyc4 0 files (21 empty top dirs). Not a current src; still partial on epyc8/epyc2/epyc4.

## Summary table

| die | wave src (config) | base main sha / date | main behind (non-merge touching tools/die_plan/rtl) | CLK-ROOT-CROSS | (a) | (b) differing + added-on-main-absent | (c) | hosts holding src |
|---|---|---|---|---|---|---|---|---|
| s81 | s87bind/bsrc3_r7b | c6c0f5cf65d2, 11-11 18:33 | 7 (4) | yes | 0 | 6 + 5 (+2 base files absent) | 2 local | epyc8 OK; epyc9 DANGLING symlinks; epyc7/2/intel2 none |
| s81_head | kw45/src_head_freg_58a264ab1e | 58a264ab1ee1, 11-11 18:16 | 23 (14) | yes | 3 (junk json) | 4 + 122 (+258 base files absent, HBM plan data) | 41 (37 stale-old, 3 unmerged branch, 1 local) | epyc8, epyc9 |
| qwen_compute | kw45/src_qc_main_fc5cd3af6f | fc5cd3af6f, 11-11 17:41 (config src_sha 1ceef03108; qse main@730345725942+genscope branch claude/kw-fix-45-qc-cut-comp-1111) | 39 (22) | yes | 1 (data) | 31 + 239 | 2 | epyc8, epyc9 |
| qwen_kvsys | kw45/src_kv_main_2041e424bb | 2041e424bb56, 11-11 09:10 | 239 (140) | yes | 0 | 180 + 518 | 3 | epyc8, epyc9 |
| hbm | kw45/src_hbm_main_fe0002fac6 (+ item srcs) | fe0002fac6cc, 11-11 10:08 | 213 (126) | yes | 0 | 158 + 504 | 3 | epyc8, epyc9 |

HBM item srcs: bitgrp_fe0002fac6_efdab72dbc13 (14 items; base fe0002fac6 + kit_istations.py + kit_bus_bitgroups.py): (a) 0, (b) 157, (c) 3 (gen_core_kit_hbm.py, run_kit_hbm.sh, gen_phys.py), epyc9 only. nph_fc5cd3af6f (q_spu0__physical_v1; DO_NOT_COUNT mixed): (a) 0, (b) 82, (c) 7, epyc9 only. rd1_nph (hnx_vms_bank_q0_faces vecd4ae item; DO_NOT_COUNT mixed): (a) 0, (b) 80, (c) 8, epyc9 only. opsg_fe0002fac6_1b4ef2e1ce: see below. (b) for item srcs is against base fe0002fac6.

Class fixes missing from the HBM snapshot by name (merged on main after 11-11 10:08, tools/ die_plan/ rtl/): CLAND-WSTART-1 (7dd83f04a2), CLAND-QREG-1 (2d5e254595), FREG-DECL-1 (1ece4481e7, 4f05a8240f), SEAM-HOP-1 path_respace + collector_reach G0 ERROR (ce27841937, ba88610f5d, 0d73dc057e, 6986f44fe9), KIT-OVERLAY-1 type_overlay (368131ef80, 300587e0f5), core_shape G0 core_shape_change ERROR (ce4685ee52, a8e3a29cad), gen_phys core_input_place + bind core_input_lockup pipe/pipe_except (d95f7cc25e, 63ee76574e, fc99961086, 443adc0829), grt_nonport_hold (a6f7097695, ef585c8b2f; present only in the nph item src), kit_wave retry-epoch / QUEUE-CANCELLED follow_queue / KIT-INPUT-STORE-1 land (fe846c4a58, e3fa343ee8, af57ebdd50), ot-run --cancel-dir single-line fix (c59dcc5c63, 141d1cbc80), geom_rules spare_out (272b543931), kit_topology SUL0-PINFACE-1 census (ab0cf7d04a), kit_istations per-bit-group sites + kit_bus_bitgroups pass-through (fecdddfb19, efdab72dbc; only in the bitgrp item src), rd1 RTL +1 read stage (a918972c20, befde7c09d and merge 52216309aa), HBM form A' per-hop ft latch (24a9a12d6a), DIE-LAYOUT-HBM io re-form (1637f6ae93), compiler rd1 response shift (882687e50e, 225791101e). Full per-die lists below.

## Copy-completeness table (find -type f, hosts as of 11-12 05:00 UTC; same on /srv/opentallas-scratch and scratch2 = one fs)

| src (relative to /srv/opentallas-scratch2/claude) | epyc8 files | epyc9 files | empty dirs (e8/e9) | other hosts | note |
|---|---|---|---|---|---|
| s87bind/bsrc3_r7b (S81) | 141047 (+45 symlinks, 144465 followed) | 141047 (+45 symlinks, ALL DANGLING) | 0/0 | epyc7, epyc2, intel1, intel2: absent | symlinks -> kw43/src_s81_main_e5cc5a2, present on epyc8 only; real dirs only physical, results, rtl, tools |
| kw45/src_head_freg_58a264ab1e | 323301 | 323310 (+9 pycache) | 0/0 | absent elsewhere | tools equal ex-pycache |
| kw45/src_qc_main_fc5cd3af6f | 323411 | 323462 (+51 pycache) | 0/0 | absent elsewhere | tools equal ex-pycache (1 pyc differs) |
| kw45/src_kv_main_2041e424bb | 322957 | 322990 (+33 pycache) | 0/0 | absent elsewhere | tools equal ex-pycache |
| kw45/src_hbm_main_fe0002fac6 | 322989 | 322969 (-20 pycache) | 0/0 | absent elsewhere | tools equal ex-pycache |
| kw45/src_hbm_opsg_fe0002fac6_1b4ef2e1ce | 322984 | 322896 | 0/0 | absent elsewhere | equal ex-pycache |
| kw45/src_hbm_bitgrp_fe0002fac6_efdab72dbc13 | ABSENT | 322971 | -/0 | absent elsewhere | 14 HBM items; epyc8 lacks it |
| kw45/src_hbm_nph_fc5cd3af6f | ABSENT | 323077 | -/0 | absent elsewhere | q_spu0 item; epyc8 lacks it |
| kw45/src_hbm_rd1_nph | ABSENT | 323078 | -/0 | absent elsewhere | rd1 vecd4ae item; epyc8 lacks it |

Top-level dir sizes/counts (compiler 291, configs 213, data 14, docs 240, jobs 15, opentools 58, physical ~112.6-113.0k, results ~179k (S81: 14), rtl 10.9k, runtime 160, schemas 208, site 19, spec 33, spice 27, src 16, tb 3, testdata 319, tests 1760, tools ~17.1-17.2k) match between epyc8 and epyc9 for every current src except S81 on epyc9 (dangling). Note results/ in head/qc/kv/hbm is 179k files / 15 GB each (hardlink-shared, nlink 6-7).

---

# Per-die detail (top 20 paths per class, commit list top 40; (b2) = added on main after the base and absent from the snapshot, (b3) base files missing from snapshot are counted but only meaningful for HEAD)

### s81  (s87bind/bsrc3_r7b)
- base main sha c6c0f5cf65d2, committed 2026-11-11 18:33:54 -0800; main behind: 7 commits (2 first-parent merges); non-merge commits touching tools/ physical/die_plan/ rtl/: 4
- CLK-ROOT-CROSS e425162438 in snapshot base: YES
- hashed 144465 files (results/ and untracked physical/ data skipped: 22)
- counts (pycache excluded): (a) snapshot-only 0 (+0 deleted-on-main); (b) older than main 6 differing + 5 files main added after base absent from snapshot + 2 base files absent; (c) newer/diverged 2

Missing non-merge commits (newest first, top 40 of 4):
  - a8e3a29cad 11-12 03:14 core_shape: base-name variant family (_cs1/_bfp/_rN/__cdN, WARN) for modules with no signed record of their own
  - ce4685ee52 11-12 03:11 G0: core_shape_change ERROR (opt-in --core-shape-index) + core_shape_exceptions schema
  - 300587e0f5 11-12 03:09 KIT-OVERLAY-1: kit_wave item_inputs type_overlay + type_positions overlay key
  - 368131ef80 11-12 03:01 KIT-OVERLAY-1: per-type positions-only overlay (type_overlay.py, gen phys --type-overlay, typed validation scope)
- (c) split: LOCAL-EDIT 2

(a) snapshot-only: 0

(a2) in base, deleted on main: 0

(b) differing, snapshot == base blob (main fixed since): 6
  - tools/autopilot/kit_wave.py
  - tools/autopilot/test_kit_wave_genhosts.py
  - tools/die_plan/check.py
  - tools/die_plan/gen.py
  - tools/die_plan/gen_rtl.py
  - tools/die_plan/schema.py

(b2) added on main after base, absent in snapshot: 5
  - tools/die_plan/TYPE_OVERLAY.md
  - tools/die_plan/core_shape.py
  - tools/die_plan/test_core_shape.py
  - tools/die_plan/test_type_overlay.py
  - tools/die_plan/type_overlay.py

(c) differing from base and main (local patch): 2
  - physical/die_plan/s81/plan_h2_2249.json  <= LOCAL-EDIT no matching commit in origin
  - tools/die_plan/gen_phys.py  <= LOCAL-EDIT no matching commit in origin

### s81_head  (kw45/src_head_freg_58a264ab1e)
- base main sha 58a264ab1ee1, committed 2026-11-11 18:16:34 -0800; main behind: 23 commits (8 first-parent merges); non-merge commits touching tools/ physical/die_plan/ rtl/: 14
- CLK-ROOT-CROSS e425162438 in snapshot base: YES
- hashed 144160 files (results/ and untracked physical/ data skipped: 30)
- counts (pycache excluded): (a) snapshot-only 3 (+0 deleted-on-main); (b) older than main 4 differing + 122 files main added after base absent from snapshot + 258 base files absent; (c) newer/diverged 41

Missing non-merge commits (newest first, top 40 of 14):
  - a8e3a29cad 11-12 03:14 core_shape: base-name variant family (_cs1/_bfp/_rN/__cdN, WARN) for modules with no signed record of their own
  - ce4685ee52 11-12 03:11 G0: core_shape_change ERROR (opt-in --core-shape-index) + core_shape_exceptions schema
  - 300587e0f5 11-12 03:09 KIT-OVERLAY-1: kit_wave item_inputs type_overlay + type_positions overlay key
  - 368131ef80 11-12 03:01 KIT-OVERLAY-1: per-type positions-only overlay (type_overlay.py, gen phys --type-overlay, typed validation scope)
  - 67cfe043c5 11-12 02:23 CPL-HBM-B1: d6d street-widened positions event for q_b010/q_b011 (+pv1) against t19
  - ba88610f5d 11-12 02:20 path_respace: re-check real normal-input S0->S1 on every moved normal slot (rejects the lane, no new G0 stations error)
  - cd800b3ed2 11-12 02:18 S81-LEAF-CYC quad2 composer stage for DIE-S81-87 ready8 (on the current layout)
  - 6a3ac7073c 11-12 02:18 QC q01 NK quads S2: plan_qc99_s23_nkl, left-column NK tiles R0 -> MY; t22 MY trial measured
  - 0d73dc057e 11-12 02:12 SEAM-HOP-1: path_respace stage script (IN OUT REPORT, declared keys, sidecar passthrough/republish) + rebank proposal
  - 7c501990c2 11-12 02:11 HEAD hd_ctl setup form: status relay on lepk_i0 -> lepk_o0 (TT -88 cland fault collector path)
  - ce27841937 11-12 02:06 SEAM-HOP-1: face-register fix, collector_reach G0 ERROR, path_respace one-pass station respacing, seam hop renderer
  - ce7dff7008 11-11 22:15 CPL-HBM-B1: post-ladder type-top cell counts (q_b001 ~368k, q_b010 ~372k, q_b011 ~224k; flat 840k includes the hard cores)
  - befde7c09d 11-11 22:11 CPL-HBM-B1: name the delta d6c_hcol_s2_cplb1_1111 (d6_hubdrop_1111 already exists in hbm-cut-1111/deltas)
  - e0890eb024 11-11 22:10 CPL-HBM-B1: hcol S2 re-layout of q_b001/q_b010/q_b011 (+pv1) on t19 ladder outlines (d6_hubdrop_1111)
- (c) split: STALE-OLD-MAIN-VERSION 37, UNMERGED-BRANCH 3, LOCAL-EDIT 1

(a) snapshot-only: 3
  - macro_rects_hd_host_e.json
  - macro_rects_hd_host_w.json
  - macro_rects_hd_mesh.json

(a2) in base, deleted on main: 0

(b) differing, snapshot == base blob (main fixed since): 4
  - tools/autopilot/test_kit_wave_genhosts.py
  - tools/die_plan/gen.py
  - tools/die_plan/gen_rtl.py
  - tools/die_plan/render.py

(b2) added on main after base, absent in snapshot: 122
  - physical/die_plan/hbm/cpl_hbm_b1_1111/deltas/d6c_hcol_s2_cplb1_1111.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/deltas/d6d_hcol_s2_cplb1_1111.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4.cut.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4.stscan.tsv
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4apply.classify.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4apply.log
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/cells_post_ladder.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/cut_budget_t19_vs_c4.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/cut_budget_t19_vs_d6d.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d.cut.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d.g0cmp.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d.stscan.tsv
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d_plan.sha256
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6dapply.log
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/g0cmp_t19_vs_c4.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/route_supply_t19_vs_c4.tsv
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/route_supply_t19_vs_d6d.tsv
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/t19.cut.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/lad_reports/base_q_b001.rep.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/lad_reports/base_q_b001__physical_v1.rep.json

(c) differing from base and main (local patch): 41
  - physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py  <= STALE-OLD-MAIN-VERSION 86cebb38d2 11-11 16:35 gen_core_kit_hbm: opt-in --pre-gpl-extra FILE (extra PRE_GLOBAL_PLAC [->,origin/main]
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_cap5_lp.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_cap5r_lp.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_lp.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_lp.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c3x.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c3x_lp.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - rtl/common/ot_dp_clk_landing.sv  <= STALE-OLD-MAIN-VERSION 501d1181a2 11-09 18:55 S81 iqf__t1: ring read-select replication DSREP=4 on its six landing [->,origin/main]
  - rtl/common/ot_dp_clk_landing_ca.sv  <= STALE-OLD-MAIN-VERSION 525a0a57ad 11-11 20:39 DIE-QC-97 PLACEREP-1: per-read-chunk copy of the ring placement valu [->,origin/main]
  - rtl/dsrom_sys/s81_dv/slice/landed/c1x/ot_s81sl_slice_c1x_lp.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8/ot_s81sl_slice_c1x_k8_lp.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5/ot_s81sl_slice_c1x_k8_cap5_lp.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp_e6.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp_w3.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - rtl/dsrom_sys/s81_dv/slice/landed/c3x/ot_s81sl_slice_c3x_lp.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - rtl/dsrom_sys/s81_dv/slice/landed/c3x_k8_cap5r/ot_s81sl_slice_c3x_k8_cap5r_lp.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - rtl/dsrom_sys/s81_dv/slice/landed/c3x_k8_cap5r/ot_s81sl_slice_c3x_k8_cap5r_lp_w3.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]
  - rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_c1x.sv  <= STALE-OLD-MAIN-VERSION e46e22c3d7 11-11 16:09 S81-LEAF-CYC: +1 shared quad station on the leaf vn<->lane hi/ho pat [->,origin/main]

### qwen_compute  (kw45/src_qc_main_fc5cd3af6f)
- base main sha fc5cd3af6f, committed 2026-11-11 17:41:06 -0800; main behind: 39 commits (13 first-parent merges); non-merge commits touching tools/ physical/die_plan/ rtl/: 22
- CLK-ROOT-CROSS e425162438 in snapshot base: YES
- hashed 144292 files (results/ and untracked physical/ data skipped: 3)
- counts (pycache excluded): (a) snapshot-only 1 (+0 deleted-on-main); (b) older than main 31 differing + 239 files main added after base absent from snapshot + 0 base files absent; (c) newer/diverged 2

Missing non-merge commits (newest first, top 40 of 22):
  - a8e3a29cad 11-12 03:14 core_shape: base-name variant family (_cs1/_bfp/_rN/__cdN, WARN) for modules with no signed record of their own
  - ce4685ee52 11-12 03:11 G0: core_shape_change ERROR (opt-in --core-shape-index) + core_shape_exceptions schema
  - 300587e0f5 11-12 03:09 KIT-OVERLAY-1: kit_wave item_inputs type_overlay + type_positions overlay key
  - 368131ef80 11-12 03:01 KIT-OVERLAY-1: per-type positions-only overlay (type_overlay.py, gen phys --type-overlay, typed validation scope)
  - 67cfe043c5 11-12 02:23 CPL-HBM-B1: d6d street-widened positions event for q_b010/q_b011 (+pv1) against t19
  - ba88610f5d 11-12 02:20 path_respace: re-check real normal-input S0->S1 on every moved normal slot (rejects the lane, no new G0 stations error)
  - cd800b3ed2 11-12 02:18 S81-LEAF-CYC quad2 composer stage for DIE-S81-87 ready8 (on the current layout)
  - 6a3ac7073c 11-12 02:18 QC q01 NK quads S2: plan_qc99_s23_nkl, left-column NK tiles R0 -> MY; t22 MY trial measured
  - 0d73dc057e 11-12 02:12 SEAM-HOP-1: path_respace stage script (IN OUT REPORT, declared keys, sidecar passthrough/republish) + rebank proposal
  - 7c501990c2 11-12 02:11 HEAD hd_ctl setup form: status relay on lepk_i0 -> lepk_o0 (TT -88 cland fault collector path)
  - ce27841937 11-12 02:06 SEAM-HOP-1: face-register fix, collector_reach G0 ERROR, path_respace one-pass station respacing, seam hop renderer
  - 4f05a8240f 11-12 01:59 FREG-DECL-1: declare the FREG cycle in the ring_wreg test fixtures; strap K + 2 asserted
  - 8af99c3857 11-12 01:58 S81-LEAF-CYC quad2 plan delta: 71 non-KV ot_s81sl_leaf types (lane permutation + 2-stage quad sites)
  - 6986f44fe9 11-12 01:45 G0 advisory seam-hop check (SEAM-HOP-1): last station -> first station across each seam, WARN over 405 um
  - cb54a72e65 11-12 01:41 QC NK quads S2: plan_qc99_s22_nkr0, right-column NK/NL tiles MY -> R0 (data pins to the middle channel)
  - 63676d718d 11-12 01:40 S81-LEAF-CYC quad2: two shared hi/ho stations per lane quad (CS_HI/HO D2 GS2 G4)
  - d7abde7747 11-12 01:31 HBM next-event plan d49a_io_reform_1111: t19 + DIE-LAYOUT-HBM NW_io/NE_io re-form (plan e9ae418c06ca, strict bind OK, G0 554 -> 554)
  - 1e6d71e1cc 11-12 01:14 HEAD FREG marking event: freg declared on 18 count-aligned ports, +1 raised on hd_ctl_n x2 and hd_turn_a x12
  - 1ece4481e7 11-12 00:48 FREG-DECL-1: fail closed on an undeclared FREG data cycle (count-aligned rings)
  - ce7dff7008 11-11 22:15 CPL-HBM-B1: post-ladder type-top cell counts (q_b001 ~368k, q_b010 ~372k, q_b011 ~224k; flat 840k includes the hard cores)
  - befde7c09d 11-11 22:11 CPL-HBM-B1: name the delta d6c_hcol_s2_cplb1_1111 (d6_hubdrop_1111 already exists in hbm-cut-1111/deltas)
  - e0890eb024 11-11 22:10 CPL-HBM-B1: hcol S2 re-layout of q_b001/q_b010/q_b011 (+pv1) on t19 ladder outlines (d6_hubdrop_1111)
- (c) split: LOCAL-EDIT 1, UNMERGED-BRANCH 1

(a) snapshot-only: 1
  - physical/die_plan/qwen_compute/qc_start_1106/runtime/sidecar_pv.json

(a2) in base, deleted on main: 0

(b) differing, snapshot == base blob (main fixed since): 31
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_cap5_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_cap5r_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c3x.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c3x_lp.sv
  - rtl/dsrom_sys/s81_dv/slice/landed/c1x/ot_s81sl_slice_c1x_lp.sv
  - rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8/ot_s81sl_slice_c1x_k8_lp.sv
  - rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5/ot_s81sl_slice_c1x_k8_cap5_lp.sv
  - rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp.sv
  - rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp_e6.sv
  - rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp_w3.sv
  - rtl/dsrom_sys/s81_dv/slice/landed/c3x/ot_s81sl_slice_c3x_lp.sv
  - rtl/dsrom_sys/s81_dv/slice/landed/c3x_k8_cap5r/ot_s81sl_slice_c3x_k8_cap5r_lp.sv
  - rtl/dsrom_sys/s81_dv/slice/landed/c3x_k8_cap5r/ot_s81sl_slice_c3x_k8_cap5r_lp_w3.sv
  - rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_c1x.sv
  - rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_c3x.sv
  - tools/autopilot/kit_wave.py
  - tools/autopilot/test_kit_wave_genhosts.py

(b2) added on main after base, absent in snapshot: 239
  - physical/die_plan/hbm/cpl_hbm_b1_1111/deltas/d6c_hcol_s2_cplb1_1111.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/deltas/d6d_hcol_s2_cplb1_1111.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4.cut.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4.stscan.tsv
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4apply.classify.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4apply.log
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/cells_post_ladder.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/cut_budget_t19_vs_c4.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/cut_budget_t19_vs_d6d.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d.cut.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d.g0cmp.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d.stscan.tsv
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d_plan.sha256
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6dapply.log
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/g0cmp_t19_vs_c4.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/route_supply_t19_vs_c4.tsv
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/route_supply_t19_vs_d6d.tsv
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/t19.cut.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/lad_reports/base_q_b001.rep.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/lad_reports/base_q_b001__physical_v1.rep.json

(c) differing from base and main (local patch): 2
  - tools/die_plan/gen_phys.py  <= LOCAL-EDIT no matching commit in origin
  - tools/die_plan/landing_place.py  <= UNMERGED-BRANCH 054e07a4c1 11-12 04:19 CLAND-FACEWIN-1: writer-face relay window leaves FT bit sites / hard [origin/claude/cland-facewin-1111]

### qwen_kvsys  (kw45/src_kv_main_2041e424bb)
- base main sha 2041e424bb56, committed 2026-11-11 09:10:38 -0800; main behind: 239 commits (70 first-parent merges); non-merge commits touching tools/ physical/die_plan/ rtl/: 140
- CLK-ROOT-CROSS e425162438 in snapshot base: YES
- hashed 144030 files (results/ and untracked physical/ data skipped: 3)
- counts (pycache excluded): (a) snapshot-only 0 (+0 deleted-on-main); (b) older than main 180 differing + 518 files main added after base absent from snapshot + 0 base files absent; (c) newer/diverged 3

Missing non-merge commits (newest first, top 40 of 140):
  - a8e3a29cad 11-12 03:14 core_shape: base-name variant family (_cs1/_bfp/_rN/__cdN, WARN) for modules with no signed record of their own
  - ce4685ee52 11-12 03:11 G0: core_shape_change ERROR (opt-in --core-shape-index) + core_shape_exceptions schema
  - 300587e0f5 11-12 03:09 KIT-OVERLAY-1: kit_wave item_inputs type_overlay + type_positions overlay key
  - 368131ef80 11-12 03:01 KIT-OVERLAY-1: per-type positions-only overlay (type_overlay.py, gen phys --type-overlay, typed validation scope)
  - 67cfe043c5 11-12 02:23 CPL-HBM-B1: d6d street-widened positions event for q_b010/q_b011 (+pv1) against t19
  - ba88610f5d 11-12 02:20 path_respace: re-check real normal-input S0->S1 on every moved normal slot (rejects the lane, no new G0 stations error)
  - cd800b3ed2 11-12 02:18 S81-LEAF-CYC quad2 composer stage for DIE-S81-87 ready8 (on the current layout)
  - 6a3ac7073c 11-12 02:18 QC q01 NK quads S2: plan_qc99_s23_nkl, left-column NK tiles R0 -> MY; t22 MY trial measured
  - 0d73dc057e 11-12 02:12 SEAM-HOP-1: path_respace stage script (IN OUT REPORT, declared keys, sidecar passthrough/republish) + rebank proposal
  - 7c501990c2 11-12 02:11 HEAD hd_ctl setup form: status relay on lepk_i0 -> lepk_o0 (TT -88 cland fault collector path)
  - ce27841937 11-12 02:06 SEAM-HOP-1: face-register fix, collector_reach G0 ERROR, path_respace one-pass station respacing, seam hop renderer
  - 4f05a8240f 11-12 01:59 FREG-DECL-1: declare the FREG cycle in the ring_wreg test fixtures; strap K + 2 asserted
  - 8af99c3857 11-12 01:58 S81-LEAF-CYC quad2 plan delta: 71 non-KV ot_s81sl_leaf types (lane permutation + 2-stage quad sites)
  - 6986f44fe9 11-12 01:45 G0 advisory seam-hop check (SEAM-HOP-1): last station -> first station across each seam, WARN over 405 um
  - cb54a72e65 11-12 01:41 QC NK quads S2: plan_qc99_s22_nkr0, right-column NK/NL tiles MY -> R0 (data pins to the middle channel)
  - 63676d718d 11-12 01:40 S81-LEAF-CYC quad2: two shared hi/ho stations per lane quad (CS_HI/HO D2 GS2 G4)
  - d7abde7747 11-12 01:31 HBM next-event plan d49a_io_reform_1111: t19 + DIE-LAYOUT-HBM NW_io/NE_io re-form (plan e9ae418c06ca, strict bind OK, G0 554 -> 554)
  - 7dd83f04a2 11-12 01:17 CLAND-WSTART-1: anchor writer START relay chains at the origin home when relocating around hard cores
  - 1e6d71e1cc 11-12 01:14 HEAD FREG marking event: freg declared on 18 count-aligned ports, +1 raised on hd_ctl_n x2 and hd_turn_a x12
  - 1637f6ae93 11-12 01:11 DIE-LAYOUT-HBM io re-form: NW_io/NE_io cut to logic height + NW_iorly/NE_iorly relay columns (t19 delta)
  - fc99961086 11-12 01:10 bind: core_input_lockup pipe_except -- ports that keep the latch without the pipe (NK rst_n)
  - ef585c8b2f 11-12 01:03 gen_core_kit_hbm: opt-in --grt-nonport-hold (shared nonport hold adapter after the kit PRE_GLOBAL_ROUTE_TCL); absent = byte-identical
  - fe846c4a58 11-12 00:50 kit_wave: a retry entry absent from the config forgets its first-seen time, so remove + re-add re-arms it (retry epoch)
  - 443adc0829 11-12 00:49 core_input_place: chain spread at PRE_RESIZE; keep the first stage after a core output
  - d95f7cc25e 11-12 00:49 gen_phys: core_input_place hooks for the QC NK A+P form (anchor + chain spread)
  - 63ee76574e 11-12 00:49 bind: core_input_lockup pipe -- +D declared register stages before the NK lockup latch (QC NK A+P form)
  - 1ece4481e7 11-12 00:48 FREG-DECL-1: fail closed on an undeclared FREG data cycle (count-aligned rings)
  - 2d5e254595 11-12 00:42 CLAND-QREG-1: landing ring read-leg +1 pipeline cycle (QREG output stage), class opt-in
  - e3fa343ee8 11-12 00:37 kit_wave: follow_queue turns a CANCELLED queue job into a CANCELLED (class QUEUE-CANCELLED), retry-eligible wave row
  - fa29bae4b9 11-12 00:37 HEAD hd_host_w TX_STAGE: one register stage on host276 h_rx_o (a3 TT -76 retime) + host_rx lane +1
  - a6f7097695 11-12 00:36 gen_phys: opt-in OT_GRT_NONPORT_HOLD=1 chains tools/grt_nonport_hold.tcl at the end of the kit PRE_GLOBAL_ROUTE_TCL; absent = byte-identical
  - 86cebb38d2 11-11 16:35 gen_core_kit_hbm: opt-in --pre-gpl-extra FILE (extra PRE_GLOBAL_PLACE hook after face_flops.tcl)
  - 225791101e 11-11 16:30 IDX ack/end windows follow the rd1 response shift; windowed tests; identity vs base
  - 882687e50e 11-11 16:29 Compiler: default-off rd1 hub response calendar shift (shift_response, --rd1-resp-shift, IDX wired) with hub bench
  - 272b543931 11-12 00:23 geom_rules: outputs listed in a kit spare_out.json are not unregistered pins (pin_reg_metrics spare=, --spare-out, geom_check.sh passes it)
  - c59dcc5c63 11-11 16:20 ot-run --cancel-dir: write the record as ONE line (a multi-line parent command split it and signals_cancel never matched); test with a heredoc parent
  - 36bd5fa243 11-12 00:20 QC NK output class: core_out_land plan opt-in + plan_qc99_s21_nkout
  - db302c9bdf 11-12 00:19 S81 as-built BF bench with bound-plan seam stages; re-measured col_h9_asb_x/nx, col_h10_asb_x |E2|bseg1024
  - c9a64c107c 11-12 00:00 HBM rd1 bind-side +1: cover VM share b_rr clients (COLL gq issue VM_RT)
  - 141d1cbc80 11-11 15:59 ot-run --cancel-dir KIT_PATH: end the autopilot record of a job whose client is already dead
- (c) split: LOCAL-EDIT 2, UNMERGED-BRANCH 1

(a) snapshot-only: 0

(a2) in base, deleted on main: 0

(b) differing, snapshot == base blob (main fixed since): 180
  - physical/die_plan/hbm/bind/hbm_param_regen.py
  - physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_banks.sv
  - physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_gathered_mix_reader_static.sv
  - physical/die_plan/hbm_arch_cores/core_tap_align.tcl
  - physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py
  - physical/die_plan/hbm_arch_cores/recipes_b2.json
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_cap5_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_cap5r_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c3x.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c3x_lp.sv
  - rtl/common/ot_dp_clk_landing.sv
  - rtl/common/ot_dp_clk_landing_ca.sv
  - rtl/dsrom_sys/s81_dv/frame/col_h10.sv
  - rtl/dsrom_sys/s81_dv/frame/col_h9.sv
  - rtl/dsrom_sys/s81_dv/frame_l4/col_h10_l4.sv
  - rtl/dsrom_sys/s81_dv/frame_l4/col_h10_l4_nx.sv
  - rtl/dsrom_sys/s81_dv/frame_l4/col_h9_l4.sv

(b2) added on main after base, absent in snapshot: 518
  - physical/die_plan/hbm/bind/subtype/ot_hgi_sfu_split3_lane_core__idpin__bsub.sv
  - physical/die_plan/hbm/bind/subtype/run/bind_subtype.sh
  - physical/die_plan/hbm/bind/subtype/run/hook_subtype.py
  - physical/die_plan/hbm/bind/subtype/run/prep_sub_lec.py
  - physical/die_plan/hbm/bind/subtype/run/run_sub_lec.sh
  - physical/die_plan/hbm/bind/subtype/run/wire_all.sh
  - physical/die_plan/hbm/bind/subtype/tkm_full/run.sh
  - physical/die_plan/hbm/bind/subtype/tkm_full/tb_tkm_root_full.sv
  - physical/die_plan/hbm/cpl_hbm_b1_1111/deltas/d6c_hcol_s2_cplb1_1111.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/deltas/d6d_hcol_s2_cplb1_1111.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4.cut.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4.stscan.tsv
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4apply.classify.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4apply.log
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/cells_post_ladder.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/cut_budget_t19_vs_c4.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/cut_budget_t19_vs_d6d.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d.cut.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d.g0cmp.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d.stscan.tsv

(c) differing from base and main (local patch): 3
  - physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json  <= LOCAL-EDIT no matching commit in origin
  - tools/die_plan/gen_phys.py  <= LOCAL-EDIT no matching commit in origin
  - tools/die_plan/landing_place.py  <= UNMERGED-BRANCH 054e07a4c1 11-12 04:19 CLAND-FACEWIN-1: writer-face relay window leaves FT bit sites / hard [origin/claude/cland-facewin-1111]

### hbm  (kw45/src_hbm_main_fe0002fac6)
- base main sha fe0002fac6cc, committed 2026-11-11 10:08:04 -0800; main behind: 213 commits (65 first-parent merges); non-merge commits touching tools/ physical/die_plan/ rtl/: 126
- CLK-ROOT-CROSS e425162438 in snapshot base: YES
- hashed 144063 files (results/ and untracked physical/ data skipped: 3)
- counts (pycache excluded): (a) snapshot-only 0 (+0 deleted-on-main); (b) older than main 158 differing + 504 files main added after base absent from snapshot + 0 base files absent; (c) newer/diverged 3

Missing non-merge commits (newest first, top 40 of 126):
  - a8e3a29cad 11-12 03:14 core_shape: base-name variant family (_cs1/_bfp/_rN/__cdN, WARN) for modules with no signed record of their own
  - ce4685ee52 11-12 03:11 G0: core_shape_change ERROR (opt-in --core-shape-index) + core_shape_exceptions schema
  - 300587e0f5 11-12 03:09 KIT-OVERLAY-1: kit_wave item_inputs type_overlay + type_positions overlay key
  - 368131ef80 11-12 03:01 KIT-OVERLAY-1: per-type positions-only overlay (type_overlay.py, gen phys --type-overlay, typed validation scope)
  - 67cfe043c5 11-12 02:23 CPL-HBM-B1: d6d street-widened positions event for q_b010/q_b011 (+pv1) against t19
  - ba88610f5d 11-12 02:20 path_respace: re-check real normal-input S0->S1 on every moved normal slot (rejects the lane, no new G0 stations error)
  - cd800b3ed2 11-12 02:18 S81-LEAF-CYC quad2 composer stage for DIE-S81-87 ready8 (on the current layout)
  - 6a3ac7073c 11-12 02:18 QC q01 NK quads S2: plan_qc99_s23_nkl, left-column NK tiles R0 -> MY; t22 MY trial measured
  - 0d73dc057e 11-12 02:12 SEAM-HOP-1: path_respace stage script (IN OUT REPORT, declared keys, sidecar passthrough/republish) + rebank proposal
  - 7c501990c2 11-12 02:11 HEAD hd_ctl setup form: status relay on lepk_i0 -> lepk_o0 (TT -88 cland fault collector path)
  - ce27841937 11-12 02:06 SEAM-HOP-1: face-register fix, collector_reach G0 ERROR, path_respace one-pass station respacing, seam hop renderer
  - 4f05a8240f 11-12 01:59 FREG-DECL-1: declare the FREG cycle in the ring_wreg test fixtures; strap K + 2 asserted
  - 8af99c3857 11-12 01:58 S81-LEAF-CYC quad2 plan delta: 71 non-KV ot_s81sl_leaf types (lane permutation + 2-stage quad sites)
  - 6986f44fe9 11-12 01:45 G0 advisory seam-hop check (SEAM-HOP-1): last station -> first station across each seam, WARN over 405 um
  - cb54a72e65 11-12 01:41 QC NK quads S2: plan_qc99_s22_nkr0, right-column NK/NL tiles MY -> R0 (data pins to the middle channel)
  - 63676d718d 11-12 01:40 S81-LEAF-CYC quad2: two shared hi/ho stations per lane quad (CS_HI/HO D2 GS2 G4)
  - d7abde7747 11-12 01:31 HBM next-event plan d49a_io_reform_1111: t19 + DIE-LAYOUT-HBM NW_io/NE_io re-form (plan e9ae418c06ca, strict bind OK, G0 554 -> 554)
  - 7dd83f04a2 11-12 01:17 CLAND-WSTART-1: anchor writer START relay chains at the origin home when relocating around hard cores
  - 1e6d71e1cc 11-12 01:14 HEAD FREG marking event: freg declared on 18 count-aligned ports, +1 raised on hd_ctl_n x2 and hd_turn_a x12
  - 1637f6ae93 11-12 01:11 DIE-LAYOUT-HBM io re-form: NW_io/NE_io cut to logic height + NW_iorly/NE_iorly relay columns (t19 delta)
  - fc99961086 11-12 01:10 bind: core_input_lockup pipe_except -- ports that keep the latch without the pipe (NK rst_n)
  - ef585c8b2f 11-12 01:03 gen_core_kit_hbm: opt-in --grt-nonport-hold (shared nonport hold adapter after the kit PRE_GLOBAL_ROUTE_TCL); absent = byte-identical
  - fe846c4a58 11-12 00:50 kit_wave: a retry entry absent from the config forgets its first-seen time, so remove + re-add re-arms it (retry epoch)
  - 443adc0829 11-12 00:49 core_input_place: chain spread at PRE_RESIZE; keep the first stage after a core output
  - d95f7cc25e 11-12 00:49 gen_phys: core_input_place hooks for the QC NK A+P form (anchor + chain spread)
  - 63ee76574e 11-12 00:49 bind: core_input_lockup pipe -- +D declared register stages before the NK lockup latch (QC NK A+P form)
  - 1ece4481e7 11-12 00:48 FREG-DECL-1: fail closed on an undeclared FREG data cycle (count-aligned rings)
  - 2d5e254595 11-12 00:42 CLAND-QREG-1: landing ring read-leg +1 pipeline cycle (QREG output stage), class opt-in
  - e3fa343ee8 11-12 00:37 kit_wave: follow_queue turns a CANCELLED queue job into a CANCELLED (class QUEUE-CANCELLED), retry-eligible wave row
  - fa29bae4b9 11-12 00:37 HEAD hd_host_w TX_STAGE: one register stage on host276 h_rx_o (a3 TT -76 retime) + host_rx lane +1
  - a6f7097695 11-12 00:36 gen_phys: opt-in OT_GRT_NONPORT_HOLD=1 chains tools/grt_nonport_hold.tcl at the end of the kit PRE_GLOBAL_ROUTE_TCL; absent = byte-identical
  - 86cebb38d2 11-11 16:35 gen_core_kit_hbm: opt-in --pre-gpl-extra FILE (extra PRE_GLOBAL_PLACE hook after face_flops.tcl)
  - 225791101e 11-11 16:30 IDX ack/end windows follow the rd1 response shift; windowed tests; identity vs base
  - 882687e50e 11-11 16:29 Compiler: default-off rd1 hub response calendar shift (shift_response, --rd1-resp-shift, IDX wired) with hub bench
  - 272b543931 11-12 00:23 geom_rules: outputs listed in a kit spare_out.json are not unregistered pins (pin_reg_metrics spare=, --spare-out, geom_check.sh passes it)
  - c59dcc5c63 11-11 16:20 ot-run --cancel-dir: write the record as ONE line (a multi-line parent command split it and signals_cancel never matched); test with a heredoc parent
  - 36bd5fa243 11-12 00:20 QC NK output class: core_out_land plan opt-in + plan_qc99_s21_nkout
  - db302c9bdf 11-12 00:19 S81 as-built BF bench with bound-plan seam stages; re-measured col_h9_asb_x/nx, col_h10_asb_x |E2|bseg1024
  - c9a64c107c 11-12 00:00 HBM rd1 bind-side +1: cover VM share b_rr clients (COLL gq issue VM_RT)
  - 141d1cbc80 11-11 15:59 ot-run --cancel-dir KIT_PATH: end the autopilot record of a job whose client is already dead
- (c) split: LOCAL-EDIT 2, UNMERGED-BRANCH 1

(a) snapshot-only: 0

(a2) in base, deleted on main: 0

(b) differing, snapshot == base blob (main fixed since): 158
  - physical/die_plan/hbm/bind/hbm_param_regen.py
  - physical/die_plan/hbm_arch_cores/core_tap_align.tcl
  - physical/die_plan/hbm_arch_cores/recipes_b2.json
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_cap5_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_cap5r_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c3x.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c3x_lp.sv
  - rtl/common/ot_dp_clk_landing.sv
  - rtl/common/ot_dp_clk_landing_ca.sv
  - rtl/dsrom_sys/s81_dv/frame/col_h10.sv
  - rtl/dsrom_sys/s81_dv/frame/col_h9.sv
  - rtl/dsrom_sys/s81_dv/frame_l4/col_h10_l4.sv
  - rtl/dsrom_sys/s81_dv/frame_l4/col_h10_l4_nx.sv
  - rtl/dsrom_sys/s81_dv/frame_l4/col_h9_l4.sv
  - rtl/dsrom_sys/s81_dv/frame_l4/col_h9_l4_nx.sv
  - rtl/dsrom_sys/s81_dv/frame_l4/frame_l4.json
  - rtl/dsrom_sys/s81_dv/frame_lp/col_h10_l4_lp.sv

(b2) added on main after base, absent in snapshot: 504
  - physical/die_plan/hbm/bind/subtype/ot_hgi_sfu_split3_lane_core__idpin__bsub.sv
  - physical/die_plan/hbm/bind/subtype/run/bind_subtype.sh
  - physical/die_plan/hbm/bind/subtype/run/hook_subtype.py
  - physical/die_plan/hbm/bind/subtype/run/prep_sub_lec.py
  - physical/die_plan/hbm/bind/subtype/run/run_sub_lec.sh
  - physical/die_plan/hbm/bind/subtype/run/wire_all.sh
  - physical/die_plan/hbm/bind/subtype/tkm_full/run.sh
  - physical/die_plan/hbm/bind/subtype/tkm_full/tb_tkm_root_full.sv
  - physical/die_plan/hbm/cpl_hbm_b1_1111/deltas/d6c_hcol_s2_cplb1_1111.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/deltas/d6d_hcol_s2_cplb1_1111.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4.cut.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4.stscan.tsv
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4apply.classify.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4apply.log
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/cells_post_ladder.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/cut_budget_t19_vs_c4.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/cut_budget_t19_vs_d6d.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d.cut.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d.g0cmp.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d.stscan.tsv

(c) differing from base and main (local patch): 3
  - physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py  <= LOCAL-EDIT no matching commit in origin
  - physical/die_plan/hbm_arch_cores/run_kit_hbm.sh  <= UNMERGED-BRANCH 2713b2eb62 11-12 03:55 hbm core kits: honour OT_GRT_TRANSITION_MODE (K/grt_transition_mode  [origin/claude/kw-fix-45-core-grtm-1111]
  - tools/die_plan/gen_phys.py  <= LOCAL-EDIT no matching commit in origin

### hbm_opsg  (kw45/src_hbm_opsg_fe0002fac6_1b4ef2e1ce)
- base main sha fe0002fac6cc, committed 2026-11-11 10:08:04 -0800; main behind: 213 commits (65 first-parent merges); non-merge commits touching tools/ physical/die_plan/ rtl/: 126
- CLK-ROOT-CROSS e425162438 in snapshot base: YES
- hashed 144057 files (results/ and untracked physical/ data skipped: 3)
- counts (pycache excluded): (a) snapshot-only 0 (+0 deleted-on-main); (b) older than main 156 differing + 503 files main added after base absent from snapshot + 0 base files absent; (c) newer/diverged 4

Missing non-merge commits (newest first, top 40 of 126):
  - a8e3a29cad 11-12 03:14 core_shape: base-name variant family (_cs1/_bfp/_rN/__cdN, WARN) for modules with no signed record of their own
  - ce4685ee52 11-12 03:11 G0: core_shape_change ERROR (opt-in --core-shape-index) + core_shape_exceptions schema
  - 300587e0f5 11-12 03:09 KIT-OVERLAY-1: kit_wave item_inputs type_overlay + type_positions overlay key
  - 368131ef80 11-12 03:01 KIT-OVERLAY-1: per-type positions-only overlay (type_overlay.py, gen phys --type-overlay, typed validation scope)
  - 67cfe043c5 11-12 02:23 CPL-HBM-B1: d6d street-widened positions event for q_b010/q_b011 (+pv1) against t19
  - ba88610f5d 11-12 02:20 path_respace: re-check real normal-input S0->S1 on every moved normal slot (rejects the lane, no new G0 stations error)
  - cd800b3ed2 11-12 02:18 S81-LEAF-CYC quad2 composer stage for DIE-S81-87 ready8 (on the current layout)
  - 6a3ac7073c 11-12 02:18 QC q01 NK quads S2: plan_qc99_s23_nkl, left-column NK tiles R0 -> MY; t22 MY trial measured
  - 0d73dc057e 11-12 02:12 SEAM-HOP-1: path_respace stage script (IN OUT REPORT, declared keys, sidecar passthrough/republish) + rebank proposal
  - 7c501990c2 11-12 02:11 HEAD hd_ctl setup form: status relay on lepk_i0 -> lepk_o0 (TT -88 cland fault collector path)
  - ce27841937 11-12 02:06 SEAM-HOP-1: face-register fix, collector_reach G0 ERROR, path_respace one-pass station respacing, seam hop renderer
  - 4f05a8240f 11-12 01:59 FREG-DECL-1: declare the FREG cycle in the ring_wreg test fixtures; strap K + 2 asserted
  - 8af99c3857 11-12 01:58 S81-LEAF-CYC quad2 plan delta: 71 non-KV ot_s81sl_leaf types (lane permutation + 2-stage quad sites)
  - 6986f44fe9 11-12 01:45 G0 advisory seam-hop check (SEAM-HOP-1): last station -> first station across each seam, WARN over 405 um
  - cb54a72e65 11-12 01:41 QC NK quads S2: plan_qc99_s22_nkr0, right-column NK/NL tiles MY -> R0 (data pins to the middle channel)
  - 63676d718d 11-12 01:40 S81-LEAF-CYC quad2: two shared hi/ho stations per lane quad (CS_HI/HO D2 GS2 G4)
  - d7abde7747 11-12 01:31 HBM next-event plan d49a_io_reform_1111: t19 + DIE-LAYOUT-HBM NW_io/NE_io re-form (plan e9ae418c06ca, strict bind OK, G0 554 -> 554)
  - 7dd83f04a2 11-12 01:17 CLAND-WSTART-1: anchor writer START relay chains at the origin home when relocating around hard cores
  - 1e6d71e1cc 11-12 01:14 HEAD FREG marking event: freg declared on 18 count-aligned ports, +1 raised on hd_ctl_n x2 and hd_turn_a x12
  - 1637f6ae93 11-12 01:11 DIE-LAYOUT-HBM io re-form: NW_io/NE_io cut to logic height + NW_iorly/NE_iorly relay columns (t19 delta)
  - fc99961086 11-12 01:10 bind: core_input_lockup pipe_except -- ports that keep the latch without the pipe (NK rst_n)
  - ef585c8b2f 11-12 01:03 gen_core_kit_hbm: opt-in --grt-nonport-hold (shared nonport hold adapter after the kit PRE_GLOBAL_ROUTE_TCL); absent = byte-identical
  - fe846c4a58 11-12 00:50 kit_wave: a retry entry absent from the config forgets its first-seen time, so remove + re-add re-arms it (retry epoch)
  - 443adc0829 11-12 00:49 core_input_place: chain spread at PRE_RESIZE; keep the first stage after a core output
  - d95f7cc25e 11-12 00:49 gen_phys: core_input_place hooks for the QC NK A+P form (anchor + chain spread)
  - 63ee76574e 11-12 00:49 bind: core_input_lockup pipe -- +D declared register stages before the NK lockup latch (QC NK A+P form)
  - 1ece4481e7 11-12 00:48 FREG-DECL-1: fail closed on an undeclared FREG data cycle (count-aligned rings)
  - 2d5e254595 11-12 00:42 CLAND-QREG-1: landing ring read-leg +1 pipeline cycle (QREG output stage), class opt-in
  - e3fa343ee8 11-12 00:37 kit_wave: follow_queue turns a CANCELLED queue job into a CANCELLED (class QUEUE-CANCELLED), retry-eligible wave row
  - fa29bae4b9 11-12 00:37 HEAD hd_host_w TX_STAGE: one register stage on host276 h_rx_o (a3 TT -76 retime) + host_rx lane +1
  - a6f7097695 11-12 00:36 gen_phys: opt-in OT_GRT_NONPORT_HOLD=1 chains tools/grt_nonport_hold.tcl at the end of the kit PRE_GLOBAL_ROUTE_TCL; absent = byte-identical
  - 86cebb38d2 11-11 16:35 gen_core_kit_hbm: opt-in --pre-gpl-extra FILE (extra PRE_GLOBAL_PLACE hook after face_flops.tcl)
  - 225791101e 11-11 16:30 IDX ack/end windows follow the rd1 response shift; windowed tests; identity vs base
  - 882687e50e 11-11 16:29 Compiler: default-off rd1 hub response calendar shift (shift_response, --rd1-resp-shift, IDX wired) with hub bench
  - 272b543931 11-12 00:23 geom_rules: outputs listed in a kit spare_out.json are not unregistered pins (pin_reg_metrics spare=, --spare-out, geom_check.sh passes it)
  - c59dcc5c63 11-11 16:20 ot-run --cancel-dir: write the record as ONE line (a multi-line parent command split it and signals_cancel never matched); test with a heredoc parent
  - 36bd5fa243 11-12 00:20 QC NK output class: core_out_land plan opt-in + plan_qc99_s21_nkout
  - db302c9bdf 11-12 00:19 S81 as-built BF bench with bound-plan seam stages; re-measured col_h9_asb_x/nx, col_h10_asb_x |E2|bseg1024
  - c9a64c107c 11-12 00:00 HBM rd1 bind-side +1: cover VM share b_rr clients (COLL gq issue VM_RT)
  - 141d1cbc80 11-11 15:59 ot-run --cancel-dir KIT_PATH: end the autopilot record of a job whose client is already dead
- (c) split: LOCAL-EDIT 2, UNMERGED-BRANCH 2

(a) snapshot-only: 0

(a2) in base, deleted on main: 0

(b) differing, snapshot == base blob (main fixed since): 156
  - physical/die_plan/hbm/bind/hbm_param_regen.py
  - physical/die_plan/hbm_arch_cores/core_tap_align.tcl
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_cap5_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_cap5r_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_k8_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c1x_lp.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c3x.sv
  - physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_c3x_lp.sv
  - rtl/common/ot_dp_clk_landing.sv
  - rtl/common/ot_dp_clk_landing_ca.sv
  - rtl/dsrom_sys/s81_dv/frame/col_h10.sv
  - rtl/dsrom_sys/s81_dv/frame/col_h9.sv
  - rtl/dsrom_sys/s81_dv/frame_l4/col_h10_l4.sv
  - rtl/dsrom_sys/s81_dv/frame_l4/col_h10_l4_nx.sv
  - rtl/dsrom_sys/s81_dv/frame_l4/col_h9_l4.sv
  - rtl/dsrom_sys/s81_dv/frame_l4/col_h9_l4_nx.sv
  - rtl/dsrom_sys/s81_dv/frame_l4/frame_l4.json
  - rtl/dsrom_sys/s81_dv/frame_lp/col_h10_l4_lp.sv
  - rtl/dsrom_sys/s81_dv/frame_lp/col_h10_l4_lp_rf3r.sv

(b2) added on main after base, absent in snapshot: 503
  - physical/die_plan/hbm/bind/subtype/ot_hgi_sfu_split3_lane_core__idpin__bsub.sv
  - physical/die_plan/hbm/bind/subtype/run/bind_subtype.sh
  - physical/die_plan/hbm/bind/subtype/run/hook_subtype.py
  - physical/die_plan/hbm/bind/subtype/run/prep_sub_lec.py
  - physical/die_plan/hbm/bind/subtype/run/run_sub_lec.sh
  - physical/die_plan/hbm/bind/subtype/run/wire_all.sh
  - physical/die_plan/hbm/bind/subtype/tkm_full/run.sh
  - physical/die_plan/hbm/bind/subtype/tkm_full/tb_tkm_root_full.sv
  - physical/die_plan/hbm/cpl_hbm_b1_1111/deltas/d6c_hcol_s2_cplb1_1111.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/deltas/d6d_hcol_s2_cplb1_1111.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4.cut.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4.stscan.tsv
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4apply.classify.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/c4apply.log
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/cells_post_ladder.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/cut_budget_t19_vs_c4.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/cut_budget_t19_vs_d6d.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d.cut.json
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d.g0cmp.txt
  - physical/die_plan/hbm/cpl_hbm_b1_1111/gates/d6d.stscan.tsv

(c) differing from base and main (local patch): 4
  - physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py  <= LOCAL-EDIT no matching commit in origin
  - physical/die_plan/hbm_arch_cores/recipes_b2.json  <= UNMERGED-BRANCH 98823e93c3 11-11 21:50 KW-FIX-45: HBM opsb_group private src (fe0002fac6 + 5 named files of [origin/claude/kw-fix-45-hbm-opsg-comp-1111]
  - physical/die_plan/hbm_arch_cores/run_kit_hbm.sh  <= UNMERGED-BRANCH 2713b2eb62 11-12 03:55 hbm core kits: honour OT_GRT_TRANSITION_MODE (K/grt_transition_mode  [origin/claude/kw-fix-45-core-grtm-1111]
  - tools/die_plan/gen_phys.py  <= LOCAL-EDIT no matching commit in origin

