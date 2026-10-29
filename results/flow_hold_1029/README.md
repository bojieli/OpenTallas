# FLOW-HOLD takeover 2026-10-29

Shared source fixes: e6d564618 scopes sender-min core obligations to their exact plan and receiver module, with core-in-partition parent receipt selection. S81-029 still needs the first routed col_h9 parent with real CFG7 views (u_r2.u_s13); no such parent kit exists. The real flat/ILM parent summary can then be passed to io_hold_parent.py PLAN STA --core-instance u_r2.u_s13 --core-kit CFG7_KIT --out RECEIPT. A missing view, missing input or stale plan stays incomplete.

65bb9a7ca fixes the existing RC calibration runner for modern exact-library loading. First native probes failed with missing BUFx4 because grep selected no libraries; preserved *_rc_missinglibs outputs on intel1. The corrected prefix reads the exact signoff-selected libraries and isolates its receipt.

## Q3 hold closure

Inherited intel1 flow-hold-3-v1/q3_holdeco is actually eco_from=grt (OT_HOLD_FORM default pre_drt), despite the preceding post-route description. Its clock-freeze log has zero routed clock wires and it is still in hold repair. Left untouched. Its source q3 is a stable copy of kv-kits-20 q3_t2.

A fresh real post-route variant now runs at intel1:/srv/opentallas-scratch2/claude/codex-flow-hold-0830/q3_post2_holdeco, unit oth-ubuntu-1644745-1793288469 (subsequently stopped by exact own container name after the mixed-corner bug below was diagnosed). Source own worktree /srv/opentallas-scratch2/claude/wt/codex-flow-q3-post-0838 @65bb9a7ca0; OT_HOLD_FORM=post_route, OT_DRV_LAST=1, margin15 under OWNER12.19 because measured routed-clock drift exceeds10ps. Original routed geometry was viewed in geometry.png before submission (review in results/geom_review/codex_flow_hold_1029). DRC, frozen clock geometry, TT setup and FF hold remain required. Earlier prelaunch missing-bundle and existing-directory failures are retained in q3_post_missing_bundle.log / q3_post_existingdir.log; no physical result was generated in those attempts.

## Risk sweep (own measurements, UNCHECKED by independent number review)

One existing routed sample per die; this is a risk sample, not a completeness census. Current RC script ran read-only with the same exact FF libraries and each kit SDC. Clock arrival comparisons use matching register clock-pin names and source latency zero. Values in risk/summary.json: KVq3 max41.40/mean17.67ps routed minus GRT; QC BTAB max57.14/mean14.63; S81 CFG7 max10.55/mean1.16; HEAD turn_a max7.44/mean-2.27. HBM HNX max14.48/mean-5.60ps routedminusGRT on39375matchingclockpins; the last probe completed withoutnewphysicalbuild. Full artifacts intel1+intel2:/srv/opentallas-scratch2/claude/codex-flow-hold-0830/*_rc/ff*.tsv. No new route or release follows from this diagnostic.

Q3 routed-wire fit over351clocknets recovers R(M3)=31.214, R(M4)=17.9997, R(M5)=18.982ohm/um with meanR residual0.054%. A fit against GRT guide lengths gives meanR error52%/p95+153% and is rejected as a transferable correction. Actual GRT M5 clock legs become M3 in detailed route (mp_ck_Tpq_br_out: guideM5 26.79um vs routedM3 26.85um, plus vias). Thus a blanket1.8 RC multiplier does not fix the underlying layer assignment. No globalRC default changed.

## Canary collection

Main a592 QC, HBM SRAM and KVtype completed NO-REGRESSION with their original absolute design stops retained. HEAD a445 is canonical stage PASS but REGRESSION: TT-33.83/FF-6.63,109holdEP vs74baseline, FFclockmean193.06 vs175.72, DRV332vs185. Its own HEAD owner was notified. The old hd_turn_a type outline and type clock fields are unchanged relative to the05f9baseline; the current margin10 reduces earlier241holdEP to109, and its measuredGRTclock drift stays below10ps. No HEAD tag authorized. HEADa592, KVcorea445 and AB81f9 are still live. No repeated canary.

## Corrected FF-only ECO and current builds, 09:01 PDT

Shared source6be8c010c (codex/flow-eco-ff-1029) fixes a real native-kit integration failure: copied config had `override CORNERS=tc BC` and `override OT_HOLD_MM=1`, while the b-variant ECO launcher did not patch OpenROAD for the two-mode session. Command-line `CORNERS=bc` did not beat the override. Both corners were loaded in one ordinary mode with FFvclk202.5, producing q3initialhold-61.791ps. The b variant now explicitly selects MM0/singlebc and runs the existing kit_modes_eco guard.20 focused tests pass, including executing make precedence. Source656e6924a is superseded only to retain executablefilemode; use6be8c010c.

Only my wrong-mode post2 job was stopped; inherited pre_drt1253686 was not touched. Corrected q3_ffonly_holdeco LIVEintel1unit1787016 uses same frozen411clockwires, FF-onlylibraries andKIT_MODES ecoFF-only202.5. Its initialFFhold-30.317 matches actualsignoff-30.32. It completed holdrepair at+15.000ps with4913buffers (3.4%area) and reached detailedroute; finalsignoff/DRC/clockgeometry remain pending. Clockfreeze restored144wire encodings destroyed byGRTupdateDirtyNets, all411coveredgeometry frozen. This is actual data-onlyholdrepair, no clock adjustment.

E0freshroute is LIVEintel2unit2828389 atcodex-flow-hold-0830/e0_ff15 (64GB16threads), sourceownWTcodex-flow-e0-0855 explicit6be8c010c. OriginalRTL/pins/SDC/binding/outline/clock/reset geometry retained; currentcoreflowhelpers, FF15 and two-modeGRTstaging applied. Personally viewed existingfloorplan/density/actualFFpath beforelaunch; E0_REVIEW.md records it. Script run_e0_ff15.sh routesfresh and then invokes truepost_routeECO6be on the actual resultingroutedview. No E0duplicate or prior checkpoint recovery claim.

## HEAD canary diagnosis

The baseline mixes GRTmetrics from05f9canary with SIGNOFFmetrics from the earlierPROTO m5 kit (baseline context.source explicitlynames proto1025/kits/m5/hd_turn_a). That prototype wasgenerated before per-cornerFFclockbinding; its FFclockmean175.72 has no recordedbound. CurrentexplicitFFbound202.5 is a differentcomparisoncontract; mean193.06 is nearerthatbound. Do not attach a HEADflowtag or silentlyrebaseline it.

GEN-only05f9currentcomparison (no old P&R): clock_binding.json,budget.json,pins.json,constraint.sdc are byte-identical. Config changes are holdmargin5->10 and SYNTH_CANONICALIZE_TCL. Generated functionalcontrol is NOTidentical: oldturn_a lacks start_i and has7ot_dp_rrelay instances/0rgate; currentturn_a has start_i/u_run_in,20rrelay+8rgate,8reset+STARTtaps instead of3reset-onlytaps. The clockpopulation grows21registers and the formerlyemptythirdtapnowcarriescontrol. These are mandated reset/START additions, not a new FLOWchangehere. Currentholdmargin10 lowers241holdEP to109; GRT-vs-routedclockdriftmax7.44 rules outbulkRC. AbsoluteTT-33.83/FF-6.63/DRV332 and109holdEP remainNOTSIGNED; comparingthosecounts with oldPROTO's74EP/DRV185 does not isolate a flowregression on the same RTL vehicle. Action: coordinator must select/approve a baseline for the current mandatorycontrolcontract while preserving oldfailures; no oldbaseline reroute performed.
