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

## 11:10 PST takeover update
- Latest private actual runs: A spec suffix 1122104037, unit runitem-dsdv_slice_lepw_mus_LP__t2-72895, work suffix 1122103955; B spec 1122104125, unit -72903, work suffix 1122104047. Both epyc8. Both now progressing in kit_rtl, actual ot-run scopes 4134244-1795374324 and 4124466-1795374312. They are legacy group utilization A=.50 / B=.30 with the same 20 anchors, distinct from earlier failed fence/soft overlay specs.
- The 10:56 rc78 came from ODB cone-dump client 695718 under E8 q/, with no result after its declared 3600-s wait and no stage evidence. Actual inherited A/B had explicit E8 load admission waits. The older 10:13/10:14 waiter posts had simply preceded kit-directory creation and had already been corrected.
- E8 q/lepw/cone_takeover.tsv and cone_takeover.live.log, unit oth-ubuntu-4149090-1795374343 rc0, recovered exact baseline: 720 counter flops in 20 groups and 6,472 visited cone gates. The sampled tx0/address1 counters cluster at x115.668–119.772, y721.845–725.355, ~9–13 µm below their SRAM, yet measured path is 1679.4 µm / 19 stages / −347.11 ps. Counter seats are already local; inspect whether the exact candidate group captured the intervening gates.
- Reviewed exact 20 bank anchors, macro shelves, channels and clock taps, picture E8 q/review_1122/cone_scatter_plan_ab.png, coord 05990647db6f. A/B Tcl in-memory read-only replay against the retained ODB is queued E8/I1, E8 q/review_1122/replay.live.log. This checks group coverage and computed regions while the actual builds continue. Review actual placed layout before any new Codex route. No inherited process was stopped.
- KV pc_v3 is the same scatter signature but its id/lpc result drives status and macro pin 490 µm apart. A single generic fence has competing loads. IOPC's existing macro-local register / separate combinational copy proposal is the needed architecture path. No duplicate KV run.
