# Shared LEC / ECO / RC takeover state — 2026-11-08 11:50 PST

Owner: Codex /root/wave/lec_eco, sub-lane of /root/wave. Watcher: no merges/tags/POR edits, no production ECO launched here, no healthy job stopped. Originals mounted read-only for diagnostics.

## READY: ECO-PREROUTED-CLK

Canonical branch codex/eco-prerouted-clock-1113@539f02fdd75 (base d28cf565d0). PRD-only original PRE_GLOBAL_ROUTE hook chain plus pin_access wire save/restore. FlexPA temporary wires discarded, original dbWire objects restored in finally; original result/error/arguments retained. Clock-freeze code and post-route blocking audit unchanged.

Five focused Tcl tests pass. Existing PRD regression:47 pass, one known base failure test_eco_drt_pre_hook_contract (forbids write_db already present in unchanged eco_drt_pre.tcl). Generated PRD staging/chain fixture and shell syntax pass. A standard synthetic TemporaryDirectory fixture cleaned its own704KB mock data; no physical/source/input tree was deleted.

Actual installed OpenROAD6cb3f2b704:
- E6 /srv/opentallas-scratch2/claude/codex-eco-prerouted-1113/a2/probe.log: vecd6_final pin access COMPLETE, all65995 original wire objects/raw opcode+data tokens identical, PASS. Initial GRT vehicle had no prewired nets and is retained as a rejected probe input.
- E5 /srv/opentallas-scratch3/claude/codex-eco-prerouted-1113/probe.log: t51 full pin access COMPLETE,121148 originals restored; initial overly strict transient-wire diagnostic failed after restoration. Corrected behavior is tested below.
- E5 /srv/opentallas-scratch3/claude/codex-eco-prerouted-1113/a2/probe.log: reduced actual offending t51clk vehicle COMPLETE in1s, original object/raw tokens identical; one FlexPA transient wire removed; PASS. This is the corrected helper, no remaining native probe wait.

Own source I2 /srv/opentallas-scratch2/claude/codex-eco-prerouted-1113; source-only patch I2+E5 /tmp/codex-eco-prerouted-1113.patch, SHA2569a78a60607ccc25f060b4ad250cdea4e0ee977d3c7d8ed30dead9e1807963309. S81 owns t51's one strict ECO; HBM owns vecd. Root ruling: input-start parent hold only, register-to-output core-owned, no global output exception. Helper does not alter eligibility or authorize an override.

## LEC collected

Kshare unhinted kit_lec_fix is terminal NOT EQUIVALENT after8011.8s:67598 points,67596 proved,2 differs,0 undecided. Remaining lane0.u_fill.wr_gray[2],[3], wr_bin[3] removed nonconstant. auto_twins proposed2/kept1(rd_bin[3]). Frontend unit1560733 exit0 is not an EQ verdict. Exact result I2 /srv/opentallas-scratch2/claude/hbm-hard-6-ksh/kit_lec_fix/lec/lec.json. Hinted predecessor EQ67599 is insufficient to mark57b854d123 unhinted-ready. /root/gaps owns TKM348 loaded-state class and then kshare twin repair; no lec.py edit by me.

KV PC43 existing proof unit1859707 remains healthy; intermediate282 differs/129559 points is not a terminal retry authorization. Exact source intel1 /srv/opentallas-scratch2/claude/codex-kv-hubs-0222/pc43/full_qualification. S81 BKSEL hinted current proof owned /root/s81, unit2003994, no duplication.

## RC-MODEL readonly measurement

No layer table, margin or signoff changed.600 deterministic non-clock signal nets per kit, exact same pin+master signatures in GRT and final; cap reports associated by explicit call order because report_net display unescapes OpenDB names. All600 match after correcting that display-name join. Dominant-layer statistics retained in analysis.json.

- S81 t51: GRT TT+17.435ps -> RCX-1.899ps; routed/GRT wire-C median0.88449,p10–p90 .65545–1.32023. M3-dominant median .7905; M2 .8128; M5 1.0265. Root E5 /srv/opentallas-scratch3/claude/codex-rc-model-1113/s81; source E5 /srv/opentallas-scratch2/claude/codex-s81-0222/t51_vD.
- QC coll_ftm baseline: GRT TT-46.528ps -> RCX+5.767ps; median1.24814,p10–p90 .65616–2.27540. M7-dominant median1.8902, M3 .7524. Root E2 /srv/opentallas-scratch2/claude/codex-rc-model-1113/qc; source E2 kw26-wave-1106/.../coll_ftm/attempt_9/gen/coll_ftm (original baseline, not ECO sibling).
- HEAD CTL baseline: GRT TT+24.771ps -> RCX-116.135ps; median1.20551,p10–p90 .93482–1.49966. M4-dominant1.3529,M5 1.4861. Root E6 /srv/opentallas-scratch3/claude/codex-rc-model-1113/head; source E6 /srv/opentallas-scratch3/claude/dh87/ctl/hd_ctl_vG (mw sibling untouched).
- KV original FDI read-only pair queued by I1 load cap, not failed: root I1 /srv/opentallas-scratch2/claude/codex-rc-model-1113/kv, source I1 /srv/opentallas-scratch2/claude/codex-kv-fdi-0222/kits_nonport/ot_kv_fdi_join_rf__198.72x198.72. No duplicate.

Canonical client logs ~/coord/autopilot/codex-rc-{s81,qc,head,kv}-1113.log. Each own root has grt.log,final.log,out/{nets_*.tsv,rnet_*.txt,libraries_*.json,candidates.txt}. Small local summaries /tmp/codex-lec-eco-1113/rc_{s81,qc,head}/analysis.json; scripts same temp parent. HEAD/QC RCX has pre-existing STA-1652 clock hierarchy warnings; do not claim full parasitic name coverage. Signal sample excludes clock nets.

Next: collect KV; commit reproducible RC report/scripts. No blanket HBM1.32 extension. Native set_layer_rc lacks per-class selection; all-layer scaling also affects C++ incremental clock estimation. Native -spef_file exports per scene, and clock-only restoration works at Tcl boundaries, but that alone is not qualified for every incremental clock/leaf-repeat update. Keep existing calibrated table and approved interim margin/maxwire rules until a class-scoped mechanism is qualified.

RC findings published on codex/rc-model-findings-1113@cc68e96d90c; all three completed pairs and source scripts/raw reports committed. No model/gate change. ECO branch tip f79c00b83ca records the corrected t51 native clock PASS; code539f02fdd75 unchanged.

HC0W pending reuse API screen: current main supports pending reuse only within the same K registry. External reference-completed requires producer done+rc0+EQUIVALENT and exact captured identities. Original E6 slw_hc0 attempt10 is pending, source ID c88d760e0ebee32852499ccd74010bfdb73420ed6b22251a44e89058bbb5c61d / all ID2a2ae91a4355f7b9f61b9d037f721fe6337e295ed71f89837d5dd37d09bbb490. Ready proves1_2_yosys.v42112098bytes; NewA minimal target has no netlist/proof state yet. No supported cross-kit pending reference found; no PID/marker/physical receipt copied. Reach has exact completed-reference requirements and keeps original proof healthy. No new proof launched.
