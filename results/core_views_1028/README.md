# CORE-VIEWS-1 (2026-10-28): signed hard-core timing views with provenance, all 5 dies

Why: FLOW-ONEMODEL-3 (die_sta_related --core-insertion view) times every early core tap with the core's own signed
view and FAILS CLOSED without one; --core-view-match-pins (gate default) needs provenance kit.pins_sha256 /
pins_canon_sha256. QC (prog/btab no view dir, crh views without provenance) and S81 (1696 early taps, 0 views) failed
closed.

## Exporter (shared, no second one)
`tools/autopilot/export_view.py` = the autopilot's own view exporter (PROBE_VIEW_READ + view_payload, the code that
publishes `view/<module>/` when the autopilot archives a run it signed) with a command line for runs signed before or
outside the autopilot. autopilot.py is unchanged. Additions, all recorded in provenance.json `export`: verdict text is
the run's own (signoff.py verdict + routed LEC record if given, never the autopilot chain text); signoff.json sha256 +
generated; freshness (6_final.odb not newer than signoff.json generated, else 'incomplete'); kit.pins_sha256 = kit
pins.json sha when the freeze/core record has none, and pins.json is copied into the view (die_sta_related
signed_pins_doc then verifies signed content -> exact mirror match works); ORFS base `<m>_tc/_bc.lib` -> `_tt/_ff`
when the kit has no views/ libs (same rule as tools/die_plan/s81_eco/publish_view.sh). Test: test_export_view.py (3).

## Views exported here (`results/core_views_1028/<die>/<module>/`)
- qwen_compute: qfd_dv_s8x_crh (qc/closed kit; LEF from results/qc_cores_1025, libs sha-equal), qfd_dv_s8_crh_rp1
  (autopilot archive **f4g** = the 250.56x216 core in the die plans; SIGNED, src 5ed4500430, no flow tag; the
  release-cache record f62 is 259.2x276.48 and is NOT the plan core), qfd_dv_s8x_prog (autopilot archive s8b, ORFS
  tc/bc libs), qfd_dv_s8x_vmr (autopilot f4kfinal, routed LEC record attached; OWNERS SIGNED-UNVERSIONED).
- s81: 12 views re-published with provenance from the committed `physical/die_plan/s81/cores/views/<m>` (run data not
  re-read; freshness not checkable there). dsdv_eng_rr_h1, dsfd_su_t_rxsb, ot_dsrom_su_hcpost_lane_pr have no LEF/ETM
  in their committed view -> not exported (need run data).
- kv / head: existing views already carry provenance (physical/ref_tile/kv3_head_eighth_e{1,5}/views,
  results/die_head_1027/views); checked, not re-exported.

## Checks (CHECKED = the gate's own functions / the gate itself on these files)
- Pin match (die_sta_related.pins_relation per plan instance, checks/match.py):
  QC on qc_k2b_phase12 (DIE-QC-16 basis): crh 12/12, crh_rp1 12/12, prog 12/12, vmr 36/36 canonical.
  S81 on plan_s10: 9 views canonical (3106 inst: node_LLd/LLfd/LLfu/NNfd/NNfu, cfg7_seq, hrow, gunit_l4r, l5f);
  dsfd_rstg 216 + ot_s81_sstn_payload536 660 MISMATCH (ECO views: rstg 2 pins x differ; payload536 all 1074 pins y
  +53 nm), ot_s81sl_vq 75 MISMATCH (view has 830 pins incl. y[128..], plan 702).
  KV (main plan): e1 256 / e5 256 MISMATCH -- plan added strap_bsel[0..1] (TYPE-REDUCE-2 ffc63645f, 10-25) after the
  sign-off (signed pins = 563711727, 544 pins, 0 moved) -> e1/e5 need a re-sign with the strap pins.
  HEAD: elemA 1056/1056, elemB 264/264 canonical.
- QC gate rerun (FLOW-ONEMODEL-3 die_sta_related @ad1358b21c = DIE-QC-16 tool_om3, same t11i proof/flags,
  checks/run.sh): early core taps view 0 -> 72/96 (missing 24 = c6/c7 per su_c, the unsigned btab + demoted rst3);
  intra FF hold -281.85 -> -206.36 (real-view pairs 2952/163972, -129.26), TT setup 198.65; seam unchanged -143.27;
  verdict still FAIL (closed) until btab + rst3 have views.

## Per-die table
TABLE.md (early taps from the lane plans: S81 plan_s10, QC k2b_phase12; KV/HEAD/HBM origin/main plans; OWNERS.tsv
snapshot 12:3x). Early taps with a matched signed view: S81 0/1696, QC 72/96, HBM 0/1181, KV/HEAD no early taps.
