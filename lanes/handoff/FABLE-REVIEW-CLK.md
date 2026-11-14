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

## 1b. UPDATE 06:3x: pilots and the final form of R-CLOCK-7 (supersedes items a-e above where they differ)

### Pilots on t42 (no hold cell added in any of them; FF hold = reg-to-reg endpoints after CTS, TT setup the same way)
| form | hold endpoints | worst | setup endpoints | worst |
|---|---|---|---|---|
| as built: 36 taps, cap pass, absolute windows 60..182 | 2,923 | -206.2 | 1,351 | -260.6 |
| ONE glue tap (WITHDRAWN): 30 buffers per path, insertion 1,578 | 1,968 | -1,082 | 6,817 | -1,270 |
| cap pass off (clk_t23 keeps 4,335 sinks), same SDC | 2,183 | -189.2 | 1,379 | -280.5 |
| cap off + small taps folded (min 400 sinks / 450 um) | 2,230 | -206.2 | - | - |
| as-built kit, taps timed at their measured arrival on the regional DME die clock, tolerance +-0 / +-10 / +-20 | 438 / 777 / 1,082 | -89 / -109 / -129 | 432 / 500 / 568 | -260.6 |
| cap off + measured arrivals, +-0 / +-10 / +-20 | 36 / 201 / 524 | -57 / -77 / -97 | 281 / 350 / 496 | -279.7 |
Dirs: B/hs (pilot.log, pilotb.log, pilotc.log, offs_hold_*.log, offs_setup_*.log). Same-tap endpoints with the cap off: 9.
With the cap off and the windows at 0 the kit's own floor is 21 (367 with the cap pass); a uniform 20 ps window gives 58, 45 ps 443.

### What the die clock gives (S81 B3t, 98 landed regions, region DME, routed; B/s81/r98, table tap_offsets.tsv)
- Glue taps of one partition: spread median 65 ps TT (p90 96, max 244); leaf median 70, slice_station 50, col 66, svc 81.
  t42's partition: 59 TT / 51 FF (185 / 178 on the die-wide H-tree). The hot taps sit close: clk_t11 -7, clk_t24 -1, clk_t23 +17.
- So even a good die clock, read as one absolute window per port, is a 60-70 ps window = about 1,300 endpoints per type.

### Setup (COORD question)
- 923 of the 1,351 setup endpoints are the same windows seen from the capture side; they go with the fix (1,351 -> 281..350).
- The worst path (-260.6, -279.7 in the rebuilt tree) is not skew: flop driver_xwa_c_q -> SRAM u_b0 on the same tap, 1,066 ps of data. R-RTL item.

### Is it a modeling artifact (S81-TAPSKEW reading)? Partly.
- Yes: the kit charges every pair of a port the port's WORST die damage (its window), although the pair's own two taps differ by
  far less. Timed at the taps' own arrivals the same kit has 438 endpoints, not 2,923.
- No: the window is not free pessimism that CPPR would remove. Two taps are two die-tree leaves; their arrival difference is real
  (59 ps across t42 on the DME clock). The kit can only time it right if it knows each tap's arrival.
- Also real and kit-made: the cap pass (pipelines cut) and tap balance (182..365).

### R-CLOCK-7 (final)
1. Kit SDC: a tap port is timed at its ARRIVAL OFFSET on the die clock of record, with a tolerance, not at an absolute window.
   Per port p and corner (TT in constraint.sdc, FF in the FF overlay file that core taps already have):
     set_clock_latency -source -early [o_p - u]  /  -late [o_p + u]
   o_p = routed arrival of tap p minus the median glue tap of its partition (mean over the type's instances; a core tap's o_p
   already contains its early delivery), u = max(10, half the range over instances). The IO shift uses max o - min o + 2u.
   Plan key clock.tap_offset {per_port_ps: {type: {port: {TT, FF, tol}}}, source proof}. A type without a row keeps today's window.
2. Kit tap split: no cap pass (OT_TAP_MAX_SINKS = 100000). No tap is added for sink count; the B3t added taps are withdrawn
   at the next plan event. Small-tap folding is NOT adopted (measured worse).
3. Die clock: region DME on the landed regions (R-CLOCK-6). It is built before the kits and is the clock of record;
   die gate check = every tap of every instance inside [o_p - u, o_p + u] of its partition's glue median. A tap outside =
   STA re-sign of that type at the new offsets (no P&R unless hold then fails).
4. Remaining hold after 1-3 is built once before the first GRT (R-CLOCK-1). Expected on t42: about 200 endpoints at +-10.
   Under 100 needs +-5 or less, which is a frozen routed die clock; it is the target once the die clock is frozen.
Cost: 0 cycles, 0 area. Kits are tied to the die clock of record (re-sign STA when it moves by more than u).
Tool work: gen_phys.tap_window_tcl (emit offsets), die_sta_related (--kit-offset-out + the gate check), schema key.
Applies to: every type with more than one clock port on S81 (all families), KV (kv3_hgi*, pv, hg, pc; multi-instance types
get u from the instance range), QC (slw/sle_su, st). HEAD keeps its rp17 per-port windows until its next clock event.
S81 offsets from the r98 clock: B/s81/r98/tap_offsets.json (all 395 types).
NOT done: the tool change itself; a full kit run (route + sign-off) with the new SDC; KV/QC offsets.

## 2. Die clock architecture, S81 and KV (the original review task)

Gate (owner): routed related-pair setup >= 0 and hold >= 0; kit-window contract advisory. All numbers below: routed combo
GRT RC (50 it, overflow 0 / 0 / 0 on every run), nominal, CPPR at the last common node, declared core insertion.
Hold is NOT measured on any run (die_sta_related needs signed kit views: BLOCKED(kits)); what is measured for hold is the
per-port need against the kit window, and the t42 kit proof of section 1.

### Finding common to both dies
DIE-PROTO-1 ran a die-wide balanced tree. Neither plan is that form: both are landed plans. The clock regions are the
connected components of the plain-seam graph (ports not in clock.landing_network): S81 B3t 98 regions (= the regions of
the B3v sidecar, largest 10.1 x 4.2 mm), KV kv102sem_ftgrid 128 regions (= results/locality_1027/kv_land128_regions.json,
largest 2.2 mm). Related pairs exist only inside a region; region-to-region ports are rings.

### S81 (plan B3t 4b7f1e087434; B3w only rotates macros inside types, no clock change)
- Wrong today: the feed of record (clock.cohort s81_feed_bal19_1111) is per partition, 398 roots, and cuts 63 of the 98
  regions across feed branches. That is where the 1.1 ns related-pair skew and the -470 ps came from.
- Architecture: 98 regions from the sidecar; one root per region at the tap centroid; die feed along the region links
  (locality.py score --feed spt, root std_bg_54_0, depth <= 13, no balancing, no pads); region tree = delay-mode DME with
  early core taps merged; inv2, repeaters 250 um, stage model inv2_ndr_s81_g03b_refit.
- MEASURED (B/s81/r98): intra TT setup +420.3 (0 negative of 1,182,934 pairs), plain-seam TT setup +363.9. Die-wide tree was
  -470 / -409. Kit contract (advisory): intra need 208.5 against 39, seam 332.7 against 40; replaced by R-CLOCK-7 offsets.
  Worst region: bk_sel (damage 701.7 on its core tap clk_c0; glue spread 244), then s_7N_x13 slice_station__t51 (244).
- Rings: the bind has fixed 3-cycle rings (count_aligned false, 993 ports, landing_phase_sign UNMEASURED). On this clock
  |d| is median 1,018 ps, max 3,501: only 25 of 993 keep a stable sign at TT and FF (12 LEAD, 13 LAG); 968 need the
  count-aligned ring. All 993 fit DEPTH 4 on nominal arrivals (partition-level estimate, B/s81/r98/landed_classes.json).
  Model check with OCV (locality v3, r99 map): fish feed 934 DEPTH-4 + 59 DEPTH-8, 0 fail; DME region trees 200 fail.
- PLAN for DIE-S81-92 (one event, B4-CLK, after or with B3x):
  1. regions = sidecar regions (tool: B/frc_comp.py or the sidecar itself); feed: locality.py score --regions MAP --feed spt.
  2. die clock: ot_clk.py kit B/s81_r98.yaml (66 min on a loaded host), then B/proto_reg.sh (GRT + arrivals + die STA, 25 min).
  3. clock.tap_offset from B/mkoffs.py on the proof (R-CLOCK-7); bk_sel and slice_station__t51 get their own look first.
  4. rings: landing_network data_cycles_per_crossing -> count_aligned for all 993 ports, K and DEPTH from count_align_plan on
     this proof, K as straps (KV form) so a later clock move re-ties straps only; bind + LATCHECK + lane latency rows.
     Cycles move (pre-approved). This is the large item: every type with a ring input re-kits.
  5. phy_hbm has no clock tap and glues eng + six svc_lo columns into the 10.1-mm region; its dfi/hbmrd ports are PHY timing.
     Leave it out of the region graph (regions then: the svc_lo chain and eng alone).
- NOT measured: hold on real views, reset release, the count-aligned plan with OCV on routed arrivals, clock reach (the kit
  ran without --rep-reach-max / --rep-actual-max).

### KV (plan kv102sem_ftgrid plan_c f9abb1802590)
- The clock of record form (cohort tree_kv58: link_htree feed on 128 regions, inverter stages, DME only on pv_S_6, pv_S_7,
  sys_SW, sys_SE) is the right architecture; rings are already count-aligned with strap K.
- MEASURED: kva = that form on the current plan: intra TT setup +447.1, plain-seam +545.1 (0 negative); intra need 207.3
  against 130, seam 155.8 against 180; glue spread per partition median 85 ps. kvb = DME in every region: +444.7 / +591.1,
  need 232.6, glue spread median 98: no gain, NOT adopted. DIE-PROTO-1 die-wide wire-balanced tree: +555 / +554, need 113.9,
  but 4.26 ns mean insertion and wire pads; it is not needed because every long hop is a ring.
- Rings on kva: |d| median 528, max 1,290; all 3,754 clock landings fit DEPTH 4 on nominal arrivals. K must be re-derived on
  the clock of record (straps only).
- PLAN for KV-102: 1. keep tree_kv58 form; rebuild it on the current plan with B/kv_a.yaml + proto_reg.sh (33 + 17 min).
  2. count_align_plan / bind on that proof, re-tie straps. 3. hold: R-CLOCK-7 offsets (multi-instance types: tolerance =
  instance range; B/qwen_kvsys/kva/tap_offsets.json) instead of raising per-port windows to 160. 4. cap pass off in KV kits.
- NOT measured: hold on real views; CA plan with the bind's own K; data-path die STA.

### Scripts (intel1 B): proto_reg.sh (chain), s81_r98.yaml / kv_a.yaml / kv_b.yaml (ot_clk configs), run_s81b.sh / run_kva.sh,
rd.py (gate summary), lcls.py (ring classes), alltap.py (per-partition tap spread), mkoffs.py (tap offsets), tapsp.py, frc_comp.py.
Launch: ot-run --crit --hosts intel1 --mem 120 --threads 24 --dir B --priority die -- bash B/run_s81b.sh
Nothing of mine is running. No waiter is armed (all chains finished).

## 3. 11-14 follow-up: dropped tap_offset rows (eng__t1 clk_c0, bk_sel__t2 clk_c0/c4)
See queue RESULT to DIE-S81-92: offsets are declared early core delivery, not imbalance; judge residual = offset + (insertion - common). eng fine (+49 TT / -22 FF); bk_sel real residual 125 ps on u_tx and g_q[1], -68..-97 on g_q[0] = regional tree item. Script intel1 fable-review-clk/ec.py.
