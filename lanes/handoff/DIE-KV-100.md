# DIE-KV-100 handoff (KV qwen_kvsys die owner; successor of DIE-KV-99 / KV-VN2-FIN) -- 2026-11-13 03:28 PST
## Scope (COORD brief 11-13 + owner directive 03:4x)
1. train-34 check: regenerate kv3_hub_Eo / kv3_hub_Wo kits PRIVATELY from current main and measure the cland_origin fanout/reach (GEOM-VIS-13 BAD 03:08).
2. cland_origin fanout fix + kv3_sys_c ROM register stage: apply EXACTLY the RULEBOOK R-REACH rule (RULES-REACH-1, ~/coord/lanes/RULEBOOK-1113.md) once posted; RULES-REACH-1 uses kv3_hub_Eo as a proof kit -> coordinate, no duplicate builds.
3. kv3_sys_SD: SD-GROW outline (as kv3_sys_SD_v1, E strip ~149 um).
4. reset relay collapse (hub_Eo 272 / hub_Wo 198): check vs RELAY-PLACE-1 FT-LANE class (train 36).
5. One KV event branch off origin main, READY; adoption after the 48 h freeze (11-15 04:00). Stop after READY.
## Worktree
- epyc7 /srv/opentallas-scratch2/claude/wt/die-kv-100 (blobless clone of hub, sparse minus physical/ref_tile, results/roofline, results/uarch). Clone in progress at 2026-11-13 03:28.
## Findings so far
- train 34 (CLAND-RELAY-3) reach default = ONE reader-START relay per WIDE soft ring at the ring's own reset-relay site (clock_landings.reader_start_reach). It cuts origin fanout but NOT the origin->relay distance (one flop hop, up to ~2 mm on hub_Eo). Narrow rings still take cland_start straight. Expectation: does not fix; to be measured on a private place.
- Explicit plan form clock.landing_reader_start {depth, branches{bus:{stages:[{xy_um,raw_reset}]}}} already exists (K - depth, boot + depth, data exact): a candidate carrier for relays <= 405 um, pending R-REACH.
- Baseline hub_Eo a1 geom copy: localhost scratchpad base_Eo/ (r2r_max 2381.5, 3869 > 405, relay_collapsed 272).
- private kit recipe: kit_wave.py run-item with a private spec/job dir (VISLAYOUT3-KVHEAD pattern; needs future_lec/ in the job dir, plan on gen host).
## Running jobs
- none yet (clone only).
## Next
- clone done -> strict bind of plan_of_record with current main tools (model epyc8 dkv99/bind_e.sh) -> private run-item hub_Eo + hub_Wo -> view place -> post RESULT.
## UPDATE 2026-11-13 04:01
- Worktree epyc7 /srv/opentallas-scratch2/claude/wt/die-kv-100 (shallow depth-20 clone), branch claude/kv100-event-1113 @ origin/main 055e36edab (train 36 FT-LANE merged). Work dir epyc7 /srv/opentallas-scratch2/claude/dkv100 (scripts there); intel2 /srv/opentallas-scratch2/claude/dkv100/jobs (run-item specs); logs intel2 ~/dkv100log.
- BASELINE CLASSIFICATION (a1/a2 geom.tsv, classifier epyc8 /srv/opentallas-scratch2/claude/dkv100_chainclass.py = geom_rules relay/r2r by name class):
  hub_Eo r2r>405 3869: cland_origin->ring 3206 (2317 >900), datapath 400, ring->bin 168, rrl_150->fstart 35, origin->fstart 30, rrl->bin 23.
  hub_Wo 4328: origin->ring 3837 (3081 >900), datapath 323, ring->bin 70, origin->fstart 35, rrl_216->fstart 30, rrl->bin 24.
  relay_collapsed (272 Eo / 198 Wo) is NOT reset relays: Eo 147 ring->bin + 124 seq fan->bout; Wo 196 seq fan->bout. The 'reset collapse' items are the origin's raw-reset relay (rrl_150/rrl_216) -> fstart face flops/origin at 1.2-2.4 mm = same cland_origin locality family.
  sys_c a2 7316: d2d_kv datapath 5693 (4418 >900), reset_regions rst_n 766, ring->bin 656, reader_start->ring 174 (<=522), rrl->bin 22.
- Running: strict bind m055 (ot-run epyc7, dkv100/bind_m055, log intel2 ~/dkv100log/bind_m055.log) -> then run-item jobs m055_kv3_hub_Eo / m055_kv3_hub_Wo (python3 /srv/opentallas-scratch2/claude/kw38/rt/tools/autopilot/kit_wave.py run-item SPEC on intel2).
- SD-GROW-W plan: dkv100/sdgrow/p3.json = sys_SD +103.68 at cut 1855.44 (as _v1) + kv3_io_ft (io_W2 only, pure E/W ft, no N/S ports) shrunk -64.746 at 280.8 and -38.934 at 961.254 (empty bands, site-aligned), io_W2 origin +103.68 -> no die growth, no port window change. sidecar RC 0; G0 running (sd_g0.sh).
- R-REACH not yet in RULEBOOK at this time; no cland_origin / sys_c fix built.
## UPDATE 2026-11-13 04:31
- COORD 04:2x: R-CAP folds into the KV event: hub_Eo/Wo 2-way, kv3_pv family (16 plan types incl. v1n-v6n) 3-way (pv, v8 2-way). ACK posted 04:16.
- Sub-agent KV-SPLIT-1 (Claude background agent of this session) is writing the N-way type split tool (tools/die_plan/type_split.py, physical/die_plan/qwen_kvsys/split_1113/; work dir epyc7 dkv100/split) and applying it to the hubs -> G0 + strict bind RC 0. It does not commit; DIE-KV-100 commits.
- Strict bind m055 RC 0 (epyc7 dkv100/bind_m055/out). Run-items m055_kv3_hub_Eo/Wo running (intel2 dkv100/jobs/m055_*/unit.log; kits epyc7 dkv100/pilots_m055/items/*).
- SD-GROW-W v2: grow 77.76 (not 103.68: io_ft tap grid nx=ceil(W/400) must stay 4 -> W >= 1200.06). Plan dkv100/sdgrow/plan (p3.json md5 b2909a63). Base G0 PASS 0 errors; new G0 running; diff with dkv100/g0_slot.py.
- census_map_v35.json added to the tree (missing on main; copy of epyc4 /dev/shm, md5 d2157225).
## UPDATE 2026-11-13 05:10
- COORD 04:5x APPROVED pv cut (A): 4-way per lane group for 14 members, 2-way middle cut for kv3_pv/v8. R-REACH posted 04:48 (claude/rules-reach-1-1113@1376d26613); 2nd worktree epyc7 wt/die-kv-100-rr on that branch (tools only).
- Hub split: KV-SPLIT-1 found the 2-way cut (forced y 846.72) leaves Wo S at ~338k (279-397k): DECIDED 3-way family cut [c1, 846.72] for Eo+Wo (cycles pre-approved). Agent continues (type_split.py draft in tree, untracked).
- SD: bind_sdg FAILED RC1 'kv3_io_ft raw Q rst_rl_63' (shrink renumbered reset relays) -> street_rule.py resetfix -> sdgrow/p3r.json md5 5de1af02 (2 types, 5 refs reselected); rerun sidecar+G0+bind_sdg2 via ot-run (intel2 ~/dkv100log/sd_g0r.log).
- sys_c R-REACH-2: dkv100/sysc/sysc_form.py: reach_homes d2d_phyN [959.04,859.68,2142.72,1019.52] (PHY pins all on its N face die x 968-1417) + dcal home; 4 d2d link SRAMs moved SW corner -> x 1615.68 y 518.4-777.6 (E of PHY). First try at x 1494.72 hit added tap clk_t13 halo. rr.sh = reach fix 1,2,4 + check (p5).
- hub_C R-REACH-2 (ahub 605 um, 260 loose buses): sub-agent KV-HUBC-REACH writing dkv100/hubc/hubc_form.py (homes + leafs).
- Event compose order: p3r (SD) -> sysc_form -> hubc_form -> type_split (hubs 3-way, pv 4/2-way) -> reach_rules fix 1,2,4 -> resetfix/raw step -> sidecar -> G0 -> strict bind -> lane latency.
