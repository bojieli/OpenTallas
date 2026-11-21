# FABLE-PD-S81-2340 (2026-11-20 22:55 PST): structural review of S81 J6 (cut 11-21 13:00), run beside its binds

Reviewer: FABLE-PD-S81-2340 (Fable). Read-only. Nothing cancelled, signalled, patched or launched except one census job (section 7).
Marking: **V** = I read the file or computed the number this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Clock numbers are post-hook only (`OT_CTS_POST_TIMING`, `4_cts_post_hook.rpt`).
Scripts and raw outputs: localhost scratchpad `pd2340/` (`summ.py`, `j5scan2.sh`, `an2.py`, `grt.sh`, `ser.sh`, `deltas.py`, `an2.txt`, `summ_existing.txt`).

## 0. Headline

1. **J6 as composed does not touch the classes that fail J5 at CTS (V).** 46 J5 kits have a post-hook CTS read (40 column / leaf, 6 slice_station). Their worst setup paths are: hard core to hard core on columns, the reset register of a core-pin relay bank, `u_rrl -> cland_fstart`, `cland_origin -> reader_start / fstart`, and vp `driver_dodd_q -> vp_cf`. None is a station-to-station hop. C2d has 0 ops on col_h9_r0_p1..p6, col_h10_*, slice_station, bk_sel, gunit, and no reset-leg, START or tap row on any type.
2. **C3 is the better apply, and it is not composed.** Its three inputs (monitor-home, the 39-define reprove, the CBC300 fold) have waited 1.8 to 2.0 h for memory on epyc10 as 7 GB jobs submitted without `--priority plan`; the gates, submitted with it, were admitted (V). intel1, epyc7 and epyc9 admit 93 to 129 GB now.
3. **C1d as fallback leaves 62 types unlaunchable (V):** the monitor-pin distances equal J5 (69 monitors, 62 types over 300 um, max 2,905). EVENT-CENSUS "REGRESS 0" does not show it: MON_UM is relative to J5, and DEFINES_KIT, UNREG_READS and 321 RESET_UM rows are UNMEASURED (no kits given).
4. **Three row sets arrived after the C1d / C2d compose and are in no candidate:** leaf `relay_sites` key fix (47 types, FABLE-FIX-S81-LEAF 22:42), corrected lepe rows (S81-DIE-R5 79d3d16b4a8), and monitor-home.
5. **120 types (col_h9_r1 60, col_h9_r2 60) have no J5 kit at all (V, item list on epyc10).** They are the first J6 launches.
6. The t39 `lpad_leafdn -> crr_rxsb` 1 ns path is a D8i number. On J5 t39 a3 it is +63 at CTS (V); the J5 leaf wall is vp `dodd -> cf` (-74 to -183), fixed on main since 11-19 (CFX e828eac088) and not adopted.

## 1. Census of C1d and C2d (C3 does not exist)

Source (V): the lane's own outputs of `plan_geom_census`, `event_census`, `event_adopt_diff` on epyc10 `s81-j6/census/`, written 9 to 10 s after each compose; plan sha C1d 87b70a00 checked equal to the gate input, C2d plan unchanged since. I re-aggregated them by family and against J5 (`geom_treeB`). My independent rerun is queued (section 7).

| Check | J5 | C1d | C2d | CBC300 pass on J5 base (not in C3) |
|---|---|---|---|---|
| HOP rows over 300 / over 350 / over 405 | 9,807 / 4,703 / 752 | 9,761 / 4,640 / 718 | 7,301 / 3,563 / 718 | 2,194 / 1,046 / 464 |
| RESET_LEG rows / types | 522 / 82 | 522 / 82 | 522 / 82 | 522 / 82 |
| CORE_WIRE rows / types | 1,265 / 63 | 1,254 / 63 | 1,254 / 63 | 1,265 / 63 |
| Monitors over 300 um / types | 69 / 62 | = J5 (R) | = J5 (R) | - |

HOP rows over 300 um by family, J5 -> C1d -> C2d (rows; max um in C2d):

| Family (types) | J5 | C1d | C2d | max |
|---|---|---|---|---|
| leaf (75) | 7,825 | 7,825 | 5,403 | 471 |
| slice_station (46) | 210 | 210 | 210 | 502 |
| col_h9_r1 (60) | 180 | 180 | 180 | 400 |
| col_h9_r0_p1..p6 (60) | 780 | 780 | 780 | 594 |
| col_h10_r0_p1 / p4, r1, r2 (36) | 288 | 290 | 290 | 566 |
| kv_leaf (5) | 155 | 155 | 117 | 440 |
| c1x_C (9) | 127 | 83 | 83 | 403 |
| col_h9_r2 (60) | 60 | 60 | 60 | 390 |
| svc (9) | 40 | 40 | 40 | 495 |
| lep*_C (4) | 69 | 69 | 69 | 460 |
| serdes (11) | 12 | 12 | 12 | 457 |
| iq_C, kv512_C, c3x_C | 49 | 41 | 41 | 416 |
| lep*_LP (4) | 6 | 10 | 10 | 399 |

By kind in C2d: core-end station rows 3,833 (J5 6,293; the vp_sr real sites), ft_slot 978 (max 502), `leafdn_i` 798 (max 468), relay_depth 613 (max 594), `leafup_o` 408, `frame_int_o` 288.

Regressions against J5 (V): 3 types, 7 new rows, all new relay_depth rows whose D is too small for the cap.
- `dsdv_slice_lepe_mu_LP__t2`, `lepw_mu_LP__t2`: `u_lnl3.k_li_r` path 762 um D 1 (381), `u_lnl0.k_li_r` 671 um D 1 (335). Reset `u_land.rst_n` still 361 / 387 / 361 on three LP types. These are the old lepe rows; the corrected D4 rows (285.8 um) were posted at 21:5x, after the compose.
- `col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f` (f0_q donor): `u_r0_u_s2.lc` 1,072 um D 1 (536), `u_r0_u_t1.cci` 860 um D 1 (430), `u_r0_u_s0.lc` 1,086 um D 2 (362).
- RESET_LEG and CORE_WIRE: 0 types worse, 0 better. leaf keeps 495 reset rows on 75 types (max 1,089); t39 has 7 core reset pins 440 to 913 um from the nearest planned seat.

Missing proven fixes (V adopt_diff + ledger, R where named):
- `bksel-l4-define` MISSING (only ledger miss; waits on chain_r4c).
- vp CFX e828eac088: `ot_s81sl_vp.sv` is class BOTH (tree differs from main), and it is not a ledger row.
- leaf `relay_sites` keys: 9 of 11 J5 leaf kits print `placed 0 flops FIRM (plan keys unmatched: 25 of 25)`; all 38 column, kv_leaf and phy kits read match every key (V). So the D8E reset relays float on leaf only.
- Form S (`u_rrl -> cland_fstart`) and START pipeline rows: none in any delta.
- The adopt_diff ran against main a4fc295c2a; main has moved (TAP-GRID 02ceee2474, 054ac247c4 BAD, 47295f4adc). Kits generate on the scheduler rt (now 3dd8e5c1baa7), not on the bind pin.

MONITOR-PIN (V on J5 TSV; R that C1d / C2d equal it): over 300 um by family: leaf 29 types, slice_station 6, c1x_C 5, kv_leaf 4, col 7, svc 4, seqhost, iqf, lepw x2, iq_C, kv512_C, serdes t3. Rows exist and are proven on the J5 base (strict bind 0, LATCHECK 0, G0 0 new, precheck 0; R, S81-MONITOR-PIN-1745). Not in C1d or C2d.

## 2. Families that still fail on J6, from the newest J5 kits (post-hook, V)

| Family | J5 kits at CTS | setup ws | Worst setup class | Internal hold | In J6? |
|---|---|---|---|---|---|
| col_h9_r0_p1 / p2, col_h10_r0_p4 | 12 | -58 to -284 | `u_y_xo0_0.g_rsreg.rq -> u_y_xoN_1.o[*]` (reset register of a relay bank, 6 kits); `u_rrl_N -> cland_fstart_ft*_o` (3); core to core (3) | `u_y_rt_*.g_rsreg.rq -> o[*]` -66 to -89 | no row |
| col_h9_r0_p3 / p5 / p6 | 12 | -42 to -190 (1 at the gate) | `u_rrl -> cland_fstart` (5); core to core `u_r0.u_sN -> u_r0.u_eN.u_w` (6) | port ends | no row |
| col_h9_r0_p4, col_h10_r0_p1, r1, r2 | 12 | -25 to -109 (2 of 12 at -42 or better) | core to core `u_bsN -> u_eN.u_w` | port ends; r2 -122 | no row |
| col_h9_r1, col_h9_r2 | 0 (never launched on J5) | - | - | - | rom donors, r1_frame |
| leaf | 3 (t25 -37, t39 -74, t44 -183) | | vp `driver_dodd_q -> vp_cf` (t39, t44); `lpad_leafdn.q[594] -> crr_rxsb` (t25) | -56 to -105, vp hig station pairs across taps; in-tap skew 118 to 163, 5 to 9 over-cap warnings | vp_sr only; no CFX, no legs, no tap rows |
| kv_leaf | 1 (t5 -277) | | `vn_u_b.u_g` lane mix, logic | -359; taps 423 to 763, in-tap 208, 11 warnings | no row |
| slice_station | 6: t22 +1, t24 +160 (at abstract), t25 +69, t52 +98, t37 -244, t51 -182 | | `cland_origin/s2 -> reader_start`, `s1 -> fstart` | port ends only | no row |
| serdes | 0; DPL-0033 on 9 J5 kits, the last at about 21:20 PST (t12 a8; t1__clfe a7 at 21:05), no EXTEND / INHERIT line in their logs | | | | region removed on all 11 (C1d and C2d): this fixes it |
| lepe LP | 0 on J5 (held, no RIP1) | proof6 -154, hold +4.6, RSZ-0074 at GRT (R) | | | RIP1 in; old rows |
| bk_sel | 0 past place | | | | no row |

Reading by the classes in the brief:
- **Setup length class.** Real, but not where the brief puts it. On J5 it is column core-boundary wire and reset / start scalars; leaf `lpad_leafdn` is +63 (t39) to -37 (t25). Station hops over 300 um set no worst path on the 46 kits; slice_station carries hops to 502 um and is positive.
- **Within-tap skew.** leaf and kv_leaf only (118 to 208 ps). Columns 60 to 80, slice_station 37 to 103. No tap row can reach J6: TAP-GRID col_A r1 regressed, r2 running, t60 queued on epyc10.
- **bk_sel.** Fails on J6 unless chain_r4c folds; one type.
- **lepe.** LP gets RIP1; the -154 class of proof6 stays until P8 (proof7b, no CTS read yet).
- **serdes DPL-0033.** Closed by the row removal. First CTS read of the family is still to come.

GRT (V): slice_station t22 finished GRT with hold +19.7; `RSZ-0060` there is the per-chunk cap, caught. Leaf t25 / t44 at extra iteration 11, columns 0 to 25. No J5 GRT TT number yet.

## 3. Fold-ins before the cut

| Item | State | Verdict |
|---|---|---|
| monitor-home rows | job queued 1.9 h, epyc10, no priority | **Fold, first.** Also into a C1d-based fallback |
| 39-define reprove (svc H8) | queued 1.8 h | Needed for C2d / C3 bind at all |
| leaf relay_sites keys (47 types, 1,175 renames, 0 cycles) | posted 22:42, base C2d | **Fold.** Rerun the key fix on the J6 bind for the 11 unchecked types; kit log must print `unmatched: 0` |
| lepe rows | C2d has the old set (legs 335 to 387) | **Replace** with 79d3d16b4a8 (D4, 285.8). P8 only if proof7b reads before 08:00 |
| f0_q D | 3 rows 362 to 536 | Raise D to 3 / 2 / 3 or accept as listed |
| iq_C WCOPY | taken into C3; lane test `BUILD_FAILED` (bench file absent), `EQUIV_NOT_PROVEN` (5,126 cells, SRAM cell has no SAT model), synth stat identical (V) | **Risky.** No passing proof in the J6 tree. Take only with the main bench of 6637dd7c83 rerun in the tree, else J7 |
| bk_sel L4 | chain_r4c in bind, place about 04:00; lanes +10 to +16 | Own delta, only if placed hops and the recompiled vmux schedule read by 09:00; else J7 |
| leaf class rows | lane says J7 (dormant landing) | J7 |
| leaf reset legs | p1 at CTS pending; sibling rows provisional | J7 unless p1 reads no worse than a3 (-74 / -75) by 08:00 |
| 300 um station pass (CBC300) | fold queued 2.0 h; 8,356 rows, +2,807 stages, 530 + 272 lanes re-priced, 57,894 flops, 10 refusals | **Not J6.** No measured worst path is a station hop; it re-prices 800 lane entries with no kit proof |
| core-pin wire rows | 573 rows, no kit proof; A/B settled the tap only | J7, but column reps need them: build one private col_h10_r0_p4 proof now |
| lockup, tap grid, root entry | held by their lanes | Stay out |

**C3, not C1d.** C3 = C2d + reprove39 + monitor-home + leaf keys + corrected lepe rows + iq_C (conditional), on rt 2ddb19c08ba6 (kept in `s81-j6/rtpin`; it is gone from `rt/` on epyc10). Latest gate start that still leaves a retry: 08:00 (the C1d gate took 85 min).
Fallback should be **C1m = C1d + monitor-home**, not C1d: monitor-home is plan-only and already proven on the J5 base, and it frees the 62 held types without the svc reprove. Compose and gate it now beside C3.

## 4. Launch order, one representative per family

Launch what J6 changes; J5 kits of unchanged families keep running.
1. col_h9_r2: one rom-donor type that is not one of the two monitor types. No read exists for 60 types.
2. col_h9_r1 `cl49d7a23e` (the CORE-PIN-RELAY control type), and the r1_frame type.
3. leaf t39 (controls: J5 a3 -74 / -75, proof p1). Then t44__clf6cf8492 for `dodd -> cf`.
4. serdes t4 (DPL history; first CTS of the family).
5. slice_station t36 (monitor 2,057 -> 31), then iqf t1, seqhost t1, gunit t1 (pins moved).
6. lepe_mu_LP t2. 7. c1x_C t4, iq_C t1, kv512_C t1. 8. svc_hi rs t4, pvso_entry t2. 9. kv_leaf t5.
Read each at `OT_CTS_POST_TIMING`, with `OT_RELAY_SITES` and the worst five paths of `4_cts_post_hook.rpt`.

## 5. Ranked fix list

| # | Fix | Owner |
|---|---|---|
| 1 | Resubmit monhome, reprove39 (and any J6 compose step) with `--priority plan`, or off the epyc10 pin; compose C3 and C1m | S81-J6-ASSEMBLY |
| 2 | Fold leaf relay_sites keys and the corrected lepe rows into C3; fix the f0_q D | S81-J6-ASSEMBLY |
| 3 | Column reset and start rows from the J5 placed kits (geometry unchanged in J6): relay-bank `g_rsreg` legs on col_h9_r0_p1 / p2 and col_h10_r0_p4; form S on `u_rrl -> cland_fstart` (col_h9_r0_p1 / p3 / p5, slice_station t51); START pipeline on slice_station t18 / t37 / t45 / t51 (the `clock.landing_writer_start` form bk_sel uses). J6 if bound by 08:00, else J7 | RESET-RELAY-GEN-R3 |
| 4 | vp CFX: finish the overlay bench, elaborate with `OT_S81SL_VP_CFX`, +1 on hc_post in the compiler table; add a ledger row. J7 first item; J6 only if green by 08:00 | FABLE-FIX-S81-LEAF |
| 5 | One private column proof with the `relay_depth --pin-w` rows on col_h10_r0_p4 (worst core to core, -171 to -227) | S81-DIE-R5 |
| 6 | Give `event_census` the J5 kits (`--prev-kits`) and report MON_UM absolute, so "REGRESS 0" cannot hide a carried defect; RESET_LEG census is blind on columns (0 rows, measured -284) | PRECHECK-1119 |
| 7 | Confirm the kit-side tools at apply: one bound-type proof gen on the scheduler rt, since the bind pin and the gen rt differ | S81-J6-ASSEMBLY |

## 6. Stop list

- No apply of plain C1d while a monitor-home candidate can still gate.
- No CBC300 station pass, lockup, tap-grid, root-entry or core-pin volume rows in J6.
- No iq_C WCOPY on the strength of `byte-identical to main` alone.
- No bk_sel fold after 09:00; no lane re-pricing after the last gate starts.
- No more J6 jobs on epyc10 without plan priority.
- No "REGRESS 0" as evidence that monitors, kit defines or reset legs are clean.
- No relaunch of J5 column kits expecting a J6 gain: J6 has no row for them.
- No clock or hold verdict from `4_cts_final.rpt`.

## 7. Not checked / pending

- My own rerun (rt 2ddb19c08ba6 tools; J5, C1d, C2d; plus MONITOR-PIN precheck and the monitor table per candidate): intel2 `~/fable-pd-s81-2340/census.otrun.log`, ot-run client 225076, waiting for memory on epyc10 since 22:41. Outputs epyc10 `/srv/opentallas-scratch2/claude/fable-pd-s81-2340/summary.txt`. A waiter posts RESULT-ADD. Until then the C1d / C2d monitor equality with J5 is the lane's statement.
- No J6 kit exists; every J6 verdict here is J5 evidence plus the delta contents.
- vp_sr (79 leaf types): I found no kit proof; GRT load of the added stages is unmeasured.
- lepe proof7 / proof7b, bk_sel chain_r4c, leaf p1, TAP-GRID r2: not read (no CTS yet).
- epyc8 holds no J5 item tree; ot-jobs there had no J5 S81 kit past CTS.
- The -154 path class of lepe proof6 and the kv_leaf t5 logic path were not opened.
- Whether the 21:05 / 21:20 serdes failures were generated before rt carried 6829d05470.
