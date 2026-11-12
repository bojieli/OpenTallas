# S81 ready12b plan with the insertion-balance estimate (S81-CLKBAL-1, 11-12)

Base: ready12 = ready12ng, plan sha256 77cad171c6ee (bind running on epyc8). ready12b is a type-local delta on it.
Evidence: branch claude/s81-clkbal-1112 (events/s81_clkbal_1112/: pairdump.py, solve.py, report.py, trims_ready11r.json, residual_hops_ideal_gt250.tsv).
Model: DIE-RECHECK-1 die_sta_related on ready11r db1da17a93ab, nominal, CPPR, landing window 416.5 ps. Every one of the
3,016,331 landed pairs per corner is evaluated (not the 780 rows only); damage = max(la-ec-cr, lc-ea-cr).

## 1. What the 780 landed hops are

780 (TT) / 568 (FF) partition-pair hops over 416.5 ps. Damage = difference of the clock arrival of the launch and capture
taps, i.e. the clock-tree distance between two parts that are neighbours on the die. Tap late arrival spans 556..7552 ps
(398 parts; part means 656..7449). The feed is a BFS spanning tree of the abutment graph (feed_bal.py, depth 19), so die
neighbours in different branches differ by whole branches of insertion. Groups over the window (TT): frame-frame 370,
leaf-leaf 114, svc-svc 44, station-station 34, sliceC-sliceC 26, leaf-station 23+22, sliceC-leaf 22+22, lk-lk 20, station-frame 22.

## 2. Insertion balance: the numbers

All figures are from the model, partition granularity, worst case over all tap pairs of a part pair. FF offsets = 0.843 x TT
(measured FF/TT late-arrival ratio of 20,414 taps, p10..p90 0.840..0.846).

| scenario | TT hops over | FF hops over | max damage TT / FF | cost |
|---|---|---|---|---|
| baseline (ready11r) | 780 | 568 | 1616 / 1356 | none |
| IDEAL equal: every part mean arrival raised to the latest part mean (7449 ps) | 0 | 0 | 378.8 / 303.9 | mean +3.37 ns, max +6.79 ns per part |
| LEAST pad-only trim, 30 ps margin, d>=0 (difference-constraint solution, 363 of 398 parts trimmed) | 0 | 0 (0 at tap-pair level too) | <= 386.5 by construction | mean +1.13 ns, max +3.41 ns, sum 409 ns, ~1.64 m of added NDR wire at 0.25 ps/um |
| least trim clipped at 2400 / 1600 ps | 97 / 284 | 67 / 202 | | |

Intrinsic infeasibility: none (no part pair has Pmax+Qmax > 2W; same-part pairs max 414 ps tap spread, none over).
Max late arrival never rises (7552 ps before and after): all trims stay below the existing latest tap.

Headroom problem: even the IDEAL balance leaves worst damage 378.8 ps TT (37.7 ps headroom: tolerates only +-19 ps
per-part insertion error; FF 112.6 ps headroom). The residual hops under ideal balance (>250 ps: 83 part pairs; >300 ps TT: 5):
- bk_sel->gunit 378.8, s_4N_x06<->bk_sel 365.5 (both directions), s_6N_x06<->bk_sel 353.6 (both directions); FF: s_4N_x06<->bk_sel 303.9 and bk_sel->gunit.
All five are the bk_sel family (22 HARD ports, the known late capture clock on the h4_15 sub-tree). Those need the
+1 register (REACH-FIX-1) regardless, plus the bk_sel__t2 early landing. List: residual_hops_ideal_gt250.tsv (88 rows).

## 3. Can balance be implemented at compose? (no, not as a plan stage)

- A trim is a per-part ADDED insertion. The kit carries it only as (a) per-tap pad cells (`--tap-pad`, DIE-KV-5): the least
  trim needs 1,056,221 BUFx24 pads (sum over 20,555 taps of ceil(trim/25 ps)): infeasible; or (b) extra feed-leg length on the
  parent->child feed edge: the trim is not monotone along the feed tree (352 of 397 feed edges have child trim < parent trim,
  min edge trim -998 ps), so edge snakes cannot realise it; the monotone closure costs 1,339 ns of summed trim.
- The plan schema rejects unknown clock keys (schema.py:1588), so a `clock.insertion_trim` plan key would need a schema change,
  a consumer in feed_bal/ot_clk, and a bind change, all before the 11-14 24:00 cut. A key nobody consumes balances nothing.
- Conclusion: the ready12b plan has NO insertion-balance composer stage. The balance is a CLOCK-KIT change (die clock flow), see 4.

## 4. Recommended implementation (clock flow, not plan)

Build the S81 die clock as the balanced-by-construction H-tree (tools/die_plan/die_clock.py: every root->tap path has the
identical cell/wire sequence; last-mile padded wire per level, shared by all taps below, so no per-tap pads) instead of the
BFS feed (link_htree / feed_bal.py). The model says equal arrivals clear all 780/568 hops with 38 ps TT headroom; the measured
residue of that tree decides. A run of die_clock.py build on ready11r was started (intel1
/srv/opentallas-scratch2/claude/s87bind/clkbal_1112/dieclock_build, log dieclock_build.log); its `sta`/`report` give the real
tap skew and the real related-pair damage. Until it reports, "0 hops by estimate" holds for the ideal tree only.
Cost to check before adoption: insertion rises to the farthest-path level for all taps (core-tap early_ps contracts,
clock.common_latency_ps 250, kit-contract hold window W 21 / need 137 ps, 9,076 FF hold contract pairs) and clock power.

If the balanced tree is rejected, the only remaining lever is +1 register on every over hop: 780 TT part-pair hops (list
s87bind/reach_hops_ready11r.tsv, REACH-FIX-1), at a cost of a register per landed bit on 780 hops.

## 5. ready12b item list and stage order (all on top of ready12ng 77cad171c6ee)

| # | item | owner | status |
|---|---|---|---|
| 1 | VISLAYOUT3 stage5 fixed-slot leaf (fam5N: street/sliver/tap legalized positions, add_regs) | VISLAYOUT3-S81-LEAF | fam5N running; stage5 relative to ready12ng; stage4b already in ready12ng so the kv_leaf t3/t4/t5 revert is NOT needed |
| 2 | STREET-RULE-1 pass 2 types not covered by 1 | STREET-RULE-1 | bind in flight |
| 3 | X-TIER-OTC M8/M9 lanes t1/t8/t12/t55/t58/t72/t75 | X-TIER-OTC | READY after its bind |
| 4 | DIEREVIEW resign stage (51 RESIGN signed types: early landing on need>cap ports, c1x_C t4/t8 hop re-place, svc_hi_rs__t6 7 hops) + measured serdes windows (content already in ready12) | S81-DIEREVIEW-1 | table done; stage in progress |
| 5 | REACH-FIX +1 register: the bk_sel family hops (5 TT/3 FF part pairs) if the balanced die clock is adopted, else the 780 TT hops | REACH-FIX-1 | list delivered |
| 6 | serdes clk_pma_rx single tap of 22k sinks: split | REACH-FIX-1 | not started |
| 7 | gear delta (stage g2_gear_nudge + landing_width_sync_1112.py + manifest asbuilt_f_s87r12g.json) | BUS-GEAR-1 RTL by 11-13 18:00 | conditional; clears the s_2N_L1 cut 0.72>0.6 |
| 8 | balanced die clock (kit flow, no plan change) | S81-CLKBAL-1 / DIE-RECHECK-1 | die_clock.py build running |
| later | centre re-pack inside the lattice (S81-LEAF-FLOOR-1 table) | after ready12b | |

Order: 1 -> 2 -> 3 -> 4 -> 5/6 (hop list recomputed after 1-4 move cores/stations) -> 7. Types renamed by the col_h split (clones)
must be addressed by clone name in stages touching col_h types; the dead-input proof stays last.
Each stage needs G0 + EQ and one combined strict bind of ready12b; the clock kit change has no bind.

## 6. Risks
- Balanced tree residue unknown until die_clock `sta/report`: the ideal model leaves 37.7 ps TT headroom and a 5-hop bk_sel residue.
- Raising all insertion to the latest level interacts with core-tap early contracts and the FF hold contract (-116 ps / 9,076 pairs).
- Partition granularity: sub-part tap spread (p50 192 ps, p90 238, max 414 ps) is inside the model through the worst-case pair maxima, but region-tree balance (25 types / 174 ports over the 208 cap) is a separate item.
- Pad-only/least-trim numbers are not realisable with the present kit knobs (section 3); do not plan on them.
