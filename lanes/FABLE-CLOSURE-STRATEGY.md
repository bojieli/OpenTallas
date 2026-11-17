# FABLE-CLOSURE-STRATEGY 2026-11-17 00:50 PST (0050): die-scale reset / START legs are now the common residual; col has its first routed numbers; the cb setup class survived the L2 source

Reviewer: FABLE-CLOSURE-STRATEGY-0050 (Fable). Read-only. Technical PD only. HBM parked.
Blocking gates (R-MINIMAL): DRC 0 route, routed TT setup >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK. All else advisory.

Read 00:45-00:55 PST: strategy 2140, FABLE-FLOW-2200 (no technical content used), `failure_breakdown.py` 00:45, all queue posts
21:35-00:47 (233 technical posts), handoffs FABLE-FIX-S81-BKSEL, FABLE-FIX-QC-DIECLK, QC-PLAN-R, KV-R, S81-SERDES-R2, HEAD-CODEX-FINAL-1117.
No FABLE-PLAN / FABLE-PD file is newer than 21:40. FABLE-PLAN-HEAD-NF15D2 has no file yet; its subject (HEAD landing-ring seams) is not re-diagnosed here.

**Every number below is REPORTED by the named lane; I opened no DB, log or render this round.** INFERENCE is marked.
Codex covered 22:18-00:43 and parked at 00:43; the live jobs it left are named per lever.

## 0. Verdict

1. **Reset and START distribution is the residual class on all four dies.** S81 t47 has a die-corner reset relay that crosses 2,880 um
   in one cycle (106 ends, -1096) and START origin -> reader legs (t47 63 / -463, t75 24 / -531, station t37 30 / -250.5 at GRT).
   KV's 80-stage START candidate has an unbuffered 2,996 um reset net. HEAD real-pair reads show reset / START hold -225 / -269 and
   sp4 -> sp3 START setup -487.7. QC's SC reset rows passed vacuously. These legs were never reach-scripted like data lanes.
2. **S81 col (203 types) has routed numbers for the first time, and the two 21:40 unknowns are named.** h9_r1 congestion = unordered
   station rows (ordered rows: GRT overflow 0). h9_r2 DRT-0255 = PG cap (PG1 routes DRC 0). What is left on h9_r2 is 29 endpoints
   whose relay or reset wire crosses the seam between paired macro halves (gap 0.036 um) and detours around the macro.
   h10_r2 (rm3) is 3.6 ps from sign-off.
3. **QC cb setup did not close on the L2 source.** The cb pilot is at TT setup repair iteration 1,050 with WNS about -302.9 on
   `u_d6_u_fab_u_x_1_2_a_d.r[0][460]`, 143 endpoints: the same `b_d -> a_d` class as the old source (-294.44, 409 of 417). The xcst
   fanout fix does not touch it. It is a reach class and needs a stage.
4. **The tap-window class is confirmed on KV (99.4 % and 100 % window-only) and half-confirmed on HEAD (45 %).** KV has a clock form
   that removes it at the source (compound template: per-port spread max 56.2 -> 16.1 ps, 0 ports over 20).
5. **Four final-mile hold ECOs signed off since 21:40** (bksel eco3, IFN0 HW hold41, hd_host_w hei3 / outpad5, QC W0 r2). The recipe
   is now fixed; three earlier variants are dead ends.

## 1. The 21:40 levers: done, open, wrong

| # | 21:40 lever | state | evidence |
|---|---|---|---|
| 1 | col route-stage diagnosis | **DONE; my density inference was half right** | h9_r1: station rows, not relay rows (IR1 GRT overflow 0 on M2-M8, pre-GRT FF 5,072 cells, 0 ends, TT +0.04). h9_r2: PG cap (PG1 DRC 0), then TT -138.10 / internal FF -11.24 on 4. h10_r2 rm3: DRC 0, TT -45.58, internal FF 10 ends cleared to +5.01 (estimate) |
| 2 | tap windows on KV / HEAD | **KV CONFIRMED; HEAD PARTLY** | KV hgi_v1 4,408 cross-tap ends, 4,382 pass with the window removed; sys_SD_v1 2,323, all window-only. HEAD hd_mesh: 85.7 % pass with no window, rows tol = SPEF + 10 give 12,346 -> 6,791; about 1.77k are real datapath hold |
| 3 | strip GPL exit 0.25 | **WRONG as posted; corrected** | 0.25 alone skips the second timing-driven pass and leaves 812 um unbuffered nets (-986). Form of record 056783ac187: exit 0.25, second pass at 0.30. t75 -531 / 867 paths, t47 -1538 / 1,486 |
| 4 | QC re-frame, cb pilot reads setup | **re-frame DONE; setup FAILS** | M clock frame: CA 2,993 FAIL 0, cap-in 2,525 FAIL 0, 0 negative landings. cb pilot setup: see verdict 3. New: cbn_q00 NB macro overhangs the outline by 34.572 um (fixed in proposal N) |
| 5 | HEAD stand-ins | **5 -> 4, three got worse** | host_w signed off (TT -29.73, parent pair hold +85.07 on 513 bits after 2,565 output pads). ctl routed TT -96.09; lep0N post-CTS TT -1552.79; sd9c GRT plateau -95.7 / 3,605 ends (GRT-0228) |
| 6 | KV HG3 bind, gen classes | **bind DONE; gen blocked by a checker** | HG3b: PRE 0, G0 0 errors, strict bind 0 over 2,545 crossings, LATCHECK 2,404 / 2,404. Dry GEN refused a spare unloaded `rst_xn[22]`; checker fix approved, D14 tree building |
| 7 | SerDes H3p / G / J | **H3p at DRT; G blocked; J has rows** | H3p GRT overflow 0, hold +0.096. Setup is reported two ways: +103.41 (S81-SERDES-R2) and reloaded -54.29 (Codex; AM predicate + 43 RM.mem paths). J6c: 3 stations, 1,545 FF, hops <= 401.8 um, lane cycles 1 -> 4 |
| 8 | bksel, IFN0 HW | **DONE, both signed off** | bksel eco3 TT -41.23, FF +10.04. IFN0 HW TT -40.23, internal FF 0, after two DRT-1231 failures and one data-unwire detour |

## 2. Levers now, ranked by types / dies unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | col: ordered station rows + PG cap as the col default; relay / reset endpoints on outer macro-face channels; rm3 setup ECO | 203 col types | S81-TYPES-R2 (kits), S81-DIE-R2 (C4 rows) |
| 2 | S81, KV, HEAD, QC | reset / START legs as reach-scripted relay rows, one family per die | S81 75 leaves + station types; KV and HEAD die gates; QC SC | S81-DIE-R2, KV-CLK-R2, HEAD-SPE-EXPORT + HEAD-DIE-R, QC-PLAN-R |
| 3 | QC | cb: one stage on `b_d -> a_d`; then the cb pilot gate | 18 cb types / 192 partitions; QC die clock gate | FABLE-FIX-QC-DIECLK, QC-PLAN-R |
| 4 | S81 | strip: one XR form (t34 / t62) through a full C4 bind | 75 leaf types | FABLE-FIX-S81-STRIP, S81-DIE-R2 |
| 5 | KV, HEAD | tap windows: KV compound template rows in HG4; HEAD rows in NF15e | KV 50 unsigned types; HEAD mesh / ctl | KV-CLK-R2 + KV-R, HEAD-DIE-R |
| 6 | HEAD | the 4 stand-ins by structure: ctl mchk, lep0N NF15e, serdes sd9e / sd9f, mesh | HEAD die gate | HEAD-TYPES-R2, FABLE-FIX-HEAD-SERDES |
| 7 | all | final-mile hold ECO recipe as the only hold ECO form | every near miss; first: rm3, PG1, hd_ctl, QC P3 | HOLD-FLOW-R |
| 8 | S81 | SerDes: H3p routed read decides H4; J6c in C4; G needs PHY macro outlines | 11 serdes types | S81-SERDES-R2, S81-DIE-R2 |

### Lever 1. S81 col (203 types)

Evidence.
- IR1 (col_h9_r1, ordered wide N/S station rows, source e943f1f62f4, 0 RTL / cycle change): GRT overflow 0 on M2-M8 (old kit: max 119 %,
  28,663 hot gcells). Pre-GRT FF repair 5,072 cells, 0 ends, cross-tap +45.03, TT +0.04. GRT pair-skew advisory -31.70. Now past GRT.
- PG1 (col_h9_r2 with PG cap): GRT overflow 0, DRC 0, antenna 0. Sign-off TT -138.10 (rt24b_5.o35 -> rt24b_sk.o35/D), reset recovery
  -99.32 (rt28b_1 rq -> o17/RESETN), internal FF -11.24 on 4 D ends. Census: 318 negative TT ends = 14 D (6 below -42), 25 RESETN
  (23 below -42), 279 macro pins (none below -42, worst -38.44).
- PG1 geometry: the data wire runs (1132.0, 405) -> (1133.6, 177.7) = 357.3 ps around macro e11E; the reset wire runs
  (1131.4, 812.2) -> (1131.4, 583.7) = 346.7 ps around e14W. The gap between paired macro halves is 0.036 um, so nothing crosses it.
- rm3 (col_h10_r2, per-bit istations): DRC 0, TT -45.58 on 73 ends, internal FF -7.46 on 10 (3 D + 7 RESETN). One coupled repair:
  FF 10 -> 0 (+5.01 estimate), setup 73 -> 27 ends, worst unchanged -45.58. Incremental DRT running.

Root cause. Three separate ones, all placement structure: (a) station rows emitted unordered, so bus bits cross inside the row;
(b) PG cap over the station band blocks pin access (DRT-0255); (c) relay and reset endpoints sited at the midpoint seam of a macro
pair, where the only route is a detour of about 230 um each side.

Fix.
1. S81-TYPES-R2: e943f1f62f4 (ordered rows) and the PG1 PG cap become the col kit default in the next S81 tree. Both are 0-cycle.
2. S81-DIE-R2, C4: site rows for the 29 PG1 endpoints (rt24b_sk D, rt28b RESETN sinks) on the outer macro-face channels of
   e11E / e14W. Apply the same rule to every col layout hash by script: no relay or reset endpoint within one macro height of a
   paired-half seam.
3. S81-TYPES-R2: rm3 needs 3.6 ps on 27 ends. Read the worst path first; if it is one net class, one sizing ECO on the routed DB
   (lever 7 route-keep form). If it is the same seam detour, it takes fix 2 and no ECO.
4. Relay depth (P1, 52f93dd0fda) stays opt-in: +3,644 FF and +16.7 % RET words on 6 frames. It goes in only with a fresh native
   bind + LATCHECK in C4, and only for the r0_p* groups that rows cannot fix (10 groups at 21:40).
5. Col volume starts when IR1 and rm3 have routed sign-off and PG1's successor reads >= -42 at reloaded GRT.

### Lever 2. Reset / START legs as plan rows (all dies)

Evidence.
- S81 t47 (GPL fixed, x1.45 CTS census): die reset 106 ends / -1096; u_rrl_235 at (1425, 17) -> u_cland_fstart_ft*_o on the north face,
  2,686-2,880 um, 24 buffers. START: u_cland_origin -> reader_start 63 / -463. Half-cycle (negedge) relay -> next relay -300..-401 on 101 ends (t75).
- S81 t75: origin -> reader start 24 / -531 (1,480 um). slice_station t37 at GRT: -250.5, 30 of 32 ends are START origin -> reader.
- S81 VP reset relay -> 16 lane cores: 40 ends / -378.6 (1,421 um, 9 buffers).
- KV 80-stage selected START: reset b212 -> b300 unbuffered 2,995.9 um, clock slew 381-386 ps; 1,528 virtual stages have no measured arrival.
- HEAD real pair (shared root): reset / START hold TT -225.0 / -225.5, FF -269.4 / -269.8. sp4 -> sp3 START setup TT -487.7.
- HEAD -2023 seam hold: 96 `delaybuf_otstb` pads per forwarded branch (TT 2,175.5 ps) from a balance pass that read a sinkless
  subtree as an early arrival. Tool fix 68c5f9608db; 192 pads being removed by reroute. This is a tool defect, not a design class.

Root cause. Data lanes are budgeted by the reach script (hop <= 405 um, cycles priced). Reset, START and origin legs were emitted as
single-cycle broadcasts or as virtual stages with no site, so they show up as the worst path of every sparse type once placement is sound.

Fix.
1. S81-DIE-R2, C4: relay rows for every `u_rrl_* -> cland_fstart`, `cland_origin -> reader_start` and VP reset -> lane leg, by the reach
   script over ALL S81 types (not only t47 / t75 / t37), hops <= 405 um, cycles as needed (pre-approved). Raw-reset phase fix
   3ba97e3bdc4 (t47 / t75 chains 30 / 18 FF, 0 cycles) is the emitter; it needs sites.
2. Half-cycle relays: put relay and follower on the same edge, or keep the pair within 150 um. A negedge relay has 416 ps for the whole hop.
3. KV-CLK-R2: the bounded-405 START successor (model running) must give every one of the 1,528 stages a site and a measured
   arrival before any build. No rerun of the 80-stage form.
4. HEAD-SPE-EXPORT: finish the 192-pad removal and re-read the pair; then the 2-bit falling-entry coupon for the genuine -225 / -269
   phase miss, and the sp4 clock fork (model only so far) for START. FABLE-PLAN-HEAD-NF15D2 owns the verdict.
5. QC-PLAN-R: SC reset rows through the new composer (the old PASS dropped all 61-66 rows); W0 needs a reset contract >= 5 edges.

### Lever 3. QC cb: the `b_d -> a_d` setup class (18 types / 192 partitions)

Evidence. Old source, placement RC: -294.44, 417 ends, 409 are `u_fab_u_x_*.u_st.b_d -> tap_d / cap / u_d*_a_d.r[0]`; worst is zero
logic, 20 buffers, 955 ps of wire. L2 source pilot (cbn_q01__clab6e67f2, E8 unit 3164095): CTS done 00:35, TT setup repair at
iteration 1,050, WNS about -302.85 on `u_d6_u_fab_u_x_1_2_a_d.r[0][460]/D`, 143 ends. Hold side is closed: 785 ends -> 0 with 1,311 cells.
Old Q6D kits: cbx_q10 -8369.76 (sx0 -> cap31 high fanout), cbn_q00 -186.48 (NK lockup -> u_t11.tap).

Root cause. 955 ps of wire at about 0.45 ps/um buffered is roughly 1.5-2 mm (INFERENCE): the fabric station output feeds a capture
bank that sits a die-scale distance away with no stage. Repair cannot buy 300 ps on a zero-logic path.

Fix.
1. FABLE-FIX-QC-DIECLK: let the pilot repair end, then print the 143 ends with launch and capture coordinates and wire length. Do not route it.
2. QC-PLAN-R, in M (or N if M is sealed): one station row on `b_d -> a_d` per fabric column, placed at the a_d bank, +1 lane cycle on
   those lanes, or move the `u_d*_a_d` capture bank beside `u_x`. Rows by the reach script.
3. Pilot gate for the cb wave stays: reloaded GRT TT >= -42 with no `b_d` endpoint below -42, internal FF >= 0, overflow 0.
   The M contract differs from the L2 pilot (count straps 7 -> 6, 34k changes), so the proving pilot is on M.
4. QC-CLK-R2: N geometry (u_cland_nb_i00 x 1129.68 -> 1086.48) needs its one clock branch proof (clk_c6 moves 43.2 um in 11 copies).

### Lever 4. S81 strip leaves (75 types)

Evidence (FABLE-FIX-S81-STRIP 00:44). GPL form 056783ac187: t47 exit 1.07 x minimum, DPL max displacement 2.3 um; ring, ft-station and
unbuffered classes gone. Left on t47, 655 ends below -42: die reset 106, START 63, VP coefficient controls 202 / -264, vpw 281 / -249.
Form B full-shape elab: +5,018 FF per leaf (4,096 HI + 902 writer + 16 DSR + 4 reset); write +1, hc_post +1, boot +1. Writer / RAW
proof 10,001 / 9,995 checks PASS. A partial-context bind cannot emit it (`native_istations.annotate` aborts on an omitted column).
t75 ft0 station 4 -> 5: 390 bits at 442.8 um; repack v2 gives 380.7 um, 0 FF, 0 cycles.

Fix.
1. S81-DIE-R2: one full C4 bind carrying XR + 16 dswp copies + bank-end placement + CFR with XR + lane reset copies on t34 and t62,
   the t75 repack, and the lever 2 rows. Source keeps HI_D 2; the stage mapping must be XR-aware before the ELAB (else 4 stages).
2. All 75 take XR after the t34 / t62 reloaded-GRT read is >= -42. Lever 2 rows must be in the same bind, or t47-like leaves fail
   on reset / START with XR on.
3. Next S81 tree: 056783ac187 + 588ce81. Leaf kits only from it.

### Lever 5. Tap windows: KV HG4 and HEAD NF15e

Evidence. KV e9 compound template (264823d689, default off) on HG3b: GRT overflow 0 TT / FF, 11,571 taps, exact SPEF per-port
tolerance max 56.2 -> 16.1 ps, p99 24.2 -> 11.4, ports over 20 ps 95 -> 0. hgi_v1 projection with e7 rows: 4,408 -> 163 ends.
KV signed pair io_E6 / sys_SE flat: TT -11.16, FF hold +216.6. HEAD: rows tol = SPEF + 10 cut hd_mesh cross-tap 45 % and raise TT by
11.6 ps; port_in gets worse (-94 -> -121) unless seam in_min / out_min are re-derived at span 71.7.

Fix.
1. KV-CLK-R2 + KV-R: HG4 rows are re-cut from the e9 compound clock, not e8 (e8 leaves 95 ports over 20 ps). One bind.
2. KV-R: first D14 pilot stops at the post-CTS FF gate and prints cross-tap ends; expected under 200 on hgi.
3. HEAD-DIE-R: rows tol = SPEF + 10 with re-derived seam in_min / out_min go into NF15e, together. hd_mesh is at GRT congestion
   iteration 30 / 30; its hold padding is the likely load (INFERENCE), so mesh is rebuilt on those rows rather than pushed through DRT.

### Lever 6. HEAD: 4 stand-ins, each structural

- **ctl** (routed TT -96.09, 16 ends; internal FF -9.59 / 24): g_ms[4].g_h[1].u_h/q -> about 1 mm of wire (372 ps in 3 repeaters) ->
  6-level OR -> mchk_cpy on a far tap. Fix running: MCHK_LOCAL (local OR stage), pre-GRT TT +1.53. HEAD-TYPES-R2.
- **lep0N** (post-CTS TT -1552.79, 4,416 ends, worst g_pout.g_s[0].u_st.q[540]; core taps 518-612 against 450): NF15c form is dead.
  NF15e (45 SRAM moves, +4,555 FF, 35 stage groups) has G0 0 errors, LATCHECK 329 / 329; route held on two control legs at 405.34 /
  405.72 um and the TXI producer cone (ROQ 1,104 FF). HEAD-TYPES-R2 confirms g_pout reach is inside NF15e before GEN.
- **serdes**: sd9c ended GRT-0228 at -95.7 / 3,605 ends (rm rp_g2 -> mem -166.87; rem_q pays a 50 ps window + 58 ps HB4). sd9e (RM
  staged local write, +1 rclk) is at GRT, earlier TT +2.76 / FF +4.86; sd9f adds encoder look-ahead at 0 cycles. FABLE-FIX-HEAD-SERDES.
- **mesh**: lever 5 item 3.

### Lever 7. Final-mile hold ECO recipe (HOLD-FLOW-R)

Evidence. bksel: 46 of 51 failing ends were macro input pins the planner skips; padding 7 of 8 sinks of a net shortened the
re-route and cost the 8th sink 14 ps. IFN0 HW: 280 HB4 gave DRT-1231 twice (PA wipe proven not causal); the data-unwire reroute
passed DRC but moved 39 previously positive ends to -3.37; a 41-cell route-keep pass on that base signed off. QC P3: 9 HB4 at GRT
0 ends, then DRT-0255 on worker-boundary access points in old nets with no HB4 pin.

Fix (one form). Hold-only, route-keep, clocks frozen, every other repair off, target +10; the plan includes macro input pins and
pads every capture sink of a touched net or none; never data-unwire a signed-quality route to place pads; a second small pass on
the routed result is normal. First users: rm3 / PG1 internal FF, hd_ctl 24 ends, QC W1. P3 needs a router-side cause, not a new plan.

### Lever 8. S81 SerDes (11 types)

- H3p: take the routed sign-off number, not either GRT figure. If the AM predicate / RM.mem class is below -42, H4 (predicate beside
  the alignment FSM, max hop 267.9 um, 0 cycles; CTS running) is the form.
- J: J6c rows in C4 (lanes coll EN3 58 -> 61, WS2 74 -> 77).
- G4: local encoder clock entries are blocked by a blanket PHY keepout over the whole legacy u_phy lot; the real macros occupy only
  y 951-1223 (PMA) and y 62-231 (SRAM / dchn). S81-DIE-R2 replaces the lot keepout with macro outlines + explicit feeds in a clock event.

## 3. Stop list

1. col: an unchanged PG1 retry; unordered station rows; rm2 / rm4; col volume before IR1 and rm3 have routed sign-off.
2. GPL: global `-overflow 0.2` (78c5645) and 0.25 alone (39ef73a); the ft_polarity_local band shift (3,306 macro hits).
3. Strip: partial-context binds for form B; leaf volume before the t34 / t62 read; plan HI 3 written into source with XR; XR without the reset / START rows.
4. Reset / START: single-cycle die-corner broadcasts; KV 80-stage reruns (also at 0 uncertainty); MCP or window waivers on sp4 -> sp3;
   hold cells against the HEAD -2023 seams (they are 96 tool-inserted pads).
5. QC cb: more setup repair iterations on `b_d -> a_d`; old Q6D retries (cbx_q10, cbn_q00); raising MAX9 column pads for W5 S (the
   stale CB16 extra was the cause); L2 pilot proof borrowed for M; placement-RC reads quoted as GRT (the -1950.60 cbx read).
6. Tap windows: KV HG4 on e8 rows; xmirror retry; HEAD flat tol 10; hold cells on window-only cross-tap ends on any die.
7. HEAD: sd9c / sd9d; hw5 dedicated-bank tap (TT -47.65); NF15c lep0N; original ctl; pushing mesh through DRT at 30 / 30 congestion iterations.
8. Hold ECO: data-unwire to place pads; forced PA wipe or generic catalog restore as the DRT-1231 fix; padding part of a net;
   bksel fx7 and eco_hold_codex1116; same-kit P3 retry.
9. SerDes: H2 (-169.93), G3, J5, J6b (411 off-row sites); G4 route before the PHY keepout is replaced.
10. Still valid from 21:40: clock rows cut from GRT readout spread; hold cells on a capture pin whose setup slack is below the cell delay.

## 4. Not checked

- Nothing was measured by me this round: all numbers are lane posts and handoffs. No DB, log or render was opened.
- H3p setup after GRT is reported as +103.41 and as -54.29 by two lanes; unresolved until routed sign-off.
- The cb `b_d -> a_d` wire length is my estimate from 955 ps; the pilot's coordinates were not read. The pilot repair had not ended at 00:43.
- hd_mesh congestion cause, and whether PG1's 279 macro-pin ends (worst -38.44) move below -42 when endpoints are re-sited.
- How many of the 203 col types each of the three pilot forms covers; the r0_p* relay-depth groups have no routed pilot.
- IR1, rm3 incremental DRT, H3p DRT, H4 / G4 CTS, sd9e / sd9f, MCHK_LOCAL ctl, KV D14 build and HG4 gate, HEAD 192-pad route: all still running at 00:45.
- S81 "other flow error 7", QC "other flow error 6", serdes__t3 place error and serdes__t4 hold after CTS in the breakdown: not opened.
