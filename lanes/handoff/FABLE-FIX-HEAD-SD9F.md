# FABLE-FIX-HEAD-SD9F handoff (Fable; owner of HEAD type hd_serdes form sd9f through sign-off + export)
Logs: intel2 ~/fable-fix-head-sd9f-logs/. Lane dir: epyc7 /srv/opentallas-scratch2/claude/fable-fix-head-sd9f.
Gates R-MINIMAL: DRC 0, routed TT >= -42, internal FF hold >= 0 (port hold advisory).
- Started 2026-11-17 10:2x PST. Input: NEEDS-FABLE bundle in HEAD-TYPES-R4.md (eco1-4: DRT 0 viol, clk_t8 + clk_t11 unrouted). Step 1: DB diagnosis of both BPINs.
## 11-17 10:40 PST state
- DB census (E7 lane diag1.out, script diag1.py; renders lane render_orig/site_{t8,t11,t5}_{all,m4up}.png LOOKED): every tap BPIN (M7, 0.032 x 0.768)
  sits INSIDE a reserved die clock-tree site (hard placement blockage + M1-M7 routing obstructions, CLKSITE-RESERVE-1115); 19 of 22 tap
  pins are covered on M1-M7, the tap buffer abuts the site edge.  Original DRT: 17 taps shorted straight through the M7 obstruction
  (19 M7 Shorts); clk_t8 / clk_t11 instead reached the pin from die-reserved M8 (VIA78 on the pin, M8 run 1.2-1.6 um, stack outside the site).
- R4 ECO DBs: clk_t8/clk_t11 keep their wires through 5_2e_geom/pre_drt/guided and have NONE after DRT (5_2_route.odb), every other net routed.
  They were never in the rip list; DRT itself discards the kept M8/VIA78 routes after the M7 carve and does not re-route nets that came in routed.
- Experiments running (E7 lane, plain detailed_route with the kit arguments on R4 eco4 5_2_route.odb = 0 DRC, the 2 nets wire-less):
  xa = as is; xb = same + clean guides for the 2 nets (M7 strip down the carved column + M6..M1 stack at the buffer; no M8).
  Scripts drt_x.tcl, run_x.sh, guides_b.py; logs xa/drt.log, xb/drt.log; client logs intel2 ~/fable-fix-head-sd9f-logs/x{a,b2}.log.
  NEXT: the first with unrouted.txt empty + 0 violations -> `ot-run --mem 96 --hosts epyc7 --dir LANE --stage E7:head-types-r4/sd9f_eco
  --stage E7:fable-fix-head-serdes/sd9f_lane -- bash LANE/run_fin.sh xa fin` (private kit copy LANE/fin/hd_serdes: fill, final, abstract, antenna,
  pin audit, signoff_fable).  Then export (ffht_export.sh pattern) to AGIdock + rtx-pro s81_head/hd_serdes__sd9f_fable_1117 + INDEX rows.
- Routed timing of sd9f was NEVER measured: the original kit stopped at PIN_AUDIT (extra 1088 = pma_rx pads, declared 1057/1057 ok) before
  signoff, and signoff.py on any hd_serdes kit died in golden.sdc: phy_clock_export.tcl opens /work/phy_clock_export_binding.json for write
  on the read-only sign-off mount (TT/FF NOT RUN).  Fixed in the lane kit copies (copy+mv, .gen_orig kept) and on the branch.
  Measurement of R4 eco4 6_final (2 nets unrouted, estimate only): LANE/meas4/hd_serdes/signoff_meas4b (client log so_meas4b.log).
- FLOW branch claude/head-clksite-tap-escape-1117 (E7 lane repo, NOT pushed yet; base main bc7521448860):
  60c22e5730d CLKSITE-TAP-ESCAPE-1117 gen_phys.reserved_sites_tcl: escape column (pin + 0.10 um each side, full site height) in the pin-layer
  obstruction over each interior tap pin + 3-site E/W placement pad of route-obstructed sites (per-site opt-outs tap_escape / edge_pad_sites);
  on the sd9f plan + placed pins it emits 27 columns, M7 pieces identical to R4's carve (val_flow.py).  db7b25b131a PHY-EXPORT-RO-1117.
  Tests: test_clksite_kit (6), test_phy_clock_export (7), test_reserved_sites/test_die_rows/test_region_form_straps/test_s81_ca_band pass.
  NEXT: push + READY once the routed DB proves the geometry (both nets routed, DRC 0).
## 11-17 11:40 PST state
- ROUTE PROOF: xa and xb (plain detailed_route on R4 eco4 5_2_route.odb with clk_t8/clk_t11 wire-less; xb with clean M7-column guides)
  BOTH end 0 violations, 0 unrouted (LANE/x{a,b}/{5_2_route.odb,5_route_drc.rpt,unrouted.txt,drt.log}).  So the carve geometry routes;
  the R4 failures were DRT discarding the kept M8/VIA78 tap routes.  Any later ECO rips clk_t8/clk_t11 (us_eco.tcl does).
- TIMING (first ever routed measurement, sign-off frame; LANE/meas4/hd_serdes/signoff_meas4b): TT setup -105.88 (287), internal FF hold
  -15.48 (15).  ONE family: u_enc.ch_q[] -> pp1[]/pp0[] (252, 243 cross-tap) + u_syn.sc_q -> sp1 (35, pma_rck).  Same worst path at GRT
  -16.30: clock -28 both sides (cancels), data +92 ps (789 -> 881) = routed wire delay in the saturated encoder blob.
  Census tools: run_paths.sh, census.py, tapmap.py (register -> tap), run_q.sh + q1..q4.tcl (sign-off-frame queries / what-if).
- TIMING FORM = per-register capture skew (not a route ECO): the failing capture flops have launch-side setup +307 (TT) and FF hold room
  >= 62, so a delay chain in front of their CLK pin moves the slack.  List LANE/eco2_list/eco_list.tsv (mk_eco_list.py, CUT -15 TARGET -8):
  202 flops (pp1 169, pp0 21, sp1 12) with BUFx4 / 2xBUFx4 / HB4 / HB4+BUFx4 / HB4+2xBUFx4 (309 cells) + 43 hold pads (FF reg->reg
  hold < +3: BUFx4 or HB4 at the D pin).  STA what-if (set_assigned_delay on the pin's net arc, both corners, q4): TT -105.88 -> -14.90,
  FF reg->reg hold violators 15 -> 0.
- ECO2 RUNNING: LANE/run_eco2.sh xb eco2 (us_eco.tcl insert + detailed_placement: 352 new cells, 0 existing cells moved; 478 nets
  ripped; us_guides.py; drt_x.tcl).  Client log intel2 ~/fable-fix-head-sd9f-logs/eco2.log, kit log LANE/eco2/drt.log.
  NEXT: when eco2/unrouted.txt is empty and 5_route_drc.rpt has 0 violations:
  `ot-run --mem 96 --threads 16 --hosts epyc7 --dir LANE --stage /srv/opentallas-scratch2/claude/head-types-r4/sd9f_eco --stage
  /srv/opentallas-scratch2/claude/fable-fix-head-serdes/sd9f_lane -- bash LANE/run_fin.sh eco2 fin2` -> LANE/fin2/hd_serdes/signoff_fable/signoff.json.
  SIGNED -> export with scratchpad ffht_export.sh (epyc7, el hd_serdes__sd9f_fable_us_1117, base fin2/hd_serdes/run/results/asap7/dp_hd_serdes/base).
  If TT is short: rerun run_paths.sh on the fin2 signoff, regenerate the list from the new census, one more ECO round on eco2's DB.
- fin (xa, no timing ECO) is the route-only baseline record: LANE/fin/hd_serdes (expected NOT SIGNED on TT).
- FLOW branch still local (E7 LANE/repo, claude/head-clksite-tap-escape-1117: 60c22e5730d + db7b25b131a); push + READY now due (route proof done).
## 11-17 12:20 PST -- SIGNED
- ECO2 route (LANE/eco2): DRT 0 violations, 0 unrouted (1135 -> 367 -> 7 -> 0); 352 new cells, 0 existing cells moved; render
  LANE/render_eco2/site_t8_m4up.png LOOKED (tap wire leaves the site down the carved M7 column).
- fin2 (LANE/fin2/hd_serdes, run_fin.sh eco2 fin2): signoff_fable/signoff.json = R-MINIMAL SIGNED: DRC 0 (5_route_drc.rpt), TT setup -20.79
  (achieved 853.79 ps), internal FF hold 0 violators (complete census), check_antennas 0 nets (fable_fin.log; record field NOT RUN, advisory),
  sdc_lint PASS.  Advisory: port hold -22.57 (die STA), pin audit extra 1088 = pma_rx pads (declared 1057/1057 ok), drv.
- Route-only baseline (LANE/fin/hd_serdes, xa, no timing ECO): NOT SIGNED, TT -105.61, internal FF hold -15.79 -- kept.
- Export: el s81_head/hd_serdes__sd9f_fable_us_1117 on rtx-pro /home/ubuntu/signed-export-1114 and AGIdock /archive/opentallas-signed-1114,
  INDEX rows keyed hd_serdes (ffht_export.sh).  See the RESULT post for the ODB sha.
- OPEN for the die owner (HEAD-DIE-R): (1) swap the hd_serdes view; (2) the die clock cell stack must keep off the M7 escape columns;
  (3) 202 capture flops carry +20..+107 ps clock delay (useful skew) -- inside the type only, port timing unchanged.
- OPEN flow: branch claude/head-clksite-tap-escape-1117 @db7b25b131a READY posted (MERGE-OPS gate).  Not built: a GRT-stage derate for signal
  nets in >90% gcells (the -16 vs -106 gap was +12% data wire delay), and a flow form of the capture-skew ECO (us_eco.tcl / mk_eco_list.py).
