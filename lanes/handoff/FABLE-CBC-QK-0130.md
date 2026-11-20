# FABLE-CBC-QK-0130: QC and KV hard types, close-by-construction review (2026-11-20 01:25 PST, interim)

Lane: Fable expert. Marking: **V** = I read the database, log or code this session. **R** = a lane post. **I** = inferred. **P** = proposal.
Gate used: route DRC 0, TT >= -42, FF internal hold >= 0, bind + LATCHECK. Nothing here is a new gate or hold.
Files: epyc7 `/srv/opentallas-scratch2/claude/fable-cbc-qk-0130/` (`hd_sle_hc0/`, `census27/`, `pc_formB/`, `kx_hc0_xt/`);
`census27/` also on epyc2, epyc9, intel1. Lane clone: intel2 `/srv/opentallas-scratch2/claude/wt/fable-cbc-qk-0130`.

## 0. Headline

| # | item | cause class | state |
|---|---|---|---|
| 1 | QC kit hold (27 failed sign-offs 11-19: hc0, hc1, su_l0, su_l1, st_b, sc, stm) | flow: the cross-tap hold guard has been off since 11-14 | **fixed on main 77553520681**; proof kit queued |
| 2 | kv3_pc PDN form B | PDN: every core PG pin is open | **form B must not be used**; form A + lattice rows below |
| 3 | cb legs "up to 2,149 um" | misread: 2,149 is a COUNT of legs over 405 um; the longest is 471.9 um | no geometry fix needed |
| 4 | coll_core, tt_ctlm | RTL depth: memory read in one cycle (R-RTL-3) | owners' forms are right; two additions below |
| 5 | kv3_hub_Eo | geometry: a 3 % filled soft type with no regions | rows = the 61 station rows of its own placed scan + 2 forms |
| 6 | qkd_hr_ingest_eng | clock: the 117 ps is an internal range, not a boundary number | early tap + input lockup, no re-CTS |
| 7 | sink bins 2.64x | bins measured before the stations were added | generator rule |

## 1. QC kit hold: the cross-tap guard was silently off (V)

**Evidence.**
- `pregrt_ff_hold.log` of every kit read (8 of 8): `OT_PREGRT_FF_HOLD cross-tap guard not applied (no tap window lines in the kit SDC)`,
  `tap_ports 0`. The kit SDC has the lines (227 in sle_hc0).
- Cause in `pregrt_ff_hold.tcl`: every port named in `core_taps_ff.sdc` went into the skip list ("early core taps"). Since R-CLOCK-7
  (11-14) that overlay carries the FF arrival offsets of **every grid tap** (126 ports on sle_hc0), so no tap was left. The 45 ps
  route guard (`OT_PREGRT_HOLD_GUARD`) never ran; cross-tap pairs were padded to the 5 ps base margin on placement RC, and the GRT
  hold repair then stops at 0 violators on GRT RC (sle_hc0: ws +1.26), which is not the routed clock.
- Routed misses by tap pair, from `6_final.def` + `signoff/ff/ep_ff.tsv` (`deftaps.py`, no STA):

| kit (wave) | internal hold ends | cross-tap / worst ps | same-tap / worst ps | unresolved |
|---|---|---|---|---|
| sle_hc0__cl929603c0__cl38badc56 (N4 a3) | 157 | 150 / -21.86 | 7 / -5.76 | 0 |
| sle_hc0__cl929603c0__cl4baa7c9c (N4 a5) | 308 | 304 / -41.41 | 4 / -9.41 | 0 |
| sle_hc0__cl05696ed1 (N4 a8) | 28 | 24 / -15.10 | 4 / -1.48 | 0 |
| slw_hc0__cl1bc59e1c (N4 a4) | 97 | 93 / -13.26 | 3 / -6.86 | 1 |
| slw_hc1__cl3449ea95 (N4 a5) | 143 | 77 / -16.04 | 13 / -10.90 | 53 |
| slw_su_l0__cl1a1c1f8f (N41Q) | 58 | 43 / -15.68 | 15 / -9.05 | 0 |
| sle_su_l1__cl5ea486db (N42) | 47 | 38 / -10.73 | 9 / -6.26 | 0 |
| sle_su_l1__clc6d66f5b (N42) | 19 | 3 / -9.85 | 16 / -17.26 | 0 |
| total | 857 | **732 (85 %)** | 71 | 54 |

- One path in full (sle_hc0, `hd_sle_hc0/sta.log`): launch `u_xl0_3.wd[131]` on tap clk_t90 (source latency early -9.6, flop clock
  at 169.9), capture `g_t[0].g_e[8].m[3]` on clk_t47 (late +30.1, flop clock at 229.0), CRPR 0, data 40 ps (INV + OA21), slack -20.19.
  The same pair on one tap gets the 20.2 ps window back as CRPR.
- QC-HOLD-0030 class C called these "zero-logic chains, tap not resolved". They are tap crossings of ordinary 1 to 3 gate paths
  inside the xslice (wd -> m, wd -> wo_d, xh <-> xl). No lockup latch is needed on them.

**Fix (done).** main `77553520681` (`tools/die_plan/pregrt_ff_hold.py` + test, 41 tests pass): only a core tap (the port with a plain
`-source -clock` line in the overlay) is skipped; a grid tap takes its FF early value from the overlay, so widening and restore use the
live value. Same-tap pairs still get the widening back as CRPR, so the cost falls on cross-tap pairs only. Per-type opt-out is unchanged
(`clock.pregrt_hold_guard_ps` <= base margin).

**Rows (P).**
- QC-PLAN-R3: take tools >= 77553520681 into the next event (V1). Die-level `clock.pregrt_hold_guard_ps` 55 instead of the default 45:
  the worst routed cross-tap miss was -41.4 from a +5 target, so the measured drift is 46 ps. Read the buffer count on the proof kit first.
- KV-D23-COMPOSE: same tools pin from D25f. kv3_pv types: keep `clock.pregrt_hold_guard_ps` at the base margin (5) until form C
  (lockup) is in the kit: v8b has 47,549 cross-tap ends, which a 45 ps pad cannot afford (R, FABLE-FIX-KV-PV). hg / hgi / pc: default 45.
- The 7 to 16 same-tap ends per kit (worst -17.3) are GRT-to-route drift inside one tap: the late ECO class, unchanged.
- cb tiles keep the `r_dly_lockup` rows of N46V0: their die port windows are 100 to 283 ps, beyond any pad.

**Proof status.** Private kit `kx_hc0_xt` (epyc7, fork of the N4 a3 kit with its CTS result, patched guard, old runner so no uniform
reg-to-reg pass, GOAL route) is **queued, not started**: every host admits 0 GB at 01:20. ot-run client pid 4053890 on intel2, log
intel2 `~/.local/state/cbcqk_kx_hc0_xt.log`. Read when it runs: `pregrt_ff_hold.log` line `pass xt` (ends, hold cells, setup after),
then routed internal FF hold. Pass mark: cross-tap internal hold >= 0 at route with TT >= -42. Owner to collect: QC-HC-STM-0005.

## 2. kv3_pc PDN: form B leaves the cores open (V)

Read-only on KV-PC-PG-2330 `pdn_b6.odb` (form B = no `core_pg_M5` macro grid; pdngen rc 0):
- 0 of 688 core PG pin stripes overlap or touch a same-net die shape (8 cores, 66 VDD + 66 VSS per pcc, 20 + 20 per pcf);
  `dbITerm isConnected` 0 (`pc_formB/conn.log`, `conn2.log`).
- Die M5 stripes stop 1.8 um outside the core; the pins start 4.3 um inside: a 6.1 um gap.
- Lattice: u_kvpc2 is placed at x 552.576, 0.384 um off the 4.32 lattice (die VDD M5 at 6.900 in core coordinates, core pin at 6.516).
  AUTO-GEOM already reports it as `macro_lattice ... residual 0.384` and nobody reads it.
- Die M6 over a pcc survives on 816 of about 18,200 um (VDD): a via-drop onto the M5 pins gives about 3 vias per stripe, none on some.
- The core has no M6 PG of its own (M1 / M2 follow-pins + M5 stripes only) and routes 17 % of M6 and 30 % of M7. A 0.12 um M5 stripe of
  259 um is about 980 ohm end to end (I, from the kit M5 unit R). Fed from the ends only, the drop is I x 123 ohm per rail: 0.3 mA
  per stripe already spends the 35 mV budget. So the view cannot be powered by any parent form. Core power not read; the number is a bound.

**Rows (P), KV-PC-PG-2330 + KV-D23-COMPOSE.**
1. Form A is required, not optional: recipe `pg_top M7` on qkd_kvs_pcc, pcf and the two h_head_p views (own M5 / M6 / M7 mesh, PG tracks
   reserved before the core routes, M7 stripes exported to the core edge). The uncommitted change in the central checkout does this.
2. Rule: **a hard core is fed through an orthogonal crossing, never by same-layer abutment.** The die M8 PG straps (12.1b) cross the
   core's M7 stripes; the tile abstract must list the core M7 stripes as tile PG pins.
3. Until 2 is in the die flow, same-layer M7 needs the origin on the lattice: x = 0 mod 8.64 for R0 / MX, x + W = 0 mod 8.64 for MY / R180,
   y = 0 mod 4.32. The generator comment "core origins sit on the 8.64 lattice" is false for this plan (552.576 / 8.64 = 63.96), and
   pcf is 10.5 pitches wide, so its MY copies land half a pitch off: 0.384 um = one M7 VDD / VSS step (0.288 + 0.096).
4. Compose estimator: read `macro_lattice` from AUTO-GEOM for every hard core with PG pins above M4.

**Proof status.** Form B disproved on the real DB. Form A not built (needs the core re-harden; owner KV-PC-PG-2330).

## 3. cb family legs (V)

`2149` in the PRECHECK line is `legs_over` for cbn_q01__cld9ff4c40 (leg rule pin2pin-nocore-nostrap). The longest are
`u_lpad_nb_i12.r[0] -> r[1]` 417.6 um, `r[1] -> q` 417.1 um (514 bits each) and `u_ist_y_o12_1 -> u_bout_y_o12` 471.9 um (408 bits).
The same scan's one-cycle reach is 580 um; at its 1.24 ps/um these legs take 517 to 585 ps. They are 3 to 17 % over the 405 um planning
target, not a failure class. Other cb kits: 905 to 1,978 legs, same form.
- P, generator rule: a pad chain spreads its D stages at span / (D + 1); cap the pitch at 380 um and put the surplus stages at the
  consumer end. 0 cycles where D allows it. Where it does not, +1 pad stage on the whole latency group.
- The cb failures in the wave are flow and plan churn (src_manifest, kit_rtl, cland band, `OT_XSTN_STRETCH` on cbn_q11 b_d trees) and
  the post-CTS triage (pin-reg mean 279 to 310 against 250). cbn_q11: the b_d buffer trees over 3x direct distance are a siting row for
  QC-PLAN-R3 (not opened here).

## 4. coll_core and tt_ctlm (review, R + V of the posts)

Both are R-RTL-3 (after a memory output: at most 5 cells and 100 um before the next register). coll_core sring: 434 ps + 8 cells;
tt_ctlm calrom 591 ps + 5 cells, op ROM 520 ps + 10 cells.
- coll_core pkw4 (S-ring read register, LATCHECK delta 0): right form. Apply the same register to `pring rd_out -> hi_q / lo_q`
  (-188, 143 ends): it is the same class and pkw4 does not touch it. `g_wd -> sring wd_in` (-218, 80 ends) is the write side:
  a write-data register at the SRAM pin edge. The face codec `u_ctl rf -> epo / fault / rx` (3 ends, 960 um) needs 2 stations
  (3 hops of 320 um), +2 cycles on status bits.
- tt_ctlm: take **rae** (ROM read registers) as the base. r1be (early ROM clock) leaves the leaf ROM address setup at 57 to 108 ps on
  placement RC, which is thin for route; keep it as the 0-cycle fallback only.
- Family rule (P, generator): every SRAM / ROM / CAM port gets a register bank within 30 um of the pin, at most 2 cells between pin
  and register, on the macro's own tap. Check at compose from the bound netlist (cells between a macro pin and the first flop).

## 5. kv3_hub_Eo (V, attempt 2 geom on KV-D25d, epyc7)

381k cells in 1278.72 x 1676.16, fill 0.033, 83 % empty, 2 hard cores (kv3_astk at x 1010, y 25 and 1438). The same numbers since
kvgeom4 (pin_reg_max 489.49 -> 487.2 over 5 events): the class is structural, not a placement accident.
`placed_scan.tsv`: 86 groups over reach, 61 need a station, 1,338 bits over one cycle. Classes:
1. landing ring -> bin register, 811 to 1,485 um (`u_cland_i_seq__g_xs_N__u_xs_q_e` 128 bits x 2, kc_EN_kf, astk ep_zo): the bin sits
   with its consumer, not at the landing. Form: bin at the landing pin, stations onward.
2. boundary -> `u_seq_g_fan_2 / 3` (kq 33 bits x 2, 1,546 um; am 28 bits) and `g_xs_3.q_e -> g_fan_3.qd` 128 bits, 799 um.
3. astk hard core <-> ist / lpad / bout, 876 to 1,188 um (35 to 43 bits each; 8 of the 45 longest rows already carry a plan row, e.g. "5/340um").
4. reset: one relay leaf `u_rrl_100` feeds at least 15 bin `eq` flops 808 to 1,241 um away; `u_bin_i_host_die_rst_n` -> astk_EN 2,007 um.
5. `ft31_i` pins 487 um from their register; `ft15_i` 64 unregistered pins.

**Rows (P), KV-HUB-0005 -> KV-D23-COMPOSE (D25f or later).**
- Fold all 61 station rows of `placed_scan_rows.json` (same dir), not only the few that have a plan row; +cycles pre-approved.
- Regions: `u_seq_g_fan_2 / 3` and `u_seq_g_xs_2 / 3` as placed regions beside the face their bins land on (they are the consumers
  of classes 1 and 2); outline unchanged.
- Reset: per-region relay leaf (<= 32 loads, <= 405 um), `bank_reset_delta.py` form; the astk reset through 4 relay hops.
- ft31_i / ft15_i: pin registers at the pins (R-REACH pin rule), then stations.
- Estimate after the rows: longest leg <= 405 um by construction (61 rows cover all 1,338 over-cycle bits); margin 580 - 405 um.

**Proof status.** None: a station row needs a re-bind, which a kit fork cannot do. First proof is the D25f kit of KV-HUB-0005.

## 6. qkd_hr_ingest_eng (V, `kvd23_hr_views_1118` lib)

The 117 ps is `min / max_clock_tree_path` over every sink inside the core. The core closed its own paths on that tree, so it is not
a die number. What the die sees is on the boundary arcs: 719 input pins with hold arcs 65 to 146 ps FF (p50 117), setup -111 to +309
(p95 -57); 333 outputs at 7.0 ps clock-to-out (the view times outputs from an ideal clock: check before use).
**Rows (P), KV-HUB-0005 / DIE-CORETAP-1119:** early tap 106 / 78 ps (as posted) + core-input lockup latches (`test_core_input_lockup`
form) on the input pins: the 146 ps hold requirement then sits against T / 2. No core re-CTS. Leave the lockup off the pins whose
setup arc is over 300 ps. Proof: die STA on connected pins once the view is signed (it is not).

## 7. Sink bins (R, QC-PLAN-R3 00:04)

The 1.6 to 2.6x types (su_l1, fw_v2, stm, ctl, su_l0) are the ones that took station and pad rows after their bins were measured.
P, generator rule: at compose, every row that adds flops (station x bits, pad stages, landing rings, lockup latches) adds its count to
the bin at its site; placed dumps refresh only the native logic. Then `tap_max_sinks` 1,000 holds by construction. N46V0 already has
rebuilt bins for 20 types.

## 8. Not done / not checked

- No kit reached GRT in this session: the fleet admitted 0 GB on every host from 00:50 to 01:20. The one proof kit is queued.
- The guard fix is proven by code, log and the 8-kit census, not yet by a routed kit. Its buffer cost is unmeasured.
- The census covers 8 of the 27 kits (those with `6_final.def` under the N4x waves); st_b, sc and stm kits were not read.
- KV kits: I read no KV `pregrt_ff_hold.log` myself; FABLE-PD-KV-2300 quoted the same "not applied" line on hg k10 / k11.
- pc core power, so the IR number in section 2 is a bound from geometry.
- hc* / stm beyond hold; cbn_q11 b_d siting; LONG-LEG-CENSUS.tsv had not landed.
