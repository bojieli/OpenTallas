# FABLE-FIX-CONE-SCATTER handoff (Opus 5.5 for Fable; COORD launch 11-22 09:4x). Owns class LOCAL-CONE-SCATTER + its tool.
Lane dirs: intel2 /srv/opentallas-scratch2/claude/fable-fix-cone-scatter (clone/ = ot-lane-clone of main 7564be45ae; tmp/), epyc2 same path q/ (cone_dump.tcl, run_cd.sh).

## Findings so far (10:xx)
- The plan ALREADY HAS placement-group fields (COORD note "no field" is stale):
  * partition_types.<t>.place_regions [{name, inst_re, util, centre_um | near_re}] -> gen_phys install_place_regions -> place_regions.tcl
    (PRE_GLOBAL_PLACE, dbRegion+PHYSICAL_CLUSTER group; cone auto-extend when members < 0.5 of cone; DROP when cone > 8x members).
    S81-DIE-R5 kit-patch made it GPL-only (released before DPL) on serdes (DPL-0033) -- check whether that is on main.
  * partition_types.<t>.placement_guides [{inst, bbox_um, kind soft_region}] -> region_guide.py from-plan (kit_wave) -> soft GPL guide.
- Census source: ~/coord/autopilot/jobs/*/a*.log stop lines with path_um/span_um (format since ~11-21). Script: scratchpad census.py.
  48h: 42 distinct stop paths, 6 match signature (span<=200, path>=1000, wns<=-150):
  leaf t45 -663 (hi_sw->wdo_q), leaf t31 -503 (hi_sw->wdo_q), leaf t1 -348 (sw_a_q->wmw_q), dsdv nh_mus_C t1 -679 (xf driver flt_q self loop, 26 st),
  dsdv lepw_mus_LP t2 -347 (count_r[1]->count_r[5], 19 st), KV kv3_pc_v3 -1045 (idpc bin q -> u_kvpc1 core pin, span 10, 30 st). QC/HEAD: none.
- t1 kit (epyc2 kw43 .../18a2688b741/items/ot_s81sl_leaf__t1/gen/...) already has s81_vpw_bank.tcl (XR flops at banks, FIRM).
  End wmw_q is the b_dec (priority write decode) output reg; cone dump running (epyc2 q/t1_ctl.tsv).

## 10:2x update
- COORD scope change 10:0x: NO leaf t1 proof (LEAF-R10 owns XR decode fix, main d4aeaa3c6b58). Proof type from census outside leaf XR:
  chosen dsdv_slice_lepw_mus_LP__t2 (counter count_r; family owner FAM-S81-DSDV-R1, ASK posted 10:1x, launch if no OBJECT in 30 min).
- Tool commit 1 ddf3601771 (clone): place_regions kind fence|soft (place_regions_release.tcl before DPL), box_um, radius_um; precheck long row; schema+json. ot-push-main running (bg).
- Tool commit 2 (uncommitted at 10:2x): type_overlay.py accepts top key "place_regions" (kit-only, no rebind) -> private-spec --overlay route for the proof. Tests pass (test_type_overlay 29, test_place_regions 25).
- lepw t2 J7 place ODB copied to epyc8 q/lepw/3_place.odb; cone dump queued via ot-run (end re g_safe_write.g_address[N].count_r) -> q/lepw/cone.tsv.

## 09:5x update (hub clock PST)
- PUSHED main 4040b479bc (place_regions kind/box/radius + release hook) and 51fdaae779 (type_overlay place_regions key). rt/51fdaae7793b exists.
- Proof specs (rt 51fdaae7793b, overlay, default J7 tree/bind, goal route):
  A fence: ~/coord/autopilot/private_specs/FABLE-FIX-CONE-SCATTER/s81_dsdv_slice_lepw_mus_LP__t2_1122094657 (ov intel2 L/ov_lepw_A.json)
  B soft : .../s81_dsdv_slice_lepw_mus_LP__t2_1122094715 (ov_lepw_B.json)
  Launch = kit_wave.py run-item <spec> (bg, on intel2) after 10:10 if no OBJECT from DSDV-R1. Waiter: ot-wait --kit --durable.
- Rows: 20 place_regions, lcs_tx<t>_b<k>: inst_re g_tx[t].g_safe_write.g_address[(4k..4k+3)]. near_re tx t bank k SRAM macro, radius 30, util .5.
- Census+tool post 09:5x (hub 66f5021280). COORD report sent after this.
- epyc8 cone dump of lepw J7 ODB (q/lepw/cone.tsv) still queued (bg).

## 10:3x update
- Launched 10:10; first try FAILED kit_snap: KIT-STORE MISSING type_overlay (overlay file must exist on ALL die hosts). Copied ov_lepw_A/B.json to /srv/opentallas-scratch2/claude/fable-fix-cone-scatter/ on epyc8 intel1 epyc9 epyc10 epyc2 epyc7; relaunched 10:24 (units runitem-dsdv_slice_lepw_mus_LP__t2-71876 A, -71881 B; logs intel2 L/runitem_<spec>.log, try1 logs kept).
- Durable waiters (intel2 nohup) L/waiter.sh A-fence / B-soft: poll kit dir, then ot-wait --kit place/route --durable, post PROOF lines. (A junk 10:13 PROOF post was corrected.)
- Next: read place result (wns vs -347 baseline, OT_PLACE_REGION lines, DPL), hand row file to S81-J6-ASSEMBLY-R5 (J9) + DSDV-R1.

## 10:4x-17:3x (weekly limit ~11:1x-17:2x)
- Overlay form refused: BIND-GEN-TOOLSKEW (J7 bind rt d6f543 vs 51fdaae reset generators). Switched to tree+plan form:
  fork epyc8 /srv/opentallas-scratch2/claude/fable-fix-cone-scatter/trees/s81_j7_lcs (ot-tree-fork, 54 GB), plans physical/die_plan/s81/plan_lcsA.json (fence util .5) / plan_lcsB.json (fence util .3), 20 rows each (mkplan.py in lane dir epyc8).
  Specs: private_specs/FABLE-FIX-CONE-SCATTER/s81_dsdv_slice_lepw_mus_LP__t2_1122104037 (A), _1122104125 (B); --rt d6f543 --rt-floor-exempt; run-item rt a4c5d882015d. Old overlay specs 1122094657/94715 = FAILED (do not reuse).
  Work dirs epyc8 .../18a2688b741/private/FABLE-FIX-CONE-SCATTER/dsdv_slice_lepw_mus_LP__t2_1122103955 (A) / _1122104047 (B).
- Place queued through the limit; admitted on epyc8 17:19 (A oth-ubuntu-2666901-1795394364) / 17:20 (B oth-ubuntu-2712767-1795394442).
- Waiters intel2 pids 3706320 (A-fence-u05) / 3706321 (B-fence-u03) alive: ot-wait --kit place then route, post PROOF lines. Baseline J7: -347.11 ps count_r[1]->count_r[5].
- COORD 10:04 ruling: A/B approved; proven rows -> DSDV-R1 + S81-J6-ASSEMBLY-R5 (J9 now); kv3_pc_v3 row -> FAM-KV-IOPC-R4 if same class.

## 17:4x-21:3x
- B placed 17:38: ALL 20 rows OT_PLACE_REGION_DROP (auto cone > 8 x members). A/B = baseline twins, left running (route waiters live).
- Pushed dabe421818ef: place_regions row key cone auto|between (ot_pr_cone_between in place_regions_cone.tcl; member->member cells only, never DROP). 71 tests pass.
- Proof C (fence util .5 between rad 20) / D (soft, same): fork epyc8 trees/s81_j7_lcs2 (manifest 12af64d4f18d), plans plan_lcsC/D.json written.
  Private rebind on rt dabe421818ef: epyc8 lcs_bind.sh via ot-run (log lcs2_bind.otrun.log, queued 21:2x). After LCSB_DONE: private-spec --tree fork2 --plan plan_lcsC/D --rt dabe421818ef --goal route, then waiters.
- 21:2x COORD: leaf wdo_q cone (t14/t74/t31/t45) -> lever form posted to LEAF-R10 (hub c5a7d1af8c). Census rule widened: path>=800, span<0.2*path, wns<=-150, st>=10; 72 h = 8 hits.
- 17:5x COORD: A/B CANCELLED (ot-run --cancel pid 1020194 + B dir; B run-item 3699714 + A/B waiters killed by pid). Regex check (q/rxcheck.py on 1_synth_odb.v): lepw rows 140 members (b4 70), near = 1 SRAM each; leaf t14 lcs_wdo_b0/b1 240 each (112 src + 128 wdo_q). Hub 37bd2029fa.
- Rebind queued since 17:50 PST; if not admitted by 18:50 -> chain spill (main 8bb9f7f78176) / epyc7 / epyc10.
