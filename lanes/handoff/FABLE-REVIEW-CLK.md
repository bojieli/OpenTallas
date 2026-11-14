# FABLE-REVIEW-CLK handoff (Fable; clock/timing review S81 + KV). Started 2026-11-14 04:45 PST

Work dirs: intel1 /srv/opentallas-scratch2/claude/fable-review-clk (B below); launch logs intel2 ~/frc-logs/.

## 1. S81 leaf/slice cross-tap hold (COORD/OWNER top priority, posted 06:3x) -- rule R-CLOCK-7

### Measured (ot_s81sl_leaf__t42, wave 7073a6b4a59 attempt_5 4_cts.odb = after CTS, before any hold repair; FF, placement RC,
### FIX-HOLDSTALL's gate script; B/hs: sweep.log, cls2.log, cls0.log, hold_class.tsv, hold_class0.tsv)
- As built: 2,923 register-to-register hold endpoints, worst -206.2 ps. 2,882 are cross-tap, 41 same-tap (worst -17.7).
  By kind: glue flop -> glue flop on two grid taps 1,935; flop -> hard core 705; hard core -> flop 242.
- 2,033 of the 2,882 sit on six tap pairs: clk_t11/clk_t24 895, t23/t24 328, t11/t23 280, t23/t25 170, t11/t19 158, and the
  core pairs clk_c1/t18 262, clk_c3/t23 202, clk_c17/t24 148. The endpoints are station pipelines (zero or one cell between
  the flops): vp g_hig cst gd_s 1,059, vni gd_s 339, driver_hw_d 238, vp g_hog gd_s 234.
- Why those taps: the nearest-tap split put 4,246 sinks on clk_t23. The 1,500-sink cap pass then moved 2,032 of them to
  clk_t11 and clk_t24 (both end at exactly 1,500) and clk_t23 keeps 2,214. The cap pass cut the pipelines.
  The type has 36 grid taps for 10,825 glue sinks; 20 of the taps carry 35 sinks or fewer.
- Worst path, term by term (-206.2): die window on the launch tap clk_t11 144.0; kit insertion clk_t23 minus clk_t11 at FF
  74.6 (t11: six CTS levels, 139.6; t23: five tap-balance delay cells + four levels, 214.2); hold uncertainty 25.0; library
  hold 12.2; data 49.7 (clk->Q 39.1, one INV 10.3, wire 0.3).
- The kit's own tap balance ends at "tap mean insertion 182..365 ps (spread 184, target 250), 199 delay cells".
- Window sweep (all 61 tap ports, same ODB): window x1.0 2,923 / x0.5 1,401 / x0.25 914 / 0 ps 367 (worst -64.9; 326 cross-tap
  on t23/t24 211 and t11/t23 88, 41 same-tap). Uniform window on every port: 20 ps 645, 45 ps 1,079, 60 ps 1,353, 100 ps 2,372.
  That is about 20 endpoints per ps of window, on top of a floor of 367 that the kit makes by itself.
- Die side of the same partition (s_4N_L0), DIE-PROTO-1 B1 routed H-tree: 36 glue taps, 34 with 126 stages and 2 with 128,
  routed arrival spread 185 ps TT / 178 FF; per-port need median 150, max 212. The plan value 182 was measured on an older
  die clock (G50 proof). Equal stage count does not give equal arrival: leaf-to-tap legs and loads differ.

### Reading
- The debt is proportional to the window and the pairs are zero-logic. No die clock delivers 36 separately routed taps of one
  1.4-mm type inside ~5 ps, so a tighter die clock cannot reach 100 endpoints: 45 ps still leaves ~1,080, 0 ps leaves 367.
- The only class that is small is same-tap: 41 endpoints for the whole type, although most flop pairs are same-tap.
  So the fix is to put the pairs on one tree. The split into 36 taps is not needed by the load: 10,825 sinks is one small tree.

### R-CLOCK-7 (S81 leaf and slice_station first; every die's types by the same test)
a. ONE glue tap per partition type when the type has <= 16,000 glue sinks and its long side is <= 1.5 mm: every glue flop
   stays on port clk and CTS builds one tree. S81 leaf: 10.8k sinks, 1.44 mm -> one tap.
b. Larger types: grid taps on a pitch >= 600 um (at most 8), and the domains are cut by register group (a station chain, a
   ring, a FIFO is one unit: OT_TAP_GROUP_RE / chain affinity), never by sink count. tap_max_sinks is not a reason to add or
   split a tap (LIMIT-BIND-1 already made it info-only). The taps B3t added on 36 types for the 1,500 cap are withdrawn.
c. No tap-balance delay cells between taps of one type. With one tap there is nothing to balance; the kit's measured
   insertion is written to the type (clock.insertion_ps) and the die delivers that tap early by insertion - common
   (the early-tap delivery of R-CLOCK-6 i, already built for core taps).
d. Hard cores keep their early core tap at the core (R-CLOCK-5). Their window is the measured die need + 10, capped at 100
   (R-CLOCK-2c); the flop <-> core pairs (947 on t42 at windows 60..182) are the only cross-tap class left and are built by the
   pre-GRT hold step. Pilot next: the core clock pin as a sink of the glue tree (macro insertion delay), which removes that class too.
e. Check, printed by every kit after the tap split and before CTS: cross-tap pairs with at most one cell between the flops.
   Target <= 100 per type. Over the target = the tap domains are wrong; fix the domains, do not repair.
Plan delta per type (DIE-S81-92, B3x): tap grid pitch >= the outline so the grid yields the one tap at clock.tap_um;
added_taps empty; tap_max_sinks removed; per_port_ps of the removed ports dropped; core taps unchanged.

### Cost
- Cycles 0, area 0 (199 delay cells and the 7,319 hold buffers of FIX-HOLDSTALL's t42 build go away or shrink).
- Kit insertion: ESTIMATE 240 TT / 190 FF for a 10.8k-sink tree (today clk_t23, 2,214 sinks, is four levels = about 130 FF
  without its pads; two more levels for 10.8k). The pilot measures it.
- Die clock: S81 taps drop from 20,576 to about one glue tap per partition plus the core taps; the die DME gets faster and
  die routing scatter inside a type stops mattering.
- Every type that has more than one grid tap changes its clock ports and SDC, so it re-kits. On S81 that is nearly every type.
- NOT measured yet: the single-tree hold count on t42 (pilot launched, section 1b), other types (S81-TAPSKEW table).
