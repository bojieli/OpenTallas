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
