# TA15 selected production digital body

CONFIRMED REVIEW_20261009.md review0443 X5 explicitly selects Claude's first-closed `ta15prod_body-1f77ae2d0` over H15 DATA. Exact source/collars/bench/mutant and paired production_body_cl.sdc are imported byte-identically from1f77ae2d0. The owner branch's existing production route helper now selects these files; no new route or bench rerun was launched. H15 DATA e631befc2 remains evidence only, with retries retired.

Both canonical jobs are CLOSED, DRC0:

| Job | TT setup | FF hold | Host |
|---|---:|---:|---|
| ta15prod_body-1f77ae2d0-tc-hm10-cl | +269.46ps | +8.03ps | ot-agidock128 |
| ta15prod_body-1f77ae2d0-tc-hm25-cl | +269.73ps | +21.52ps | ot-epyc2 |

hm10 SS sensitivity is +201.50ps. Lockstep seeds1/2/3 each PASS, composition PASS, NODROP mutant FAIL. Collected raw corner_sta.json, original physical.json, constraints, final netlist and DRC report for both. physical.json's earlier pre-corner NOT_MET verdict is deliberately retained; canonical final corner signoff under production_body_cl.sdc is the selected evidence. Do not overwrite the early receipt or claim it passed.

Digital structure retains three destination release edges and two AON readiness return edges, zero added token cycles. Approved bounded500/0 synchronizer entry window and raw-assert-only exceptions remain unchanged; post-synchronizer paths remain synchronous. Production analog PLL/lock characterization, actual AON entry/MTBF and die loaded clock/reset fanout remain external obligations. This adoption selects the isolated digital body; it does not qualify a whole-die PLL implementation.

Remote final ODB/DEF/GDS/SDC/SPEF stay in each job's original routes/<underscore-label>/work/orfs/results/asap7/opentallas_ot_hbm_production_clock_digital_body_asap7_mtp_<underscore-label>/base. corner_sta.json records exact ODB/SPEF/SDC SHA256. No hardened LEF/Lib abstract was exported by these jobs; source-pin adoption and final object locators are retained without inventing views.

## Standard hardened abstract follow-through
Standard pinned tools/w18/export_view.py and corner_sta.py exported SS/TT/FF timing models and write_abstract_lef from byte-matching immutable hm10 ODB/SPEF/finalSDC copies, reading exact production_body_cl.sdc. Original ORFS untouched. Remote run `/srv/opentallas-scratch/codex/ta15-body-export-206798f3f`, launcher2475154, is terminal0. Existing guard1GiB basis is same-final-object6_report measured738888KB (nearest report inventory, not an exact export container peak); wrapper time-v31364KiB is not claimed as OpenROAD container peak. Latest and asap7lock image IDs match sha25616470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29. No clock/RTL/tool behavior change or wall cap.

All three exports completed and reproduce the retained corner slack: SSsetup201.500ps, TTsetup269.458ps, FFhold8.025ps. Readonly remote checker PASS48signalpins, exact100.224x99.36um outline, actualM4/M5 signal rectangles bounded in slot, exact source bit directions and exact LEF/SS/TT/FF Liberty pin sets. Files installed under `physical/hbm_accel_die_views/clock_boundary/closed_body_cl`; export hash manifest, rawlogs, source-objecthashes, command and check receipt retained under exported_view/. This supplies previously missing hardened views for the selected isolated digital body; analog source/MTBF and die-loaded composition remain unqualified.
