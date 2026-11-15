# FABLE-PD-QC-0700: S4r2 PARAM_REGEN root cause, S4x / S4z structural review, levers

2026-11-15 07:00 PST, FABLE-PD-QC. Technical PD and plan only. Read: FABLE-PD-QC-0650, FABLE-TRIAGE-QC, handoff DIE-QC-103, queue to 06:36.

MEASURED = read by me from a bind report, `bus_groups.json`, derived R8 table, plan, placed dump or placed timing report.
REPLAY = `qc_fabric_transport.derive` (the bind's own code, imported unchanged) run on the bind's own `bus_groups.json` or derived table. Control: the replay of S4p and S4q2 passes and S4q2's real rebind passed (0 errors); the replay of S4r2 predicted 48 stale members = 24,672 bits and the real rebind `S4R2Q` reports exactly 24,672.
Work dir (read-only on lane data): epyc9 `/srv/opentallas-scratch2/claude/fable-pd-qc-0700/` (`qft.py`, `qft2.py`, `qft3.py`, `qft4.py`, `s4x.py`, `face.py`, `census2.py`, `*.out`).

Not available: S4r4 / S4r5 binds were still running at 06:52 (no report). No probe is at CTS: sle_fw_v2 and sle_st_b_v2 are placed on S4k (dump + placed timing, ideal clock), cbn_q11 and slw_fw_v3 are at gen. S4x / S4v / S4v2 rebinds and all G0 runs of S4v..S4y were still running.

## 0. Decisions

1. **S4r2 is balanced as planned. The +3 on na_i00 is the right leg and the right sign.** The failure is a frozen pad table, not the plan.
2. **Cause:** `cb16_pads_hbm_codex.json` (the cb16 tree-align table, `land_r8_extra`, authoritative) holds the level-4 pad on `u_t_0_0.n_a` keyed to the old lane depth (bound 18-20). S4r / S4r2 change that depth by +3, so all 48 members go stale and the pad of 9-12 cycles is not applied. The n_a leg then lands 10 (near) or 11 (far) cycles early.
3. **Fix:** regenerate or re-key that table for the 48 `u_t_0_0.n_a` members (bound +3, pad unchanged). No plan change. REPLAY with the pad restored: S4r2, S4v, S4v2 all derive clean, SKEW_S 13..14, SKEW_N 12..12.
4. **S4r4 and S4r5 will both fail and do not decide the sign** (section 1.4). Do not wait for them.
5. **S4x does not bind either** (not yet posted by the lane): `W5: r_d of region 0 is not the latest`, then `nb_od of region 0`. The +2 on st_b moves regions 4-7 past region 0. Fix: +2 on the two st_a return lanes.
6. **S4x has a geometry error on all 6 slw_fw types:** 117 of the new station rows are x-mirrored onto the wrong face. slw_fw has the same faces as sle_fw. The last hop to the real pin is 517-835 um.
7. **S4x misses the worst measured path of sle_fw_v2:** `u_bin_x_fe_p1_i` -> 1 gate -> `u_core.ch_dn_o`, 818 pairs over 405 um, -467.6 ps placed. x_fe_p1_i has no station on sle_fw_v1 / v2.
8. **S4z: hold.** 4 measured reset hops in total, and the sle_fw_v2 reset recovery path has +560 ps. Build it only after the cbn_q11 probe names the -861 endpoint, and on the merged plan.

## 1. S4r2 PARAM_REGEN "W5 S"

### 1.1 What the check computes (`qc_fabric_transport.py`, `_cluster`)

Start shift T(c, r) = column entry delta at row 0, plus the row-2 delta for rows 2-3. Level 4 joins rows 0-1 (n_a of `u_t_0_0`, bus na_i00, from `u_t_2_2`) with rows 2-3 (n_b, bus nb_i00, from `u_t_1_2`). Column pads cannot fix a row imbalance, so the message is always "no column pad up to 9".

### 1.2 Measured, W5 S (delta = landed - as-built)

| bind | cluster | T rows 0-1 | T rows 2-3 | n_a: bound + pad = landed (delta) | n_b delta | level-4 a / b |
|---|---|---|---|---|---|---|
| S4PQ (record) | near c16_W5_1 | 19, 22, 24, 21 | 18, 21, 23, 20 | 20 + 10 = 30 (-1) | -5 | equal, root 16 |
| S4PQ | far c16_W5_0 | 19, 22, 24, 21 | 19, 22, 23, 20 | 19 + 11 = 30 (-1) | -6 | equal, root 16 |
| S4Q2R | near / far | +1 / +2 on all rows | same | unchanged, pad kept | same | equal, root 17 / 18 |
| S4R2R | near | 20, 23, 25, 22 | 22, 25, 27, 24 (+3) | 23 + **0** = 23 (-8) | -5 | **10 / 20** |
| S4R2R | far | 24, 27, 29, 26 | 27, 30, 31, 28 (+3) | 22 + **0** = 22 (-9) | -6 | **13 / 24** |

- The B/D stations move rows 2-3 by +3 against rows 0-1. The plan answers with +3 on na_i00 (bound 20 -> 23). That is correct: with the pad kept, n_a delta is +2 and a = b.
- The shortfall is 10 on near and 11 on far, exactly the pad that is no longer applied.
- All 24 slice-sides fail in S4R2R, not only W5 S. `_column_pads` raises on the first.
- Levels 1-3 are unchanged and balanced in every bind (L1 +3 INNER pads, L3 -5 / -7 and 0 / -2).

### 1.3 Why the pad is dropped

- Bind order (`bind.py` 2168-2180): the `land_r8_extra` member replaces the derived R8 member of the same id. The id carries the as-built depth (`@31`) but not the bound depth; the member body does (`bound: 20`).
- `cb16_pads_hbm_codex.json` (11-14 00:37, sha 60098047954a26b9, 126 crossing + 280 INNER members) was generated from an older bind. Its 48 `u_t_0_0.n_a` members have bound 18-20 and pad 9-12.
- In S4r2 the bind has bound 21-23 for these, so each bit is `R8_STALE` and gets no pad. `S4R2Q` first error line: `R8_STALE c16_E0_0.u_t_0_0.n_a[0:513]<-c16_E0_0.u_t_2_2.n_y@31 bit 0: bind has ... bound 23, table ... bound 20`.
- The derive step (`bind_derive.sh`) cannot repair it: the derived table has the right bound (23) and pad 0, and the extra table overrides it.
- This is why three rounds gave the same result. S4r (47 members, 24,158 bits stale: all types but `cbf_q00_s2`), S4r2 (48, 24,672), S4v, S4v2 (48 each).
- The "30 R8_STALE" printed are the first 30 bits of one member; the report field `landing_alignment.stale` has the real count.

### 1.4 S4r4 / S4r5 (not landed), predicted from the same replay

| variant | na_i00 | nb_i00 | pad on n_a | level-4 result |
|---|---|---|---|---|
| S4r4 | unchanged (bound 20 / 19) | unchanged | kept, 10 / 11 | b later by 3: FAIL, same message |
| S4r5 | +3 | +3 | dropped | a earlier by 13 / 14: FAIL, same message |

Both fail, so they cannot show the sign. The sign is already fixed by 1.2: rows 2-3 are the n_b child, so the leg to raise is n_a = na_i00.

### 1.5 What each leg needs so that S4r / S4v bind

| leg | plan (S4r2 / S4v / S4v2) | table |
|---|---|---|
| na_i00 (`u_t_2_2.n_y` -> `u_t_0_0.n_a`), 48 members | keep 4 -> 7 stations (+3) | bound +3 (21-23), pad unchanged (9-12), landed = bound + pad |
| nb_i00 (`u_t_1_2.n_y` -> `u_t_0_0.n_b`) | no change (7) | no member, no pad |
| `u_t_1_2.n_b`, `u_t_2_2.n_a`, `u_t_2_2.n_b` (78 members) and 280 INNER | no change | no change, still match |

Two ways, same result:
- (a) Re-key: copy the table, add 3 to `bound` and `landed` of the 48 `u_t_0_0.n_a` members, point `R8_EXTRA_SPEC` of these variants at the copy. One rebind.
- (b) Regenerate: `cb16_pads.py BIND_DIR R8_TABLE OUT.json` on the Q bind of the variant with its derived table, then a third bind. Do this in `bind_chain.sh` for every later variant that touches a cb tree lane.

REPLAY with the pad restored (`qft2.py whatif`, `qft3.py`): S4r2, S4v, S4v2: 0 of 24 slice-sides fail, derive OK, SKEW_S 13..14, SKEW_N 12..12 (inside 3..27), RD_PAD / NB_IN_PAD / HI_PAD sets equal to S4p, added flops 229,040 as S4p. S4r (first form) still fails W5 S after the restore (the _s2 type without stations), which S4r2 already fixed.

## 2. S4x (fw / st_b stations) and S4z

### 2.1 S4x bind: fails in the station regions

`S4XR`, `S4WR`, `S4YR` reports: 30 R8_STALE + `PARAM_REGEN W5: r_d of region 0 is not the latest; its r_v would need a pad`. REPLAY on the derived table (the rebind view) gives the same, so the rebind will not clear it. The cb16 pads are not involved here (0 stale).

Measured, W5 (same on all 12 slices):

| item | S4p | S4x |
|---|---|---|
| `x_st_a_st_b` lane into regions 4-7 (rs_s, bt_q) | +11 | +13 |
| E(0..3) / E(4..7) | 27 / 38 | 27 / 40 |
| r_d lane, regions 0-3 (`st_a__x_st_a_ctl`, bound 7 + pad 13) | 20 | 20 |
| r_d lane, regions 4-7 (`st_b__x_st_b_ctl`) | 8 | 8 |
| r_d arrival, region 0 / region 4 | 47 / 46 | 47 / **48** |
| nb_od lane, regions 0-3 (`st_a__x_st_a_fe`) / 4-7 (`st_b__x_st_b_fe`) | 18 / 5 | 18 / 7 |
| nb_od arrival, region 0 / region 4 | 45 / 43 | 45 / **47** |

The valid of both joins comes from region 0, so region 0 must be the latest. S4p had 1 cycle of margin on r_d and 2 on nb_od; S4x uses +2 and +4.

REPLAY of the fixes (`qft4.py`):

| change (landed) | result |
|---|---|
| r_d(0-3) +1, nb_od(0-3) +1 | FAIL nb_od |
| r_d(0-3) +1, nb_od(0-3) +2 | OK, RD_PAD {0, 12} |
| **r_d(0-3) +2, nb_od(0-3) +2** | **OK, RD_PAD {0, 1, 13} as S4p, SKEW_S 9..10, SKEW_N 8, flops 218,768** |

Recommended: +2 on both st_a return lanes (`sl_*_st_a__x_st_a_ctl`, `sl_*_st_a__x_st_a_fe`, 12 slices each), which keeps the S4p shape. The requirement is on landed depth (21+ and 20+); `x_st_a_ctl` carries an R8 pad of 13, so check landed after the derive, not only fixed_cycles.

### 2.2 S4x station geometry (plan `zz_s29_qc103_s4x.json`, 295 rows on 27 types)

| group | rows | plan hops, um | finding |
|---|---|---|---|
| st_b, 11 types | 3 each | 139-311 | Right. Row ends are on the pin windows. |
| sle_fw_v1 / v2 / v3, 5 types | 23 each | 146-368 on outputs | Right on outputs. Row end to real pin: up to 396 um (st_eo on v1), 298 (x_ctl_p2_o). |
| same, inputs cmd_ei, dr_ei, x_ctl_i | 3 each | first hop 456, 489, 473; rest 228-245 | First hop is 2x the others and holds `u_bin`. Under 405 only if `u_bin` is sited at its middle. The sidecar has the 18 cb types only. |
| **slw_fw, 6 types** | 20 new each (17 on v3) | 146-368 as written | **Wrong face on 117 rows.** |
| slw_fw old rows (S4k, skipped by the copy) | 5 each | ard_wo 397 / 702-735, x_ctl_i 468 / 467, x_stm_p1_i 588-626 / 276 | ard_wo keeps 1 station where sle ard_eo gets 3. |

slw_fw detail (`face.py`): the rows were mirrored x -> 622.08 - x. The slw_fw types are not mirrored types: in the plan and in the placed dump of slw_fw_v3 (S4C a8) the ring buses are on W (dd_wo at x 22, dr_wi ring at x 21), the x_ buses on E (x_stm_o at x 605) and x_ctl_o on N, as on sle_fw. Examples on slw_fw_v3, hops to the real pin:

| bus | pin face | row end to pin | hops with the real pin |
|---|---|---|---|
| x_stm_o (549 b) | E | 711 | 181, 181, 530 |
| x_ctl_p2_o (536 b) | E | 1,005 | 170, 170, 835 |
| x_fe_o (539 b) | E | 878 | 253, 253, 625 |
| dd_wo (548 b) | W | 688 | 341, 341, 676 |
| dr_wi (520 b) | W | 769 | 829, 245 |
| cmd_wi (116 b) | W | 839 | 544, 228, 228 |

As written these rows pull each chain to the far side and make slw_fw worse than S4p. Fix: no mirror; take the sle_fw_v3 coordinates as they are, with each row end on the type's own pin window.

### 2.3 What the placed S4k probes show against S4x

sle_fw_v2 cl69f5e854 (placed 14:16 UTC, ideal clock): WNS -467.6 ps, TNS -101,783, 8,112 setup endpoints. 7,097 of 30,144 zero-logic hops over 405 um (max 1,401), same families as the S4C dump.

| family (S4k dump) | hops over 405 | max um | S4x |
|---|---|---|---|
| `u_core.*` -> `u_bout_*` (x_stm*, x_ctl*, x_fe*, dd, ard, art, sc, ag) | 4,763 | 1,351 | stationed, 146-368 |
| `u_bin_x_stm_i` / `x_stm_p1_i` -> `u_bout_st_eo` | 1,087 | 1,151 | st_eo x3; from the E pin 184-387, then 275 |
| ring -> `u_bin` x_ctl_i, dr_ei, cmd_ei | 1,117 | 1,224 | stationed; needs `u_bin` sited (2.2) |
| ring -> `u_bin_hr_ei` | 47 | 484 | not stationed; sidecar siting is enough |
| **`u_bin_x_fe_p1_i` -> 1 gate -> `u_core.ch_dn_o`** (`census2.py`) | **818 pairs** | 787 | **not stationed on sle_fw_v1 / v2. This is the WNS path (-467.6).** |
| `u_rrl` -> `u_bin_hr_ei` / `re_ei` eq | 2 | 671 | reset, recovery slack +560.7 |

sle_fw_v3 has no x_fe_p1_i bus, so the copied set cannot hold it. The slw types have an old 1-station row for it (400 / 86). Needed: x_fe_p1_i +2 on the 4 sle_fw_v1 / v2 types (route about 790 um, hops about 263).

sle_st_b_v2 clfde1249e (placed 14:37 UTC): WNS -42.2 ps, TNS -59,965, 9,626 setup endpoints, GRT 0 overflow. 854 of 38,486 hops over 405.

| family | hops | max um | S4x |
|---|---|---|---|
| ring -> `u_bin_x_hc*_i` | 391 | 1,220 | +2, 305-311 |
| ring -> `u_bin_x_st_a_i` | 284 | 866 | +2, 139-147 |
| `u_nbo_pad` -> `u_bout_x_fe_o` | 128 | 834 | +2, 246-259 |
| in-core reset branch -> leaf, cfg_mid -> cfg_final, g_pin | 50 | 587 | not covered (core internal) |

The st_b WNS path is logic, not a hop: `u_r5.g_sc[0].u_mul` exact multiplier, 868 ps of gates, at the -42 ps gate before CTS and route. 9,626 endpoints at about -6 ps average. INFERENCE: the stations remove the 803 long hops but st_b will sit at the setup gate after route; this needs the CTS probe on S4x to confirm.

Lane latency: LATCHECK is PASS 1,921 / 1,921 on S4x, S4w, S4v, S4v2, S4r2 as bound, so the +1..3 on the 268 lanes is delivered as planned. The counts are right; the errors above are balance (2.1), face (2.2) and one missing bus (2.3).

### 2.4 S4z (consumer_localization of `u_bin` resets)

- Evidence for the class: 2 hops in cbn_q11 (S3R dump, 1,411-1,466 um) and 2 in sle_fw_v2 (S4k, 477-671 um). The measured recovery slack on the sle_fw_v2 form is +560.7 ps (`u_rrl_8` -> `u_bin_cmd_ei/eq`). Nothing yet ties the -861 ps of cbn_q11 to it; the cbn_q11 probe is at gen.
- If built: generate the rows on the merged plan. The `u_bin` sites change with the bc_i stations (S4v2 sidecar, first hop 317.6 um) against S4x (680.7 um on cbf_q00_s2), so the nearest tap is not the same on both.
- Depth: all taps are depth 7 by the lane's read; `localize` fails closed on unequal depth, which is the right gate.
- S4y inherits the S4x r_d failure; it shows the schema path only after 2.1 is fixed.

## 3. Levers, ranked

| # | lever | owner | evidence | effect |
|---|---|---|---|---|
| 1 | Re-key (or regenerate with `cb16_pads.py`) the 48 `u_t_0_0.n_a` members of the cb16 pad table for S4r2 / S4v / S4v2: bound +3, pad unchanged; rebind | DIE-QC-103 | 1.2, 1.3; `S4R2Q` stale 24,672 = 48 x 514; replay clean | S4r2 / S4v2 bind; cb crossing class closed on 18 types |
| 2 | Add the cb16 regenerate step to `bind_chain.sh` after the derive | DIE-QC-103 | three rounds lost on a frozen table | no repeat on the next cb tree change |
| 3 | S4x: +2 landed on `st_a__x_st_a_ctl` and `st_a__x_st_a_fe` (24 lanes) | DIE-QC-103 | 2.1; replay OK, shape as S4p | S4x / S4y bind |
| 4 | S4x: slw_fw rows without the mirror, row ends on own pin windows (117 rows, 6 types) | DIE-QC-103 | 2.2; last hop 517-835 um | 6 slw_fw types usable |
| 5 | S4x: x_fe_p1_i +2 on sle_fw_v1 / v2 (4 types) | DIE-QC-103 | 2.3; 818 pairs, -467.6 ps | removes the WNS path of sle_fw_v2 |
| 6 | S4x: slw_fw ard_wo 1 -> 3 stations, x_ctl_i 1 -> 2 (6 types) | DIE-QC-103 | 2.2; 702-735 and 467 um | old rows brought to the sle form |
| 7 | Sidecar for fw and st_b input buses: `u_bin` at the middle of the first hop (cmd, dr, x_ctl, hr, x_hc*, x_st_a, x_stm*) | CLAND-BIN (reader), DIE-QC-103 (sites) | 2.2; first hops 456-489, hr_ei 484 | all input hops 228-245, no latency |
| 8 | Adopt S4q2 now (rebind 0 errors, 0 stale); then S4v2 after lever 1; then S4x after 3-6 | DIE-QC-103 | `S4Q2Q` report | cb types regenerate once per adoption |
| 9 | Keep the 4 probes to CTS; rerun sle_fw_v2 and sle_st_b_v2 on the fixed S4x | DIE-QC-103, KIT-OPS-5 (all gen hosts) | no CTS data yet; st_b at -42.2 placed | endpoint names for st_b logic and cbn_q11 -861 |
| 10 | cbn_q11 nb_i pad chain and d-chain spread | TYPE-QCCB-GEN | 0650 section 2, 1,349 hops | unchanged from 0650 |

## 4. Stop list

1. No further sign tests on na_i00 / nb_i00 (S4r4, S4r5 or new ones): the plan is balanced, the table is stale.
2. No reading of "30 R8_STALE" as the stale count; read `landing_alignment.stale`.
3. No adoption of S4x, S4w or S4y as built: they do not bind, and the slw_fw rows point at the wrong face.
4. No release of slw_fw types on the mirrored rows.
5. No extra stations on st_b x_st_a_i or x_fe_o to "fix" r_d: the fix is on the st_a return lanes.
6. No S4z bind chain before the cbn_q11 probe names its endpoint, and none on a plan other than the merged one.
7. S4w (on S4k) can be dropped: S4x is the same set on the plan of record.
8. Still in force: 0650 stop list 3 (no stations on cbf_q00_s2 alone) and 6.

## 5. coll_s (COORD addition): structural hold -268.69 ps, held ER4-HOLD-1113

Evidence state: the two failing kits are gone (hcut1111 attempt_2 was on epyc4, terminated; efdb36e864 attempt_19 on epyc2 is deleted). Read instead: PHYS-QC's 11-13 17:56 read of the attempt_2 report (queue line 8881), the surviving kit of the same pre-merge form (epyc2 `kw26-wave-1106/.../efdb36e864/items/coll_s/attempt_16`: RTL, `constraint.sdc`, placed dump), the S4p plan and the S4p bound RTL. So the -268.69 path list is second-hand; the mechanism below is MEASURED on attempt_16 and S4p.

### 5.1 Root cause

- The pre-merge kit has three clock roots that the SDC treats as one synchronous clock: `create_clock` on `clk` (+ `clk_t1..t5`), on `clk_coll` and on `clk_serdes`, all 833 ps, same source latency (-30 / 0), no clock group and no common insertion target (`constraint.sdc` lines 4-9, 23-28; RTL lines 29-30, 113-114).
- CTS builds each root on its own. PHYS-QC's read: `clk` sinks at 200 ps, `clk_serdes` at 560 ps (edge chain + 20 delay buffers). Every clk -> clk_serdes / clk_coll path then carries 360 ps of skew: -257 to -365 ps on 4,138 endpoints, FF. That is a clock-structure error, not a data path, so no hold buffer pass or ECO closes it (stop was -245).
- The die does not have this skew: in the die these domains ride the core clock.

### 5.2 State on the plan of record

- S4p (and every s29 plan) carries `clock_merge` coll_s {coll: core, serdes: core}. The S4p bound `qfd_qc_coll_s_part.sv` has `clk` only: 0 occurrences of `clk_serdes` / `clk_coll`; the io_serdes_1 boundary registers (`u_bin_io_collective__serdes_*_from_io_serdes_1`, 599 bits) are on `clk`.
- So the cause is already removed in the plan. **No coll_s kit has ever been built on a merged-clock plan:** the last rows are hcut1111 (11-12) and efdb36e864 (11-13), and ER4-HOLD-1113 has kept it out of the wave since. The hold item now blocks the build that tests the fix.

### 5.3 What else the next form needs (attempt_16 placed dump, 21,176 zero-logic hops, 1,148 over 405 um)

| family | hops | max um | S4p | fix |
|---|---|---|---|---|
| `u_face.u_rx.o_data` -> `u_bout_rec_rx_s1/s2` | 324 | 547 | 0 stations | +1 station on rec_rx_s1 / s2 |
| ring -> `u_bin_rec_tx_s1/s2_i` | 237 | 602 | 0 stations | `u_bin` sited mid-route (sidecar), or +1 |
| codec bank `dout` -> `u_ctl.q_pin` | 269 | 658 | inside the face | move the bank output register or the ctl capture next to the SRAM bank (face core) |
| `u_tx.r_rst_n` -> rx / cal flags, `u_rrl` -> codec ctl | 243 | 692 | reset | local reset relays in the face |
| `fault_cause` -> `u_bout_fltv_o` | 16 | 840 | 0 stations | +2 on fltv_o (25 bits) |

coll_s has no `internal_stations` in S4p and 3 clock taps. The old dump also had fill 0.038, empty 0.84, 2,486 sinks on one tap, relay_collapse 795; these are the likely content of the visual ISSUES verdict (the verdict text is not on disk any more), and are advisory under the academic profile.

### 5.4 Fix and owner

1. KIT-OPS-5: remove coll_s from ER4-HOLD-1113 now. DIE-QC-103 launches it on S4p to sign-off. Expected: the 4,138 cross-clock endpoints are gone; what is left is the same-clock hold of the tap window.
2. DIE-QC-103, next cb / fw delta: rec_rx_s1 / s2 +1, fltv_o +2, rec_tx `u_bin` sites in the sidecar (lanes `coll_s__crec_rx_s*`, `coll_s__fltv`, both 21 cycles today, to coll_core).
3. One own lane for the type (TYPE-QC-COLLS, Sonnet) for the face-internal items of 5.3 and the first S4p result.
4. Stop: no rebuild of any pre-merge form, no hold ECO, no per-port tap windows for `clk_serdes` / `clk_coll` (the 11-13 proposal): those clocks no longer exist in the type.
5. Open, not verified here: the die-level seam coll_s <-> io_serdes_1 (2-cycle direct lanes, 598 + 599 bits). If the PHY side is not on the core regional clock, the seam hold is real at die STA; `die_sta_related` on S4p decides.
