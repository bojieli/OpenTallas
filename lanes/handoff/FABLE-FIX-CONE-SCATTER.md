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
