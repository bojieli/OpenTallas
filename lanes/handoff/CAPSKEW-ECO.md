# CAPSKEW-ECO handoff (Sonnet; FABLE-CLOSURE-STRATEGY 11-17 lever 6)
Branch claude/capskew-eco-1117 @a225128886cc (base main 26f27e903e, 1 commit, 6 files in tools/die_plan). Lane clone epyc7 /srv/opentallas-scratch2/claude/capskew-eco/repo
(own warm bare capskew-eco/warm.git: the shared warm repo refused fetch because FABLE-FIX-HEAD-SD9F's worktree holds a branch). Gate clone epyc2 capskew-eco-gate.

## What
tools/die_plan/capskew_eco_run.py (+ post_route_drv/capskew_eco_{insert.tcl,guides.py,route.tcl}, test_capskew_eco_run.py): the sd9f ECO2 as a post-route tool,
same pattern as hold_eco_internal_run.py (first sign-off sessions -> STA dump -> plan -> insert -> guides + incremental DRT -> re-sign).
- Selection: flop D endpoints with TT setup < --cut-ps (-15) and FF reg->reg hold room > --hold-margin-ps (10); delay ladder BUFx4 20 / 2xBUFx4 42 / HB4 65 / +BUFx4 86 / +2 BUFx4 107 / 2xHB4 130 (TT ps) sized to --target-ps (-8),
  FF delay estimated 0.65 x TT and capped by hold room - margin; launch side (Q pin slack) must keep >= 10 ps. Broken reg->reg FF hold (< +3) gets a D pad.
- Limits (OT_LIMIT, RESULT.json, exit 4): capture flops <= 300, delay <= 130 ps, leaf clock pins only (no port net, no tap net of ot_clock_taps.json, <= 100 sinks; checked in Tcl before any change),
  planned setup gain >= 0.7 x deficit (worst slack, an unfixed worst endpoint counts), hold pads <= 100, PG obstruction count in == out.
- Exit: 0 SIGNED, 1 not signed, 2 nothing to do, 3 step failed (incl. dump/first-sign-off unit mismatch guard), 4 limit.
- eco_loop.py: OT_CAPSKEW_ECO=1 (default OFF) -> when the loop ends not-PASS and the base record fails only TT (DRC 0), capskew_fallback() runs the tool on the base DB; exit 0 adopts the signed DB as best (verdict PASS). Tests: capskew_enabled / capskew_case.
- Input DB must be unfilled (5_2_route.odb / 5_route.odb, or --db); the signed output is the re-routed DB as 6_final.odb for sign-off (same as the hold ECO). Fill/finish of that DB is the kit's usual downstream (not run by the tool).

## Replay (sd9f pre-ECO DB fable-fix-head-sd9f/fin/hd_serdes, route-only, TT -105.61)
epyc7 capskew-eco/replay2 (ot-run, exit 0 SIGNED): plan 201 flops / 308 clock cells / 45 pads (lane ECO2: 202 / 309 / 43), predicted -7.9; 0 existing cells moved, 478 nets ripped, DRT 1115 -> 363 -> 0, 0 unrouted, DRC 0,
PG obstructions 14538 = 14538; TT -20.86 (lane -20.79), gain 84.7 >= 0.7 x 105.6, internal FF hold 0 (record hold_ff PASS; port hold -22.57 advisory), verdict SIGNED. replay1 = unit bug run (get_property slack is already ps), delete when done.
Gate (epyc2, not epyc7): test_capskew_eco_run, test_hold_eco_internal_run, test_eco_loop, test_hold_eco_internal, test_kit_modes = 149 passed. Full die_plan suite NOT run.

## Open
- Not exercised: the eco_loop fallback end to end on a live kit (unit-tested only); a type where the launch-side check bites; a run with --first-signoff absent.
- The tool adds cells only (no re-fill / abstract); a kit flow that wants fill after the ECO must run its fill stage on the output DB.
- Not built: GRT-stage derate for saturated nets (the -16 vs -106 gap), per FABLE-FIX-HEAD-SD9F.
- Cleanup: replay1/replay2 (~15 GB each) under epyc7 capskew-eco; ot-delete after the merge.

# HOLD-MARGIN-FAMILY (CAPSKEW-ECO lane, FABLE-CLOSURE-STRATEGY 17:2x lever 1)
Branch claude/hold-margin-fam-1117 @54e6039579b9 (base main 26f27e903e; gate main 41129805aac GREEN 94/94, record ~/merge-queue/gates/54e6039579b9....json). Lane clone epyc7 capskew-eco/repo.
- tools/die_plan/hold_margin_family.py: QC/KV/HEAD type kits (plan dies qwen_compute, qwen_kvsys, s81_head) 40 ps; every core_flow.apply kit (svc + hard cores) 15 ps; S81/HBM unchanged.
  Overrides: die.hold_ff_margin_ps, type hold_ff_margin_ps (plan), per-item env OT_HOLD_FF_MARGIN_PS (wins), gen env OT_HOLD_FAMILY_MARGIN=0 (off).
- Reaches the kit: config.mk OT_HOLD_FF_MARGIN = max(caller, family) (GRT FF repair), OT_PREGRT_HOLD_R2R_MARGIN (new reg-to-reg pass in pregrt_ff_hold, ports excepted; only when pregrt is on for the type),
  OT_HOLD_FAMILY_MARGIN_PS (evidence), OT_HOLD_SETUP_GUARD_PS=0 (hold_guard_grt.tcl: chunked GRT hold repair stops when worst setup < min(before, 0); pregrt keeps its own TT fail-safe at the -42 ps gate).
- VERIFIED on a real generated QC type (gen.py phys qwen_compute die_plan cbf_q00, epyc7 capskew-eco/genchk*): OT_HOLD_FF_MARGIN = 40, FAMILY 40, SETUP_GUARD 0; with OT_PREGRT_FF_HOLD_AUTO=1 also R2R 40 and `all rr xt` in the kit tcl.
  `python3 tools/die_plan/hold_margin_family.py check KITDIR qwen_compute|qwen_kvsys|s81_head|core` reads config.mk back: run it on the first kit of each wave (exit 1 = the tools tree predates the knob; kits built from rt/<sha> only get it after this merges and ot-tools-sync materializes it).
- NOT done: replay on a routed QC L2 kit's pre-route DB (no 4_cts.odb of a QC L2 kit found quickly; GRT repair at 40 ps not measured: HB4 count, TT setup on padded ends, routed internal hold are the lever-1 item 4 read on the first kit).
  QC types where pregrt is neither plan-enabled nor AUTO get only the GRT margin (40), not the pre-route r2r pass. S81 col keeps its own 10 (OT_HOLD_FF_MARGIN_PS).
- Cleanup: epyc7 capskew-eco/genchk, genchk2 (+ .log).
