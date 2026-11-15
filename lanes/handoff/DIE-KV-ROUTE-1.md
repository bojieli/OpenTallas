# DIE-KV-ROUTE-1 handoff (2026-11-14 ~22:00 PST)
## Scope
First die-level detailed-routed DB for KV (qwen_kvsys). Plan: kvgeom5 plan_c (sha 8301f154d3b2; KIT-OPS-5 has NOT posted ADOPTED for kvgeom6 as of 21:56, switch only if it does; kvgeom6 differs only in clock core_taps/tap_pair_affinity). Run host epyc2 (212 GB free RAM, 58 GB disk free: use epyc8 scratch3 if disk tight).
## Shared flow with DIE-HEAD-ROUTE-1 (COORD order: ONE script, parameterized by die)
PROPOSAL (DIE-HEAD-ROUTE-1: reply in the queue if you object): DIE-KV-ROUTE-1 writes the shared script, because the chain is already mapped. HEAD-ROUTE-1 supplies the HEAD config (plan sha, ot_clk yaml, signed-view dir) and tests it first, since HEAD has most types signed. Path (epyc2+epyc8): /srv/opentallas-scratch2/claude/die-kv-route-1/shared/die_route.sh DIE CONFIG.env TAG ; git copy committed later under tools/die_plan by the merge lane, not by me.
Stages (all heavy via ot-run --priority die, docker openroad/orfs):
 S1 kit   : ot_clk.py kit <die yaml> (= die_trial kit: plan-shape abstracts, clock H-tree/regional tree, grt/ route.v + obs.tcl + tracks.tcl, psm/pdn.tcl). Existing recipe: epyc9 die-proto-1c/kv/kv_chain.sh (kit ~17 min).
 S2 views : signed abstracts. For each type in INDEX.tsv (kind t/c, ARCHIVED-BOTH) run openroad read_db + write_abstract_lef into VIEWDIR/<type>/<module>.lef; kit --views VIEWDIR replaces the plan-shape abstract with the closed view. Unsigned types keep the plan abstract, listed as FLAGGED in views_report.tsv.
 S3 assemble: combo.tcl (mk_combo_kv.py) -> read abstracts+route.v, initialize_floorplan, ot_place every partition and hard core (R0/MX/MY/R180), pins, die PG (psm/pdn.tcl: M8/M9 grid), clock tree nets. Writes die_top_pre.odb + .def.
 S4 route : global_route (ADJ 0.75, M4-M7, clock/pdn M8-M9) -> detailed_route die-top nets only (partitions are blackbox macros). Nets with abutted pin-to-pin seams (pin rects touch/overlap at distance 0) are counted and excluded from DRT: report n_total, n_abutted, n_routed.
 S5 report: DRC by class + location (seam / channel / corner / over-core) from the DRT drc report, overflow, runtime, RSS, die_top_routed.odb path for lv_extract.py.
Prior measurements (kvgeom4 g4): 202,491 GRT nets, 32,281 clock nets, 0 overflow, GRT 2.5 min, 7.5 GB RSS. Memory is not expected to need >400 GB.
## Status
- 22:00 read chain; no run launched yet. Next: S3/S4 script on epyc2, kit from kvgeom5 src /srv/opentallas-scratch2/claude/kw45/src_kv_kvgeom5_pgL.
