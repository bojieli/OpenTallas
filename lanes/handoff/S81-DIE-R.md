# S81-DIE-R (successor of FABLE-DIE-S81 + DIE-S81-92): S81 whole-die plan, clock, adoption

MEASURED = files/runs I read or ran. Base: current819/D3 adopted (ADOPT fb0a249ce735), raw 819037bbe371, source epyc10 kw45/src_s81_pin_3c913dbdfb23_f2s4_cohort_d3.
Work dir: epyc10 `/srv/opentallas-scratch2/claude/s81-b3-clk/rows/f2s5_S81-DIE-R` (E). Clock dir: epyc10 `/srv/opentallas-scratch2/claude/fable-die-s81` (W), run `W/s81/F2s4currentECOv3` (R). Logs: intel2 `~/fable-die-s81/current8190_v3_R4{c,d}.log`, `~/s81-die-r/`.

## 2026-11-16 17:5x PST state

### 1. Die clock on 819 (ECOv3 tree cda34b3a)
- GRT TT/FF: overflow 0 on M4-M9, 0 errors (R/grt_st_{TT,FF}/combo_*.log). Usage M4 2.7 / M5 4.0 / M6 4.4 / M7 2.2 %.
- Ordinary STA (unit 1715200, exit 0, R/sta/die_sta_related.json): TT setup intra +340.60, seam +270.13, 0 negative pairs. Skew intra 326.7, seam 452.4 (fW1_p4_b0.clk_c6 <-> fW1_p3_b0.clk_t35), WARN only.
- Hold: UNMEASURED. 0 signed views fed (3,374,386 pairs; 41 cores + types missing). Arrival contract needs 266 intra / 386 seam against 37 / 40 declared (advisory under R-MINIMAL). Per-port kit windows: R/kitwin.json (395 types, 21,571 ports).
- Landed pairs: single-cycle FAIL as designed (damage 3769 TT / 3379 FF). Covered by the K table below once composed.
- R4 (client 4065010, unit 1553643) exited 2: the D3 `count_align_plan.py` has no `--strap-window` / `--min-lat-cycles` (those 3 opt-in hunks live only in epyc10 die-clk-s81-b6/ca_tools). Failed r4/ kept. Phase/OCV inputs of r4/ were complete and are reused.
- R4c (same recipe, ca_tools planner; unit 2116733): 993 crossings, fail 0, start 376/376 clean, strap sim 0 violations, min margin +106.2 / +107.0. 60 depth changes vs adopted (22 of them 8->4).
- R4d (R4c + opt-in `--depth-floor` = adopted depth; unit 2526812; driver W/reach_codex/run_current_r4_ca_floor.sh): same margins; delta vs the adopted sidecar table: K 795 ties, depth 4->8 on 38 crossings (16,855 bits, 37 lanes, 15 receiving types), no 8->4, sched_lat changed on 294 crossings / 206 lanes, sum 2522 -> 2561. R/r4d/{plan.json,regions_ca_strap.json,straps.json,delta_vs_adopted.json}.
- The adopted K table is still the B6gsh-kit table. The landed margin of record is therefore not measured on this clock until R4d is composed and bound (item CA_R4_ECOv3 of the F2s5 ledger).
- Node 248 (feed std_bg_72_0 -> std_bg_91_0 around the lk PHY): 13 stages, 2275.8 um detour, max hop 234.4 um, legal. Node 19 (cap/xr overflight, std_bg_54_0 -> std_bg_64_0): 8 stages, max hop 343.4 um, 423.6 ps. Both are inside the measured TT/FF arrivals; neither is in a worst pair.
- NOT closed: no type reserves the 93,626 die clock cell sites. R2 candidate plan W/reach_codex/f2s4_current8190_native_R2.json differs from 819 only by clock.reserved_sites_um on 395/395 types (93,506 windows, M1-M7) and die.channels. Adopting it re-keys every type; needs a ruling + an occupancy census on signed/routed DBs.

### 2. CFIFO 72-row K2 / E[2,3]
W/reach_codex/current8190_frame_lk_DIE_EPOCH.json (script derive_current_frame_lk_die_epoch.py). The six CFIFO root pins have no core tap; under the kit rule (nearest generic tap to the PIN) they hang on 2 taps (6 rows) or 4 taps (66 rows). Measured ECOv3 tap pairs (TT+FF, rise+fall, CPPR at LCA): die xk-cr in [-106.7, +142.2] ps (model assumed 80). 72/72 rows keep K=2 and legal E [2,3]; remaining kit CTS allowance >= 514 ps. Still kit gates: kit CTS skew xk vs cr, reset recovery/removal (R0-G0 = 0), provider 1-cycle bank->o.

### 3. SerDes clk_t48
E/t48/t48_feed_decision.json. Row: serdes__t1__clb45db5be clock.added_taps += clk_t48 [1992.6, 228.96] (die 24679.072, 332.64). The earlier [1985.048, 228.96] site is refused by schema (tap spacing 8.64). Feed: second sink on leaf net n30607 of b30607 (clk_t13 leaf), 0 new cells, common13/48 not split. Bounds (primitive NLDM, model): +3.94 fF, common shift <= 1.81 ps TT, 13-48 pair <= 0.2 ps. Kit rule: clk_t48 takes the clk_t13 window, one common clock. Waits: SERDES source port + successor graph tap row.

### 4. T51 native_e -> signed 1116 view
E/t51e/{t51_e_signed1116_rows.json (207 patches), overlay/ (11 files), t51_e_signed1116_report.json, plan_819_plus_t51e.json dabeea89}. Signed LEF == D3 _rphase1116 LEF; 11145/11145 ledger pins == signed pins.json; 43 M7 roots +0.020 um x; lib -> 1116 tt; insertion 254.88 / 195.31 on 41 taps. W child untouched (unsigned). G0 of the candidate: E/g0/t51e, unit oth-ubuntu-2472551-1794879363, intel2 ~/s81-die-r/g0_t51e.log (expect the 6 inherited errors, 0 new).

### 5. Next event
E/F2s5_ledger.json. Ready: CA_R4_ECOv3 (compose next), T51_E_signed1116. Row ready, waits source: clk_t48. Waiting on owners: SVC t6 stage 9, COLTAP reset-chain sites (none needed so far), IFN0 halves (unsigned), CONG t43 (SOURCE_HOLD). Needs ruling: R2 reservation.

### 6. COORD 11-16 ~18:0x: gunit bf rows
FABLE-FIX-S81-GUNIT writes delta rows (bf back to the signed 432x216 shape + pre-nrev pins, 4 ba1 +43.2 y, W/E landings +21.6). Folded into the F2s5 ledger as GUNIT_l1f_bf_signed_shape, waiting for the rows. Checked in 819: gunit__t1 has 4 bf at [432.0,172.8] with nrev_1113 pins and LEF, ba1 abutting at bf y + 172.8. On delivery: expected-before, overlap/outline of gunit__t1, pin_sites, G0, then compose. gunit__t1 also takes one depth 4->8 ring from the CA table, so one re-key covers both. COLTAP reset-chain sites, t43 and IFN0 rows join the same event when ready.

### 7. Fable review FABLE-PD-S81-F2s5 (hub post fb8f6ff51727)
- BLOCK on the CA table as-is for svc_lo_dsdv_svc_rs__t1 (svc_2): depth-8 rings do not fit bands ft0_i (use 1.80) and idx_i0 (1.74); unit_i1 0.95. Tight: slice_station__t26 ft4_i, ot_s81sl_leaf__t11 leafdn_i0 (1.01). Band sizing is depth-blind.
- Cheaper first (not evaluated): the four svc_0->svc_2 crossings miss the depth-4 limit by 6.5-19.2 ps (try a ~20 ps svc_2 phase move or T/2 edge); svc_14->svc_12 and svc_14->eng miss by 1.9 / 2.6 ps; nine crossings are deep only through --min-lat-cycles 1.
- sched_lat OK; LATCHECK must show the three partition pairs with one-cycle lane differences are independent.
- T51 OK; view port-start FF hold -53.04 ps on 5268 endpoints must close in the parent kit.
- clk_t48 OK. R2: separate event, read-only odb census, ECO only hits.
- So step 2 below starts with a planner pass that removes the near-miss depth-ups before any compose.

### 8. COORD r389 (11-16 ~18:4x)
- (a) Planner reruns on epyc10 W/s81/F2s4currentECOv3 (driver reach_codex/run_current_r4_ca_phase.sh; opt-in --part-phase and --min-lat-exempt in the private planner copy). r4g = R4d + svc_2 clock 20 ps earlier (MODEL: crossing d and fall interval shifted, start edges not): 33 depth-ups, svc_2 has none. r4h = r4g + the 9 crossings exempt from --min-lat-cycles 1: 993 crossings, fail 0, start 376/376, strap sim 0 violations, +106.2 / +104.9; depth 4->8 on 24 crossings / 9 types (9,125 bits), sched_lat sum 2522 -> 2551, 9 crossings at sched_lat 0. svc_lo_dsdv_svc_rs__t1, slice_station__t26 and ot_s81sl_leaf__t11 take NO deeper ring, so their bands stay as adopted. Scaled ring fit of the 24 remaining bands (x 5527/3074): 23 at 0.85-0.89, one over: svc_lo_dsdv_svc_rs_w__t1 hbmrd_i0 (1120 b) 0.648 -> 1.165, must grow in compose.
- The svc_2 -20 ps move is a planner model. It needs a real clock ECO on the svc_2 feed (successor graph + GRT + arrivals) before the table is a measured result.
- sched_lat 0 on 9 crossings: the planner and strap sim accept it; the bind / lane price of a 0-cycle landing is not yet proven (adopted table minimum is 1).
- (b) R2 reservation is its own event (census first); not in F2s5.
- (c) gunit rows copied to E/gunit (40 patches, 11 overlay files). Applied with the T51 rows on 819 with expected-before: E/cand/plan_819_t51e_gunit.json ed35d72ec082, overlay E/cand/overlay (22 files). gunit__t1: 22 cores, 0 overlaps, 0 outside, 0 pin-site duplicates. Bind needs define OT_GUNIT_BF_FWPIPE, lane RT_LAT 66/64. G0 of this candidate: E/g0/t51e_gunit, intel2 ~/s81-die-r/g0_t51e_gunit.log.
- (d) T51 adopts only if the view port-start FF hold (-53.04 ps, 5268 endpoints) closes in the parent slice_station__t51 kit. No parent measurement exists yet (W child view is unsigned).
- Compose: the last real compose was B6gF2s from a PRE plan; every later event applied rows on the composed plan. Estimate-only recompose of the candidate with the r4h table: E/cmp/r4h_t51e_gunit, intel2 ~/s81-die-r/compose_try_r4h.log.

### 9. COORD 11-16 ~19:1x (items 1-4) + strip rows; state 19:5x PST
- G0 819 + T51: FAIL 6 = the 6 inherited, NEW 0 (E/g0/t51e). G0 819 + T51 + gunit still running (E/g0/t51e_gunit).
- (2) Latency 0: none of the 9 crossings can be a same-phase reg-to-reg path. Their launch-to-capture intervals are 896-1670 ps wide against T = 833 (R/r4h/lat0_same_phase_check.json). All 9 are back at 1: table of record candidate = r4g form (33 depth-ups on 14 types; svc_rs__t1 none; slice_station__t26 3 and leaf__t11 1 are back, so their bands and svc_rs_w__t1 hbmrd_i0 grow in compose).
- (3) svc_2 20 ps EARLIER is not buildable as a row: svc_2 hangs alone on feed leg 11873 (8 hops of 194.9 um, near the delay-optimal pitch ~173 um); fewer or more stages both come out later. The equivalent that IS buildable: svc_0 LATER (svc_0 hangs alone on leg 11401, 4 stages). Planner r4i (svc_0 +20) and r4j (svc_0 +32) give exactly the r4g result (fail 0, strap sim 0 violations, 33 depth-ups, svc_2 none). Two adjacent inverter pairs on leg 11401 are about +42 TT / +32 FF. NOT built yet: no successor graph, no re-measured arrivals.
- Compose: an estimate-only recompose of the candidate with the new table FAILED (E/cmp/r4h_t51e_gunit, compose rc 1): landing_contract "cland_tstart__start_s_3N_L0__s_3N_L2 actual endpoint hop 2562.496 um exceeds 405". The planner derives the start tree from the clock tree (--start-tree clock), ECOv3 is the kr3 topology and the adopted start network is the B6gsh one (378 vs 376 start edges, 145 / 143 region names differ), and a recompose drops every post-compose row (start/monitor relays, reset bridges, tapfix). So the new K table is NOT a row delta on 819. It needs either a full recompose with all post-compose row sets re-applied, or an in-place table refresh tool that keeps the adopted start network. Not in the bind below.
- (4) T51 parent kit: GEN of slice_station__t51 on the 1116 view (E/t51kit/try1, tools/gen_t51_parent.sh) FAILED: "macros have LEF but no timing liberty: ..._native_w". The W child is an unsigned abstract without a lib, so no parent kit can time the E ports. T51 is carried out of this event.
- Strip rows (S81-TYPES-R): E/strip. t34 VQ rows applied as given. t43 file read by intent (rows 79..87 withdrawn, 15 two-station rows added with stations = 2; "unchanged" markers and bus_stations are annotations); lanes dn_s_4N_L1 / up_s_4N_L1 fixed_cycles +1 -> lane cycles 8->9 / 5->6, sum 14715 -> 14717. Open question to TYPES-R: withdrawn rows carried 192 dn / 100 up bits, new rows carry 101 / 410 (u_vs.s_d 156 b and s_v have no row now).
- t8 (TYPES-R HOLD): three edge_clocks tap_um at x 1440.736 were not moved with the 1598.40 outline; row fix owed by this lane, not in this bind.
- BIND LIVE: B6gF2s5 = 819 + gunit 40 rows + t34 + t43 (+2 lane cycles), adopted CA sidecar unchanged, define OT_GUNIT_BF_FWPIPE added, overlay E/cand/overlay_A (gunit signed view). Plan E/cand/plan_A3_819_gunit_t34_t43.json 83511ebe12a9 -> M/ev/B6gF2s5.json. Chain M/chain_f2s5.sh (fresh elab, G0 beside elab, strict bind, LATCHECK), unit oth-ubuntu-3411709-1794882691, logs epyc10 M/log/B6gF2s5.log, intel2 ~/s81-die-r/chain_f2s5.log. Fable review FABLE-PD-S81-F2s5b running in parallel. Likely fail-closed points: LF_CS_DEPTH (leaf station netlist die_b178_lfcs.v not regenerated for t43), gunit seam/pins, t34 reset identity.
- Other G0 runs: E/g0/plan_A2, plan_B2 (same plans without the lane price); E/g0/plan_A, plan_B are invalid first attempts (t43 markers applied literally), kept.

## Next steps
1. Read G0 t51e. 2. Compose CA R4d on the 819 lineage (fallback_land compose; check the 38 deeper rings fit their bands), regenerate lanes, estimate before build. 3. F2s5 = 819 + T51 + CA (+ SVC stage 9 if delivered): source cohort with the overlay and the ca planner hunks from TOOLS-CONVERGE, fresh elab, strict bind, LATCHECK, G0; Fable review in parallel. 4. R2 ruling and census.
