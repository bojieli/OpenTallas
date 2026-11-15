# FABLE-PD-QC-0300: QC cb family, ring -> fabric distance and the bco hop

2026-11-15 03:15 PST, FABLE-PD-QC. Technical PD only. Read: FABLE-TRIAGE-QC (section 6, CLAND-BIN post), FABLE-QC-CB, FABLE-CLOSURE-STRATEGY section 3, the DIE-QC-103 and CLAND-BIN queue lines.

MEASURED = read by me tonight from a database, RTL, plan or log. INFERENCE is marked.
Work dir (read-only runs, nothing of a lane changed): epyc9 `/srv/opentallas-scratch2/claude/fable-pd-qc-0300/` (`geo_g2.log`, `hop_g2.log`, `bc_spans_s4k.tsv`).

## 0. Decisions

1. **Both questions are one defect, and it is larger than the two hops.** Every bc crossing between two cb types has 5 bound stages against 6 as built, and 3 of the 5 are the landing ring, which sits at one point. Two registers are left to carry the corridor word from one tile tap to the next, and the tap is 633 to 1,184 um inside the type from either face. All 24 bc buses of the family have this, not only bc_i02 / bc_i12 and bc_o03 / bc_o13.
2. **There is no 0-net trade for it.** No pad stage can come off: the bc lanes carry no pad, and the pads on the tree legs are distance stations already at 311-399 um per hop. The correct form is stations as net cycles, **the same count on all four columns of a crossing class**. That form balances by the code with column pads unchanged.
3. **cbf_q01 itself needs no plan change.** Its ring -> tap span is 642-704 um and it has one free register (`u_bin`). Sited at the equal-hop point, both hops are 321-352 um.
4. **G2 as built (capture register beside the ring) is not a default.** Make it opt-in now. It becomes default-on in the equal-hop form (section 3).
5. **S4k passed and is not held for any of this.** Build S4p, S4q and S4r over S4k in parallel (section 4).

## 1. What was measured

### 1.1 cbf_q01, G2 placement (CLAND-BIN proof, `3_place.odb`)

`hopq.py` on the whole type, 49,157 zero-logic hops, 4,246 over 405 um:

| source -> sink | hops | over 405 | max um | cause |
|---|---|---|---|---|
| `u_bin_bc_i*` -> `u_fab_u_x_*_2.u_st` | 1,792 | 1,784 | 850 | this review |
| `u_d6_*_a_d.q` -> `u_fab_u_x_*_3.u_st` | 1,034 | 762 | 1,296 | d6 chain not spread to the tap of the row-3 tile |
| `u_d*_u_t_*_n_y` chain | 11,822 | 517 | 907 | chain spreader |
| `u_r8b_strap_r8pad_*_n_b_in_f` chain | 1,028 | 514 | 628 | crosses a tile (514) |
| `u_d6_*_a_d` chain | 4,128 | 229 | 697 | chain spreader |
| `y_o12` stations (2 hop classes) | 1,028 | 375 | 468 | plan station pitch 388.8 um |
| other | | 65 | 620 | |

So 1,784 of the 4,246 belong to the ring question. The other 2,462 are chain siting and station pitch.

Positions (um, type frame). Tiles: t02, t03, t12 are MY (tap on the W face), t13 is R0 (tap on the E face, x 1149).

| bus | ring flops | `u_bin` (G2) | tap register `t_q` | ring -> tap |
|---|---|---|---|---|
| bc_i02 | x 24-73, y 20-37 | max 9 um from ring | x 67-78, y 630-708 (tile tap pins x 86.4, y 630-729) | 642-699 |
| bc_i12 | x 596-684, y 19-29 | max 4 um | x 648-685, y 627-710 (pins x 691.2) | 657-704 |
| nb_i12 | x 1167-1218, y 2434-2523 | max 12 um | first lane station y 2186 | 247-392, none over 405 |

The count rose from 1,024 to 1,784 because `u_bin` drives two register banks, so each long bit is counted twice (section 1.2).

### 1.2 The column station RTL (kit `rtl/ot_qfd_xslice.sv`, module `ot_qfd_xcst`)

- Two banks load the corridor input in parallel: `b_q` (516 bits, drives `a_d` to the next station) and `t_q` (380 bits, drives the tile tap pins).
- `b_q` is not a pure forward bank. 137 of its bits (`xl` 128, `tag` 8, GO) feed the tag compare and the `cap` / `hold` registers, and `hold` drives the other 128 tap pins.
- So `b_q` cannot leave the tap by siting. Correction to FABLE-TRIAGE-QC verdict (d): the tap copy `t_q` already exists; what ties the station to the tap is these 137 bits.

### 1.3 The lane (bind logs)

- `bind_s29q103S4K2R.log`: `c16_E0_0.u_fab.u_x_0_0.b_d <- c16_E0_1.u_fab.u_x_0_3.a_d`: as-built 6, table 5, S4k2 bound 7. Today's 5 stages are `u_bout` + ring 3 + `u_bin`. No pad.
- S4KR: BIND_RC=0, LATCHECK 1921/1921 PASS, G0 2 errors (baseline). `param_regen.json`: column pads [0,0,0,0] on both sides of all 12 slices, SKEW_S 7-8, SKEW_N 6 (range 3..27).

### 1.4 Tap <-> port span of every bc bus (plan S4k, tile origin and orientation, port window)

Tap y is 610.7 um above the tile origin; tap x is the W face for MY and the E face for R0. Span is Manhattan, which is the real route round the tile. Cross-check: cbf_q01 bc_i02 717 / bc_i12 700 against 642-704 measured; cbn_q01 bc_o13 1,103 against TYPE-QCCB-GEN's 460-970 with a floating station.

| bus kind | tile | buses | span um | hops today | hop today |
|---|---|---|---|---|---|
| bc_i | MY | cbf/cbn_q01 i02, i12; cbx_q10 i20; cbn_q00 i00 | 696-761 | 2 (`u_bin` free) | 348-380 at the equal-hop point |
| bc_i | R0 | cbf_q00 i00, i10; cbf/cbn_q11 i22, i32; cbn_q00 i10; cbx_q10 i30 | 1,077-1,184 | 2 | 538-592 |
| bc_o | MY | cbf_q00 o01, o11; cbn_q00 o01, o11; cbn_q01 o03; cbn_q11 o23; cbx_q10 o21 | 633-723 | 1 (`b_q` at the tap) | 633-723 |
| bc_o | R0 | cbn_q01 o13; cbn_q11 o33; cbx_q10 o31 | 1,103-1,112 | 1 | 1,103-1,112 |

Full table per type: `bc_spans_s4k.tsv`. Not covered: cbf_q00_s2 and cbf_q01_s2 (1 instance each, other tile naming); DIE-QC-103 computes those from the pins.

INFERENCE: only cbf_q01 (bc_i) and cbn_q01 (bc_o) were seen in a placed database. The other rows are plan geometry.

## 2. (a) The plan form

### 2.1 Why no pad comes off

- bc lanes: 5 stages, none is a pad.
- Tree legs: `nb_i00` in the q00 types has 7 lane stations over 2,790 um (hops 354-363); `na_i00` 4 over 1,843 um (311-389); `nb_i12` went 4 -> 3 in S4k and is at 411-418. The y_o23 trade used the only slack there was.

### 2.2 Why S4k2 failed, and what balances (read from `qc_fabric_transport.py`)

Start shift of a tile = sum of the bc crossing shifts on its column, plus one pad per column that the near and the far cluster share.

| crossing class | lanes | shift reaches |
|---|---|---|
| A: head -> near row 0 | bc_i00, i10 (cbn_q00), i20, i30 (cbx_q10) | every tile, near and far |
| B: near row 1 -> row 2 | bc_o01/11/21/31 -> bc_i02/12/22/32 | near rows 2-3, all of far |
| C: near row 3 -> far row 0 | bc_o03/13/23/33 -> bc_i00/10/20/30 | all of far |
| D: far row 1 -> row 2 | as B, far types | far rows 2-3 |

- S4k2 put +2 on C for columns 0 and 1 only. The far cluster then has columns {0,1} two later than {2,3}; the near cluster does not. One pad per column, shared, cannot serve both. Hence PARAM_REGEN at any pad limit. The half that was missing is bc_o23 / bc_o33 (cbn_q11), which have the same hop (633 and 1,112 um).
- **C or A with the same count on all four columns: balanced with pads unchanged.** The far root moves; SKEW_S / SKEW_N take it (+d on C).
- **B or D with the same count on all four columns: rows 2-3 move against rows 0-1.** The level-4 join at `u_t_0_0` then needs the same count on its `n_a` leg (`u_t_2_2.n_y -> u_t_0_0.n_a`, bus `na_i00` in cbn_q00 and cbf_q00). That is a paired change, not a single-leg change.
- Correction to FABLE-TRIAGE-QC section 6, last line: a column pad does not absorb a shift that reaches only the far cluster.

### 2.3 The family rule

**Every bc_o bus: 2 FIRM stations. Every bc_i bus: 1 FIRM station, and `u_bin` sited as a station. `na_i00`: +3.**

| | hops after | hop um |
|---|---|---|
| bc_o, MY tile | 3 | 211-241 |
| bc_o, R0 tile | 3 | 368-371 (about 385 on the channel centre lines) |
| bc_i, MY tile | 3 | 232-254 |
| bc_i, R0 tile | 3 | 359-395 |

- Lane cycles: A +1, B +3, C +3, D +3. Near root +4, far root +10. SKEW +6: S 13-14, N 12, inside 3..27. HI_PAD unchanged (both sides move alike).
- Flops: about 496 k for the bc stations (40 stations x 517 bits x 24 slice sides) and 74 k for `na_i00`. Pad flops today 1,337,969. G0 density decides.
- cbx_q10 serves near and far, so its bc_i count must be the same in A and C, and its bc_o count the same in B and D. The rule above satisfies this.

## 3. (b) G2

- As built it is a relocation: 1,024 -> 1,784 long hops, worst 721 -> 850 um, type total 3,583 -> 4,246. It also pins a FIRM register at the wrong end of the span.
- **Now: opt-in (`OT_CLAND_BIN=1`).**
- **Default-on in this form (CLAND-BIN):** `u_bin` is station 0 of the chain ring -> anchored load. Anchored load = the first FIRM flop or hard-core pin reached forward through at most two unplaced register ranks. For bc_i that is the tile `tap` pin behind `t_q`; for nb_i12 it is lane station r[0]. With k plan stations on the bus, `u_bin` and the stations take the equal-hop points L(j+1)/(k+2), the rule `face_flops.tcl` already uses for ft slots. If the hop is still over 405 um, print the span and leave the count to the plan.
- Expected on cbf_q01 (computed from the G2 database, not a placed run): 1,784 -> 0, hops 321-352. Proof: one place-only run of cbf_q01, same census.
- Same rule on S81 c1x_C__t1 (1,924 of 2,004 hops).

## 4. (c) Delta for DIE-QC-103

Adopt S4k now. Then three nested variants over S4k, bound in parallel; adopt the largest that passes (bind 0 errors, R8 changed 0 after the pinned derive, LATCHECK, G0 baseline only).

| variant | delta over the one before | types | expected |
|---|---|---|---|
| **S4p** | 2 FIRM stations on bc_o03, bc_o13 (as S4k2) **and** on bc_o23, bc_o33 | cbn_q01 x3, cbn_q11 x2 | C +2 on 96 lanes (bound 5 -> 7); column pads stay 0; SKEW_S 9-10, SKEW_N 8 |
| **S4q** | 1 FIRM station on every bc_i of the q00 / q10 types: bc_i00, bc_i10, bc_i20, bc_i30 | cbn_q00 x3, cbf_q00 x3, cbx_q10 x4 | A +1, C +3; SKEW_S 10-11, SKEW_N 9 |
| **S4r** | 2 FIRM stations on bc_o01, bc_o11, bc_o21, bc_o31; 1 on bc_i02, bc_i12, bc_i22, bc_i32; `na_i00` 4 -> 7 stations | cbn_q00 x3, cbf_q00 x3, cbx_q10 x4; cbn_q01 x3, cbf_q01 x2, cbn_q11 x2, cbf_q11 | B +3, D +3; near root +4, far root +10; SKEW_S 13-14, SKEW_N 12 |

Station sites:
- On the route, not on the straight line. S4k2's bc_o13 sites (993.6, 2125.4) and (829.4, 2332.8) are inside `u_t13` (x 691.2-1149.1, y 1304.6-2462.4). For an R0 tile go up the E margin and along the top channel: about (1192, 2300) and (1007, 2500) for bc_o13; same form for bc_o33 and bc_o31.
- bc_i with an R0 tile: along the S channel, then up the channel at the tap face.
- bc_i stations sit between the ring and `u_bin` in the count; with G2 opt-in the kit places `u_bin` by global placement until the equal-hop form is in.

If S4p passes and S4q or S4r does not, post the PARAM_REGEN line; the failing join names the class.

## 5. (d) Stop list

1. No cycles on a subset of the four columns of a bc crossing class (S4g, S4i, S4k2 form). No more bind time on S4k2.
2. No search for a pad stage to pair with bc stations. There is none (section 2.1).
3. No `MAX_COLUMN_PAD` raise.
4. No G2 beside the ring as a default, on any die.
5. No siting of the column station at the tap face as the fix for a bus that leaves the type, and no siting of `b_q` away from the tap: 137 of its bits feed the tap logic.
6. No RTL split of `b_q` now. A local 137-bit copy would save the bc_o stations later; it does not remove the bc_i need on R0 tiles (538-592 um).
7. No tile mirror and no bc port move for this.
8. No plan stations for the d6 pipe. In cbf_q01 it has the stages but is not spread to the row-3 tap (762 hops, max 1,296 um): TYPE-QCCB-GEN, generator.
9. No hold on S4k adoption.

## 6. Owners

| item | lane |
|---|---|
| Adopt S4k; build S4p, S4q, S4r; s2 type spans | DIE-QC-103 |
| G2 opt-in now; equal-hop form and the cbf_q01 proof | CLAND-BIN |
| d6 chain to the row-3 tap (cbf_q01, check cbn_q01) | TYPE-QCCB-GEN |
