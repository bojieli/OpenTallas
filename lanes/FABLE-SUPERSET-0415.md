# FABLE-SUPERSET-0415 (2026-11-20 01:0x PST): shared superset pinouts, census, forms, pilot

Lane: FABLE-SUPERSET-0415 (Fable). Owner decision 11-20: YES to shared superset pinouts (one outline and one union pin set per family of equal logic, unused pins tied off, sign-off inherited under SIGN-PROFILE-0400).

Marking: **V** = measured or opened this round. **E** = my estimate. **P** = proposal. Nothing live was changed: no plan, no kit, no job of another lane. One generator change is on main (section 5).

Inputs (V): S81 D8i `05b98332d100`, QC N46R3 `ce3a7b3c4671`, KV D25f2 `26fa4732ff8e`, HEAD r11b `0eb418a2a6da`.
Scripts and tables: epyc7 `/srv/opentallas-scratch2/claude/fable-superset-0415/{scripts,out}`. Class tables for the plan lanes: `lanes/handoff/FABLE-SUPERSET-0415-classes.json` (sha c6b142d032c7).

> **OWNER 11-20: "do not use the +16% growth."** Superset uses only no-growth classes on every die. Section 9 is the valid S81 form. Every growth figure below (the +16 % area, the 13 / 17-build leaf tables of section 2.1, station 46 -> 12, kv_leaf 5 -> 2, the t13 pilot of section 4) is OBSOLETE and kept only as history. Valid counts: S81 leaf 75 -> 33 (4,500-bit cap) or 25 (6,000), station 46 -> 16, serdes 11 -> 2, kv_leaf 5 -> 3; S81 395 -> about 110; area 0 on all dies. The handoff file (sha 728d928f6546) now holds only `*_nogrowth_j4e` tables; the growth tables were removed.

## 0. Answer

| Die | Types now | Builds after | What collapses them | Area | Cycles |
|---|---|---|---|---|---|
| S81 | 395 | about 90 | col by inheritance (216 -> 20), leaf superset (75 -> 13 to 17), station (46 -> 12), serdes (11 -> 2), kv_leaf (5 -> 2) | leaf 0 to +16 % per tile (pilot form is the +16 % end), others 0 | +0 to +2 per tile crossing on lanes that take the class maximum |
| QC | 133 | 50 to 62 | union clock-tap + count-strap pin set (57 types), v1/v2 port superset (about 14 to 26) | 0 | 0 |
| KV | 56 | 24 to 30 | hg width maximum (6 -> 1), hgi (11 -> 1 to 3), pv and pc pairs | 0 | 0 |
| HEAD | 26 | 26 | nothing: 26 families, already replicas, 25 signed | - | - |
| All | 610 | about 190 to 210 | | | |

- All "after" counts are plan-level (module and parameters, outline, buses, ft slots, hard cores). The netlist diff of SIGN-PROFILE-0400 has not been run on any group. Treat them as upper bounds on the collapse until it has.
- The superset is a pin problem only on S81 (leaf, station, serdes). On QC it is a clock-tap and strap problem. On KV it is one bus width plus ft population.
- Pilot (section 4): one S81 leaf superset kit and its per-type control are generated-and-route armed on epyc9; both are waiting for memory admission (epyc9 admits 0 GB, 32 waiters). No measured area or GRT number yet.

## 1. Census

### 1.1 S81 (V, `out/s81_rows.json`, `census.py`)

| Family | Types | RTL | Outlines | Bus pin sets | With ft set | Signed items | Verdict |
|---|---|---|---|---|---|---|---|
| col h9 / h10 (12 families) | 216 | 1 per family | 1 per family | 1 per family | 1 per family | 0 | already equal in pins, ft and hard cores; 20 distinct after clock taps and strap rows. Inheritance, no pin work (FABLE-S81-TYPEMERGE R1 to R4) |
| ot_s81sl_leaf | 75 | 1 | 5 | 53 | 69 | 0 of 68 | superset, section 2.1 |
| slice_station | 46 | 1 (no logic) | 5 | 6 | 45 | 25 of 35 | superset for the unsigned ones, section 2.2 |
| serdes | 11 (14 inst) | 1 | 1 | 6 | 9 | 0 | superset, 2 builds |
| ot_s81sl_kv_leaf | 5 | 2 | 3 | 5 | 5 | 0 | 2 builds at 6,000 bits; 1 build needs 10,212 bits, not proposed |
| dsdv_slice c1x_C | 9 | 1 | 1 | 9 | 9 | 0 | bus sets differ by 1,314 bits; 9 -> 8, not worth an event |
| svc_hi / svc_lo | 16 | 4 | 3 | 16 | 16 | 0 | different logic and bus sets; none |
| other dsdv_slice, eng, gunit, iqf, phy, seqhost, bk_sel | 17 | 17 | - | - | - | - | singles |

How the leaf variants differ (V, `out/s81_leaf_detail.txt`):
- Own interface is always the same two buses: `leafdn_i0` 597 in and `leafup_o0` 668 out, both on N (33 types) or both on S (42). The window sits at 6 to 1,307 um along the face, set by how many lanes were packed before it.
- Feedthrough slots: 0 to 20 per type, 0 to 7,786 bits (median 2,628). Widths are from a short list: 1104, 668, 597, 276, 70 (six at a time), 571, 562, 513, 132, 45, 32, 1. 42 distinct (in face, out face, station count) triples; straight N-S and S-N carry most bits, E-W and W-E the 1104 and 6 x 70 row buses, and 12 turn forms.
- Stations per slot: 2 to 12.
- Outline: 1442.88 x 1226.88 (46 types), x 1278.72 (19), x 1356.48 (8), two wider singles (t28, t8).
- All 27 hard cores are the same masters in every type, but their origins differ in every type (46 to 67 distinct origins per core): each tile's floorplan was moved around its own lanes.

### 1.2 QC (V, `out/qc_modgroups.txt`, `out/qc_n46r3_vfam.tsv`)

- 133 types, 50 family stems, 62 groups of equal content modules.
- Inside a content group every bus, ft slot and outline is already equal. The members differ only in the clock tap table (`__cl`), count-strap rows and pads (`__pad`), and station-variant hash (`__pv`). 31 stems are of this kind, 57 types.
- v1 / v2 / v3 variants of fw, fe, stm, sc, st_a, st_b on both halves: v2 is v1 without one or two buses (`x_st_a_o` 258, `x_st_b_o` 258, `l9_wi` 514, `x_fw_i` 258) and one ft slot. Union pins are at most 1 % above the larger variant. st_a and sc also differ by one hard core.
- v3 are chain-end variants: `sle_fe_v3` lacks 25 buses, `slw_fw_v3` has 4 buses v1 does not. They merge only as a true union; count them as uncertain.
- cb tiles (cbn / cbx / cbf, 24 instances per type) are already replicas; their types split on clock class only (cbn_q00: 141, 14 and 9 taps).
- East and west halves (sle_ / slw_) use different station modules (`qfd_dv_redstn2_region` vs `qfd_dv_s8_station_tail1`): different logic, not merged.

### 1.3 KV (V, `out/kv_modgroups.txt`, `out/kv_d25f2_vfam.tsv`)

- hg v1, v1p2 .. v1p6: one content set, one hard-core set, 4 ft slots, equal outline. The only difference is `i_kvs_hroot_Q_o_cN` 10 / 15 / 20 / 25 / 30 / 35 bits and `o_kvs_hroot_Q_o_cN` 5 .. 30. Six types, 24 instances.
- hgi (11 types, 32 instances): buses equal (1,659 bits). ft slots 3 to 27 (1,072 to 5,311 bits), hard cores 18 to 25.
- pv (16 types): v1/v1n, v3/v3n, v5/v5n and v2/v2n, v4/v4n, v6/v6n pairs have equal buses and differ by one hard core or clock rows. A whole-family union is 21,054 bus bits against 15,622 (+35 %): not proposed.
- pc (6): three content sets, the rest clock class.
- phy / phy_v1 (32 instances): one 1-bit bus and one 1-bit ft slot apart; both already signed, leave.

### 1.4 HEAD (V)

26 types, 26 family stems, 358 instances (hd_tile 264). No two types share logic. 25 of 26 signed. No superset case.

## 2. Superset forms

### 2.1 S81 leaf (P; class table V from `cluster.py`) -- OBSOLETE where it assumes growth (OWNER 11-20); see section 9

Slot model: a tile = own buses (exact) + ft slots keyed by directed face pair. A narrower lane may ride a wider slot. The class superset per face pair is the element-wise maximum of the width lists. Each member may be mirrored (R0 / MX / MY / R180). Greedy merge by least added bits, with a cap on tile ft bits and a face pin cap of 3.6 pins per um.

| Cap on ft bits per tile | Builds | ft bits carried, all 75 tiles | Station flops | Largest class |
|---|---|---|---|---|
| 3,000 | 45 | x1.16 | x1.17 | 11 types |
| 4,000 | 33 | x1.30 | x1.40 | 22 |
| 5,000 | 23 | x1.43 | x1.52 | 20 |
| 6,000 | 17 | x1.65 | x1.84 | 31 |
| 7,786 (today's largest tile) | 13 | x1.79 | x2.01 | 31 |

Recommended: the 6,000-bit table (17 builds), rolled out largest class first.

| Class | Types | Superset ft bits | Slots (class frame) |
|---|---|---|---|
| leaf_S00 | 31 | 4,470 | N>S 597, 597, 276, 1; S>N 668, 668, 668, 276; N>W 597; S>W 45, 45; W>S 32 |
| leaf_S01 | 9 | 5,585 | E>W 1104; N>S 668, 276, 276; S>N 597, 276 x3; S>W 1104; W>E 176, 70, 70; W>S 276, 70, 70 |
| leaf_S02 | 8 | 4,464 | N>S 668, 70 x6; S>N 1104, 1104, 597, 571 |
| leaf_S03 .. S05 | 4 each | 5,019 to 5,717 | in the handoff file |
| leaf_S06 .. S08 | 3, 2, 2 | 4,424 to 5,986 | in the handoff file |
| 8 singles | 1 each | as today | t3, t8, t28, t33, t52, t67, t72, t75 |

Form:
1. **Pins.** One window layout per class. Own buses at fixed windows. Every class slot has a window on its two faces at the measured pitch (0.217 um per pin, M7 / M5). Pass lanes use the shift form: a lane enters at lane position j-1 and leaves at position j (in window and out window differ, the Z path `ft_corridor.py` already builds). With it a class closes under stacking: the tile above receives a neighbour's own bus where its first pass slot starts, so tiles of one class abut in any order.
2. **Hop cap.** A straight crossing of a 1,227 um tile is 6 stations at 245 um per hop; turn slots 4 to 6. All under 300 um. The class takes one station count per slot.
3. **Outline.** One per class: the largest member's (1442.88 x 1356.48 for S00) plus pin margin. S00 needs 5,613 pins on its N face = 1,219 um of 1,443 at today's pitch, so it fits the face only with a re-packed window order and no core within 86 um of the face (R-LEAF-2b). Outline growth is 0 % if the floorplan is redone for the class, up to +16 % if lanes are added in a new street beside an existing floorplan (the pilot form).
4. **Unused pins.** Spare ft slot: bind `kit-rtl` already chains the spare bits through the slot's own stations (bind.py "plan bus with no bound bit (spare lane)"), so every pin is registered at its face. Spare input pins are tied at the parent like strap pins (OWNER 10-25 B); spare outputs are open. Declared in the as-built `declared_ties` list, reported in `bind_declared_ties.json`; LEC sees the spare chain as kept logic with no observer.
5. **Landed slots.** A slot that is a forwarded-clock landing on any member carries its landing band (3,200 flops, about 5,000 um2) on all members. Count straps take the class maximum width (TYPEMERGE R2).
6. **Die level.** Neighbour pins move on every tile that faces a leaf: the other leaves of the column, slice C, stations, col r0. Station counts change on lanes that take the class maximum, so K values and LATCHECK rows change. This is one slice-region re-pin per class group, not a per-type delta.
7. **ID constants and tap tables (V, bound wrappers of the D8i tree, 62 leaf files).** With ft lines removed, two bound leaf wrappers still differ (t13 vs t7: 2,874 lines; t13 vs t30: 7,345): (a) ID parameters `S_<inst>_u_vq_sid` [3:0] (14 values) and `S_<inst>_u_vq_k` [2:0], and the instance name itself (`u_lf0`, `u_lf1`, `u_lf3`, `u_lf4`, `u_lf`); (b) clock tap indices (`clk_t19` vs `clk_t24`) and reset tree taps (`rst_n_t33` vs `rst_n_t31`); (c) the reset collector relays. So a leaf class also needs `sid` and `k` as strap pins tied at the parent (7 bits, OWNER 10-25 B), one instance name, and one tap table and reset tree per class. (b) and (c) follow from one class floorplan; (a) is an RTL / bind row. Without (a) the SIGN-PROFILE-0400 diff will not read the members as equal.

Cost (E): cell area under 1 % of the tile (S00: 28,400 station flops and up to 8 landing bands on 1.77 mm2). Wiring: static channel check `ft_channel_route.py` at 0.70 reports 0 channels over on the pilot type with the four added lanes, with and without the street (V, but the no-street variant has station points on cores, so that reading is not a proof). Cycles: +0 to +2 per tile crossing; a leaf-to-C lane crosses at most 2 tiles.

### 2.2 S81 station, serdes, kv_leaf (P) -- OBSOLETE where it assumes growth (OWNER 11-20); see section 9

- slice_station: pure feedthrough tiles. 46 -> 12 at 6,000 bits (largest class 21 types), 6 at 8,000. 25 of the 35 station items are signed: keep them, apply the class form to the unsigned ones and to stations whose pins a leaf class moves anyway. Outline: unchanged (the largest class superset is below today's largest station, 7,625 bits).
- serdes: 11 -> 2 (8 + 3), superset 3,078 bits = today's largest. No growth.
- kv_leaf: 5 -> 2 (4 + 1) at 6,000 bits.

### 2.3 QC (P)

1. **Union tap and strap pin set per family (57 types).** This is the type-root clock of FABLE-CONVERGE move 2 (owner #5): all taps of a type under one root, so the tap table leaves the type identity. Add: count-strap rows at the family maximum width, pad straps at the family maximum (`r8_strap_pad_max` 31 is already there for sle_ctl). No bus pin moves, no neighbour moves, 0 cycles.
2. **v1 / v2 port superset (fw, fe, stm, sc, st_a, st_b; both halves).** Build v1; v2 instances tie the unused input bus (`x_fw_i`, `l9_wi`) and leave `x_st_a_o` / `x_st_b_o` open; the extra ft slot is a spare lane. At most 1 % more pins, 0 area, 0 cycles. st_a and sc keep the extra hard core of v1.
3. v3 chain ends: leave as separate builds until the netlist diff says otherwise.

### 2.4 KV (P)

1. **hg v1 .. v1p6 -> one type** at `i_kvs_hroot_Q_o_cN` 35 and `o_..` 30. Unused high bits tied at the parent / open. Not checked: that the RTL peels the same 5 bits at every position (if the peel index is a parameter it becomes a strap).
2. **hgi 11 -> 1 to 3**: buses already equal; the union ft set is 5,315 bits against the largest variant's 5,311. The hard-core sets (18 to 25) must be compared first: if the extra cores are slot-driven the union is one build, otherwise split by core set.
3. **pv and pc pairs** (v1/v1n and so on): clock and one-core differences; they go with the type-root event.

## 3. Cost summary (E unless marked) -- OBSOLETE where it assumes growth (OWNER 11-20); see section 9

| Family | Builds before -> after | Area | Cycles | Die effect |
|---|---|---|---|---|
| S81 col | 216 -> 20 | 0 | 0 | none (inheritance) |
| S81 leaf | 75 -> 17 | 0 to +16 % of 133 mm2 of leaf tiles | +0 to +2 per crossing | slice-region re-pin |
| S81 station | 46 -> 12 (unsigned first) | 0 | +0 to +2 per crossing | follows the leaf classes |
| S81 serdes | 11 -> 2 | 0 | +0 to +1 | pin windows of 14 instances |
| QC tap / strap union | 133 -> 76 | 0 | 0 | none |
| QC v1 / v2 | 76 -> 50 to 62 | under 1 % pins | 0 | spare pins tied at parent |
| KV hg | 6 -> 1 | 0 | 0 | 25 spare bits per instance at most |
| KV hgi, pv, pc | 50 -> 23 to 29 | 0 | 0 | to be confirmed |

## 4. Pilot: S81 leaf, class S00 (private, epyc9 `/srv/opentallas-scratch2/claude/fable-superset-0415/pilot`) -- OBSOLETE where it assumes growth (OWNER 11-20); see section 9

- Two hardlinked copies of the strict-bound D8i tree `tree6base` (plan f2ec5ffc3bda): `tree_base` (per-type control) and `tree_sup`.
- Type: `ot_s81sl_leaf__t13` (R0, own bus N, 5 ft slots, 2,662 bits, the largest R0 member of S00).
- Superset form in `tree_sup` (plan 979cbabb4f42, `patch_sup.py`): the trunk superset of S00 without its three small turn slots and the one N>W slot: N>S 597, 597, 276, 1 and S>N 668, 668, 668, 276(132 + 144). Four spare lanes added (1, 144, 276, 668 bits; ft bits 2,662 -> 3,751, +41 %), 6 stations each at 238 um hops, in a new east street. Outline 1442.88 -> 1673.28 um (+16.0 %). `superset` key set, so the spare ends get pins (checked: ft5 .. ft8 have 2 / 145 / 277 / 669 pins on N and S).
- This is the pessimistic end: the existing floorplan is kept and all new lanes are paid in new area. A class floorplan redone from scratch should need less.
- Status 01:4x: both kit generations (`kit_ab.sh`, ot-run 24 GB, priority proof) are waiting for memory on epyc9. Hub chain `intel2 ~/lanes-fable-superset-0415/chain.sh` launches each kit with `run_kit.sh ... route 64 8` when its gen lint is clean. Logs: `kit_{base,sup}.log`, `route_{base,sup}.log`, `chain.out`.
- To read when it routes: placed utilisation and cell area of both, GRT overflow TT and FF, post-CTS and routed setup / hold, DRC count. Not yet measured: all of it.
- Not in the pilot: a die bind with the spare ends declared (the die bind of `tree_sup` was not re-run; the kit takes the bound t13 module and adds spare lanes), the shift-form windows, the landing bands of spare lanes.

## 5. Generator change on main

- `gen_phys.py` SUPERSET-1, main `e00be6bb605`: `type_pins()` took pins only from the die ports of the first instance, so a declared bus or ft-slot end with no die port had no hardened pin. With the opt-in type key `partition_types[T].superset`, those ends get pins from the type's own window through the same `pin_positions()` a bound port uses. Types without the key are unchanged. Test `tools/die_plan/test_superset_spare_pins.py` (4 pass); the gen_phys suite passed in ot-push-main.
- Still needed for a real class (not written): a class window solver (shift-form windows for a whole class, then `ft_corridor` siting); the die-bind rows that declare the spare ends; G0 "identical pin tables across a replicated type" must compare the full type table, not the bound subset.

## 6. Rows for the plan lanes

| Lane | Next cut | Row | Ready |
|---|---|---|---|
| S81-DIE-R3 | J5 11-20 14:00 PST | none for J5. The leaf class form is not proven; do not fold it yet | - |
| S81-DIE-R3 | J6 11-21 14:00 PST, if the pilot routes | S00 (31 types) as one class: window layout, `superset` key, spare ends declared; stations facing S00 follow. Class table in the handoff file, `s81.leaf` | class table yes; window solver no |
| S81-DIE-R3 | any cut | serdes 11 -> 2 (`s81.serdes`): smallest die effect, good second pilot | class table yes |
| QC-PLAN-R3 | V1 11-21 06:00 UTC or the #5 event | strap rows at the family maximum on the 31 clock-only stems (`qc` table, verdict "CLOCK/STRAP only"); v1 / v2 port superset on the 12 stems marked SUPERSET | table yes; needs the type-root clock for the tap part |
| KV-D23-COMPOSE | D26 11-21 04:00Z | hg v1 .. v1p6 -> one type at 35 / 30 bits; check the peel index first | table yes; RTL check no |
| HEAD-CROSSING-1119 | - | none | - |

## 7. Not checked

- Netlist equality of any group (no SIGN-PROFILE-0400 structural hash was run).
- Any routed or placed number for a superset tile; the pilot has not started.
- That the die strict bind accepts a type slot with no port on some instances with only a `declared_ties` row.
- That class S00 fits its N face after a real window re-pack (5,613 pins on 1,443 um is 84 % at today's pitch).
- The greedy class table is not optimal and counts slots, not window positions.
- Whether the leaf `sid` / `k` constants can become strap pins without a cycle (they feed `u_vq`); the plan note says k arrives in-band, the bound wrappers still carry the parameters.
- KV hg peel index, KV hgi hard-core sets, QC v3 unions.
- Cycle cost in lanes (LATCHECK) for any class.

## 8. Left behind

- intel2 `/srv/opentallas-scratch2/claude/fable-superset-0415-wt`: a partial clone of mine (5.6 GB) that I stopped. `ot-delete` skips it as protected (`.git/shallow.lock` marker). I did not delete it another way.
- intel2 `/srv/opentallas-scratch2/claude/fable-superset-0415-lane` (lane clone, 1.4 GB), epyc7 and epyc9 `/srv/opentallas-scratch2/claude/fable-superset-0415` (plans copy 295 MB; two hardlinked trees).

## 9. Die-fit check (COORD 11-20 01:5x: the S81 die cannot grow) -- supersedes the +16 % form of sections 2.1, 3 and 4

Plan read: plan_j4e `9780ae146139`, die 32,693.76 x 25,980.48 um, 398 partitions covering 94.0 % of the die (V, `sitefit.py`, `out/s81_j4e_leaf_sitefit.txt`).

### 9.1 Does +16 % fit? No.

Free distance from each of the 75 leaf sites to the next partition or die edge, type frame:

| Slack | Sites |
|---|---|
| 0 um on E and on W | 48 of 75 (all of columns 3 to 7, and every L1 row of columns 0 to 2) |
| 146.9 or 155.5 um on one side only | 17 |
| 146.9 + 155.5 um (both sides) | 10 (column 1) |
| any slack in y | 4 (s_1S_L4 129.6, s_4S_L4 129.6, s_2N_L0 103.7, s_4N_L0 51.8); 71 have 0 |

- +230.4 um (+16 %) on one side fits at 0 of 75 sites. Split over both sides it fits at 10.
- Even +43.2 um fits at only 27 of 75 sites. The slack is the two channels beside columns 0, 1 and 2; columns 3 to 7 abut on all four sides.
- So no outline growth fits everywhere. Growing only where there is slack would split each class in two (grown and not grown) and gain nothing.

### 9.2 Smallest form that fits: no growth, classes inside one outline

Each class holds members of one existing outline only and keeps that outline. The superset has to fit the face pins and the channels the tile already has. Area cost is 0; the price is more classes.

| Cap on ft bits per tile | Builds, face cap 3.6 pins/um | Builds, face cap 4.6 pins/um (today's measured pitch) | ft bits carried | Largest class |
|---|---|---|---|---|
| 3,000 | 46 | 46 | x1.17 | 25 types at 2,666 bits |
| 4,000 | 34 | 34 | x1.30 | 25 |
| 4,500 | 33 | 28 | x1.32 to x1.45 | 28 types at 3,370 bits |
| 5,000 | 29 | 25 | x1.42 to x1.47 | 25 |
| 6,000 | 25 | 18 | x1.46 to x1.62 | 25 |
| 7,786 | 23 | 13 | x1.49 to x1.80 | 31 at 4.6 pins/um |

For scale, tiles of the 1442.88 x 1226.88 outline carry up to 5,755 ft bits today (median 2,094); the 1278.72 outline up to 7,786; the 1356.48 outline up to 5,949.

Trade-off against the earlier table (which mixed outlines and allowed growth): 17 builds with up to +16 % area becomes **25 builds at 0 area** (6,000-bit cap, 3.6 pins/um), or 33 builds if no class may exceed 4,500 bits. The 13-build table is reachable without growth only at 4.6 pins/um and tiles up to 7,786 bits, which no 1227-outline tile carries today: not recommended before a class is routed.

Recommended (P): 4,500-bit cap, 33 builds, first class F00 = 28 types of the 1442.88 x 1226.88 outline, superset N>S 597, 597, 276, 1 and S>N 668, 668, 562, 1 = 3,370 ft bits. One member (t38) already carries 3,093 of them in this outline. Then widen the cap class by class as each routes.

S81 total with this form: 395 -> about 105 (leaf 33 instead of 17); about 98 at the 6,000-bit cap.

### 9.3 Pilot changed to the fitting form

- The +16 % kits (t13) were cancelled before they started (my two ot-run clients, by exact job string). `tree_sup` is kept but is not the pilot.
- New pilot: `ot_s81sl_leaf__t38` in `tree_fit` (plan 8047689296ac, `patch_fit.py`), **outline unchanged**, class F00 superset: two spare lanes added (N>S 276 and N>S 1, +277 bits, 3,093 -> 3,370), windows in the free face span 980 to 1,045 um, 6 stations through the free channel at x 1,091 to 1,123 um, hops at most 285 um. `superset` key set; pins checked (ft6 277 pins, ft7 2 pins on N and S). Control: the unchanged t38 in `tree_base`.
- Both kit generations are queued on epyc9 (admits 0 GB); the hub chain routes each when its gen lint is clean. No measured number yet.
- The control and the pilot differ by 9 % in ft bits, so the pilot answers "does the F00 superset close in the existing outline", not "what does a large superset cost".

### 9.4 Not checked

- The four y-slack sites and the column 0 to 2 channels were not checked for what the die uses them for (clock, PG, routes); I counted them as free only for the fit test, and the recommended form does not use them.
- A smaller tile placed in a larger site (a 1227 tile in a 1279 or 1356 site) would merge classes across outlines at 0 area, but leaves a 52 to 130 um gap with unregistered wire at the face. Not priced.
- Stations and serdes classes of section 2.2 already keep their outlines; they were not re-run on plan_j4e.

### 9.5 OWNER 11-20: no growth on every die

- Handoff file rewritten (sha 728d928f6546): `s81.leaf`, `s81.leaf_cap7786`, and the mixed-outline `s81.station`, `s81.serdes`, `s81.kvleaf` are removed. Valid keys: `s81.leaf_nogrowth_j4e`, `s81.station_nogrowth_j4e` (46 -> 16 at 6,000 bits), `s81.serdes_nogrowth_j4e` (11 -> 2, one outline already), `s81.kvleaf_nogrowth_j4e` (5 -> 3), all on plan_j4e with one outline per class.
- QC and KV rows never changed an outline (tap / strap union, v1 / v2 ports, hg bus width); they stand.
- The t38 pilot is unchanged.

## 10. Class unification spec (COORD 11-20 02:2x; SIGN-PROFILE-0400 found 0 inherit)

Owner of this spec: FABLE-SUPERSET-0415. Acceptance test: `tools/fleet/netlist_inherit.py` (main 8f21fff40b3) `summary` = one hash group per class, then `prove` per member against the signed representative. No outline growth.
Per-class rows (superset port list + what each member lacks today): `lanes/handoff/FABLE-SUPERSET-0415-unify.json` (sha 2ae9ece21c46), made by `class_unify.py` from the plans (V). Plans read: S81 plan_j4e, QC N46R3, KV D25f2.

### 10.1 The rule (P), same for every class

A class is unified when every member's plan row is a copy of ONE class row; only the type name and the ROM image selectors differ.

- **U1 Links.** The class row carries every cland link any member has: `cland_dn_ready_k` / `cland_dn_fault_k` / `fclk_in_cland_dn_k` for k up to the class maximum of collector children, the up pins, every `cland_*start_*` of every landed bus. A member that does not use link k ties its inputs at the parent and excludes it from the ready / fault aggregate by one strap bit per link (`strap_cland_use[k]`). Existing tool for the col form: `cland_col_superset.py` (CLAND-TIE-1).
- **U2 Taps.** One tap table per class: the representative's `clock.taps`, `added_taps`, `sink_sites_um`, by name and site. The die clock delivers the same taps to every instance. Where the class has the type root of owner decision #5, this is the root plus the kit sub-tree.
- **U3 IDs.** Every ID that is a constant in the bound wrapper (S81 leaf `S_*_sid`, `S_*_k`; count K values; pad counts) becomes a `strap_*` input pin at the class maximum width, tied at the parent (OWNER 10-25 B). No parameter in the wrapper may differ between members.
- **U4 Reset / start.** One reset tree per class: the representative's depth, with the class maximum number of outs (`rst_o_k`, `start_o_k`); unused outs are open at the parent. All members take the collector form if any member has it.
- **U5 Data.** Union of buses at the maximum width and the class ft-slot superset (section 9). Unused inputs tied at the parent, outputs open, spare ft lanes chained through their stations (bind kit-rtl does this). Type key `superset` gives the spare ends pins (main e00be6bb605).
- **U6 Floorplan.** One set of hard-core origins, internal stations and bands: the representative's.
- **U7 One synthesis.** The kit RTL comes from the class row, not from each instance: bind must emit one bound module for the class (a TYPE_SPLIT inside a class is a spec error to fix, not to accept). Synthesis runs once per class with one flow tag and one config; a member's netlist is that netlist with the top name replaced. Golden SDC equal after the name placeholder. This removes the +-20k gate differences SIGN-PROFILE measured between separately synthesised members.

Acceptance per class, in order: (a) plan: `class_unify.py` reports 0 members with a missing or narrow item and 0 off-representative taps / cores; (b) bind: one bound module, strict bind and LATCHECK pass, `bind_declared_ties.json` lists only the U1 / U5 ties; (c) `netlist_inherit.py summary`: 1 hash group; (d) representative routes and signs; (e) `prove` per member, record in `autopilot/inherit_members.tsv`.

### 10.2 The classes (V: plan-level numbers)

| Die | Class | Members / inst | Signed | Taps equal today | Cores placed equal | What differs today | Work |
|---|---|---|---|---|---|---|---|
| S81 | col_h9_r1 | 60 / 60 | 0 | yes (14 each) | yes | links: 51 members lack the 6 monitor links (2 variants); reset outs 0 / 1 / 2, depth 8 or none; ROM image | U1 + U4 only |
| S81 | col_h9_r2 | 60 / 60 | 0 | yes (14) | yes | links: 9 in the union, 3 variants; reset outs 0 / 3, depth 6 or none; ROM image | U1 + U4 only |
| S81 | leaf_F4500_00 | 28 / 28 | 0 | no: 24 taps each at different sites (union 530) | no (27 of 28 differ) | 58 links, 24 link variants; 11 straps, 17 members narrower; reset outs 0 to 7, depth 6 / 7 / 8; `sid` / `k` constants; ft slots | U1 to U7, needs the class floorplan |
| QC | sle_ctl | 7 / 12 | 0 | yes (19) | yes | 99 links, 4 variants (children 0 / 2 / 3 / 5); reset outs 0 / 2 / 4; pad straps | U1 + U4 (+ strap pads at maximum) |
| QC | slw_stm | 6 / 6 | 2 | yes (2) | no (5 of 6) | 61 links, 6 variants; 2 members lack 2 straps; v1 / v2 / v3 contents | U1, U3, U6; keep the 2 signed as they are |
| QC | slw_fw | 6 / 6 | 0 | no (2 each, union 4) | yes (no cores) | 6 members lack a bus (v1 / v2 / v3: 46 buses in the union, 14,052 bits vs 13,895); 89 links; reset depth 6 / 7 | U1 to U5 |
| KV | kv3_hg | 8 / 32 | 0 | 6 of 8 | 6 of 8 | `kvs_hroot` bus 5 to 40 bits; 106 links, 4 variants; 25 straps; reset depth 6 / 7 / 8 | v1 .. v1p6 (6 types, 24 inst) first: U1, U3, U5 |
| KV | kv3_hgi | 11 / 32 | 0 | no (18 to 25 taps, union 91) | no | 146 links, 11 variants; 34 straps; ft 1,072 to 5,311 bits; reset depth 6 to 9 | U1 to U7 |
| KV | kv3_pv | 16 / 16 | 0 | no (24 to 36, union 185) | no | 62 buses in the union at 21,054 bits vs 15,622 largest (+35 %); 369 links; 85 straps | not one class: split into the 4 content sets first |

Why these three per die: they are the three largest classes on each die. S81 col h9_r1 and h9_r2 are added because they are larger than any superset class and need the least work; S81 station classes F00 / F01 are larger than the next leaf classes but all their members are signed.

### 10.3 Rows per plan lane

**S81-DIE-R3, J6 (cut 11-21 14:00 PST)**
1. col_h9_r1 and col_h9_r2 (120 types): U1 = every member takes the collector form with the union monitor links (h9_r1: 1 child; h9_r2: 2 children), unused ones tied (`cland_col_superset.py`, then `landing_tie_children.py`); U4 = reset outs 2 (r1) / 3 (r2) on all, depth 8 / 6. Taps, cores, buses already equal. Cost: about 700 flops on the die, 0 data cycles; reset release moves on the 51 + 44 plain tiles (inside the 64-clk hold; `bind_reset` re-proof). Expected after bind: 2 hash groups for 120 types.
2. leaf_F4500_00 (28 types): class row = t40__clf8bbdae1's floorplan and tap table + the F00 ft superset (N>S 597, 597, 276, 1; S>N 668, 668, 562, 1) + 58 links + straps at maximum + `strap_sid[3:0]`, `strap_k[2:0]`. Only if the t38 pilot routes. This is the slice-region re-pin of section 2.1 item 6.

**QC-PLAN-R3, V2 (cut 11-22 06:00 UTC)**
1. sle_ctl (7 types, 12 inst): union of the 99 links (5 children), reset outs 4, pad straps 31 on all. Taps and cores already equal. Expected: 7 -> 1 hash group.
2. slw_stm: unsigned members take the v1 row of `slw_stm_v1__cle34a73c3` (floorplan, 14 straps, 61 links); the 2 signed stay.
3. slw_fw: union row = v1 buses + the 4 v3-only buses (`ccm_wo`, `cct_wo`, `ccv_wo`, `ss_wo`) + 89 links; one tap table (4 sites).

**KV-D23-COMPOSE, D26 (cut 11-21 04:00Z) or D27**
1. kv3_hg v1 .. v1p6: `i_kvs_hroot_Q_o_cN` 35 / `o_` 30 on all six, links at the union (2 children), 25 straps, reset depth 8, the v1p6 floorplan and taps. Expected: 6 -> 1.
2. kv3_hgi: one row from v8 (25 taps, 25 cores, ft superset 6,441 bits is above v8's 5,311: check the faces first).
3. kv3_pv: no class row yet; split first.

### 10.4 Measured count within a day

The cheap path is 10.3 S81 row 1 and QC row 1: no floorplan or tap work, plan row edits only. After their bind, gen + synth of the members (no P&R) and `netlist_inherit.py summary` give the first measured hash-group count: target 120 + 7 types in 3 groups.

### 10.5 Not checked

- That bind emits one bound module when member rows are equal copies (U7); that member synthesis from an equal row is bit-stable without the rename step.
- Reset release re-proof on the plain col tiles (TYPEMERGE R3b called it medium risk).
- Whether `strap_cland_use` exists in `ot_dp_clk_landing` or needs RTL.
- QC and KV numbers are on N46R3 and D25f2, not on today's V0 / D25e3.
- The die clock can deliver one tap table to every instance of a class (U2) without the type root.

### 10.6 Landing-role check before J6 (COORD 11-20 02:4x, after the QC slw_fe pilot failed) -- corrects 10.2 to 10.4

Checked per member (V): landing pin set, die landing-network edges, start-tree role, reset shape, reader / writer start, tap table, whole plan row with names and ROM selectors removed (`roles.py`, plans S81 j4e and QC N46R3); count-aligned role, edge and pad from the sidecars (`count_aligned.parts`, S81 D8i `sidecar_new.json`, QC N46R3BQ); bound wrappers and reset trees of the strict-bound D8i tree.

| Class | Origin / relay role | Landing variants | Whole-row variants (members) | Bound wrapper variants | Merges on today's tools | Needs UNIFY-TOOLS for |
|---|---|---|---|---|---|---|
| S81 col_h9_r1 (60) | none: col parts are not count-aligned parts; S81 has 379 origins and 0 relays | 3: plain 51, collector 2 outs 8, collector 1 out 1 | 4 (51, 7, 1, 1) | 4 (51, 7, 1, 1), reset trees equal inside each | 60 -> 4 builds (ROM-only inheritance inside each variant) | 4 -> 1: spare monitor link (6 pins), reset outs at maximum |
| S81 col_h9_r2 (60) | none | 3: plain 44, 1 child 14, 2 children 2 | 8 (42, 6, 4, 3, 2, 1, 1, 1) on j4e | 7 (44, 6, 4, 3, 1, 1, 1) on D8i | 60 -> 7 or 8 builds | -> 1: spare monitor links (9 pins), reset outs, one relay / tap row |
| QC sle_ctl (7) | none: all 7 are origin, falling edge, pad 0, start role equal | 4 (3, 2, 1, 1): they differ only in `cland_dn_*_k` / `fclk_in_cland_dn_k` for k = 0..4, and in the reset relays that reader / writer start hang on | 6 (2 + five singles); pad maximum unset / 16 / 25 / 26 | not checked | 7 -> 6 now; 7 -> 4 after the V1 strap / pad union | 4 -> 1: spare cland dn links (15 pins), reset outs 0 / 2 / 4 |
| QC slw_stm (6) | DIFFERS: 4 origin, 2 relay (2 stages) | - | - | - | none across roles | origin / relay as a strap |
| QC slw_fw (6) | DIFFERS: 2 origin, 4 relay | - | - | - | none across roles | origin / relay as a strap, bus union |
| S81 leaf (75) | no relay; write edge differs (33 falling, 37 rising, 5 not count-aligned), already a strap (`strap_ca_efall`) | - | - | - | none (floorplans differ) | everything in 10.1 |

What this changes:
- **No origin / relay difference in col_h9_r1, col_h9_r2 or sle_ctl.** The QC failure mode (relay rx / tx pins) does not apply to them. It does apply to slw_stm and slw_fw.
- **Their one-class merge still needs UNIFY-TOOLS**, because the members differ in the number of monitor links and reset outs, and G0 / clock_landings refuse undeclared spare ends today (QC pilot).
- **On today's tools, col inheritance is already available inside each variant**: the bound wrappers of 51 col_h9_r1 types are text-equal once names and ROM instance strings are removed, and 44 of col_h9_r2 likewise. That is 120 types -> 11 or 12 builds with no plan change. SIGN-PROFILE read 0 because the existing kits come from different plans and synthesis runs; the test needs member kits generated from ONE tree with one recipe (gen + synth only), then `summary` / `prove`.
- Estimates: S81 col r1 + r2 **120 -> 11 or 12 today, -> 2 with UNIFY-TOOLS**. QC sle_ctl **7 -> 4 after V1 straps, -> 1 with UNIFY-TOOLS**. The "127 types in 3 hash groups" of 10.4 is the UNIFY-TOOLS figure, not a J6 / V2 figure on today's tools; today's figure is 127 -> 15 or 16.

Rows, corrected:
- **S81 J6, today's tools:** no plan row. Action: gen + synth every col_h9_r1 / r2 member from the J6 tree with one flow tag; sign one representative per variant (4 + 7 or 8); `prove` the rest. The first measured inherit count comes from this.
- **S81 J6 or J7, with UNIFY-TOOLS (schema spare ends + spare-lane bind check):** collector form with union monitor links on all (10.3 row 1).
- **QC V1:** strap / pad union on sle_ctl (already planned). **V2 with UNIFY-TOOLS:** spare dn links + reset outs. slw_stm / slw_fw wait for the origin / relay strap.

Not checked: sle_ctl bound wrappers (QC bind out not read); that synthesis of text-equal bound wrappers is bit-stable across member kits; col members on the J5 / J6 plan (rows read on j4e, wrappers on D8i).

### 10.7 Step-1 rows: one class each for S81 col_h9_r1, col_h9_r2 and QC sle_ctl (OWNER approved the merging tools 11-20)

Rows: `lanes/handoff/FABLE-SUPERSET-0415-step1-rows.json` (sha dd01e8c3deca, `step1_rows.py`). They are valid once UNIFY-TOOLS step 1 (schema spare ends + spare-lane bind) is on main. They are also that step's test inputs; the role and variant tables are in `FABLE-SUPERSET-0415-unify.json` (`role_rows`).

| Class | Class type (representative) | Union monitor children | Union reset outs | Depth | Member variants | Spare inputs tied (die total) | Outputs open (die total) |
|---|---|---|---|---|---|---|---|
| S81 col_h9_r1, 60 types | `col_h9_r1__t1__clf32cde8d__pvee46d7b8` | 3 sites (the representative has 1) | 3 (rep 2) | 8 | plain 51; collector with 1 child 9 | 513 pins | 316 |
| S81 col_h9_r2, 60 types | `col_h9_r2__t1__cl87f3ff59` | 4 sites (rep 2) | 4 (rep 3) | 6 | plain 44; 1 child 14; 2 children 2 | 666 | 324 |
| QC sle_ctl, 7 types / 12 inst | `sle_ctl__cla4f6f12f` | 5 (rep has all 5) | 4 (rep has all 4) | 7 | 0 / 2 / 3 / 5 children | 132 | 34 |

- **Correction to 10.2 / 10.3:** the col children sit at different pin sites on different members, so the union keyed by pin position is 3 (r1) and 4 (r2) children, not 1 and 2. The class row is the representative plus 2 added child sites and 1 added reset out. Each added child is 3 pins, one monitor band (320 flops, about 400 um2) and one pad chain; the outline is unchanged. `cland_col_superset.py` may fold sites within reach into one canonical site; then the count falls and the neighbour's up pin moves.
- sle_ctl needs no added site: the representative already has every child and reset out; the other six members only tie or open what they do not use.
- Per member the file gives: children used (union index), `strap_cland_use` bits, child index remap, the exact spare input pins, the open outputs, and the instances.
- The 51 + 44 plain col tiles take the collector form: all child inputs tied, `cland_up_*` and `fclk_out_cland_up` open, reset outs open. Reset release moves by the tree depth on those tiles (8 / 6 cycles, inside the 64-clk hold); `bind_reset` must re-prove it.

Rows for the lanes:
- **S81-DIE-R3 J6:** col_h9_r1 and col_h9_r2 each as ONE class from the file (member rows = class row + name + ROM selectors; spare ends per instance). Gate on step 1 being on main at the cut; if it is not, J6 takes the today's-tools path of 10.6 (inheritance inside each variant) and the one-class rows go to J7.
- **QC-PLAN-R3 V2:** sle_ctl as ONE class from the file, with the V1 strap / pad union already applied.

Expected after bind + member gen + synth: 3 hash groups for 127 types.

Review of UNIFY-TOOLS pushes (spec fit): none on main yet at 03:0x. Checks I will apply to each push: (1) spare ends are declared on the type row and per instance, never inferred; (2) a spare input is tied at the parent and appears in `bind_declared_ties.json`, no tie cell inside the type; (3) types without the key are byte-identical; (4) `type_pins` / G0 compare the full type pin table; (5) the three classes above bind to one module each with exactly the listed ties; (6) no outline or pin-window change on any member.

### 10.8 Review of UNIFY-TOOLS push 1a (main 975c3575d70) and a correction: the col / sle_ctl merge does not wait for it

**Review, spec fit (V, diff read):** FITS for buses and ft slots.
- Spare ends are declared: type key `superset` plus `partitions[].spare_ends`; an undeclared unbound end stays a G0 error; a spare end must be a declared end, must not be bound, needs the key; an ft slot is spare at both ends or neither. Matches U5 and the kit-rtl spare-lane form.
- Types without the key take the old path (the new check runs only under `superset`).
- G0 compares a superset type against the union pin table.
- Gaps to close in 1b: (A) the union table is built from instances that bind a pin; a bus that is spare on the FIRST instance gets its kit pins from the type window (gen_phys SUPERSET-1), so G0 should also compare bound pins against the type-window pins for every bus that is spare somewhere, or require type-declared geometry (`_geom_from`) on superset types. (B) a bus bound at a narrower width (KV hg 10 .. 35 bits) is not a spare end; it needs a declared spare bit range or stays out. (C) `spare_ends` names buses and ft slots only: landing pins and reset outs are not covered, and do not need to be (below).

**Correction (V):** the spare ends of col_h9_r1, col_h9_r2 and sle_ctl are landing monitor pins, and main already has their mechanism since 11-14: `clock.landing_contract.tieable_children` (CLAND-TIE-1 / 2). A declared child that an instance does not use is tied ready 1, fault 0, clock 0 at the die top (a neutral child, so no use strap is needed); `cland_up_*` may float on an instance outside the collector; the bind tie audit accepts exactly that set. The live plans carry 0 `tieable_children`: the 11-14 col delta was never applied.

Dry run on a private copy (epyc8 `/srv/opentallas-scratch2/claude/fable-superset-0415/colsup`, D8i plan + sidecar, `cland_col_superset.py --fam "col_h9_r[12]$"`): RC 0; col_h9_r1 60 types -> **1 identity** (union 3 children, 12 pins), col_h9_r2 60 -> **2 identities** (union 4 children, 15 pins); 81 plan edges and 27 sidecar edges re-indexed; no outliers. This is plan level only: no G0, bind or bind_reset was run on it.

So:
- **S81 J6 can take col_h9_r1 / r2 as one class each on today's tools**: run `cland_col_superset.py` on the J6 plan and sidecar, then G0, strict bind, `bind_reset`, LATCHECK. It does not depend on UNIFY-TOOLS. The step-1 rows file stays valid as the expected tie list (drop `strap_cland_use`: not needed).
- **QC V2 sle_ctl**: same mechanism, `tieable_children` = the 5 union children on every member, plus the V1 strap / pad union. `cland_col_superset.py` is written for col families; QC needs its `--fam` matching extended or the rows applied by a compose script. Still open for sle_ctl: reader / writer start hang on different reset relays per member (4 variants), which the class row must fix to the representative's.
- UNIFY-TOOLS step 1 is needed for data buses and ft slots (QC v1 / v2, S81 leaf), not for these three classes.
