# TEST-BASELINE-1 handoff (2026-11-14 PST)
Lane: make the tools/die_plan test family green or explicitly marked, off main 0787456ddc.
Branch claude/test-baseline-1-1114 @ 1189a56d5c (hub; 3 commits, tests + die_plan.schema.json only, no production code).
Clone epyc8 /srv/opentallas-scratch2/claude/test-baseline-1/repo (own clone, venv wt/venv60, run script ../run.sh <tag> -> <tag>.raw/.fails). Run: 1115 files, pytest -n 32 --basetemp on scratch.

Before: 62 failures/errors (60 FAILED + 2 collection ERROR), same set as ROOT-MERGE-63 base63.fails die_plan part.
After: run 2 = 0 failures, rc=0 (16 xfail, env skips). Run 1 had one flaky failure (test_xdie::test_cut_lines_count_abutted_bits, see below).

Commits:
1. 583037d4dd class (a) 4 tests: test_actual_sink_sites, test_native_split_classes::test_child_root_tap_fails_closed, test_reach_fix::test_hard_wrapper_empty_tap_fixed (all LIMIT-BIND-1: radius/empty tap = TAP-LIMIT-INFO, not blocking; assert no raise / exit 0), test_flow_gen_1028 status point outside core (KV-CLAND-EDGE 83fc576b53 grows the window to the core edge; not an owner remove-limits item, asserted placed FIRM inside core).
2. e0e5264ffa class (c) 16 xfail (non-strict, reason text on each marker), listed below.
3. 1189a56d5c class (b) 42 tests: skips tkinter (3), yosys-abc (10: lec_cons_base 6, lec_fsm_preseed 3, lec_rawprefix_bound 1), shapely (4 pg_access_plan); stale fixtures: ff_ns_stride/ff_ns_inset in tclsh harness (face_flops_margin 3, ft_mixed_occupancy 5), flow_hold_basis $MF spelling, gen_phys_bump_ports message, core_family_slice per-buffer slew, route_hold_pass eligible stub (5), plan_gen_rules cell_check spelling, post_route_drv opt-in data reroute write_db, bind_structural_bridge Binder partitions (2), clock_landing_band_reserve hard_cores inst, fresh_kit plan module; die_plan.schema.json regenerated (python3 tools/die_plan/schema.py dump-schema): local_reset_pins from TL-QCPHYSD was never dumped -> test_schema, test_tap_entries, test_ring_writer_optin.
No R-MINIMAL gate test (DRC0, TT setup, FF hold, bind, LATCHECK, token) was weakened.

Class (c) real defects, NOT fixed here (owner needed):
- ft_full_stage_bootstrap x4: ft_full_stage.validation_bootstrap rejects the real face_flops.tcl; ff_is_hop_flop (6331f166a6, HBM-VSN-XTAP 11-11) is not in the copied-helper list, so install() raises "would copy mutating code" on every full-stage FT kit. MOST SERIOUS.
- lec_unique_outputs x2: Lec.build() no longer emits cons:<side>:<key> obligations from model.cons; duplicate-name fail-closed cannot fire (lec.py reworked 11-14 f9b72b0b1d / 89e6005ace). LEC soundness-adjacent.
- kit_istations x4: col-st _col_chain returns None for the COL_BOUND fixture (no is_place cst:st lines, bound_stages 0) after 11-14 commits 9615a697f7 / c62b845496.
- kit_cts_hook[hbm_arch]: gen_core_kit_hbm.py:2757 cfg += grt_nonport_hold_setup after MS.plan_tree_cts (cfg edited after the CTS hook).
- timing_libs: signoff.py EXACT_TIMING_LIBRARIES_TCL (KW-FIX-5 variant) drifted from timing_libs.tcl.
- master_plan_r3: ft_ports._kind raises "kind not derivable" for arc mp_crep0_i->mp_crep0_o (fixture or stricter ft_ports).
- core_infra_a0_optin: default icg_tree cfg not byte-identical to base (KW-FIX-24/LEAFOPT f6680f1cd8 adds lines).
- grt183_kit, legacy_gate: sha256 pins of grt183_resume.tcl / legacy run_kit never re-blessed after intentional edits (f13e0a8c69, 7dd16dd58d, 958a7d6d7f); owner may just update the pin.
Flaky (not marked): test_xdie::test_cut_lines_count_abutted_bits failed once under xdist (AttributeError census_cov.coverage): module-name collision, physical/die_plan/s81/census_cov.py shadows tools/die_plan/census_cov.py when another test inserts the s81 dir on sys.path first. Passes alone. Needs sys.path hygiene in the polluting test.

Gate advice for ROOT-MERGE-63: after landing, base list = only xfail/skip-free family; any FAILED/ERROR is new breakage (retire base63.fails die_plan lines). The host lacking tkinter/yosys-abc/shapely now skips instead of failing; check those 3 tools exist on at least one gate host or the skipped tests cover nothing.

## Later scopes (2026-11-14 PM)
Fix branches (all on hub): claude/fix-ftfull-hopflop-1114, fix-lec-cons-1114, fix-kistations-colst-1114, fix-census-cov-collision-1114, fix-timing-libs-drift-1114, fix-rest-tests-1114, fix-prd-hold-scope-1114, fix-macro-box-rotation-1114 (approved, impact = none: 0 rotated orients in any plan of record), fix-autopilot-tests-1114 (incl. kit_wave prov_stage VIEW-FALLBACK TypeError fix). Integration run of 1-5: claude/test-baseline-integ-1114, die_plan family rc=0. Clone epyc8 /srv/opentallas-scratch2/claude/test-baseline-1/repo (identity TEST-BASELINE-1), runs via ../run.sh <tag>.
