# FABLE-PD-KV-2000 (2026-11-21 18:40-19:25 PST): why KV is at 6 of 56, what D27d3 closes by construction, and the levers ranked by types

Reviewer: FABLE-PD-KV-2000 (Fable). Read-only: nothing launched, cancelled, signalled or patched; no ot-run job. Short python and greps on
intel2, epyc2 and epyc8 only. Marking: **V** read by me this round, **R** reported by the owning lane, **I** inferred, **P** proposal.
FABLE-PD-KV-0840 stands except where section 5 says a lever is done. Scope: technical PD only. Nothing below is a new gate.

## 0. Verdict

1. **No KV type has been signed off from any plan event since 11-13.** The 6 signed types (io_ft, io_ft_v1, phy, phy_v1, sys_SD,
   sys_SD_v1) are edge types without landing rings and were signed before. Of 442 kit rows over 22 plan events, 0 reached sign-off and
   only 8 types ever started route (V, section 1).
2. **The cause is not one physical class. No kit lives long enough to be read.** Every event re-keys almost every type block, and a hub or
   hgi kit needs longer to reach GRT than the gap between events.
3. **D27d3 closes by construction for 8 types at most: pc x6 and io_cor x2.** It carries no row for the three measured stop classes:
   hg/hgi reset (19 types), pv size and first hop (16 types), hub cell count and hold (5 types). Section 2.
4. The largest physical lever is the hg/hgi reset rows (R6c): **19 types**. Then the pv split: **16 types**.

## 1. Why 6 of 56 (V: intel2 `autopilot/kit_wave_stages.tsv`, 442 KV type rows without prelint; `autopilot/log.txt`)

| Fact | Number |
|---|---|
| Plan events with KV kit rows since 11-13 | 22 |
| Rows that reached sign-off | 0 |
| Deepest stage ever reached, per type item (57) | route 8, place + auto-geom 44, place 3, earlier 2 |
| Types that started route | hgi_v1__cl42bc8b12, hgi_v2__cl2862d491, hgi_v3, hgi_v4, hroot, hub_Ei, io_cor_v1, pv_v3n |
| Rows ended by a newer event | 344 of 442: 170 while queued or running, 150 after a fail, 24 placed and then route-skipped as old plan (23 types) |
| Type blocks unchanged from one event to the next | D23H -> D25d 0 of 14, D25d -> D25e 0 of 12, D25e -> D25e3 0 of 18, D25e3 -> D26 0 of 47 |
| Gap between the last four events | 9 h, 17 h, about 15 h (D25e 11-20 05:01, D25e3 14:07, D26 11-21 07:13, D27d3 about 22:00) |

Time a KV kit needs (V, epyc2 job dirs, D26):

| Kit | Timeline | State at 18:50 |
|---|---|---|
| hub_Ei a1 | gen 06:50, placed 11:20 (4.5 h), CTS done 17:07 (5.5 h), hold repair since 17:20 | 12 h in, not at GRT |
| hub_C a1 | start 08:02, floorplan 13:49, global place 14:15-18:25, resize since 18:28 | 10.8 h in, not placed |
| hgi_v4 (KV-D25d) | CTS done 11-20 07:49, GRT since then | 35 h in GRT, 107 extra-iteration starts, log last written 18:13 |

So a hub kit needs more than 12 h to reach GRT and the plan changed every 9 to 17 h. The wave keys a kit on the hash of its type block
(`tools/autopilot/plan_block_identity.py`: `partition_types[name]` + budget), and every event changed every block.

**The D27d3 apply does it again (V, my diff of the D26 plan a9f605cb1acf against D27d3 48b92c30c8f6 on epyc8):** 52 of 56 type blocks
change. The 4 unchanged are signed types. `clock` changes on 42 types and `internal_stations` on 31. On 14 pv types the only change is
`clock.reserved_sites_um` (the pinclear row moves of 0.05 to 2.16 um). D28 will follow within a day and re-key them again.

Failure text of the 150 failed-then-superseded rows (V): clock-landing band 30, bound reset identity 12, plan contract metadata 11, native
stage/reset realisation 11, GEN_LINT 10, tool or schema exception 9, bind of record names missing HDL 8, kit not self-contained 6, PDN-0006 9.
About two thirds are generator and bind integration faults of that event, found only when the wave ran the kits.

## 2. D27d3 structural review (V: epyc8 `kv-plan-r3/d27c/g0gate_d27d3/g0/g0_report.json`, verdict PASS, 0 errors, 2,483 warnings)

"Green on all gates" is true. The same report predicts the stops below as warnings, and the D26 kits measured them.

| Check | D27d3 plan | Measured on D26 |
|---|---|---|
| Reset reach | `R-REACH-6 ring_reset_fan` on 40 types: ring reset loads span 1,166 to 2,272 um on hg/hgi (pv_v2 3,462, hub_Wi 2,737) with 1 same-cycle copy. `reset.lockup_regions` on 0 types, `reset.tail_clear` on 0 types | hg -559.80: 23 levels, 1,730 um, reset spine tail to NK lockup (R). hgi_v2 -738.66, recovery groups -470.96 / -449.57 (R). hgi_v5 -766.50, cancelled |
| Cells <= 400k | pv: 7 OVER (416k to 437k), 2 NEAR, 5 `cored_unjudged`. hub_Ei NEAR 388,235. hub_C, hub_Eo, hub_Wo, hub_Wi `cored_unjudged` | pv_v12 499,054 and pv_v7 447,860 at floorplan. hub_Ei 395,006 placed, **405,448 after CTS**. hub_C 348,434 at floorplan + 68,494 repair buffers in 3_4 = 416,928 before any timing repair. hub_Eo 450,499 (-0840) |
| Hops <= 405 um | lanes 0 over (worst 403.3). `routed_reach` 56 over on 19 types: head core `kp_o -> u_kt kp_in` hop 0 routes 439 um round the cores (Manhattan 223) on all 19 hg/hgi; hgi_v1 x2 `i_ectl_Q_N_tN` hop 4 = 482 um | pv_v1 -1,199.24, path 2,805 um, 31 stages (`u_vport_E.sel_q -> fault`) |
| Face bus to consumer | `R-REACH-3 window_far`: hub_C 72 buses, 7,760 bits over 200 um, 8,316 bit-mm, about 55,400 buffers, worst 1,118 b x 1,129 um. sys_c 30 buses, 3,215 bits, about 21,800 buffers, worst 552 b x 1,620 um. 6 pv n-types 1,360 to 3,043 bits | hub_C: 68,494 buffers in 62,061 nets at 3_4. The estimate and the build agree |
| Taps | 119 taps over the cap on 18 types, worst pv_v6n clk_t13 4,306 sinks; hgi_v8 clk_t36 1,651. Radius over 200 um on 20 types, worst hgi_v2 320 | hub_Ei post-hook: 81 taps, insertion 241.6 to 298.1 ps, in-tap skew up to 73.4 ps, TT setup +27.45 |
| Hold structure | `xtap_latency`: 5,169 of 5,441 ft hops cross tap ports with a window over 50 ps (worst 192.5) and no `clock.ft_hop_lockup`; 0 types carry the field. Top: pv_v6n 436, pv_v6 429, pv_v12 359, hub_Ei 343, pv_v7 307 | hub_Ei post-hook FF hold **-443.58 on 29,695 ends**, TNS -1.92 M ps. The kit's own structural limit is -162.3. 7,384 ring inputs on 81 forwarded clocks carry `set_input_delay -min -385` |
| Core clock depth | `timing_audit`: 35 core rows FAIL on 20 types: ring views `kv_cland_w1057_ew_94a44` 638 ps, `w781_ns_9f2d9` 605, `w288_ns_ad575` 556, `w1560_ew_0433f` 208, `qkd_pv_fin_s8_pin` 275, against 200 with no early tap. 18 rows unmeasured | Not read on a kit |
| pc PG / OBS | `qkd_kvs_pcc.lef` in D27d3 is sha 1883d59424fe: M6 OBS 23,768 rects 1,368 um2, M7 2,032 um2 = the 11-17 wire-shape form | D26 used the merged-OBS view: PDN-0006 |
| Face pins under clock sites | `clksite_pinclear`: 0 hits on the 9 proofs (R) | io_cor: 54 DRC, 44 on one south clock reserve (R) |

### Prediction per family on D27d3 as it stands

| Family | Types | Prediction | Why |
|---|---|---|---|
| pc | 6 | **Can close.** | View fixed (V), strap pad max changed on 3 types, pin sites clear. Open: tap clk_t21 1,113 of 1,200 sinks at radius 232 |
| io_cor | 2 | **Can close.** | Row moved +2.16 um. 10 of the 54 D26 DRC were not on that reserve: read them on the first route |
| hg | 8 | **Fail at place, setup about -560.** | Same reset structure as D26. Then the 439 um head hop |
| hgi | 11 | **Fail, setup -450 to -770.** | Reset tail recovery. Then ring clock depth 638 ps, hgi_v1 482 um hop, hgi_v2 congestion 114 % peak (R) |
| pv | 16 | **Fail.** | 9 at or over the cap, 5 CLAND band stops on D26, v1 2.8 mm path. D27d3 has no split |
| hub_C | 1 | **Over 400k.** | 416,928 before timing repair. The ahub ck[5] view is needed but is not what stops it |
| hub_Ei | 1 | **Over 400k and FF hold.** | 405,448 at CTS with 34,742 hold ends still to buffer |
| hub_Eo, hub_Wo | 2 | **Over 400k** unless the ring rows cut it to the 320k target (R) | 450,499 measured on D25e3 |
| hub_Wi | 1 | Port bind fails again unless the pads row is in D27d3 (the diff shows `pads` changed on hub_Wi: likely in, I) | |
| hroot | 1 | DRT-0255 again: M7 PG stripe over the via column (R); variant B is not in D27d3 | |
| sys_c | 1 | Places; setup at risk | 21,800 face buffers, 1,620 um face bus, boundary 2,333 um from the tap |

## 3. Levers, ranked by types unblocked

| # | Lever (P) | Types | Evidence | Owner |
|---|---|---|---|---|
| 1 | **Keep type blocks stable across events.** D28 changes only the blocks of types that get a row. No die-wide regeneration of `reserved_sites_um`, `landing_contract`, `landing_raw_branches` or `internal_stations` on a type without a row. Print the count of re-keyed types (the 3-second block diff) with every event post. Placed kits of an older block go on to route as a read when the type has no placed kit on the current block. | 50 | 0 sign-offs in 22 events; 0 of 47 blocks stable; D27d3 re-keys 52 of 56; hub kit over 12 h to GRT | KV-PLAN-R6; wave side FLOW-OPS |
| 2 | **hg/hgi reset: R6c rows (`lockup_regions`, and `tail_clear` sync on hgi) into D28 for all 19.** Proof kit on **hgi_v2__cle0015330**, not only hgi_v1: it has the measured baseline (-738.66, groups -470.96 / -449.57). Read after it, in this order: head `kp_o` hop (439 um routed), ring clock depth 638 ps, hgi_v1 hop 4 (482 um). | 19 | section 2 rows 1 and 3; 0 types carry the fields in D27d3 | OPUS-FIX-KV-HGI-R6 |
| 3 | **pv split for all 16 in one event**, from the v3 / v7 recipe, each with `LEAF_FIRST_HOP` 0 / 0 and tap rows per half. At one proven type per event pv takes two weeks. | 16 | 9 over or near the cap, 2 measured over, -1,199 on v1; split rows exist for v3 and v7, tap overlays for v4, v4n, v5, v5n (R) | OPUS-FIX-KV-PV-R5, TAP-GRID-R5 |
| 4 | **Sign pc x6 and io_cor x2 first on D27d3** and keep their blocks unchanged in D28 (lever 1). These are the only types D27d3 can close. | 8 | pc view V; io_cor row R | FAM-KV-IOPC-R4 |
| 5 | **Hub cell budget.** hub_C: move the 72 face-bus windows to their consumers (`MOVE-WINDOW`, 7,760 bits) or register them at the face; that is the 68k buffers. hub_Ei: same read. hub_Eo / hub_Wo: ring rows to the 320k census target. Judge all five on the placed census, not on G0 (`cored_unjudged`). | 5 | 416,928 / 405,448 / 450,499 | FAM-KV-HUBC-SYSC-R2, FABLE-FIX-KV-HUB-R4 |
| 6 | **Hub and pv hold by structure.** `clock.ft_hop_lockup` on the cross-tap ft hops (5,169, none today). On hub_Ei first split the 29,695 ends by start (forwarded ring input, cross-tap ft hop, other) from the kept `4_cts.odb`; do not accept a buffer repair of -443 ps on a type already over the cap. | 5 + 16 | hub_Ei -443.58 against a structural limit of -162.3 | FABLE-FIX-KV-HUB-R4 |
| 7 | ahub `view_eco2` as a declared overlay row; hroot variant B; hub_Wi pads row. Necessary, each 1 type. | 3 | R | FABLE-FIX-KV-HUB-R4, KV-PLAN-R6 |
| 8 | Ring views with 556 to 638 ps clock depth: read one routed hgi kit for the parent-to-ring pair slack before any re-harden. | up to 20 | G0 `timing_audit`, not measured on a kit | OPUS-FIX-KV-HGI-R6 |

## 4. Events reviewed

- **(1) D27d3:** apply it. It is the only base without the 920 pin and clock-site hits. Expect 8 types from it, not 50 (section 2).
- **(2) hub_C a1 (D26):** will end over the cap: 416,928 non-tap cells before timing repair (V). Read the census at the end of 3_4 and
  post it; that number is the result of this attempt. sys_c a5 never ran (infra). Its D27d3 run places; watch the 1,620 um face bus.
- **(3) HGI R6c:** right class and the largest physical lever. Async assertion at the input sync with the 5-clock release is consistent
  with the hold-structural rule. The proof should carry the measured hgi_v2 baseline (lever 2).
- **(4) ahub ck[5]:** the second M5 rect gives one extra abutting PG cut window in `lef_interior_pins` (R). One hub_C gen with the overlay
  is the missing check. It does not move hub_C alone (lever 5).
- **(5) Repeat failures by class (D26 rows, V):** CLAND band 5 pv (v2, v2n, v3, v4, v5); cell cap 4 pv (v7, v12, v4n, v5n); place setup
  stop pv_v1; PDN-0006 pc_v3 (fixed in D27d3); port bind hub_Wi; DRT-0255 hroot; exit 78 hgi_v3 and pv_v3n (drain, infra).

## 5. Status of the -0840 levers

Done in D27d3: 1 (landing remap, EMIT 0), 4 (pc view, V), 9 (strap pad, changed on 3 pc types), reserved-row walls and pin clear.
Open: 3 (pv R3 / R4 not measured on new RTL), 5 and 6 (hub census: now measured, over), 7 (tap rows need the reset-relay reselect: 21 new
EMIT errors, R), 8 (`OT_LAND_RESERVE` die default), 10 (hroot B).

## 6. Stop list

- No relaunch of hg, hgi or pv kits on D26. The wave launched 13 between 18:23 and 18:44 (hg x8 with hg_v1 at 24 replicas, hgi_v2,
  hgi_v3, pv, pv_v6, pv_v8), three of them as REPEAT with an unchanged fail key. hg stops at -559.80 at place; pv is over the cap.
- No die-wide regeneration in D28 that changes the block of a type without a row (lever 1).
- No "D27d3 green" read as "types close": G0 PASS carries 2,483 warnings, and section 2 lists the ones that were measured.
- No hg / hgi volume on D27d3 before R6c is in the plan.
- No unsplit pv kit on D27d3. No pv split proven one type per event.
- No hub_C or hub_Ei cell verdict from G0; use the placed census.
- No buffer repair accepted for hub_Ei FF hold -443.58 on 29,695 ends.
- No hub_C tap or ahub verdict from this D26 attempt past 3_4: it is over the cap.
- Stands from -0840: no pair-image recompile or second R8 refresh before the D28 bind; no TAP-GRID-R2 kvcap rows.

## 7. Not checked

- The split of hub_Ei's 29,695 hold ends by start class. The link from `-min -385` ring inputs to the -443.58 is my inference.
- hub_C cell count after 3_4 (resize was running); the 416,928 is floorplan census + repair buffers from two logs.
- Whether hub_Wi pads, hroot B and the hub ring rows are in D27d3; the diff shows `pads` changed on hub_Wi and `hard_cores` on hub_Eo / hub_Wo.
- R6c G0 and bind results (running). The R6c rows were not read.
- hgi_v4 GRT overflow count; only the iteration count and log time were read.
- The 10 io_cor DRC outside the south clock reserve.
- Why each of the earlier events changed every block; only D26 -> D27d3 was diffed field by field.
