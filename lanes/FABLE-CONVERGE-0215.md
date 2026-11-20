# FABLE-CONVERGE-0215 (2026-11-20 01:2x PST): why the 4 dies do not converge, a conservative ETA, and the fastest route to closure

Reviewer: FABLE-CONVERGE-0215 (Fable). Read-only: nothing launched except three 2 GB read-only directory scans through ot-run; nothing killed, cancelled or patched. HBM is parked and left out.

Marking: **V** = I measured or opened it this round. **R** = reported by a named lane or report. **E** = my estimate. **P** = proposal.

## 0. Answer

1. **It is not converging because the plan changes faster than a build can answer.** QC had 26 plan events in 7 days, one every 6.5 h. A QC build needs a median 12.4 h to reach a sign-off verdict. HEAD, the one die that did converge (25 of 26), has a 2.1 h build against one event per 8 h. Each recent event re-blocks most of the die, so most builds answer a question that is no longer asked.
2. **Half of the failures are not design failures.** 54 % of the wave's 1,835 failure rows since 11-14 are flow or infra. On three hosts, 70 % of 2,420 attempts never wrote a place-and-route log, and 1.1 % ended signed.
3. **The unit of work is too small.** 499 unsigned types are counted and built one by one. S81's 395 types are 187 physical problems; its 216 col types are 9 to 14.
4. **The design has no margin, so every class is found late and one at a time.** Routed builds miss by small amounts: median setup miss 77 ps, median hold miss 24 ps. 67 of the 84 types that routed and failed since 11-14 are within 167 ps of setup and 60 ps of hold.
5. **Conservative ETA on the current approach: end of February 2027 overall, and S81 has no date at its measured rate** (350 types at 1.6 a day is 219 days).
6. **Fastest route: all four dies around 12-16, conservative 12-28.** It needs seven owner decisions (section 5). The five moves that carry it are in section 3.

## 1. Diagnosis

### 1.1 State (V, `failure_breakdown.py` 00:48, `SIGN-RATE.tsv`)

| Die | Types signed, any plan | Unsigned | Cores | Types signed per day, 11-14 to 11-19 | Last 48 h |
|---|---|---|---|---|---|
| S81 | 44 / 394 | 350 | 64 / 64 | 1.6 (36 to 44) | +2 |
| HEAD | 25 / 26 | 1 | 5 / 5 | 1.2 (19 to 25) | +2 |
| QC | 32 / 130 | 98 | 70 / 70 | about 4 (the 11-17 step of +16 is partly a recount) | +8 |
| KV | 6 / 56 | 50 | 68 / 69 | 0.2 (5 to 6) | 0 |
| All | 107 / 606 | 499 | | about 8 | +12 |

- All hard cores are signed. Everything left is die partition types: glue, stations, feedthroughs and clock taps around signed cores.
- 59 of the 473 signed items are on retired plans (S81 22, QC 24, KV 12, HEAD 1). They count, but they do not all compose into one die.
- S81 went from 34 types on 11-09 to 44 on 11-19: one a day for ten days.

### 1.2 Where builds go (V)

**Funnel, three hosts (epyc7, epyc8, epyc10), wave attempts with a log in the last 5 days.**

| Stage reached | Attempts | Share |
|---|---|---|
| All attempts | 2,420 | 100 % |
| No numbered P&R stage log (died in bind, gen, lint, snapshot, preflight) | 1,704 | 70 % |
| Ended in synthesis or floorplan | 26 | 1 % |
| Ended in placement | 470 | 19 % |
| Ended in CTS or GRT | 136 | 6 % |
| Reached route or report | 84 | 3.5 % |
| Sign-off verdict | 74 | 3.1 % |
| SIGNED | 26 | 1.1 % |

**Wave failure rows, 11-14 to 11-20 00:5x, four dies (`KIT-WAVE-*.md`, 1,835 rows).**

| Class | Rows | Share | What it is |
|---|---|---|---|
| Flow error (exit 99, Tcl, pipeline) | 502 | 27 % | not design |
| Route make fail | 193 | 11 % | mostly not design (no result file) |
| Stopped from outside (exit 143, no OOM line) | 149 | 8 % | not design |
| Client lost, kit idle (orphan) | 113 | 6 % | not design |
| OOM, lost, watchdog | about 30 | 2 % | not design |
| **Non-design total** | **987** | **54 %** | |
| Post-CTS hold or setup stop | 351 | 19 % | design, stopped before route |
| GRT overflow | 256 | 14 % | design |
| Routed, not signed | 137 | 7 % | design, the only rows with a full answer |
| Hold repair stall, GRT time cap | about 85 | 5 % | design |

- 11-19 alone (V, `FLOW-HEALTH.tsv`): 1,922 launches, 814 failed before place and route (42 %). The three classes of that day were a stale bind realization, kit snapshot copy timeouts and pipeline timeouts.
- Fleet (R, FABLE-FLOW-0035; V `ot-run --status` 00:5x): every host admits 0 GB, about 50 waiters per host asking 2,800 GB. Threads asked are 8.1 times the 736 cores. Most of the round trip is queueing.
- 11-19 routing (V, `ROUTE-RESULTS.md` recount): 77 decided, 12 passed, 65 failed (hold 35, setup 15, DRC 13), 23 routed without a verdict.
- Only about 7 % of failure rows carry a routed timing answer. The other 93 % teach little about the design.

### 1.3 Round trip and rounds per type (V)

| Die | Hours, launch to sign-off verdict (median / p90) | Failed wave attempts per type since 11-01 (median / p90) | Plans a type was built on (median / max) | Plan events, 11-13 to 11-19 | Hours between events |
|---|---|---|---|---|---|
| HEAD | 2.1 / 7.1 | 7 / 18 | 5 / 10 | 21 | 8 |
| S81 | 8.2 / 27.2 | 7 / 17 | 4 / 7 | 8 wave events, plus private D8g, D8h, D8i, J3, J4 | 21 |
| QC | 12.4 / 18.7 | 15 / 26 | 6 / 12 | 26 | 6.5 |
| KV | not measured (no KV verdict in the sample) | 3 / 11 | 2 / 9 | 19 | 9 |

- Jobs in flight now (V, `NOPROG.tsv`, 504 jobs): route stage median age 9.4 h, p90 13.4 h; GRT p90 33 h.
- The three S81 wave rows that are SIGNED on the current plan signed at a median attempt number of 35 (max 42).
- A late ECO pass takes a median 1.4 h, p90 8.6 h. 106 of 137 routed failures got exactly one pass and were then closed as "GEOMETRY + REDESIGN, no second ECO".

### 1.4 Plan churn cost (V, `autopilot/kit_wave_stages.tsv`)

- 3,034 wave rows on the four dies are CANCELLED / SUPERSEDED, against 7 SIGNED rows. 1,046 were superseded on 11-18 and 821 on 11-19.
- Where they stopped: geometry review 1,510, place 386, gen 364, kit RTL 321. Almost none had reached route.
- The last two QC events (N46C 11:xx, N46R3 22:xx on 11-19) opened 102 and 119 new rows on a die of 130 types, 11 hours apart. S81's 19:xx event opened 528 rows. KV D25e opened 80 on 56 types. (The ledger keeps one row per item, so these are lower bounds on what each event re-blocked.)
- The rule "a type counts on any plan" protects the count, not the build. The watchdog still lists SUPERSEDED jobs as CANCEL-NOW (V, `NOPROG-TABLE.md` 00:45, four rows on intel1), against the owner's 11-19 rule.
- A type's identity contains its clock tap table (`__cl<hash>`) and its pin and station set (`__pv<hash>`). Any die clock or station change makes new types. The die clock is still being rebuilt (cw6, cw7, cw8), so type identity cannot settle.

### 1.5 Why new problems keep appearing

1. **Discovery is serial and slow.** A type passes bind, gen, place, CTS, pre-GRT hold, GRT, route, sign-off, then die STA. Each stage hides the next class. A class shows only after 8 to 27 h, and only on the 3.5 % of attempts that reach route.
2. **Each fix is a plan event that restarts most of the die.** So the learning rate is about one class per family per round trip, while the plan moves two to four times a day.
3. **Types sign against a die contract the die does not meet.** Kits assume a 40 to 57 ps tap window. The die tree delivers up to 283 ps on QC and 288 ps on S81 (R, FABLE-CLOSURE-2315). Die STA first used real views on 11-19 and read FF hold bounds of -248 (HEAD), -302 (S81), -355 (QC), -120 (KV) (R, `DIE-LEVEL-1119.md`). Signing all 606 types does not close a die.
4. **The design sits on its limits.** Hops are planned at exactly 405 um. A QC SRAM read uses 434 ps of 833 and is followed by 278 ps of logic. An S81 ROM read is 620 ps on a half cycle. With no slack, every second-order effect becomes a new failure class.
5. **Static checks came last.** Each class below was found at route or later, and each has a check that needs no build:

| Class found by building | Static check that names it | First existed |
|---|---|---|
| Memory read cannot fit one cycle (coll_core, tt_ctlm, col_h9_r2) | macro clk-to-Q + 150 ps against the period, distance to first register | proposed 11-19 |
| Hop over reach into a hard-core pin (S81 col HOP class, -310 to -537 ps) | placed distance of every last hop | PRECHECK-1119, 11-19 |
| Related taps with no shared tree node for 17 stages | unshared stage count per related tap pair from the tree and bind graph | cw8, 11-19 |
| Zero-logic chains spread over taps (KV pv 142,464 transfers) | tap of launch and capture flop per zero-logic pair | 11-19 |
| Station rows inside hard cores (QC N46T: 59 rows, 899 bit sites) | `station_rows_check.py` | 11-19 |
| Sink bins 0.26x to 1.69x of real load (24 QC types) | bins against a placed kit | 11-19 |
| Core PG pins under M6 / M7 obstruction (KV pc) | LEF check | 11-19 |
| Proofs built with an FF-only second pass; GOAL=finish skipping FF GRT (all 114 D8i col kits) | flow canary per event | fixed 11-19 |

6. **The measurement itself was wrong several times.** Insertion skew read as distance, a 10-25 log read as a result, contract hold read as measured hold, cw7 priced before two fixes. Each cost a round.

### 1.6 Split of the loss (E, from the rows above)

| Cause | Share of builds lost | Basis |
|---|---|---|
| Flow and infra | about 50 % | 54 % of failure rows; 70 % of attempts without a P&R log includes plan-side bind refusals |
| Plan churn (superseded before an answer) | about 25 to 30 % | 3,034 superseded rows; 1,867 in the last two days against about 4,100 launches |
| Design, stopped before route | about 15 % | post-CTS stop, GRT overflow |
| Design, with a routed answer | 3 to 4 % | 137 rows in 6 days |
| Signed | about 1 % | 26 of 2,420 |

## 2. Conservative ETA on the current approach

Arithmetic: unsigned types divided by the measured rate, then a tail for the die. The tail is re-signing on one coherent plan (59 items are already on retired plans) plus die STA on real views, 2 to 3 weeks per die. No die has passed die STA on real views yet.

| Die | Types | Arithmetic | Types done | Die closed |
|---|---|---|---|---|
| HEAD | 1 left | hd_lep0N is in route | 11-23 | 12-05 |
| QC | 98 left | 98 / 4 per day = 25 days | 12-15 | 01-05 |
| KV | 50 left | measured rate 0.2 per day gives 250 days. If the hg, pv and pc families (41 types) unlock with D25f inside a week and then sign at QC's rate: 7 + 13 days, plus one more family round of 10 days | 12-20 | 01-10 |
| S81 | 350 left | measured rate 1.6 per day gives 219 days (2027-06-27). If col (216) closes as a family on D8i / J within 10 days: 6 rounds at a 16 % pass rate and 1.5 days each, 9 more days, col by 12-10. The other 134 at 4 a day: 34 days | 01-10 at best | 02-01 at best |
| **Overall** | 499 left | 499 / 7 per day = 71 days = 01-30, plus the die tail | | **2027-02-28 conservative; S81 undated at its measured rate** |

The S81 "at best" line assumes a family unlock that has not happened in the two weeks since the col plan started moving. I would not promise it.

## 3. Fastest route to closure at any cost

Ranked by days saved. Cycles, area and performance loss are taken as pre-approved. ETAs assume the section 5 decisions on 11-20.

### Move 1. Harvest the routed builds: release period 1000 ps, three hold ECO passes, keep the DB (48 h)

- **What.** Evaluate setup at a release period of 1000 ps on the same routed DB (setup >= -209 ps against the 833 ps constraint). Run up to three post-route hold ECO passes instead of one. Keep the routed DB of any build inside that band until a successor signs. Builds keep the 833 ps constraint; nothing is re-synthesised.
- **Evidence (V).** Of 137 routed failures since 11-14 (84 distinct types): 43 of 47 setup misses are >= -209 ps; 76 of 102 hold misses are >= -60 ps; 67 of 84 types meet both (QC 45 of 54, S81 13 of 16, HEAD 8 of 10, KV 1 of 4). The extra 167 ps of setup room is also what hold padding needs: hd_tile's hold build took setup from +16.8 to +0.6 ps.
- **Not checked.** How many of those DBs still exist (many rows say "run data deleted"); whether a second ECO pass moves hold on the cross-tap ends. Prove on 10 QC hold-only builds first.
- **Cost.** Up to 16.7 % tok/s on a die whose slowest type needs 1000 ps. No area, no cycles. Re-closing at 833 ps continues afterwards under the no-freeze rule.
- **Removes.** The setup class (15 of 65 on 11-19) almost whole, and the small-hold class. E: 40 to 60 types within 4 days, mostly QC; finishes HEAD types.

### Move 2. Take the die clock out of type identity: type root, lockup at every boundary (one event per die)

- **What.**
  1. All taps of one type hang from one type root. The sub-tree from the root to the tap sites is part of the kit, pre-routed and timed in the kit's own STA. The die delivers one clock per type.
  2. A lockup latch (KV form C, main ebe5d224187) at every type input-port station and at every zero-logic transfer between taps. Zero cycles.
- **Why.** Cross-tap hold is the largest class (35 of 65 on 11-19, 27 of them QC). The same fault is the die-level hold of -248 to -355. With a lockup, a boundary tolerates skew up to about half a period (416 ps), which is above every measured die bound. With a type root, a die clock change no longer changes `__cl`, so it stops retiring types.
- **Cost.** About 5 to 10 % cells on station-heavy types (KV pv: 54,196 latches on 578,916 instances, V in the lane post). 0 cycles. One re-bind of every type, once.
- **Risk.** No routed number exists for form C yet (v8j is in flight). Read it within 24 h. Fallback if it fails: falling-edge capture station at the boundary, +0.5 cycle per crossing.
- **Removes.** Cross-tap and die-level inter-type hold as classes; the cw7, cw8 offset rounds; clock-driven type churn.

### Move 3. Build physical problems, not types; sign by inheritance

- **What.**
  1. S81 rules R1 to R4 of `FABLE-S81-TYPEMERGE.md` (11-15, not applied; the die still builds 394): one build per equal layout, siblings that differ only in ROM image and names inherit the record. 395 -> 193 builds, col 216 -> 14. 0 cycles, 0 area. Real weights stay: the image lives inside the ROM hard core, which has one LEF and one lib.
  2. Superset pinout for S81 leaf (75 types, 1 RTL, 67 pinouts) and slice_station (46 types, 1 RTL, 44 pinouts): every tile carries the largest feedthrough and bus set of its outline class, so tiles become replicas. E: 121 -> about 10.
  3. The same census on QC (east and west halves, v1 / v2, pad variants) and KV (hg, hgi, pv, pc), one day, read-only.
  4. Count rule: a sibling is signed when its representative is signed and an automatic diff of the bound netlists shows only ROM image strings and names.
- **Cost.** Item 1: none. Item 2: area on leaf and station tiles, E +10 to 20 %, to be priced by PRECHECK before the bind; unused stations are tied off.
- **Removes.** About 200 S81 builds at once and about 110 more with item 2. E total distinct builds left: S81 about 80, QC about 50, KV about 25, HEAD 1.

### Move 4. Margin by construction as the kit default

- **What, applied to every type in the same event as move 2, not family by family after each failure.**
  1. Every ROM and SRAM read is registered at the macro: +1 cycle per read path.
  2. Placed hop cap 300 um, a register at each end; +1 cycle where a hop splits.
  3. Outline +20 % (utilisation about 15 points lower) on every family with a GRT overflow or DRC row (256 overflow rows in 6 days).
  4. PRECHECK rows for each class in the table of 1.5 run on every event before launch, as an estimator.
- **Cost.** E a few per cent tok/s from added cycles; +10 to 20 % area on the grown families.
- **Removes.** What is left of setup after move 1 (HOP, BANK-OUT, BANK-IN, RDLOOP in the S81 col census; coll_core, tt_ctlm) and most congestion and DRC.

### Move 5. Change the loop: one event a day, representatives first, twice the fleet, flow canary

- **What.**
  1. At most one batched plan event per die per 24 h, longer than the round trip. Events are deltas: a type the event does not touch keeps its block hash and its builds. Plans still evolve; nothing is frozen.
  2. Representatives of each family launch first at top priority; siblings fill spare capacity only.
  3. Rent 12 more gen hosts for 4 weeks. Thread oversubscription falls from 8.1x to under 3x. E round trip 12 h -> about 5 h.
  4. One canary kit per die runs gen to route on the live tools before an event's volume launch. No watchdog cancels a superseded or silent job; only its owner does.
- **Cost.** About 1.9 EUR per host-hour (the epyc1 rate): about 550 EUR a day, about 15,000 EUR for 4 weeks.
- **Removes.** Most of the 54 % non-design loss and the 25 to 30 % churn loss. This move does not fix a design class; it makes moves 1 to 4 measurable in days.

### Move 6. Close HEAD at die level now, as the pipe cleaner

- HEAD has 25 of 26 types. Run die STA on real views with per-port arrivals, apply move 2 to hd_host_w first, and take the die to a token pass. E 7 to 10 days. It shows the die-level classes while the other three dies still have types to build.

### ETA on the fastest route (E)

| Die | Distinct builds left after move 3 | Types signed | Die closed | Conservative |
|---|---|---|---|---|
| HEAD | 1 | 11-22 | 11-30 | 12-05 |
| KV | about 25 | 12-02 | 12-10 | 12-20 |
| QC | about 50 | 12-02 | 12-10 | 12-20 |
| S81 | about 80 | 12-06 | 12-16 | 12-28 |
| **Overall** | about 155 | | **12-16** | **12-28** |

Arithmetic: decisions 11-20; move 1 through 11-24; one event per die carrying moves 2 to 4 by 11-23; two build rounds of about 1 day each on a doubled fleet, a third for the residue, to about 12-02 (S81 12-06); die STA and token 7 to 10 days. The conservative column adds half again.

## 4. What to stop doing

1. Stop posting more than one plan event per die per day, and stop events that re-block types they do not change.
2. Stop launching every sibling of a family on a plan no representative has routed on.
3. Stop per-pin offset rounds, `actual_max` rounds and cluster heuristics on die trees (cw7 was worse on every number).
4. Stop reading die hold from all-pairs bounds; quote measured pairs and the share measured (S81 104,310 of 1.34 M).
5. Stop single-type hand fixes (polyline rounds, station re-sites, one more wall) on a family with a named structural cause.
6. Stop closing a routed build after one ECO pass, and stop deleting its DB.
7. Stop cancelling superseded or silent jobs from watchdogs.
8. Stop reporting the type count as the headline alone. Report distinct builds left and die STA on real views beside it.
9. Stop building S81 col as 216 types.
10. Stop taking a number from a build whose goal skipped a repair step (GOAL=cts, the FF-only second pass).

## 5. Decisions for the owner

- OWNER? Sign at 833 ps where a type passes, otherwise at up to 1000 ps on the same routed DB; a die runs at its slowest type; 833 ps closure continues afterwards. Cost up to 16.7 % tok/s. Recommend YES.
- OWNER? At most one batched plan event per die per 24 h, built as a delta that keeps untouched types' builds. This is a cadence, not a freeze. Recommend YES.
- OWNER? A type inherits sign-off from a signed representative when the bound netlists differ only in ROM image and names (automatic diff; real weights unchanged). Recommend YES.
- OWNER? Superset pinouts on S81 leaf and station tiles, and the QC / KV equivalents the census finds, so tiles become replicas. Area about +10 to 20 % on those tiles. Recommend YES.
- OWNER? One event per die that puts all taps of a type under one type root and a lockup latch on every type input port and cross-tap zero-logic transfer. 0 cycles, 5 to 10 % cells on station-heavy types. Recommend YES once v8j routes (within 24 h); the fallback is +0.5 cycle per crossing.
- OWNER? Registered read on every ROM and SRAM (+1 cycle) and a 300 um hop cap as kit defaults on all four dies. A few per cent tok/s. Recommend YES.
- OWNER? Rent 12 more gen hosts for 4 weeks, about 550 EUR a day. Recommend YES.
- OWNER? Launch representatives first; siblings only fill spare capacity. This changes the 11-13 "launch all eligible rows immediately". Recommend YES.

## 6. Leading indicators, hourly

| Indicator | Now | Working if, within 24 to 48 h |
|---|---|---|
| Signed / sign-off verdicts | 12 of 77 (11-19); 26 of 74 (3 hosts, 5 days) | over 50 % |
| Attempts that write a P&R stage log | 30 % | over 80 % |
| Non-design share of failure rows | 54 % | under 15 % |
| Rows superseded per day | 1,046 and 821 | under 100 |
| Plan events per die per day | QC 3.7, HEAD 3, KV 2.7 | 1 or fewer |
| Launch to verdict, median | QC 12.4 h, S81 8.2 h | under 6 h |
| Threads asked / cores | 8.1x | under 3x |
| Routed without a verdict | 23 | under 5, none older than 2 h |
| Distinct builds left per die | not tracked (S81 187 problems for 395 types) | tracked, falling daily |
| Routed hold failures by class (cross-tap / in-tap / port) | 35 a day, cross-tap dominant | cross-tap 0 on lockup kits |
| Die FF hold on real views: worst measured, share of pairs measured | bounds -248 to -355; S81 8 % measured | measured share over 80 %, HEAD >= 0 |

One-time reads inside 24 h: the v8j routed result (move 2), ten QC hold-only builds through three ECO passes at 1000 ps (move 1), one col representative at GRT TT on D8i.

## 7. Not checked

- KV round trip (no KV verdict in my sample). Private lane builds outside the wave ledger.
- Whether a second or third hold ECO pass closes the cross-tap ends; whether the routed DBs of the 67 types still exist.
- Any routed result for lockup form C, or for a type-root tree. Move 2 rests on the lane's gen-level evidence and on cw8's direction.
- The area of the leaf and station superset; the QC and KV type census. Both figures in move 3 are estimates.
- Fleet RAM totals and the rental price beyond the one epyc1 rate.
- The 11-17 QC step (8 to 24 types): I did not separate real sign-offs from the any-plan recount.
- The share figures in 1.6 are estimates from overlapping ledgers, not one clean census.
