# TYPE-REDUCTION-CENSUS-1119 (PRECHECK-1119, COORD/owner priority 11-19)

Tool: `type_census.py` (epyc9 /srv/opentallas-scratch2/claude/precheck-1119/work, goes to main as tools/precheck/type_census.py).
Records: same dir, census_{s81,qc,kv,head}.json. Read-only; plans and binds are the live kit_wave ones at 00:4x PST:
S81 plan_h2_2249 (D8e live tree, bind native_bind/out), QC N4.2 (zz_s29_qc103_s4q9n42, bind S4Q9N42BR), KV D24c (plan_c, bind_of_record),
HEAD NF15f source_plan (script mode, no bind -> RTL column empty). D8f/D8g, N4.3 and D25 change rows, not the type list, so the counts carry.

Definitions:
- family = type name before the first `__t<N>` / `__cl<hash>` / `__pv<hash>`.
- distinct RTL = sha of the bind's rtl/<type>.sv after stripping comments, the type name, position suffixes and parameter default values (ID straps).
- RTL mod ROM = the same, also with the ROM macro `.INSTANCE("...")` / `.VIAMAP` strings stripped (ROM content = per-position macro, same LEF).
- logic = plan `contents` modules + params + non-cland hard core modules (cland = clock-landing bands, counted as station infrastructure).
- estimate = distinct (logic, outline up to 90-degree rotation): one canonical pin template per logic, position-specific relays/FT moved to the
  streets, clock taps re-derived per template, mirrored/rotated views reused. It is a lower bound: it assumes the street can take every relay.

## Totals

| die | types | instances | distinct RTL | RTL mod ROM | distinct logic | estimate |
|---|---|---|---|---|---|---|
| S81 | 395 | 398 | 278 | 112 | 41 | 51 |
| QC | 133 | 377 | 130 | 130 | 71 | 73 |
| KV | 56 | 160 | 56 | 56 | 51 | 51 |
| HEAD | 26 | 358 | n/a (no bind) | n/a | 26 (25 by modules) | ~11 + 15 station types |
| sum | 610 | | | | 189 | ~186 |

## S81 (395 -> ~51)

| family | types | RTL | RTL mod ROM | logic | outlines | est | types sharing logic differ in |
|---|---|---|---|---|---|---|---|
| ot_s81sl_leaf | 75 | 14 | 14 | 1 | 5 | 5 | pins, faces, stations, taps, cores, outline, orient |
| col_h9_r1 | 60 | 60 | 7 | 1 | 1 | 1 | ROM INSTANCE strings + orient only (plan pins/stations/taps identical) |
| col_h9_r2 | 60 | 60 | 10 | 1 | 1 | 1 | same as col_h9_r1 |
| slice_station | 46 | 20 | 20 | 2 | 5 | 6 | stations, taps, outline, orient |
| col_h10_r1, col_h10_r2, col_h9_r0_p2..p6 | 12 each | 12 | 1-6 | 1 | 1 | 1 each | ROM INSTANCE + orient (p2: core placement too) |
| col_h10_r0_p1/p4, col_h9_r0_p1/p4 | 6 each | 6 | 2-3 | 1 | 1 | 1 each | ROM INSTANCE + orient |
| serdes | 11 (14 inst) | 5 | 5 | 1 | 1 | 1 | pins, faces, stations, taps, cores, orient |
| dsdv_slice_c1x_C | 9 | 1 | 1 | 1 | 1 | 1 | plan pins/stations/taps/cores only; bound RTL already identical |
| svc_lo/hi_dsdv_svc_rs | 7 / 6 | 1 / 1 | | 2 / 1 | 1 / 2 | 2 / 2 | faces, pins, stations, taps |
| ot_s81sl_kv_leaf | 5 | 1 | 1 | 2 | 3 | 3 | pins, stations, taps, cores, outline |
| 20 singleton families (dsdv_slice_*, phy, gunit, seqhost, eng, iqf, bk_sel, ...) | 21 | | | | | 21 | |

Reading: the S81 type count is almost entirely position variance, not logic. 41 logic designs make 395 types.
- The 216 col types (col_h9_*/col_h10_*) are 7 logic designs. Their plan geometry is identical inside each family; the bound RTL differs only by the
  ROM instance name (which ROM content macro sits in the slot) and orientation. A col type with the ROM macro as a black-box view of one LEF
  (content bound at die level) gives 216 -> 7..9 types with no plan change.
- The 75 leaves are one logic design in 5 outlines; they differ in faces/pins, landed FT stations, clock taps and core placement. A canonical pin
  template per outline (pins fixed, lane order handled in the street) plus street relays gives 75 -> 5.
- slice_station 46 -> ~6, serdes 11 -> 1, dsdv_slice_c1x_C 9 -> 1 (RTL already one hash; only plan geometry differs).

## QC (133 -> ~73)

68 families; 39 have 2-7 types. Inside a family the logic is one design (except st_a_v1/v2 and slw_st_a_v1, 2 each), the outline is one, and the
plan pins are identical. What differs is the `__cl<hash>` clock-contract variant in the bound wrapper: clock tap port set (clk_t5/t7/t76 vs
clk_t13/t80/t14), clock landing roles (cland_rstart vs cland_tstart), reset exports (rst_o_N), and the R8 pad straps (strap_r8pad_* inputs present
or not). cbx_q10/cbn_q00/st_a/st_b/stm also differ in stations, taps or core placement.
Reduction: one clock-contract template per family (taps named by role, not die tap index; R8 pads always present as tied straps; reset exports always
present) gives 133 -> ~73 with no logic change. Further: the v1/v2 families (sle_st_a_v1/v2, slw_fw_v1/v2, sle_stm_v1/v2, ...) are separate logic
by name; whether v1 and v2 can merge needs an RTL read (not counted).

## KV (56 -> ~51)

51 families, almost all singletons (kv3_hg_v1p2..p6, kv3_hgi_v1..v8, kv3_pv_v*). Only kv3_pc_v1 (3), kv3_pc, kv3_hgi_v1, kv3_hgi_v2 (2 each) share
logic, and they differ by orientation and the same clock-contract wrapper items as QC (R8 pad straps, rst_o/start_o exports, cland dn ports).
The KV count is logic variance, not position variance: the hg/hgi/pv `_vN`/`_v1pN` variants are separately generated logic. A real cut there is an
RTL decision (merge variants into one parameterised design), not a plan template. Template-only estimate 56 -> 51.

## HEAD (26 types, 358 instances; already reduced)

hd_tile 264 instances = 1 type, hd_serdes 12 = 1, hd_turn_a/b 12 each. 11 types carry logic (hd_spn and hd_spn_end share modules ot_s81hd_spo/spr
and differ only in params -> 10 logic). 15 types are pure station/shim/turn types with no contents (hd_st_*, hd_turn_a/b, hd_spn_[ew]shim_[rt]x,
hd_ctl_e/n, hd_host_n, hd_mesh_e): if their relays move to the streets they are not types at all, giving ~11; if they stay as abutted station
types, 26 stays.

## What the numbers say

1. S81 is the big lever: 395 -> ~51 (-87 %). Two moves: (a) ROM content out of the type identity (col families, -200 types, no plan change);
   (b) canonical leaf pin template + street relays (leaf 75 -> 5, slice_station 46 -> 6).
2. QC: -60 types from one clock-contract template per family (tap ports by role, R8 straps always present, uniform reset exports).
3. KV: no template lever; the variants are logic. Reduction needs an RTL merge of the hg/hgi/pv variants.
4. HEAD is already instance-reduced; the 15 station types are the only further cut.
Caveat: the estimate is a lower bound. It does not price the street capacity for the moved relays or whether one tap template can meet the
450 ps landing on every position; those are the precheck checks 3 and 4 that follow.
