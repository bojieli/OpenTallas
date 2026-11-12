# QC-VIS-RESITE 11-12 (S2 type floorplan event for DIE-QC-99)

Covers the 27 QC types whose VIS / CORE-PLACE-1 placement was reverted from the 12:00 event: 16 st_a/st_b and 11 stm.
Base: plan_qc99_s25.json e4820bd9d97c (branch claude/qc-event-s25-1111@4e2764d237). Result plan: plan_of_record/plan_qc99_s25_vis.json.
DO_NOT_COUNT (plan event only, nothing built).

## Verdicts
- **10 stm types ADOPTED** (ROMs moved to the N stream/table-write window, rd_out pins facing N, intent sheet INTENT_stm.md from VIS-TRIAGE-QC).
  sle_stm_v1__cl27746664, sle_stm_v1__clbe630b9c, sle_stm_v2__cl55be2264, sle_stm_v2__cl7b3062fa, sle_stm_v3,
  slw_stm_v1__cl05fc43f7__cl2086fa2c, slw_stm_v1__cl05fc43f7__cl389df4e9, slw_stm_v2__cl1ca9c415, slw_stm_v2__cl9beb65e6, slw_stm_v3.
  route_supply p99 (current main tools): 1.03-1.35 (mstreet_H between the mid-type ROMs) -> 0.62-0.84; GRT-only probe (VIS-TRIAGE-QC) usage 13.80% -> 13.12% (sle), 13.67% -> 13.12% (slw), 0 overflow both.
- **slw_stm_v1__cle34a73c3 stays reverted**: its landing collector is rooted at a local relay (collector_root_node rst_n_t8); collector_reattach / landing_collector.reattach_sources refuse a rerooted collector ("requires an explicit parent seam event"), so its collector sources cannot follow the re-solved reset tree. Same placement gain is available (p99 1.151 -> 0.842) once that tool gap is closed.
- **16 st_a / st_b types stay reverted: the VIS placement is worse.** Station re-site itself worked (ft_nudge: 0 'station cells/sites intersect physical macros' left, station counts unchanged), but on current main tools:
  route_supply p99 0.86-1.02 -> 1.31-2.08 (new street_H/V and ring_H hot bands where the 4 region columns pack into the S rows), explorer bit-mm +20-29 %, G0C +14 ERRORS (st_a btab origins 341.28 / 453.6 off the 8.64 lattice) and new G0C-GEOM warnings (r2r 455-465 um > 405 on b_hw_ctl_hc0/hc3 ring->s1, clock_reach 365-452 um, tap sinks 1608 > 1500); VIS-TRIAGE-QC GRT-only probes: usage 12.66 -> 12.83 %, 12.04 -> 12.30 %, 8.10 -> 8.61 %, 8.48 -> 9.05 % (all worse, 0 overflow both). The st_b kit worst path (-364 ps scale_wait SRAM -> region multiplier) is region-local and does not depend on where the region sits.

## What the event changes (stm, per type)
1. hard_cores[].origin_um / orient of the 4 ROMs (VIS positions). The VIS origins sat on the 4.32 half-lattice (G0C 'not on the 8.64-um lattice'); the 4.32 residual cannot be carried in track_offset_um (schema: |track_offset| < BASE_LATTICE_UM 2.16), so each origin moves to the nearest legal 8.64 lattice point (<= 4.32 um per axis, no overlap, inside the outline). No re-shape, no re-pin; track_offset_um unchanged.
2. Structural follow-up found by the strict bind: these types use clock.tap_mode "density", so taps are re-derived from sinks and macro boxes and renumbered (71..126 taps, count changes by -2..+1). Then
   - forwarded-clock exports (landing_contract.pins[].source_clock_port/_tap) re-point to the new tap nearest the old tap's site (max shift 71 um, within the 200-um tap radius);
   - the published reset collector_tree is re-solved with the current tools (added_tap_recentre.republish), plan AND landed sidecar collector.types[t].tree: reset depth 4 -> 4, root/outs/core_resets unchanged, max hop 378-380 um;
   - collector_local_sources / collector_children follow the new tree (collector_reattach.py: PASS, +0 collector cycles, max source hop <= 405).
   Without step 2 the strict bind failed: 'forwarded clock source clk_t72 is not a planned physical tap input', then 'collector rst_n_t74: reset-tree relay absent'.

## Gates (epyc9, tools = origin/main e49b6ac817 + s25 branch: check.py d255186f2d6c, route_supply.py 51d6c2430ed5)
- schema.validate: PASS (0 errors).
- G0: 265 ERR / 296 WARN, base 265 / 296: 0 new, 0 gone. G0C: 313 ERR / 552 WARN, base 313 / 552: 0 new, 0 gone.
- station_lint: 3 NONMONOTONE (same 3 as base), 0 inverted.
- strict bind (src_s25fix branch tree incl bind-strict-src, sidecar = sidecar_pv_vis.json ebb51e036c35): errors 0, BIND_RC 0, bus_groups.json byte-equal to the s25 bind (315252676904).
- EQ: no bus, ft slot, station, register count, outline, pin, face window or latency changes; only core positions, density-tap names and the physical reset relay tree (same depth) move.

## Stacking on s26 (advisory)
Applied the same two steps on the local, unpushed s26 composer plan (epyc8 wt/qc-event-s26 plan_qc99_s26.json 779178a990b5, which changes only clock{} of these types): apply OK (same tap remap, max 71 um), collector_reattach PASS (+0 cycles), G0C (main tools) 358 -> 358 ERR, 0 new. The s26 composer re-runs both steps with ITS sidecar and gates; nothing in this delta conflicts with the s26 ring-bond / hc1-hc2 / tap-merge items (hard_cores of these 10 types are untouched by s26).

## Files
- delta_stm_vis10.json: the event (changes + the s25 'before' each core must still have).
- apply_vis_resite.py + collector_reattach.py (repo tool): apply on s25 OR s26:
  `python3 -I apply_vis_resite.py PLAN delta_stm_vis10.json STAGE.json --repo REPO --sidecar SIDECAR SIDECAR_STAGE.json`
  `python3 -I tools/die_plan/collector_reattach.py PLAN STAGE.json OUT.json REPORT.json --sidecar SIDECAR_STAGE.json SIDECAR_OUT.json`
- sidecar_pv_vis.json.gz: the republished landed sidecar for the bind (base sidecar 9f6e6f721b61 = s25 src_s25fix).
- evidence/: gate logs, G0/G0C diffs, route_supply TSVs, tap remap + reattach reports, bind summary, the not-adopted st candidate (delta + station re-site ledger + diffs).
- Pictures (explorer type view before/after with --supply, all 27 types): localhost scratchpad coreplace/qc-vis-resite/pics/.
