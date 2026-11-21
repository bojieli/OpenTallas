# RESET-RELAY-GEN-1530 handoff (FABLE-CLOSURE-1515 lever 1 + COORD 11-21 asks; updated 2026-11-21 PST)

Lane owns the reset-leg generator `tools/die_plan/reset_leg_plan.py` and S81-DIE-R4's die reset / monitor relay patch
(reach_relay_plan.py, reset_tree.py die_relays). Posts: lanes/posts/RESET-RELAY-GEN-1530.md. Rows for the die lanes:
lanes/handoff/RESET-RELAY-GEN-1530-rows.json (v2). Work dirs: epyc10 /srv/opentallas-scratch2/claude/rrgen-1530/src (lane
clone, HEAD = main 5099d315ba, clean) and rrgen-1530/{p10,leg_*,gd_*,x10}; epyc7 rrgen-1530/ (older dumps / proofs, tl/ copy).

## On main (all pushed with ot-push-main)
- e9af887233 S81-DIE-R4 die reset / monitor relays (unchanged patch)
- f02ccd50eb reset_leg_plan.py + reset.inst_taps (schema, bind, kit-rtl) + apply_inst_taps
- aa05a04543 stage site key `u_y_xd_<sid>_<port>_k<k>_<s>.q`
- 73717f6992 form R skips macro sinks (re-tapping a core by its centre cost -763 ps on cbx)
- bbcc7f022a relay_split (k_cover register duplication, partition_types[].relay_split), relay_depth D 1..16 (schema)
- b747b0ec33 form F (reset forwards through ot_dp_dly / ot_dp_st / crr bits, staged on the BITS of the input port only when
  every bound use of the bit is a reset use), geom_dump MR records (hard-macro reset-pin XY) + geom_rules parse, flat bound
  relays (u_u_vp_u_rr) and crr flops (u_u_crr_*) as groups, stage sites ON by default (--no-stage-sites), KRD accepts a
  concatenation of plain items ({eb, b}), kit_istations rs_split_all copies the flop + its single-load BUF/INV chain
- 5099d315ba form M (reset forward into a hard-core reset port: D stages on that core port only, hops incl. last stage ->
  each MR pin <= 300), reset_only / port_into fixes, entry legs staged even when the relay keeps its site

## Rule summary
`python3 -I tools/die_plan/reset_leg_plan.py PLAN TYPE BOUND_SV GEOM OUT_PLAN REPORT.json [--reach 300]` with GEOM = the
geom_dump.tcl dump of the type's newest placed / CTS ODB (main geom_dump.tcl, so MR records are present). Forms: R (inst_taps,
0 cycles), F (reset-carrying relay bit), L (local relay tree: seat or split bottom-up, equal-depth entry chain with branch
stage copies), M (core reset pin). Never a gate. Rows are per bind (tap ids, split names): re-run on each event bind.

## Model results (legs over 300 um before -> after)
| type | source DB | before -> after | main rows |
|---|---|---|---|
| QC cbx_q10__cl94a12200 | s29q103S4Q9N46C place | 4 -> 0 | 4 inst_taps (u_t30 macro row dropped) |
| KV kv3_pv_v2 | D25e3 a4 place | 13 -> 0 | 13 bank inst_taps |
| KV kv3_hub_Eo | D25e3 a3 place (-747) | 32 -> 0 | form M u_astk_EN D 8, u_astk_ES D 4; form L fan_2 D 4, fan_3 D 2; 13 inst_taps rows |
| S81 leaf t60 | CORE-LIB-LIMITS-1330 4_cts (-493) | 5 -> 0 | form F u_lpad_leafdn_i0 d bit 0 D 5 (+1 split), u_u_vp_u_rr rst_n_in D 3 |
| S81 lepe_nh_mus_LP t1 | b05c place | 20 -> 0 | land D 5, lep D 4 (stage at centre + 2 branch levels x 5), 18 split flops / 30 copies |
| S81 lepe_mu_LP t2 | b05c place | 29 -> 0 | (tl copy before form M) |

## Place proofs so far (private kit copies)
- QC cbx r2 (epyc7 proof2/cbx): WNS -473.5 -> -296.0 (now the baseline clk path), asynchronous -473.5 -> +566.5.
- S81 lepe r1 (no split): reset -456 -> +212; r2 (stage sites): +243.8, stage sites 9/9 matched FIRM; r3 (split TCL before
  the chain fix): splits not applied, +24.8 -> fixed TCL proven offline on the lepe floorplan ODB: 18 flops, 30 copies,
  189 sink pins moved, 0 missing (epyc10 rrgen-1530/st_lepe).

## Jobs in flight (ot-run; cancel only with ot-run --cancel <unit>)
| what | host | unit | goal | log |
|---|---|---|---|---|
| lepe nh_mus t1 r4 (split + F + stage sites) | epyc10 | oth-ubuntu-4060581-1795226367 | place | rrgen-1530/p10/lepe/proof.log |
| S81 leaf t60 (lever 4) | epyc10 | oth-ubuntu-4060575-1795226367 | cts | rrgen-1530/p10/t60/proof.log |
| KV hub_Eo (form M) | epyc10 | oth-ubuntu-4060666-1795226367 | place | rrgen-1530/p10/hubEo/proof.log |
| KV pv_v2 r1 (inst_taps) | epyc7 | oth-ubuntu-2363321-1795218686 | place | rrgen-1530/proof/pv/proof.log |
Check each: `grep OT_RELAY_SPLIT\|OT_RELAY_SITES <kit>/run/logs/asap7/*/base/3_3*.log` (split copies made, 0 missing),
then `python3 -I epyc7:rrgen-1530/rpt_sum.py <kit>/run/reports/asap7/*/base/3_detailed_place.rpt` (t60: 4_cts_final.rpt)
against the baselines: lepe asynchronous -456.1 / WNS -644.4; t60 WNS -492.6 (lpad_leafdn -> crr_vsw), asynchronous -386.2;
hub_Eo WNS -747.0 (u_bin_i_host_die_rst_n -> u_astk_EN); pv asynchronous -2,218.1. Kits were prepared with
epyc10 rrgen-1530/prep10.py KIT TYPE PLAN (originals *.orig_rrgen, receipt rrgen_proof.json).

## Open items
1. Splitting: done (relay_split + rs_split_all); proof r4 lepe pending. If clones place but timing regresses, look at copy
   0 vs clone cluster order (copy 0 = cluster nearest the original).
2. Depth cap: schema relay_depth D max is 16 (COORD asked 8; 16 covers it). Largest emitted so far: 8 (hub_Eo u_astk_EN).
3. Stage sites: default on; r2 lepe matched all keys FIRM. relay_mid.tcl alone bunched them.
4. Macro reset pins (KV hub_Eo): form M rows posted to KV-PLAN-R2 for D27 (post ca96574486); proof pending.
5. Lever 4 (t60 relay chains): model 5 -> 0 on the CTS DB; cts proof pending. leaf t72 / t56 / t1 not run yet: dump their
   newest placed / CTS ODB with main geom_dump.tcl and run the tool, then hand rows to S81-DIE-R4.
6. Final numbers to S81-DIE-R4 (J6), QC-PLAN-R5 (V1), KV-PLAN-R2 (D27) once the proofs land.

## Stop list
- No hand rows per type for reset relays or forwards: run the tool.
