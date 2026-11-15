# FABLE-HARD-KV (Fable expert review, KV die hard problems) 2026-11-14 18:5x PST
Read-and-diagnose only: no builds launched, nothing killed, no kit file edited. Every number below is from the named log/report.
Confidence is stated per item; "MEASURED" = read from a log, "INFERRED" = my reading, not yet run.

## 1. kv3_pc (6 types): FF hold -385 / -440, 18-30 k endpoints, stopped at the structural gate

### Root cause (MEASURED): TritonCTS macro/register latency balancing puts 300-370 ps of skew BETWEEN tap trees
Kits: epyc2 kw43-wave-1109/.../kvgeom4/items/kv3_pc__cl254f2e73/attempt_2 and kv3_pc_v1__cl4ea58a5c/attempt_2 (4_1_cts.log, 4_cts_final.rpt).
- The pc types hold 8 hard cores whose ck pins have internal latency 312-318 ps (pcc) and 193-196 ps (pcf); type target insertion is 250 ps.
- CTS splits every tap that has a core ck pin into "clk_tN" (macro) + "clk_tN_regs" (registers) and then balances the registers to the macro's
  internal latency: `CTS-0033 Balancing latency`, `CTS-0037 Total number of delay buffers: 99` (cl254f2e73) / 75 (cl4ea58a5c).
  Taps without a core get none. tap_balance.tcl can only add delay, never remove it.
- Result, cl254f2e73 `OT_TAP_BALANCE done`: tap mean insertion 209..574 ps, spread 365 (target 250). clk=555, clk_t6=574, clk_t2=436, clk_t8=409;
  the no-core taps sit at 244-264. cl4ea58a5c: 193..565, spread 372.
- The kit's own TT report already shows the register-to-register paths (4_cts_final.rpt, path_delay min):
  cl254f2e73: u_hsl0...ctrl_es[107] (clk_t1, leaf at +48 incl. the -120 window) -> u_hsl0.ctrl_es[107] (clk, leaf at 568): slack -465.29;
  the capture clock path has 16 `delaybuf_N_clk` cells (22 ps each = 350 ps). Removal path clk_t7 -> clk_t6 (14 delaybufs): -260.78.
  cl4ea58a5c: cland ring dsel di -> y: -563.01.
- The kit warned about it: `OT_TAP_CORE u_kvpc0/ck[0] tap clk pin 316 + internal 312 = effective 629 ps (target 250) WARN internal latency
  312 ps leaves no room on a grid tap: needs an early core tap (clock.taps kind core, clock.core_taps early; pair.py --core-taps)`; 8 of 8 core pins out.
- Arithmetic: 365 ps tree spread + 120 ps tap window + 25 ps hold uncertainty ~ -385..-465. It is one family: any type with a core whose
  internal latency > the type insertion.

### On KV-102's finding (ring sender_ps -385) and the "measured sender" plan
- TRUE but not the gate blocker: the SDC does put `set_input_delay -min -385` on the 1,515 / 2,211 forwarded-ring inputs (OT_FWD_RING_MIN), and
  those are port paths (advisory). hold_gate.tcl only stops when the REGISTER-TO-REGISTER worst slack is beyond the stop
  (ot_hg_rr_stats; otherwise it prints OT_HOLD_PORT ADVISORY and passes). It stopped, so reg-to-reg is beyond -320/-400 in FF, which matches the
  TT -465/-563 reg-to-reg paths above. Per-type sender_ps will remove the port term and the gate will STILL stop on reg-to-reg.
  (INFERRED for the FF number: I did not re-run FF STA; the TT report and the gate logic are measured.)
- Soundness of per-type measured sender minimum (do it, it is right for the ring ports): (a) measure at FF on the sender's routed/CTS DB as
  min over ALL instances and bits of (data-out arrival - fclk_out arrival) at the sender ports; (b) CPPR: credit only the path shared up to the
  sender's fclk_out branch point (same tap), nothing die-level; (c) keep the 12.5 + 12.5 ps seam uncertainty and add the die data-vs-fclk wire
  mismatch as explicit margin (>= 20 ps until a die STA pair measures it); (d) never take the max/mean, and re-measure when the sender's CTS changes
  (the sender types here have the same tap-spread defect, so today's measurement moves after the fix below: measure AFTER it).
- kvtap canary (clock.tap_offset): DEAD END for this failure. tap_offset moves port source latencies by <= 173 ps; the 365 ps is built inside
  the partition by CTS delay buffers and does not change. Expect the canary to return about the same WNS. Let it finish, do not wait on it.

### Fix (structural, plan + one kit setting)
1. Plan: `clock.core_taps = early` for the 6 kv3_pc types (tools/die_plan/pair.py add_core_taps, already implemented: port clk_c<k>, spine
   delivers it (latency - target) early) for the 4 pcc cores (318 ps > 250 - 40). pcf (196 ps) may stay on the grid.
   Alternative if early taps are not routable at the die: raise the pc types' clock.insertion_ps to 360 (318 + ~40 pin tree) so every tap balances
   up to it; the die then delivers the pc tiles 110 ps early (parent_early_tap_ps). Early core taps are cleaner; pick one, not both.
2. Kit: stop TritonCTS from re-balancing registers to core latency on tap kits: add `-no_insertion_delay` (the flag core_infra_late.tcl
   already uses; `-delay_buffer_derate 0` is the same lever) to CTS_ARGS in gen_phys for kits with clock taps. tap_balance.tcl is then the
   only balancer and it balances to the plan insertion.
3. Proof (one canary, no plan needed first): re-run CTS only from the existing 3_place.odb of kv3_pc__cl254f2e73 attempt_2 with
   CTS_ARGS += -no_insertion_delay. PASS = `OT_TAP_BALANCE done` spread <= ~60 ps (was 365) and hold_gate reg-to-reg within the stop; the remaining
   OT_TAP_CORE lines then show exactly what the early core taps must supply (about -68 ps for pcc). Then gen with core_taps early and run to sign-off.

## 2. kv3_io_ft_v1: 164-251 internal hold endpoints at 0..-31 ps

### Root cause (MEASURED)
Kit epyc2 scratch3 .../kvgeom4/items/kv3_io_ft_v1/attempt_5 (DRC 0, TT setup +17.64).
- 137 of 164 failing reg-to-reg endpoints are one family: u_cland_ft{0,2}_i ring u_dsel/y -> u_ft_ft{0,2}_o_0 q (zero-logic, cross-tap).
  signoff/ff/pair_skew.tsv: 28,400 pairs, min-side worst launch/capture difference 156.8 ps with CRPR 0 (p99 125): the pair sits on two taps,
  so it is charged the 100 ps tap window + 25 ps uncertainty + real tree mismatch (taps 242-269 mean, up to 296 max).
- 5_1_grt.log: GRT hold repair saw 484 endpoints at -118.85, padded 430 HB4 and stopped at `hold ws 0.01`, margin 0
  (`repair_timing -hold_margin 0`: OT_HOLD_FF_MARGIN = 0 overrides HOLD_SLACK_MARGIN = 5), on GRT-estimated RC.
- Detailed route then moved those zero-margin paths by up to 30.6 ps: 164 endpoints, 67 above -5, 45 at -5..-10, 49 at -10..-20, 3 below -20.
  So the "ECO rounds" chase the GRT-estimate-to-routed gap (~31 ps) on paths repaired to exactly 0. It is not an outline or congestion problem.
- ECO form A died in DRT at `[INFO DRT-0181] Start track assignment` after 13 min, peak 17.7 GB on a 48 GB cap, make Error 241: a tool crash in
  the route-keep (incremental) mode, NOT earlyoom. Its scoped repair itself worked (251 endpoints, 220 buffers).

### Verdict on in-flight forms (INFERRED)
- A2 (from grt, margin 5): repairs on estimates again and re-routes everything; the same ~31 ps gap applies to a 5 ps margin. Expect a miss of ~-25.
- B2 (margin 15 + repair-rc): better, still below the measured gap unless repair-rc really uses the routed SPEF. Let both finish (queued already)
  but do not start round 4 on the same recipe.

### Fix
- Now (setting, bounded): one build from the GRT DB with non-port (reg2reg) hold margin 40 ps = 30.6 measured gap + 5 + 4 slack, full detailed
  route (no route-keep). Cost bound: <= 484 pairs x 1 extra HB4 (47 ps FF) ~ 500 cells = 0.8 % of 59,356 logic cells (budget 10 %). Setup is not
  at risk: these are zero-logic pairs; port paths stay out of scope (that is what broke TT in ECO b5).
  Prove: sign-off ff_np >= 0 with tt >= -42 and OT_HOLD_BUDGET < 10 %.
- Structural (family, all landing-ring types; removes the padding instead of sizing it): in clock_taps.tcl assign the ring read register
  (u_cland_*_i u_ring dch u_dsel/y) and the ft_o stage-0 register it feeds to the SAME tap (one launch unit, as already done for hop latches);
  CRPR then cancels the 100 ps window and the pair needs no HB4. Prove on the 3_place.odb: pair_skew min_worst for these pairs < 60 ps and
  GRT hold endpoints before repair < 100 (was 484).
- Flow bug to file (KIT-OPS): prd route-keep mode crashes in DRT track assignment (exit 241); use --from grt until fixed.

## 3. kv3_hgi_v2 (hgi family): GRT overflow

### Root cause (MEASURED): the overflow is over-the-macro routing in zero-capacity tiles, not channel or W-strip capacity
Kit intel1 type-kvhgi2/fdC2/kit (plan kv101ns; same picture in fd03/fd04/fdC3 and v1a).
- Total routing use 6.65 %; M2 13.9 %, M5 5.5 %, M6 3.0 %, M7 2.0 %, M8 0.8 %. Final overflow M5 6 / M6 42 / M7 576, max 1 H / 3-5 V per gcell.
- congestion.rpt (final, 43 gcells): 42 of 43 lie INSIDE a head-core footprint, all `capacity:0 usage:1`; 37 are within 20 um of the core rim.
  At iteration 5: 2,093 of 2,171 inside cores. Congested gcells in the 95-um column channels or the W strip: 0 (1-4 vertical gcells outside in total).
  Hot rims: head2_e4 S rim (x 98-278, y 683-698), head2_e6 S rim (y 1007), head2_e2 (y 341-360), head3_e4. Nets: ectl landing-ring dsel nets
  and their buffers.
- Core abstract (macros/kv3_head_eighth_e6.lef, 216 x 216): 878 M5 pins on the S edge at 0.24 um pitch, 466 M4 pins on E, and 12 clk/rst_n
  pins at the core CENTRE (108 um deep; 154 such pins over the 16 cores). Detail OBS: M3-M6 cover ~99 % of the core area, M7 only 9.4 %.
  So the only resource over a core is M7 (vertical): a net that enters over a core cannot change column, and any jog needs M6 = capacity 0.
  The OT_CLK_LEAF_REPEAT lines show the centre-pin nets (clk_c*_tb0_tree routed 315-497 um, "over a macro").
  (INFERRED: that one-direction over-core M7 is what pulls the ring nets into the rims; the location data is measured, the mechanism is not yet tested.)
- The earlier "allow-congestion" forms did not test DRT: the main route finished (GRT-0115 warning), then the second global_route
  (after the clock-leaf repeater pass) raised GRT-0232 -> EST-0104 because -allow_congestion reached only the first call. The hook
  (run_kit.sh 14:48) fixes that; the hooked relaunches (fd04, fdC3, v1a, planB routeB2) are in GRT now and are the first real DRT test.
- GEOM "55-um channels" was render scale: plan channels are 95.0 um (x pitch 311.04) and are < 15 % used.

### Dead ends
- Column re-floor R1/r3 (+129.6 um on both hgi columns, die +2.3 %, 16 types re-kitted, 68 lanes +1 cycle): does not address any congested
  gcell; the W strip and the channels have none. Park it until the test below; keep the tooling. It may still be wanted for layout quality,
  but it is not the GRT cure and should not hold the hgi types.
- M9 forms: pointless (M8 is 0.8 % used and 70 % granted to the type) and against 12.1a. KV-HGI-REFLOOR was right not to launch them.
- PLACE_DENSITY / routability forms (fd03/fd04/fdC*): overflow 243-624 in all of them, same places; placement density is not the lever.

### Fix
1. Decide on DRT (already running): if a hooked form ends DRT with 0 violations, hgi is class B and the settings go to all hgi variants.
2. Structural, if DRT leaves violations at the rims: take over-core M7 away from signal nets so the router uses the channels:
   in the hgi kits' PRE_GLOBAL_ROUTE hook, `set_global_routing_region_adjustment {x0 y0 x1 y1} -layer M7 -adjustment 1.0` for each of the 16
   head-core boxes (clock/reset centre-pin nets excepted: they keep their route, or get it pre-routed), or have the view generator write a
   blanket M7 OBS for kv3_head_eighth_* outside the pin rims. Channels have > 85 % free tracks to absorb it.
   Prove from the existing fdC2 4_cts.odb (GRT only, ~2 h): overflow 0 and no congested gcell inside a core; then DRT.
3. Plan-level follow-up (next event, not blocking): the ectl landing bar at y ~1250 feeds S-edge pins of the row below it across a core;
   put each landing station in the row gap that the pins it drives face (gaps are 103.7 / 129.6 um), and move the 154 centre clk/rst_n pins of
   kv3_head_eighth_* to a core edge at the next core re-sign (centre pins force 108 um of over-core clock route each).

## Not done
- No FF STA re-run on the kv3_pc CTS DB (fleet memory-bound; the TT report + gate logic were enough to name the cause).
- No GRT net-level dump for hgi M7 (failed GRT wrote no odb); item 3 mechanism is flagged INFERRED.
