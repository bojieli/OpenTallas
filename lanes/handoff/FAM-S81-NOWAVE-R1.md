# FAM-S81-NOWAVE-R1 (COORD 11-22 05:0x) - 10 S81 "no kit-wave row" cores

## Finding (04:5x-05:0x)
All 10 rows are HARD CORE DESIGNS of the J7 plan a6771d121e95 (provider cores of svc_hi/svc_lo, pin files inputs/core_pins/prov1119_*), not kit-wave types. They never get a kit_wave row: the cores are built by S81-SVC-SPLIT-1119 (h259 builds) and consumed as signed views cores/svc/prov_1119/<mod> in the J7 tree.
Class (a) for all 10: SIGNED on the J7 design (profile verdict SIGNED, DRC 0, antenna 0, TT setup +150..+238 ps, internal FF hold complete 0 violators; idx_hslice_fp has an advisory boundary hold -7.87 ps = io_hold_parent only). The count tool missed them: record face_guard names no pins file and the run dir had no PROVENANCE.json, so "pins not readable" (design_unmatched).
- hdc_v41x_attn_tr_x x4 (xoff0/8/16/24) <- epyc8 s81-svc-split-1119/build/trx_xoff{0,8,16,24}_h259
- ot_s81_su_smc <- smc_h259, su_smd_fold2 <- smd_h259, su_sml_fold2 <- sml_h259, su_smr <- smr_h259, svc_merge_h4 <- h4_h259, svc_idx_hslice_fp <- irg_hsfp_mm3b (all epyc8, /srv/opentallas-scratch2/claude/s81-svc-split-1119/build)
Not (b): all 7 modules are in the J7 plan (designs + hard_cores). Not (c)/(d): no kit-wave row is needed (cores, not wave items); only_items holds types.

## Action
- Wrote PROVENANCE.json {routed_db} in each of the 10 run dirs (new file, tmp+mv; release_tree_plan._routed_def reads the routed 6_final.def).
- Added 10 rows to lanes/COUNT-DIRECT.tsv (commit 325c6e8bc8).
- Verified with release_tree_plan.fetch_rec_pins + pin_compare: all 10 DEF pin tables + outlines MATCH the J7 plan designs (550/303/306/652/274/2303/2814 x4 pins).

## Open / to check
- Next plan-cache refresh (cache 04:37) should show 72/72 designs signed. If a design stays unsigned, read design_unmatched.
- attn_tr_x: archive_gate pending_archive_cores (db, metadata missing in archive store) - export via standard export if the count still lists it.
- prov_1119 signoffs carry no routed LEC record (older svcrs-3 records had LEC EQUIVALENT); sdc_lint/face_guard FAIL are advisory.
- lanes/AUTO-RESIGN-HOLD.tsv rows for these 6 modules say NOT-IN-PLAN (11-12): stale, harmless (no re-sign wanted).
- The ask on s81-die-r3-e8 (CLEAN-AGGR-R2 11-21 19:48): its dir no longer exists on epyc2; prov_1119 views live in kw45 J7 tree, not on main.
