# FABLE-PD-HEAD-CLK 2026-11-14 23:2x PST: HEAD die clock, landed pairs on rp21z16 (run p16r)

Scope: technical PD only. Read-only on p16r (epyc2 `/srv/opentallas-scratch3/claude/die-head-route-1/head/p16r`), plus one
small diagnostic via ot-run (epyc2 `/srv/opentallas-scratch3/claude/fable-pd-head-clk/`, units oth-ubuntu-567180 and -647906).
No job, plan or kit was touched.

Status words: MEASURED = read from the p16r tree, arrivals, STA record, the plan, or my run. INFERENCE = fits the numbers, not proven.

## 0. Short answer

1. The landed "failure" is a wrong check, not a wrong clock. p16r judged the 564,864 landed pairs with the legacy
   half-period window (T/2 = 416.5 ps). HEAD's crossings are count-aligned rings (plan `clock.landing_network.
   data_cycles_per_crossing = "count_aligned"`, 427 forwarded-clock edges). For that form the nominal phase goes into K and
   DEPTH and is not held inside +-T/2 (RULEBOOK R-CLOCK-6c). `proto_die.sh` line 38 calls `die_sta_related.py` without
   `--count-align`, so the tool fell back to the T/2 model. LAND-HEAD 10-27 22:51 already recorded the same reading
   ("landed pairs still read the T/2 model FAIL until --count-align exists").
2. Judged as built (count-aligned planner on the p16r arrivals, my run): 427 of 427 crossings fit, 0 fail, 0 below 100 ps,
   worst margin 104.2 ps on both guards, 2,000-chip start-up simulation 0 violations. Limits in section 3.
3. The hop delay is die-level feed wire between region roots, 0.343 ps/um routed. It is not partition-internal CTS:
   p16r has no partition clock in it at all (0 closed views, declared 450 ps on both sides, which cancels).
4. Keep the architecture. Three real items remain: the count-aligned bind is stale against this clock (191 of 427
   latencies differ from the plan), the p16r readout is rise-only (START edges cannot be judged), and the intra-region
   arrival contract (44,303 pairs) is routing scatter in 400-ps local trees.

## 1. Why each hop adds 700-1,200 ps (MEASURED)

Die clock form (tree.json, `ot_clk_argv.json`): `link_htree`, root region sp3 at the die centre, 327 regions, 326 feed
edges from `feed_hk4.json`. Each region root is fed from its parent region's root through a chain of single inverters
(CKINVDCx16, one per ~117 um), then a delay-balanced local tree to the taps. 44,917 clock cells, 3.08 m of wire, up to 211
stages root to tap, tap arrivals 847 to 8,992 ps TT.

Split of every region's arrival, from the routed STA node arrivals (`proof/tap_arrivals_TT.json`):

| part of the path | min | median | p90 | max |
|---|---|---|---|---|
| feed, parent root to child root (ps) | 237 | 438 | 540 | 1,048 |
| feed wire (um) | 666 | 1,280 | 1,513 | 2,581 |
| feed stages | 6 | 11 | 12 | 19 |
| local tree, root to tap mean (ps) | 130 | 419 | 467 | 837 |
| local tree difference, child minus parent (ps) | -410 | -6 | +53 | +213 |
| tap spread inside one region (ps) | 5 | 67 | 90 | 106 |

- Hop (tap mean, child minus parent): median 414, p90 529, max 1,194 ps. Hop = feed wire + difference of two local trees;
  the second term is near zero. So the hop is wire flight time.
- Spine regions are 1,382 x 2,074 um, root to root 2,369-2,581 um of wire: sp3->sp2 762 ps, sp2->sp1 1,048, sp1->sp0 768,
  sp3->sp4 819, sp4->sp5 864. The "sp1 against sp2, 1,193 ps" row is 1,048 feed + 146 local-tree difference.
- Tile regions are 717 x 1,037 um. Along a row the feed runs 1,368 um for a 717 um pitch (1.91x detour: centre, corner,
  centre) and costs 469-498 ps per tile; 11 tiles per row gives the 5-6 ns row tails.
- Routed wire is slower than the stage model: 0.343 ps/um against 0.293 modelled (sp2->sp1: 1,048 routed, 733 modelled).
  The stage calibration (`inv_ndr_head26_i150`, 10-29) belongs to another route form (R-CLOCK-6h).
- Local tree depth: an hd_tile region uses 10.9 stages and 413 ps (264 instances, 320-491). Spine regions 17.8 stages,
  739 ps.

Answers to the four sub-questions:
- Tree depth inside each part: not in this number. `closed_views 0`, 26 of 26 types "missing view", `core_insertion mode
  declared`. Every pair carries 450 ps (TT) on both ends. HEAD-99's "insertion comes from each part's internal CTS" is
  wrong; so is "no plan parameter cuts a hop" as a conclusion about partitions. The hop is set by the feed graph and the
  region pitch.
- Buffer chains and wire length: yes, this is the whole cause (table above).
- `regions_hp1.json` on rp21z16: valid. 358 of 358 partitions mapped, none missing, none extra; region boxes come from
  the plan; all 326 feed edges join abutting regions. Feed wire is 1.29x the root-to-root Manhattan distance (median).
  One weakness: 144 of the 427 landing clock edges are not parent-child in the feed tree (b-row neighbours hang from
  different o-row parents), so their unshared path is long (up to 1,735 ps).
- Declared insertion: yes, see first bullet. Also the "planned 450" in the overlay is the partition-internal latency, not
  a die tap arrival target. A die tap arrival of 813-8,954 ps is not comparable with 450, and a hop delta is not expected
  to be 450. The column `abs_dev_from_450` and the count "215 of 427 edges miss the window" measure nothing the design
  depends on.

## 2. Is the forwarded spine the right architecture

Yes. Keep it.

- Die H-tree plus regional mesh: the die is 17.7 x 17.6 mm. Root to corner is 17.5 mm of wire; at the measured
  0.343 ps/um that is 6.0 ns of insertion before any local tree. At 5 % variation two leaves differ by about +-300 ps,
  against a synchronous seam budget of 90 ps. A mesh does not remove the global tree in front of it (METHODOLOGY 12.8e1
  noted 1.5-2 ns unshared between regional meshes). 12.13 already replaced this form; the numbers confirm it. INFERENCE
  for the 5 %, MEASURED for the rest.
- Source-synchronous with FIFOs at the landings: that is what HEAD has. Each crossing sends `fclk` beside the data, the
  ring (`ot_dp_clk_landing_ca`, DEPTH 4 or 8) writes on the forwarded clock and reads on the local clock, and a start
  tree fixes the latency. Adding lockup latches or async FIFOs would duplicate it.
- What the form needs is that each crossing's phase interval, over TT and FF, is narrower than the ring window. Measured
  on p16r: nominal interval width over all tap pairs and both corners, median 173 ps, max 280 ps, against 2,299 ps usable
  at DEPTH 4 (3 T minus 2 x 100). The absolute phase (up to 1,194 ps) does not matter.

## 3. Diagnostic: count-aligned plan on the p16r clock (MEASURED, my run)

`tools/s81_head/head_current_ca.py` (the HEAD chain: proof with tree paths, `landed_phase_ocv`, `count_align_plan`, bind) on
the p16r tree and routed arrivals, plan rp21z16, core latency 450 / 380, clock cell inv, no built ring clocks (declared).

- First attempt stopped at `tap_fall_merge`: "node falls matched for 0/45244". The p16r arrival files hold only T and N
  rows (rise). R-CLOCK-6g requires both source edges, polarity-resolved, for an inverter tree.
- Second attempt, same chain with the fall merge skipped (copy `head_ca_riseonly.py` in my directory; nominal margin
  policy as p16r): `ca2/plan.json`.

| item | value |
|---|---|
| crossings planned | 427 of 427, fail 0, below 100 ps 0 |
| worst margin, low and high guard | 104.2 ps (m0S_rx__6, host_tx__3) |
| start-up simulation, 2,000 chips | 0 violations, 104.8 ps to guard |
| ring DEPTH | 4 on 262, 8 on 165, 16 on 0 |
| latency per crossing against the plan's `count_aligned_cycles` | same 236; +1 135; +2 30; +3 4; -1 21; -2 1 |
| start edges clean | not judged: 0 fall rows measured, the width test marks all 497 unclean |
| start hops over 405 um | 431 |

Reading:
- The crossings close on this clock. This replaces "TT setup -524 ps, damage 1,258 ps".
- The 165 DEPTH-8 rings come from start-path ambiguity (148 crossings with 2 cycles, 24 with 3), which comes from the
  rise-only readout. QC saw the same: rise-only asked for deep rings and 276 failed START edges; both edges gave 2,873
  DEPTH-4, 120 DEPTH-8 and 0 fail (R-CLOCK-6g). INFERENCE that HEAD moves the same way; a both-edge run decides.
- The plan's K and latency table are stale for this geometry: 191 of 427 crossings change. This is a real die-level item
  (lane latency, LATCHECK, token), independent of the T/2 misreading.
- Not checked: whether every HEAD type's ring hardware accepts DEPTH 8 and K by strap without a re-sign; the START
  station placement (431 hops over 405 um); built ring clocks (`--ca-ring` with real fwd_out / fclk_in / reader delays).

## 4. The other gate failure: 44,308 block arrival-contract violations

This is intra-region (44,303 pairs, FF, need 99.4 ps against per-port windows) plus 4 seam pairs (need 94.1 against 90).
It is not a landed item.

- Cause: routing scatter in the local trees. FF tap spread per partition: median 57, max 107 ps. Among taps with the
  same stage count it is still 47 / 97, and an extra stage shifts the mean by 0 ps. So equalising stage counts will not
  help; the trees are delay-balanced already and what is left is leg-to-leg scatter over about 11 unshared stages
  (same finding as QC, R-CLOCK-6j).
- Worst types: hd_serdes 107, hd_tile 99 (264 instances), hd_lep0N 87, hd_spn 83, hd_mesh 81.
- The per-port windows in the plan were derived on an older clock (l48w_sth proof). p16r wrote new ones (`kitwin.json`).
- The number is a proxy. Hold on real views is the gate (12.19), and p16r measured 0 of 578,312 pairs because no signed
  view was loaded, although 19 of 26 types are signed.

## 5. Fixes, ranked

| # | fix | evidence | expected result | owner |
|---|---|---|---|---|
| 1 | Judge landed pairs as count-aligned. In the HEAD die chain: both-edge arrival readout (`die_trial.clock_edge_readout`, T/F/N/M rows), then `head_current_ca.py`, then `die_sta_related --count-align BIND --cppr-lca`. Drop the T/2 landed row from the HEAD verdict | section 3: 427/427, margin 104.2 ps, 0 fail on the same clock that read -524 ps | landed class PASS at >= 100 ps; DEPTH-8 count falls from 165 (INFERENCE from QC) | DIE-HEAD-ROUTE-1 (owns `proto_die.sh` and the run) |
| 2 | Re-bind K, DEPTH and lane latency from the clock of the plan being adopted (rp21z20), every time geometry moves. Feed the new latencies to `z19_lat.py`, then G0 and `head_bind_latcheck`. Check ring DEPTH 8 and strap K against the signed types before adoption | 191 of 427 latencies differ on rp21z16; `head_current_ca.py` header: no earlier K is reused | bind and LATCHECK consistent with the built clock; token latency changes by a few cycles (planner total -22 against the old ring form) | HEAD-99 (die owner, holds the latency table); HEAD-REMAP-1 carries it into rp21z20 |
| 3 | Feed graph follows the data links: hang each b-row tile from its b-row neighbour (or the shared o-row trunk) so that the 144 non-tree landing edges become parent-child; run the row feed straight through the tile centres instead of centre-corner-centre | 144 of 427 edges non-tree, unshared up to 1,735 ps; row hop 1,368 um for a 717 um pitch | row hop 469 -> about 250 ps; deepest tap 8,992 -> about 6,000 ps; unshared path per crossing about 1,735 -> 900 ps, so narrower intervals and fewer DEPTH-8 rings (INFERENCE, estimate from pitch x 0.343 ps/um) | new lane HEAD-CLKFEED-1 (feed.json + `ot_clk` config only; no plan or type change) |
| 4 | Intra contract: load the signed views (`--kit` per signed type) so hold is measured; give unsigned types the per-port windows from this clock (`kitwin.json`); for types still over the window add a second clock entry per region to shorten the local tree | section 4: scatter 47-97 ps over 11 stages; 0 pairs measured today | measured hold on 19 types replaces the proxy; local tree 413 -> about 250 ps cuts scatter to about 60 ps max (INFERENCE, scaling with stage count) | DIE-HEAD-ROUTE-1 (views, its Next item 2); HEAD-99 (windows, entries) |
| 5 | Refit the inverter stage model on legs of this route form | 0.343 routed against 0.293 modelled, worst leg +43 % | DME balance and estimates match the build | DIE-HEAD-ROUTE-1 with fix 1 |

Order: 1 and 2 now (tool calls only, minutes each on this data). 3 and 4 in parallel. 5 with the next clock build.
None of them changes a core shape or re-signs a type, except a type whose ring cannot take DEPTH 8 (to be checked in 2).

Open risk, not measured: 211 inverter stages and 9 ns of insertion at the far taps. Supply-noise jitter grows with
insertion delay and would show as period jitter inside the far regions. Fix 3 cuts it by about a third. A droop-aware
STA on the routed clock should quantify it before release.

## 6. Stop list

- Stop comparing die tap arrivals with 450 ps and hop deltas with +-416.5 ps. Withdraw `HEAD-landing-hops-p16r.tsv`
  as a failure list (its arrivals are correct and useful; its pass/fail column is not).
- Stop looking for a plan parameter or a partition CTS change that shortens a hop. No partition rebuild, no core move
  and no tap change is justified by the landed numbers.
- Do not start a die H-tree or mesh for HEAD (section 2), and do not add lockup latches or FIFOs at the landings.
- Do not reuse K, DEPTH or latency tables from an earlier clock after a geometry event.
- Do not quote landed or START results from a rise-only readout, including the DEPTH-8 count and the START rows of my
  own run.
- Do not equalise stage counts to fix the intra contract; it explains none of the spread.
- Do not count `proto_die.sh` output as a die gate: it is advisory by its own header, with declared insertion and no
  signed view.

## 7. Evidence and limits

- Files read: p16r `CHAIN.log`, `sta.log`, `sta/die_sta_related.json`, `tree/kit/clock/tree.json`, `proof/tap_arrivals_{TT,FF}.json`,
  `kitwin.json`; `cfg/regions_hp1.json`, `cfg/feed_hk4.json`, `cfg/head_p16.yaml`; plan `p16/prep/source_plan.json`
  (sha ba4f4b2dc137); `proto_die.sh`; `tools/die_plan/die_sta_related.py`, `count_align_bind.py`; hub METHODOLOGY 12.11-12.13,
  RULEBOOK R-CLOCK-6, LAND-HEAD, handoffs HEAD-99 and DIE-HEAD-ROUTE-1.
- My run: `fable-pd-head-clk/ca2/` (`plan.json`, `physical_ocv.json`, `region_ocv.json`), driver `head_ca_riseonly.py`,
  logs intel2 `~/tmp/fable_head_clk_ca{,2}.ot`. The planner exited 1 on the START rows; the bind step did not run.
- Not done: the fix2 run (die-proto-3/head/fix2) was not re-read; its landed row comes from the same script and the same
  T/2 model. No `lanes/handoff/HEAD-REMAP-1.md` exists on the hub. OCV, droop and spice calibration were off (nominal
  policy, as p16r). No both-edge readout exists for this clock, so START and final DEPTH are open.
