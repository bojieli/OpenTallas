# DIE-KV-99 handoff (KV qwen_kvsys die owner) -- updated 2026-11-12 15:50 PST
## 1 Scope
KV vN2 hand-floorplan event + vN re-issue. Items: 1 census DONE, 2 pg rects DONE, 3 hgi_EN_0 cut DONE, 4 hroot aspect exception (no edit), 5 21-type merge DROPPED (not exact; tool item), 6 REACH-FIX taps (cap 1200, hgi_v8 39) DONE in pipeline / insertion balance = die_clock stage by REACH-FIX-2 (KV PHY last-mile fix in progress there), 7 hg+hgi W street DONE, 8 sys_c stations DONE (PHY exemption ASK open), 9 drawing draft 2 posted (GEOM-VIS-6 FORM GOOD + 5 conditions), GEOM-VIS-6 cond 5 phy re-face DONE (option B).
## 2 Worktrees (epyc8 repo /srv/opentallas-scratch2/claude/wt/die-kv-98 = SPARSE, never bind from it)
- wt/die-kv-99: branch claude/kv99-vn2tools-1112 @8ddec99ab4 = origin/main 26c9ae03a4 + CORE-OBS-COV merge (local, unpushed; tools tree only).
- wt/die-kv-99-obs: claude/kv99-coreobs-cov-1112 @35f5d50a19 (pushed, READY 12:10).
- wt/die-kv-99-vn: claude/kv-vn-event-1112b @91e563ee2bc5 (pushed, READY 12:10); intel1 wt/die-kv-99-vnfull = near-full checkout of it.
- wt/die-kv-99-cb: claude/kv99-cleanbind-1112 near-full checkout (sparse '/*' minus physical/ref_tile, results/roofline, results/uarch) for binds.
- coord posting: hub ~/coord push is blocked by someone's dirty CODEX-HANDOFF.md; I post via a detached worktree of the hub repo: /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/coordwt (fetch, merge origin/coord/state, append, commit, push HEAD:coord/state, retry).
## 3 Running jobs
- epyc4: nohup bash /srv/opentallas-scratch2/claude/dkv99/resite_e.sh (log resite_e.out; steps in dkv99/vN2e/work/steps.log): vN2c+phyface -> band_fit -> reach_fix fix -> street_rule resetfix -> sidecar -> G0 (g0_vN2e, diff vs g0_vN2obs in work/g0_slot.txt). Tools /dev/shm/dkv99/m2 (main 26c9ae03a4 + CORE-OBS-COV; physical -> /dev/shm/dkv99/main/physical). ~75 min from 12:20.
## 4 Watchers
none persistent.
## 5 Results (all posted 12:10 unless noted)
- vN re-issue bind RC 0 (intel1 dkv99/vnre_i1). CORE-OBS-COV: KV vN2 G0 27 -> 0 (dkv99/g0_vN2obs). QC second-die G0 pair NOT done (re-run: G0 a QC plan with /dev/shm/dkv99/main vs /dev/shm/dkv99/m2, list relaxed cuts, add to the READY).
- vN2 base full-checkout bind RC 0 (epyc8 dkv99/cleanbind/bind_vN2.run).
- vN2d (epyc4 dkv99/vN2d md5 8bd48608) = superseded by vN2e (adds phy re-face).
- phy re-face plan epyc4 dkv99/phyface/plan/plan_c.json md5 3bafb79c (on vN2c).
## 6 Next steps
1. When vN2e steps.log shows DONE: work/g0_slot.txt must show 0 NEW (rule: any NEW -> fix by class, else go on). Hop check <= 405.
2. Strict bind of vN2e from full checkout wt/die-kv-99-cb with an overlay plan_of_record (cp -al tree, replace plan_c.json + eW_sidecar.json), model epyc8 dkv99/cleanbind scripts; via ot-run. RC 0 required.
3. Package: tools/die_plan/plan_package.py package+verify+check; branch claude/kv-vn2-event-1112 off main with plan_of_record = vN2e package; .gz any input > 95 MB; git ls-tree size check; push; READY to ROOT-MERGE-60 + plan event to KW-FIX-46 (repoint KV rows; OT_CLAND_STRIP_DENS=1.0 on 11 hgi rows; kv3_sys_SD_v1 uses SD-GROW).
4. Re-run drawing: cd /dev/shm/dkv99/main && python3 -P /srv/opentallas-scratch2/claude/dkv99/draw/draw_vN2.py PLAN OUTDIR; post to lanes/kv-vn2-1112 for GEOM-VIS-7.
5. hg/hgi build only after GEOM-VIS-7 verdict.
## 7 Open READY/ASK
- READY claude/kv-vn-event-1112b@91e563ee2bc5 (ROOT-MERGE-60). READY claude/kv99-coreobs-cov-1112@35f5d50a19 (ROOT-MERGE-60; QC list pending). taps fix ae71bf887a already on main.
- ASK COORD: PHY station checker exemption (prototype epyc4 dkv99/phystn/patch_streets.py) vs pc-side reroute (+1-2 boot cycles).
- KW-FIX-46: point kv3_sys_SD_v1 row at SD-GROW A kit (epyc8 vislayout3-kvhead/pilots_kv3_sys_SD_v1_grow).
## 8 Gotchas
- epyc8 wt/die-kv-98 and its child worktrees are sparse by default: check `git config core.sparseCheckout` before any bind.
- epyc4 sshd drops connections: retry on rc 255.
- G0 needs ../census next to each plan dir (ln -s dkv98/census).
- vN2 plan kv3_head_eighth_e2 lef is an absolute /srv path: fix in packaging.
## UPDATE 12:45
- COORD 12:4x: READY vN re-issue + CORE-OBS-COV approved to merge lane. Hub is clean: post via bash ~/coord/bin/coord-commit.sh on intel2 (coordwt workaround retired).
- PHY station exemption APPROVED (stations inside a signed PHY hard core only): branch claude/kv99-phystn-exempt-1112@95c4103509 pushed + READY; patched into epyc4 /dev/shm/dkv99/m2 check.py (pre-patch copy /dev/shm/dkv99/check_m2_pre.py) so vN2e G0 uses it.
- Item 5 merge DROPPED from vN2; re-propose as own event after vN2 types sign off.
- Bind tree for vN2e must carry REACH-FIX-2 keys (main 26c9ae03a4 has them) + core_obs + phystn branches (checker only; bind does not depend on them).
## UPDATE 13:35
- vN2e run 1 G0 = 7 errors (see queue 13:35). Run 2 RUNNING on epyc4: nohup bash /srv/opentallas-scratch2/claude/dkv99/resite_e2.sh (steps in vN2e/work/steps2.log; result G0 dkv99/g0_vN2e2, diff work/g0_slot2.txt). Inputs: work/p1b.json (p1 minus 8 stale bit_sites + ft_sites_unblock); work/ now has symlinks to all plan side dirs (pins/ etc.) -- REQUIRED or reach_fix silently skips the hg family.
- lat_sync helper: /srv/opentallas-scratch2/claude/dkv99/lat_sync.py (latency.lanes cycles := plan for changed lanes only).
- If run 2 G0 shows NEW errors: fix by class; else strict bind (wt/die-kv-99-cb overlay) -> package -> READY.
## UPDATE 13:40
- RUN 3 = event candidate: epyc4 nohup bash /srv/opentallas-scratch2/claude/dkv99/resite_f.sh (tools /dev/shm/dkv99/m3 = main 59f6e46846 + coreobs + phystn + REACH-FIX-2 54d2a1ec4b fixed_cycles; steps vN2f/work/steps3.log; plan vN2f/plan_c.json; G0 dkv99/g0_vN2f; diff vN2f/work/g0_slot3.txt). Run 2 (vN2e, lat_sync) is a cross-check only.
- Bind/package tree: epyc8 /srv/opentallas-scratch2/claude/wt/die-kv-99-e (branch claude/kv-vn2-event-1112 at main 59f6e46846, near-full sparse). Overlay vN2f plan_c.json + eW_sidecar.json into physical/die_plan/qwen_kvsys/plan_of_record, strict bind (model: epyc8 dkv99/cleanbind/bind_vN.sh, asbuilt from inputs/bind9_asbuilt.json.gz), then plan_package.py, commit, push, READY + plan event (say which latency refresh was used).
- If 54d2a1ec4b changes in train 11: re-run run 3 on the merged main.
## UPDATE 13:50
- Tool basis = main d0dc0b5307f2 (train 11; m3 tools/die_plan identical). wt/die-kv-99-e ff to d0dc0b5307f2. Before posting: vN2f/work/reach_event2.json rows must have 0 per-type error (train 12 fail-loud exits 3 on any).
## UPDATE 15:05
- Event candidate now vN2g: epyc4 nohup bash /srv/opentallas-scratch2/claude/dkv99/resite_g.sh (reach_fix --cap 1200 on 15 residue types from vN2f/work/q6.json; steps vN2g/work/steps.log; G0 dkv99/g0_vN2g). vN2f/work/q6.json = run3 + drop_cell + ft_nudge(ft27) + kv3_hgi_v5 ft1 reg5 -7.236 um (L2259).
- Bind must wait for train 14 main (4b6dee512d57) and set asbuilt kit_source_station_pricing: true (asbuilt_vN.json in plan_of_record); refresh kv3_pc_v1 lanes table from the bind (DOUBLE-PAD 13:5x).
- Event open list: hub_Eo/Wo internal hops 420/409 um; any type not reaching cap 1200 under radius.
## UPDATE 15:10
- wt/die-kv-99-e at main 614ab4a0dac0 (train 14). Bind script epyc8 /srv/opentallas-scratch2/claude/dkv99/bind_e.sh TAG PLAN SIDECAR (copies plan+sidecar into plan_of_record, sets asbuilt kit_source_station_pricing true, strict bind -> dkv99/bind_TAG/bind.run). Trial: bind_vN2f running. Tools 614ab on epyc4 /dev/shm/dkv99/m4 for the final G0.
- If bind shows KIT_ISTATION_LATENCY on pc_v1 lanes: refresh those lanes table (lat_sync to plan lane_latency or gen.py latency) and rebind.
## UPDATE 15:50
- R8: bind tree plan_of_record/r8_kv95_phy3.json = main copy rebased on 12 members of the 6 +1 lanes (epyc8 dkv99/r8_lanelog.py OLD_lat NEW_lat -> r8_rebase.py; report dkv99/r8_rebase_vN2f.rep.json). L2245/L2349 landed +1 (COORD: pre-approved). For vN2g: rerun r8_lanelog vs cleanbind/bind_vN2/bind_latency.json on the vN2g bind latency and rebase from the MAIN copy (dkv99/r8_main.json).
- Trial binds: flag-on try3 dkv99/bind_vN2f (running); flag-off to run after it (asbuilt_vN_flagoff.json in plan_of_record = TEMP, delete before package; inputs/composed_rtl/ = bind output, do not commit).
- AFTER vN2 (COORD 15:4x class items): (1) reach_fix fixed_cycles also rebases the R8 landing table (r8_rebase logic as a main tool); (2) bind R8_STALE reports all stale groups in one pass. Branch + tests after posting, or hand to REACH-FIX-2 in the event open list.
