# KIT-SNAP-1 handoff -> KIT-FIX-F (Fable). 2026-11-13 17:4x PST. STOPPED on COORD/OWNER order.

No code edits were made. No branch was pushed. Nothing is running. No shared file was touched.
Worktree (clean clone, no commits): epyc8 /srv/opentallas-scratch3/claude/kit-snap-1, branch kit-snap-1 = origin/main 28cf407973.
The successor may reuse it or delete it. It was created by KIT-SNAP-1.

## Data
intel2 ~/coord/autopilot/log.txt, lines dated 2026-11-10..13 that contain KIT_NOT_SELF_CONTAINED or "bind".
Local extract: localhost scratchpad kitlog.txt (2108 lines) and bf.txt (348 non-KNSC KIT-WAVE FAIL lines with "bind").

## 448 KIT_NOT_SELF_CONTAINED (all classified by kit_wave.py kit_not_self_contained, the FLOW rule near line 1417)
- 419 (94%) @bind: <bind_out>/bind_report.json is outside the kit. Every one is on 11-12 between 04:14 and 06:18, in 7 tick bursts, on 224 distinct items:
  s81 202 (s87bind/out_r11p2), qwen_compute 207 (kw45/qcs28in/bind_plan_qc99_s28 116, qc-s28a 78), qwen_kvsys 20 (dkv98/bind_vF2 10), hbm 15 (hbm-vsn-xtap-t39w 13).
  This is one detector rollout burst against bind-of-record dirs that did not exist on the gen host. KW-FIX-45/KW-SELFCONT-2 (the kit_wave.py bind_fetch rsync of bind_out from another die host, <= 4 GB) followed it. There have been 0 hits since 11-12 06:18. It is a host-gap class, not 419 separate faults.
- 29 others: @kit_rtl 11 (HEAD kit-ops-1/head_rp18r2/prep/assets/sink_bins_4.json x4, which is still live on 11-13 13:47 for hd_spn_wshim_rx and hd_turn_a; die_plan.json x2; dkv98/bind_vF2/rtl/*.sv x2; QC slw_stm / qfd_c_stn .sv); @gen 11 (common_flow failfast_rules.py x7, face_guard.json x3, a kv composed .sv); @kit_topology 3 (sidecar_pv.json, eW_sidecar.json, kw32 sidecar). There are also 6 WAIT-FORM hold lines that only mention the class.

## 229 bind failures (my count: 227 non-KNSC FAIL lines naming bind, plus 116 topology rows listed separately)
- 166 (73%) "kit-RTL bind of record names HDL sources that are gone (pruned bind worktree)", @kit_rtl "bind: ERROR preferred HDL source missing", on 93 items: qwen_compute 123, qwen_kvsys 41, hbm 2. The missing source roots were:
  qc-vis-resite/srcs27 123, kw32/src_27db6 23, kw45/src_kv_main_66e6607e3f 15 (the epyc4 kw45 swap self-symlink loss), kv-types-6/pv 2, hbm-bind-6/tip2 2, kv-plan-2/src_zbr 1.
  The cause is source trees deleted under live binds (cleanup / swap loss). KIT-STAGE-1 (b286608a85) now keeps them transitively in ot-autoclean.
- 14 per-instance LOGIC param split (PLAN, not tooling). 11 param_wrap clock-landing kit-rtl errors (cbn_q*, slw_su_l*; tool). 9 ssh transport INFRA @bind.
- 7 "ModuleNotFoundError: No module named 'bind_elab'" @kit_rtl, on kv3_hub_C, kv3_hub_Eo, kv3_pc__cl254f2e73, kv3_pc_v3, kv3_phy, kv3_phy_v1 and kv3_sys_c. The src tree on the host was incomplete or old.
- 6 die-prep bind recipe input missing: qc-transport-fix-4/sw2/bind2/bind_report.json.
- 4 `include ... .svh not found next to the including file` (s81 serdes__t2/t13/t15). The kit copy dropped an include sibling.
- A few singles: kit_store MISSING plan, no partition type in plan (hbm x2), gen filelist names missing files.
- Separate PLAN class: 116 KIT_TOPOLOGY_BIND_STALE @kit_topology on 99 items (qc 62, s81 40, kv 12, hbm 2). These are stale canonical binds against the plan, not missing files. They need regeneration, which a snapshot does not fix.

## Host / prov_view gaps
- 1109 "KIT-WAVE SRC-INCOMPLETE <host> <die>" probe lines on 11-10..13. The top ones are epyc2 hbm 189, epyc7 s81 140, epyc7 qc 98, intel1 hbm 92, epyc2 s81 91 and epyc9 s81 90. The latest (17:36 today) is epyc2 hbm, where die-hbm-95/bind/composed_rtl/*.sv is missing. Inputs live on a subset of hosts, so the gen host choice shrinks and items fail when they land on a gap host.
- prov_views: about 50 log lines. FAILs: "no provisional abstract for a child" (hbm q_hub_ne / q_su01, qc slw_su_c / sle_su_c) is PLAN, not tooling. "prov_view.py crashed FileNotFoundError" (s81 gunit__t1, kv3_pc_v1/v3 x4) is tooling.

## Code locations (origin/main 28cf407973; runtime intel2 /srv/opentallas-scratch2/claude/kw38/rt, kit_wave.py 8642 lines, differs from main only by the R-CAP PLAN rule)
- tools/autopilot/kit_store.py: KIT-INPUT-STORE-1. A per-host CAS blob store (<scratch>/kit-store/blobs/<sha>), snapshot into W/kit_inputs at LAUNCH on the gen host, localize-filelist, gc.
- kit_wave.py: KS_PATH / ks_cmd / kit_store_on (option kit_store, die > global, list = fnmatch pilot) / kit_store_applies / ks_inputs / ks_map / kit_store_stage (around lines 4735-4830). Staging is in the per-item stage around lines 4370-4480: bind_fetch (KW-SELFCONT-2), bind check, kit_rtl, kit_store_fl. prov_stage is used for prov_first. The KNSC classifier is around 201 and 1415. SRC-INCOMPLETE gen-host probe is around 2364-2400 and 2894. HOST_GAP_WHY is around 6317. Retry cap (KIT-STAGE-1) is around 3500.
- bind source universe: tools/die_plan/bind.py plan_base (asbuilt.base, else plan dir, else E.REPO); bind_elab.plan_sources (rtl_roots dirs + files + netlist + prefer + map_file under base); validate_preferred_files gives "preferred HDL source missing"; manifest_paths.required_prefer_files.
- kit_wave.json (intel2 ~/coord/autopilot): kit_store is enabled only for s81 ['ot_s81sl_leaf__t42*']. The KV pilot was removed (kit_store_prev_kitstage1_1113 = ['kv3_pv*']) because the kv3_pv x15 kit_rtl failed when asbuilt was mapped into kit_inputs while its base-relative rtl/ files were not.

## Gaps in the current design (what I was about to build)
1. The snapshot is made at launch, on the gen host, from whatever that host has, so missing inputs surface late and host-dependently. It should move to enqueue, on a host that holds the inputs, and fail fast there.
2. It is not named by content. The kit_inputs dir is per attempt. The proposal is <snap_root>/<sha256(sorted orig->sha)>/root/<abs path> plus MANIFEST.json. Launch rsyncs it to G when G lacks <snap>/.verified, then verifies sha256 and remaps the spec with ks_map, so gen and bind read only the snapshot. Rollback is a flag (kit_snap option off = today's path, byte-identical).
3. The closure must include the bind source universe for an asbuilt: base/rtl_roots dirs, files, netlist, prefer, map_file, and `include siblings (.svh). Without these, the asbuilt cannot move (the KIT-STAGE-1 kv3_pv failure). It must also include bind_out fully, prov views, sidecars, common_flow failfast_rules.py / face_guard.json, and HEAD prep/assets. The tools/ tree (bind_elab missing) should come from a pinned src_sha checkout, verified at launch.
4. Pilot items suggested: qwen_kvsys/kv3_pv_v8 (gone kw45 src), an s81 leaf with outside entries (ot_s81sl_leaf__t70, s87bind), and s81_head/hd_turn_a (sink_bins_4.json).
