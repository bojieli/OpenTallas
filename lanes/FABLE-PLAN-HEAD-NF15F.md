# FABLE-PLAN-HEAD-NF15F (Fable PD review, 2026-11-17 08:40-09:15 PST) -- to HEAD-PLAN-R4, COORD

Read-only review of the NF15f event as it stands on epyc9 `/srv/opentallas-scratch2/claude/head-die-r/nf15e_e10/hr4`
(g1e plan sha c291c4a4, rs5 plan sha db29fb9f) and the bench at `claude/head-plan-r4`. Nothing launched, deleted or killed.

## Verdict
Do NOT launch type kits on the gated geometry. Three blocking findings with numbers (B1-B3), two corrections to the
status as reported (S1-S2). The credit fix itself is cheap and does not reshape anything.

## Status corrections
- S1. The isolation cases c24k / c24L / c24kx / c24kr are NOT running: all four died at build 16:10-16:11 UTC with
  `PINNOTFOUND: Parameter not found: 'RXH'` (their core copy is the pre-RXH file, the tb passes `.RXH`). No run.log exists.
  Only c16 (FAIL) and c24 (PASS) have results.
- S2. rs4 bind is FAIL, not pass: `instance parameter ot_s81hd_tile_p/u_core -> ot_s81hd_tile_native: not declared
  ['XO_HOP']` (instance_params_not_in_rtl=1). Cohort and LATCHECK did not run in rs4. rs4 G0 PASS 0 errors / 220 warnings.
  rs5 had only compose (714 rows) when read. g1e: bind PASS, cohort 26/26, LATCHECK 329/329, G0 0 errors / 216 warnings.

## 1. Credit depth
Mechanism (RTL read): perr is `relp[0] && relp[1]` (pairs A and B release in one cycle), ovf=0, no FIFO overrun. A credit
link with round trip RTT and depth D carries D/RTT beats per cycle; below the lane rate the beats bunch and the A/B
stagger (reference min gap 3) collapses. It is a throughput loss, not a lost beat.
Round trip from the landing header (ot_s81_mu72_lnland: TX ~14, RX ~12 edges with the +3/+3 landing) plus 2 per K stage:
| link | K stages | RTT | D for full rate | D for the 0.764 lane cap | at D=12 | at D=16 | at D=24 |
| TX, all 4 lanes (KTX 1) | 1 | 16 | 16 | 13 | 0.75 FAIL (measured x_ktx) | 1.00 | 1.00 |
| RX lane 0 (KRX 0) | 0 | 12 | 12 | 10 | 1.00 | 1.00 | 1.00 |
| RX lane 3 (KRX 2) | 2 | 16 | 16 | 13 | 0.75 | 1.00 | 1.00 |
| RX lanes 1, 2 (KRX 6) | 6 | 24 | 24 | 19 | 0.50 FAIL | 0.67 FAIL (c16, cyc 4878) | 1.00 PASS (gap 4) |
This matches every bench point (KTX 1 alone fails at 12; c16 fails; c24 passes).
- Uniform is right, per class is not: DR / CRED are one parameter for the four lanes of u_lep, and CORE_CRED sits in the
  one hard core `ot_s81hd_lep_pair` (PAIR 1, 4 instances, 777.6 x 492.48). Per class = two pair views for no area gain.
- 24 is the minimum with ZERO slack on lanes 1 and 2, and the base RTT is a "~12" comment, not a measured count.
  Recommend uniform 28 (still AW 5, DEPTH <= 32 limit), after measuring the RTT in the bench (credit pulse to credit pulse).
- Area: the lane landing FIFO is `ot_sram_1r1w2c_32x64_m1` (32 words): 12 -> 24/28 uses the same macros, 0 macro area.
  Flops: about +70 per lane in u_lep (one-hot we / mk / mrk / mtk / mhost / mks [DR-1:0]) + counter bits. I did not open the
  u_lep RX head memory macro (assumed the same 32-word family: check AR 5).
- Outline / re-typing: no outline change, no core reshaped. But the pair core netlist changes (CORE_CRED 12 -> 24:
  AW 4 -> 5, CW, and `LOCAL_POP(CORE_CRED==12)` turns OFF, bringing back the 42-load shared pop cone). So: one pair core
  rebuild + re-sign at the same outline, and change that condition to `CORE_CRED>=12` first.
- The tb also set the PEER e-lane to CORE_CRED 24. CORE_CRED is the core face only, so the peer type need not change:
  prove it with one bench case (DUT 24, peer 12) before any other type is touched.

## 2. Relay geometry
- B1. The gated plan does not carry the reach re-site. All 28 relay rects in g1e/rs5 equal the `old_rect_um` (allocator-column
  centres), 0 of 28 equal anchor_a2. That first placement measured 3,244 unassigned / 8,345 reach-infeasible, worst cut 1.30.
- B2. The re-site (anchor_a2, plan cfd6126b) is also UNRESOLVED: 59,089 nets, 2,387 unassigned + 3,275 reach-bad;
  worst full-rect cut 1.172 at x=1210 (12,950 / 11,046), mandatory 0.489. krx3_r0 hops 502.5 / 501.1 um (> 405);
  next longest ktx2_r0 399.5, krx2_r0 389.9, ktx3_r0 384.4 (under 405 with < 21 um to spare). The decision model had
  40,670 nets and 0 unassigned; the composed edge set is 45 % larger.
- Vertical access (vert_access.py, 25 % PG/clock share): 22 of 27 anchors over limit. Worst pout_r4 2.19 (2,153 / 984),
  krx1_r0 1.62, krx1_r2 1.56, pin_r2 1.51, pout_r0 1.42, krx2_r4 1.42. Site capacity is fine (FF utilisation 0.21-0.27,
  pin ratio 0.03). The anchors are too narrow in x (16.7-54 um): widen along x, about 2x for the worst six.
- B3 keepout (my rectangle test on rs5, 132 stage rects; G0 does not test this): 3 rects overlap hard macros
  (krx2_s1 and txi2_s1 on u_land g_t[1] SRAM, txi1_s0 on u_lep g_rx[2] bank[4]); 23 rects contain die-clock reserved sites
  (pin_s3 9, pout_s2 6). Orientation was not applied to core rects: owner to confirm the 3; the 23 only lose sites.

## 3. Reset integration
- Sites: 25 of 26 types have strap_rst_ph (hd_spn_end is the root, opted out). None lies in a hard core, an S-face window
  or within 0.5 um of a reserved clock site.
- Defect: 24 types use (10.0, 4.32) on M7. 10.0 / 0.064 = 156.25, off the track grid; the existing hd_tile M7 straps sit at
  (k + 0.5) x 0.064 (527.584 ... 562.4, pitch 2.176). Use 10.016. strap_sites.py also does not test W-face windows, reserved
  sites or PG; x = 10 is 10 um from the W edge.
- Labels: NOT valid for NF15f. They are the r4 old-clock model (min margin 118.8 ps, 9 parts < 150 ps), and no NF15f clock
  GEN exists; the event moves 53 LEP taps and 193 reserved sites. Type views are phase-agnostic, so this does not block type
  kits; it blocks die STA credit. Regenerate after the clock GEN, read duty at the entry taps.

## 4. Clock / congestion risks, and the one check
- 18,665 new state bits in a 361-um band; anchors hold 552-1,150 FFs each; sink bins and tap counts are from the old census.
- hd_lep0N corridor is the route risk (B2), not the cell count (365,496).
- ONE check before kits: rerun alloc_r4 + vert_access on the exact gated plan sha and require unassigned 0, reach-bad 0,
  every hop <= 405, vertical ratio <= 0.9, and stage rect vs {hard core, reserved site, pin window} overlap 0.

## 5. Ranked fixes
1. HEAD-PLAN-R4: put re-sited anchors into the composed plan, fix krx3_r0 (one more KRX stage on lane 3 or move the tail
   anchor), widen the six worst anchors, rerun the check of section 4 on that sha. Blocks kits.
2. HEAD-PLAN-R4: credit depth uniform 28 (24 floor), LOCAL_POP condition, RTT measured, bench cases 24/28 + peer-12 +
   RXH 1; rebuild the four isolation cases on the RXH core.
3. HEAD-TYPES-R4: rebuild + re-sign ot_s81hd_lep_pair (same outline) once 2 passes.
4. HEAD-PLAN-R4: XO_HOP bind failure (hd_tile republish vs ot_s81hd_tile_native), then cohort + LATCHECK on rs5.
5. HEAD-PLAN-R4: strap x 10.0 -> 10.016, add W-face / reserved-site tests to strap_sites.py.
6. FABLE-FIX-HEAD-RESET: labels + straps from the NF15f clock census after the fresh clock GEN.
Stop list: no hd_lep0N / hd_mesh kit on g1e or rs5 geometry; no per-class credit depth; no change to the peer lane type;
no die STA credit from the r4 labels; no M8 grant widening; no core reshaping.

## Not checked
Exact RTT (taken from the RTL comment); u_lep RX memory macro; hop reach on the gated rects (only the two earlier model
runs exist); die-level relay rows outside hd_lep0N; the 1.03 % outline growth abutment beyond g1e G0 0 errors; rs5 gates.
