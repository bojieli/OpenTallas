# FABLE-LEAF-FTSLOT 2026-11-14: feed-through registers in face-to-core slots under 86.4 um (S81 leaf t34, t28, t75, t13, t71)

For S81-LEAF-PLAN and DIE-S81-92. Review only: nothing shared was changed, nothing killed, nothing bound. What-ifs ran on private copies (DO_NOT_COUNT) in epyc7 `/srv/opentallas-scratch2/claude/fable-leaf-ftslot/`.

Status words: MEASURED = read from the plan, the tool source, a trial log or my own what-if run. INFERENCE = fits the numbers, not proven.

## 0. Verdict

- Option (b) is right, for all five types. Moving the cores 86.4 um off the faces closes every feed-through slot at the SAME station count: no +1 feed-through register is needed.
- Option (a) cannot close them, at any station count. Option (c) does not address the rule.
- No type is closed yet. With (b) applied, the feed-through slots clear in t34, t75, t13 and t71; the tool then rejects the type on a different item: the leaf's own bus links (`leafdn_i0`, `leafup_o0`) get 52-82 um longer and 5-12 bus rows per type need one more register, which `--take-regs` refuses for bus rows. t28 also leaves one slot (ft1).
- The placement search does not undo the move. Four other pieces of `core_place` do (section 3). Three small changes fix that.

## 1. Slot geometry (MEASURED, plan `ev/B6t.json` 0319e627dad9)

Checker: `cp9/slot_rule_leafplan.py`, 86.4 um. "S0" is the first register of a slot, on the input face under the die pin window.

| type (partition) | outline um | cores under 86.4 from a face | closed strip | ft registers in slots | S0 registers under a core |
|---|---|---|---|---|---|
| t34 (s_3S_L3) | 1442.88 x 1226.88 | W: ve_m 34.56, vs 77.76. S: ve_m 77.76, ve_s 34.56, ln_5 25.92, ln_7 47.52 | W, y 78-613 = 535 um (one 17-um gap) | 15 (W 11, S 4) in ft0-ft5 | ft3, ft4 (S) |
| t28 (s_2N_L1) | 1442.88 x 1278.72 | W: 8 lane cores 34.56-43.2. S: ln_12, ln_14, vn_b, ve_s 34.56, ve_m 51.84 | W, y 35-1082 = 1,048 um (gaps 11-37 um). S, x 35-1054 = 1,020 um (gaps 9-50 um) | 62 in 12 of 13 slots | ft2, ft3, ft4 (S) |
| t75 (s_1N_L1) | 1442.88 x 1278.72 | W: ve_m 43.2, vsw 60.48. S: ve_m, ve_s, ln_4 34.56, ln_7 43.2. E: ln_12 58.32, ln_15 84.24 | W, y 35-639 = 605 um. S, x 43-397 = 354 um | 16 in ft0-ft5 and up_s_2N_L0x4 | ft1 (E, under ln_12) |
| t13 (s_1S_L0) | 1442.88 x 1226.88 | W: ve_m 43.2. N: ve_m, ve_s 43.2, ln_12 10.8, ln_13 6.48. E: ln_4 19.44, ln_7 58.32, ln_5 71.28 | W, y 838-1184 = 346 um, then the N corner | 6 in ft0-ft3 | none |
| t71 (s_7N_L0) | 1442.88 x 1226.88 | W: ve_m 34.56, vsw 51.84, vs 77.76. N: ve_m, ve_s 51.84, ln_12, ln_8 36.72 | W, y 397-1175 = 778 um (gaps 9 and 26 um) | 17 in ft0-ft5 | ft0, ft1, ft2, ft3 (N) |

The handoff lists fewer slots per type than the checker flags (for example t34 ft0, ft2, ft5 and t28 ft0, ft7-ft9, ft12 also hold slot registers in B6t). Those are slots the tool can re-site once a form is applied; no form has been applied for these five types, so the plan still carries all of them.

## 2. The three options

### (a) 2-3 stations per slot: cannot close

- MEASURED: 10 S0 registers sit on the face under a core that is less than 86.4 um away (last column of the table). S0 is fixed by the die pin window; `--slot-ft` keeps S0 and `ft_add_station` inserts S1. No station count moves them.
- MEASURED: the closed strips are 535-1,048 um long in t34, t28, t75 and t71, against a 360-um hop. A register may not sit in the strip, so one hop would have to span the strip.
- t13: the W strip is 346 um, but the run then has to reach the N face window at x 6-151, which lies under ve_m (N 43.2). From the last legal site below ve_m to that pin is about 390-430 um (INFERENCE, by arithmetic on the coordinates).
- MEASURED: round 2 (cp15, +1 station on 27 slots, whole-slot re-route) failed on the same slots.

### (c) M9 over the cores: not a fix for this rule

- It adds wire capacity over the cores. The registers stay in the slot and the checker counts them. Keep `type_m9_grant` as its own item with DIE-S81-92.

### (b) cores 86.4 um off the face: right

- It removes the slot instead of routing around it, and it also clears the S0 registers.
- MEASURED (my what-if "R", base B6t, same flags as cp15 plus a block-shift seed and `--face-clear` on the two faces): every core moved by one vector, so core-to-core links keep their length.

| type | shift (dx, dy) um | ft slots failed | ft registers re-sited, count kept | leaf bus rows needing +1 | links over limit | link classes taking +1 |
|---|---|---|---|---|---|---|
| t34 | +51.84, +60.48 | 0 | 5 | leafdn_i0 5, leafup_o0 3 | 31 | pvs, vsp (sw failed) |
| t75 | +43.2, +51.84 | 0 | 11 | leafdn_i0 5 | 9 | vni |
| t13 | +43.2, -82.08 | 0 | 7 | leafdn_i0 5 | 17 | u, vni |
| t71 | +51.84, -51.84 | 0 | 4 | leafdn_i0 6, leafup_o0 1 | 4 | none |
| t28 | +51.84, +51.84 | 1 (ft1, new) | 5 | leafup_o0 8, leafdn_i0 4 | 22 | ver, vni |

- All five ended `applied False`, so the tool wrote no plan row and the slot checker could not be run on the result. "ft slots failed 0" is the tool's own report under `--slot-ft 86.4`, not a checker count.
- The "links over limit" are almost all the same leaf bus links (bus pin on the S or N face to vq / vs / vn). The y shift moves those cores away from the face that carries the leaf bus.
- Room on the far side (MEASURED from the plan): N/S room is free in all five. E room: t28 337 um free; t34 leaves ln_4 28 um off E; t71 leaves ln_2 45 um off E; t13 and t75 have lane cores already under 86.4 off E. No ft register sits in those E strips in t34 and t71; t75 needs E cleared for ln_12 and ln_15 (ft1 S0, up_s_2N_L0x4).
- Second what-if "M" (x shift for all cores, y move only for the near-face cores): t75 ended with 0 links over, 0 rows needing +1 and 0 ft slots failed; t71 with 2 bus links over. Both still had core overlaps from my crude seed, so they are not valid placements. INFERENCE: t75 and t71 can close with no bus-row change once the y move is legalised properly; t34, t13 and t28 need the bus rows.

## 3. Why the move is undone today (MEASURED: `core_place.py` at c92d74c9c3, trial events cp12 `*B_ev.json`)

The search itself keeps the rule: `legal()` rejects any move of a `--face-clear` core inside the clearance. The move is lost in four other places.

1. `face_clear_legalise` restores every cluster when one cluster finds no spot (`if failed: restore()`). cp12: t34B, t28B, t75B, t13B all report `face_clear_moved 0` with 1-4 clusters in `no_legal_spot`. The failing ft slots are exactly the ones left when this restore happens: my patched run "F", which still ends in this restore, reproduced the handoff list for t34 (ft1/ft3/ft4) and t13 (ft0/ft1/ft2) exactly, and close to it for t28 (ft2-ft7, ft10, ft11), t75 (ft0, ft2, ft4) and t71 (ft0).
2. The sweep works one face at a time and tries at most 8 lateral steps (34.56 um). A corner core such as ve_s (34.56 off S, under S windows that `--window-clear` wants 86.4 off) needs 51.84 um on the other axis during the W pass. INFERENCE for the exact rule that blocks it; the block-shift seed, which moves both axes at once, does not hit it.
3. The station repair reverts station-end clusters to their base spot, and the retry pins them there (`cfix`); `face_clear_legalise` skips pinned clusters. Face-rule clusters revert last, but they do revert. Seen in my runs as "station retry: pin ... u_ve.u_s, u_vsw, u_vs".
4. `--take-regs` excludes bus rows, so the final gate rejects the type. cp12 t71B is the clean case: face-clear moved 19 clusters, every core was clear of W and N, ft slots failed 0, count kept, and the type was dropped for 2 leaf bus links (717 and 704 um against 405).

### Changes to core_place (S81-LEAF-PLAN)

- F1 block shift: `--face-clear` first translates the whole core block by the vector that puts the nearest core on each clearance line (both axes at once), then legalises only the cores that hit the far faces. Keep partial results; never restore all. Until then: `--seed` with the block-shift file (`seed_rigid.json` in my directory); the seed legaliser must accept a spot that is as legal as the base (`base_ok`), which it does not do today ("no legal spot near its seed" on ve_m in every run, because the base itself breaks the pin-face gap).
- F2 with `--take-regs`, a face-rule cluster is never reverted or pinned by the station repair; the station takes +1 instead.
- F3 `--take-regs` covers bus rows: a stretched `bus:leafdn_i0` / `bus:leafup_o0` row gets +1 on every row of that bus, and the tool writes the lane row, as `ft_add_station` does for ft lanes.
- Keep-out: none needed beyond `--face-clear W:86.4:.` plus the second face. For t75 add `--face-clear E:86.4:g_ln\[(12|15)\]`.

## 4. Plan rows and latency deltas

Per type, against B6t:

- `hard_cores[].origin_um`: block shift of section 2 (file `seed_rigid.json`, sha 9b9f9811605e), then the search's own moves. Core shapes and orientations unchanged.
- `ft_slots[].stations`: unchanged. `regs_um` / `bit_sites_um` re-sited. No feed-through lane row.
- `internal_stations` bus rows +1 register (B6t row index): t34 65-69, 326, 328, 329; t75 74-78; t13 69-73; t71 71, 73-78; t28 144-151, 159-162.
- `latency.lanes` (INFERENCE: I did not trace which field of the lane row carries the leaf's internal bus stage; LATCHECK on the merged bind decides):

| type | lane | cycles now -> new | param |
|---|---|---|---|
| t34 | dn_s_3S_L3 | 15 -> 16 | LAT_DN_S_3S_L3 |
| t34 | up_s_3S_L3 | 12 -> 13 | LAT_UP_S_3S_L3 |
| t75 | dn_s_1N_L1 | 4 -> 5 | LAT_DN_S_1N_L1 |
| t13 | dn_s_1S_L0 | 7 -> 8 | LAT_DN_S_1S_L0 |
| t71 | dn_s_7N_L0 | 10 -> 11 | LAT_DN_S_7N_L0 |
| t71 | up_s_7N_L0 | 8 -> 9 | LAT_UP_S_7N_L0 |
| t28 | dn_s_2N_L1 | 5 -> 6 | LAT_DN_S_2N_L1 |
| t28 | up_s_2N_L1 | 3 -> 4 | LAT_UP_S_2N_L1 |

- Leaf-internal link classes (LF_CS parameters, +1 cycle each, no die lane): t34 pvs, vsp, and sw (sw failed in my run: 4 vsw-vs links 430-554 um against 405-519); t75 vni; t13 u, vni; t28 ver, vni.
- That is at most 8 lane rows, against the 23 rows of the +1 feed-through chain (`ev/B6t_ft.json`), which did not close the slots.
- For DIE-S81-92: B6b already carries the +1 feed-through rows for these five types. They are not needed for the slot rule. They are harmless and make the re-site easier (INFERENCE), so I would leave B6b as launched and not add more.

## 5. Proof (one check per type)

1. `python3 -I cp9/slot_rule_leafplan.py PLAN types5.txt 86.4` prints `TOTAL 0` for the five types (today on B6t: t34 15, t28 62 ft, t75 16, t13 6, t71 17).
2. core_place row: `applied True`, `ft_failed 0`, `overlaps 0`, `timing_violations_end 0`.
3. G0: 296 errors, the same finding set as the control.
4. Merged bind: LATCHECK_RC 0 with the lane rows of section 4.

## 6. Open

- t28 ft1 (new conflict at 592, 441 after the shift) and its 12 bus rows: one run with F1-F3.
- t34 class sw: needs vsw kept beside vs in the shift (they were split by the search), or +1 on sw.
- Nothing here was bound or run through G0.

Evidence: epyc7 `/srv/opentallas-scratch2/claude/fable-leaf-ftslot/` (11 MB): `geo.py` (table of section 1), `seed_rigid.json`, `seed_min.json`, runs `t*R` (block shift), `t*M` (x shift + near-face y), `t*F` (patched copy `core_place_fx.py`, joint pre-set), each with `.log` and `_ev.json`; `summ.py` prints the tables. Can be deleted after S81-LEAF-PLAN has read it.
