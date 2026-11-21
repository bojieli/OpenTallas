# ADOPT-CENSUS-1800 handoff (2026-11-20, from FABLE-FLOW-1800 class 2 + COORD scope adds)

## Pushed on main (b9cc8c4757, 2bd53ea065, c113d4e450; 22 tests)
- `tools/autopilot/event_adopt_diff.py` ADOPT-DIFF. `diff --tree T --die D [--plan P --kit ITEMS --tools-sha S --fetch]`: pin (tree
  .src-manifest.json main_sha) / event tree / main per file in the die scope. LAG = event untouched, main moved; BOTH = both moved
  (die owner); CURRENT. Then the ledger. `carry --report OUT/adopt_diff.json --pack P [--apply NEW_TREE --link]` = src_manifest delta
  pack of LAG files (new_main = main, BOTH untouched). Report only, exit 0.
- `tools/autopilot/PROVEN_FIXES.tsv` ledger (id kind sha die types value note). 15 rows. ecd0239bd5 is NOT on main: the reset-cap fix is
  fa09197057. `bksel-l4-define` sha column says `pending`: fill it when OPUS-FIX-S81-BKSEL-R4 pushes OT_BKSEL_L4.
- `tools/precheck/event_census.py` EVENT-CENSUS vs the previous event: MON_UM (landing_contract monitor band -> cland_dn pins), HOPS_300,
  DEFINES (plan), DEFINES_KIT (only when both sides have kits), UNREG_READS (kit rtl `ifdef selectors off), RESET_UM, RESET_ROWS.
  `hold` (hub) writes hold_items "EVENT-CENSUS <event>: ..." for regressed types via kit_wave_edit and clears stale census keys.
- `tools/precheck/plan_geom_census.py` absolute check (COORD add): HOP, RESET_LEG, CORE_WIRE (core_conns.json, lower bound), UNREG_READ;
  `calib` vs kit_scan PLACED records.
- `precheck_hook.py` runs ABS-CENSUS, ADOPT-DIFF, EVENT-CENSUS (+hold) after PRECHECK; `publish_apply.py apply` passes the previous
  event (live cfg before the switch) and the tools pin. First live use = the next apply after rt/current carries c113d4e450.

## Runs (outputs: epyc9 / epyc7 /srv/opentallas-scratch2/claude/adopt-census-1800/r_<die>/{abs,census_*,adopt})
- S81 (J6 tree does not exist yet; ran on the J5 base): LAG 296, BOTH 126, ledger 14/15 missing (all but rip1-rtl). ABS HOP 9,807 / 384 types
  (752 > 405), CORE_WIRE 1,265 / 63, RESET_LEG 522 / 82, UNREG_READ 10 types. Census J5 vs D8i: 99 regressed (MON_UM 62 incl. 28 of the
  29 stopped types; gunit t1 missed).
- QC V1 (qc-plan-r6/v1/b_s3/tree): LAG 404, BOTH 170, ledger 10/10 missing (tools pin eb1e73448bd0 predates all). ABS HOP 510 / 89 types.
  Census V1 vs A4: 0.
- KV: D27 not composed; ran on the D26 R3c candidate. LAG 214, BOTH 23, ledger 2 missing (lockup c00314fc08 diverged, 887cb2d06a).
  ABS HOP 1,032 / 47 types. Census D26 vs D25e3: 0.
- Calibration (508 placed kits, 3 die plans): matched planned hops flagged correctly 91-97 %, measured/plan median 1.01-1.09 (p90
  1.17-1.29). 87-96 % of measured >300 um legs match no planned station hop (logic / core legs): plan geometry covers the station class only.

## Open
- J6: run `event_census.py run` (J5 -> J6 plan) + `plan_geom_census.py run` on the candidate before its bind (S81-J6-ASSEMBLY asked).
- KV D27: same on the compose.
- UNREG_READ GAP, 267 types unmeasured (S81 239 + QC 28): the check reads a kit RTL closure (kit rtl/ + config.mk) and the run host had no kit
  of those types (kits are spread over 6 hosts). These types are NOT shown clean: they are listed as UNREG_READ? in ABS-CENSUS.tsv.
  Fix: pass --kits roots from every gen host (rsync the small rtl/ + config.mk of the newest kit per type), or resolve the closure
  from the tree. Successors: the die lanes now run the three tools on their own composes; FABLE-PD-S81-1840 owns the unplanned long legs.
- RESET_LEG only sees planned seats (relay_depth / reset-named relay_sites); taps made by reset_tree.py at gen are not in the plan.
- FLOW-NOADV-R3: pin form (tools_sha 'j5tree' label) still unmeasurable.
