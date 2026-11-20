# FABLE-PD-S81-1100 (2026-11-20 10:55 PST): structural review of S81 plan event J5; ranked fixes for J6 (cut 11-21 14:00)

Reviewer: FABLE-PD-S81-1100 (Fable). Read-only: no job launched, cancelled or patched. This file replaces the 11-17 report of the same lane name (in git history).
Marking: **V** = I read the file or computed the number this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Plans read (V): J5 repair plan `913a7026b922` (epyc10 `kw45/s81_j5_existing_clock_r4_1120/local_fstart_inputs/plan_r4_fstart_r11_serdes_iq_native.json`, 395 types) against the live D8i plan (`kw45/src_s81_pin_3c913dbdfb23_d8i_1117_work/.../plan_h2_2249.json`). Scripts: scratchpad `an1.py`, `an2.py`, `an3.py` (plan JSON only; hops are Manhattan from -> regs -> to; no placed DB, no STA).
J5 state at 10:44 (V): repaired strict bind running, 0 EMIT, 0 ERROR in `gate_r5_repair/bind.log`; LATCHECK / G0 / PRE not started.

## 0. Verdict

1. I found no functional error in J5. Nothing here is a reason to stop the apply.
2. J5 is a 300 um event for reset only. Data stations are still drawn at 405 um, and on the leaf J5 makes both the hop count and the congestion bands worse.
3. The leaf form-C bank rows in J5 put the station flops on the GRT hot tiles. J5 leaf kits of the changed types should run as one representative per band first, not as a wave.
4. The col hold class (CTS FF hold -45 to -100 ps) is measured on col_h9_r0 and col_h10 too. J6 gives the lockup only to the two r1 / r2 masters; 96 col types get nothing.

## 1. What the data says

### 1.1 Hops over 300 um
| Item | D8i | J5 | Note |
|---|---|---|---|
| `die.reach_um`, `budgets.ft_station_max_um`, `core_internal_reach_um` | 405 | 405 | no `cbc` key in the plan (V) |
| Reset collector trees: `reach_um` / worst hop | 405 / 380-388 | 300 / 275 (seqhost 296, serdes 287; leaf 180 / 155) | 0 trees over 300 (V) |
| `internal_stations` rows with a leg over 300 | 5,408 of 24,788 | 8,064 of 24,814 | 327 of 395 types; max 404.9 (V) |
| ... of which leaf | 4,335 | 7,125 | register-to-register legs over 300: 1,991 -> 3,190 of 31,832 (V) |
| `ft_slots` station-to-station legs over 300 | 3,279 of 5,140 | 3,279 of 5,140 | leaf 1,830, slice_station 847, svc 161; unchanged (V) |
| Legs over the 405 check | 1 | 1 | `dsdv_slice_iq_C__t1` `bus:leafdn_o0` legs 296 / 416 (V) |
| `relay_polylines` over 300 | 1,020 | 1,020 | col_h9_r1 only, max 405 (V) |

Rows by family in J5 with a leg over 300 (V): col_h9_r1 180 / 480, col_h9_r0 276 / 450 (D8i 426), kv_leaf 108 / 204, c1x_C 88 / 117, col_h9_r2 60 / 120, col_h10 132 / 204, serdes 11 / 22, iq_C 10 / 11, kv512_C 11 / 12.
Limit of this count: it is plan geometry. The reach estimator does not count core-spanning legs and counts channel legs only over 550 um (`cbc_rules.reach_leg`); I did not classify the legs.

### 1.2 Reset / clock taps / hold at 833 ps
- Reset trees are re-solved at 300 on every type with a tree (V). Depth rises (col 6-8 -> 8-10, bk_sel 8 -> 14, leaf up to 19, svc 16); all far under the 64-cycle boot hold.
- `reset.relay_lockup` (negedge relay types) is the same 184-type list in D8i and J5 (V). It was derived from the plain-relay hop hold estimate at the 380 um hop. The hop is now 275 um, about 68 ps less wire at 0.65 ps/um (I). The list was not re-derived.
- 38 col trees changed form (V): D8i trees read `relay_lockup: negedge` on col_h9_r1 (9), col_h9_r2 (16), col_h9_r0_p2 (12), col_h10_r0_p1 (6), col_h10_r2 (4), none of them in the die list; the J5 trees of those families read `null` (6, 11, 12, 6, 3). Either the D8i trees were stale or J5 turns negedge reset relays into plain ones on shorter hops. The two J6 masters are in this set.
- The plan has no data lockup anywhere: no `lockup` / `latch` key outside the reset tree, no `ZL` define (V). The `bin -> lpad` latch exists only in the two private J6 masters (R, S81-DIE-R4).
- Clock taps: J5 adds 617 taps on five slice C types (c1x 464 -> 963 over 9 types, iq 59 -> 177) and 90 on col_h9_r0 / h10_r0_p1; leaf stays at 5,294 (V). Slice C keeps `tap_max_sinks` 1500; the row file reports max load 1,289 on c1x_C__t1 against the 1,000 cap, 993-998 on the other four (R, OPUS-FIX-S81-SLICEC rows). c1x t3 / t4 / t5 / t7 / t10 got depth rows but no tap rows.
- Measured hold on D8i col kits (R, S81-GEOM-OPUS 10:05; V on `~/s81-geom-opus-d8i-watch/cur.sorted`): col_h9_r0 26 kits with a CTS FF hold value, -47.3 to -88.4 ps, 0 signed; col_h10_r0_p1 -52.3; col_h10_r1 -46.8 median; col_h10_r2 -94.7 median, routed FF -118.4; col_h9_r1 -76.8 median, routed FF -164.1.

### 1.3 Leaf congestion bands: J5 does not address them, it loads them
J5 changes `internal_stations` on 62 of 75 leaf types (form-C bank sites, S81-LEAF-HI-ROWS-J5). Station bits per type are unchanged; the number of distinct station sites in the family drops from 13,878 to 7,339 (V). Station bits per 100 um tile on the 20 GRT-TRIAGE kits (V):

| Type | GRT top zone (overflow) | Peak tile D8i | Peak tile J5 | Band bits D8i -> J5 |
|---|---|---|---|---|
| t7 | 300,700 (32,087) | 400,700: 4,190 | 300,700: 21,442 | W 3,961 -> 1,572 |
| t34 | 1000,300 (16,094) | 900,400: 6,240 | 1000,300: 17,260 | E 24,745 -> 38,316 |
| t39 | 1000,400 (29,297) | 1000,500: 7,570 | 1000,400: 13,076 | E 27,359 -> 33,865 |
| t43 | 900,300 (11,694) | 1100,300: 5,186 | 1100,300: 13,332 | E 15,723 -> 19,378 |
| t65 | 1100,700 (19,048) | 1000,600: 5,232 | 1000,700: 12,814 | E 16,986 -> 31,646 |
| t35 | 200,500 (4,581) | 100,600: 4,447 | 300,400: 10,456 | W 11,716 -> 22,193 |
| t33 | 1200,700 (5,036) | 1100,400: 3,926 | 1100,400: 9,681 | E 14,721 -> 26,748 |
| t46 | 1200,700 (6,534) | 1200,1000: 4,424 | 1100,700: 8,630 | E 11,790 -> 23,024 |
| t66 | 1100,700 (14,320) | 1100,1000: 3,941 | 1100,700: 8,630 | E 14,745 -> 18,391 |
| t9 | 1100,400 (19,707) | 1100,400: 6,242 | 1100,400: 9,148 | E 22,185 -> 24,460 |
| t22 | 1100,700 (28,043) | 1100,700: 7,186 | 1100,700: 9,282 | E 23,412 -> 27,596 |
| t61 | 1100,900 (17,496) | 1100,900: 8,506 | 1100,900: 9,548 | E 9,956 -> 12,044 |
| t41 | 200,600 (15,903) | 300,800: 6,662 | 300,600: 8,892 | W 15,696 -> 15,696 |
| t4, t5 | 400,500 / 300,300 | 2,328 / 3,923 | 2,856 / 4,446 | W +1,559 / +1,308 |
| t44 x2, t53, t54 x2 | 300-400,400 / 200,400 | unchanged | unchanged | no J5 row |

On 7 types the J5 peak tile is the GRT top tile, on the rest it is within one or two tiles. East band bits rise on 9 of 9 east types. This is the plan-side measurement of the 2-4x that S81-DIE-R4 modelled. 26 `plus_one_stage` types take +1 cycle and still carry hops to 398 um (V, row file). No GRT of form C has finished (R).

### 1.4 Slice C, serdes TX, SRAMREG
- Slice C: J5 = relay depth 6 -> 8 (iq 10), the taps above, `relay_mid_half_types`. Station geometry is untouched: c1x 191 of 230 register-to-register legs over 300, iq 24 of 27, kv512_C 24 of 26 (V). kv512_C has no J5 row; its price is +5 / +3 stages, 8,840 flops, 56 taps against 40 (R, OPUS-FIX-S81-SLICEC 08:41). c1x t9 / t10 and iq t1 stay do-not-count.
- Serdes TX: the `coll_i0` stations are in on all 11 types, 512 b, hops 177-290 um (V), and the four defines (TXL4, AMOK_PIPE, RM_WPL8, RM_LOCAL_EMPTY8). Not proven on a kit (R). The `coll_o0` rows on the same 11 types are drawn at 334-401 um (t12 4 x 398, t15 3 x 397, t3 3 x 372, t4 6 x 338) (V). RX legs of 544-1,163 um have no row (R).
- SRAMREG: 0 of 75 leaf types carry `OT_S81SL_VP_SRAMREG` in 913a7026 (V). The 75 rows exist (`s81_r5_rows_j5.json`, basis plan_j4f) and run as the vp_sr donor tree. The 16 svc types are not covered (mem_ar SYNC 0; RDPIPE bench pending, R). So J5 as bound does not register the leaf-store reads.

### 1.5 col_h9_r0 (60 types, not in J6)
J5 re-stages the face buses (V): `frame_int_o0` 5 x 377 -> 5 x 335 + 208, `frame_int_i0` 3 x 384 -> 267 + 3 x 295, p6 `xo_i0` 388 / 384 -> 177 / 297 / 297, p6 `frame_int_i0` 403 / 406 / 402 -> 282 + 3 x 310. Still over 300: `frame_int_o0` 335 (328 on p6), the core leg `u_r0.u_s0.st -> u_r0.u_t0` 348 / 389 / 331 (2 rows per type, unchanged), p6 `ret_o0` 310. p6 has no landing contract and no reset tree in the plan, yet all 12 p6 types are in the negedge relay list (V). Hold: section 1.2. Sweep rows p1 / p3 / p6: flow and infra classes (R, S81-DIE-R4 09:52); no plan cause found here.

## 2. Fixes for J6, ranked (integration owner S81-DIE-R4 for all)

| # | Fix | Evidence | Row owner | First check |
|---|---|---|---|---|
| 1 | Leaf: replace the J5 form-C bank rows with the per-lane spread rows (`S81-LEAF-SPREAD-J6.json`, GS 0, hops <= 295) on the band types, and add rows for t44 x2 / t53 / t54 x2 | 1.3 | S81-DIE-R4 | t39 `tree_SP` against `tree_Cc` on epyc9: overflow at GRT iteration 10 |
| 2 | Col hold: the `bin -> lpad` lockup in the two masters (already planned), and the same form for col_h9_r0 (60) and col_h10 (36) | 1.2: every measured r0 / h10 kit at -47 to -100 ps, 0 signed | S81-DIE-R4, FABLE-FIX-S81-COL | read the hold ends of one r0 kit in route (`col_h9_r0_p2__t1__cl0045af7b__pv6882e5ea`, epyc7): same cross-tap pair or not |
| 3 | Reset relay form at the 275 um hop: re-derive the negedge list; settle negedge or plain on the 38 col trees before the masters route | 1.2 | S81-DIE-R4 | relay cell (`ot_dp_rrelay_nl` or plain) in the J5 bound RTL of one col_h9_r2 and one col_h9_r0_p2 type; `nl_est` at 275 |
| 4 | Data hops to 300 where it costs a station, in this order: serdes `coll_o0` (11 types, +1 to +2 stations), col_h9_r0 `frame_int_o0` 335 -> 6 legs and the `st -> t0` core leg (+1), c1x_C / iq_C stations (incl. the 416 leg), kv512_C +5 / +3 | 1.1, 1.4, 1.5 | FABLE-FIX-S81-SERDES-0600, S81-DIE-R4, OPUS-FIX-S81-SLICEC | pin3 placed scan on one kit per family: seat the first rank, then stage only what is still over |
| 5 | Slice C taps: tap rows for c1x t3 / t4 / t5 / t7 / t10; split the 1,289-sink tap on c1x t1 | 1.2 | OPUS-FIX-S81-SLICEC | register dumps for t3 / t5 (no placed DB yet) |
| 6 | Registered reads: leaf SRAMREG (75 rows) if the vp_sr donor is not green for J5; svc RDPIPE define in manifest + 16 rows before the svc strict bind | 1.4 | CBC-ALL-0200 rows -> S81-DIE-R4; FABLE-FIX-S81-SVC-R2 | SRAMREG adds one per-lane output station: prove it on the same kit as fix 1 |
| 7 | bk_sel__t2 A3P rows (`rows_bk_a3p.json` 53956fe8b195) once the u_c A3P view is signed; face-bus stations after the private placed form | bench PASS 10:37, hops <= 283 (R) | FABLE-FIX-S81-BKSEL-R2 | u_c A3P sign-off (epyc7), private GEN on intel1 |
| 8 | svc H8 package: t7 R9 die hop 378 -> 300, 43 landing bands at 301-403 (plan shows pin-to-band hops to 402.8 on svc_hi rs t1, V) | R, FABLE-FIX-S81-SVC-R2 | FABLE-FIX-S81-SVC-R2 | R6 strict chain, then one hi rs t4 kit to sign-off |

Not for J6 (P): the ft_slot station pitch (3,279 legs at 301-405). It changes lane latency on every type; it needs its own event. slice_station__t41 needs no row: J5 carries its START stages (R, BKSEL-R2); it needs a private place + GRT on the J5 bound out.

## 3. Stop list

- No leaf wave on J5 for the 62 changed leaf types before one form-C GRT is read at iteration 10. One representative per band first (t39 east, t7 west).
- No cancel of the D8i leaf kits marked KEEP (t22, t33, t46, t7) for J5; they can still sign on the old plan.
- No leaf GRT relaunch on more iterations alone.
- No reading of J5 as the 300 um event for data. Reset trees are at 300; stations are at 405.
- No route of a J6 col master before its reset relay form is confirmed in bound RTL and the `bin -> lpad` latch is in.
- No 120-kit col wave before both masters route.
- No hold-buffer ECO rounds on col_h9_r0 / col_h10 before the hold ends of one kit are read.
- No count of c1x t9 / t10, iq t1 or the svc types on D8i or J5.
- No SRAMREG and form-C bank rows together on a leaf without a kit that carries both.
- No ft_slot station re-pitch inside J6.
- No J3 apply, no cw9a / cw9b forms (unchanged).

## 4. Not checked

- No placed DB, GRT report or STA was opened for J5; no J5 kit exists yet. Section 1.3 is station flop density from the plan, a demand proxy.
- Leg class (core / channel / logic) of the legs over 300; the count that the reach estimator would report is lower than 8,064.
- Whether the 38 col trees lose the negedge relay in bound RTL, and whether a 275 um plain relay hop has negative hold: inferred from the plan fields only.
- Whether the col_h9_r0 hold ends are the `bin -> lpad` pair.
- START broadcast hops (taken from BKSEL-R2 for t41 only); tap sink counts (the plan does not hold them); the J5 bound out (bind not finished).
- The S81-LEAF-SPREAD-J6 rows themselves; the 11 EMIT repairs; LATCHECK cycle deltas of J5.
