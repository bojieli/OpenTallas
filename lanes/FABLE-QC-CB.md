# FABLE-QC-CB: QC cbn / cbx / cbf family (16 types) structural review

2026-11-14 22:36 PST, FABLE-QC-CB. Read: FABLE-TYPES-QC-EAST (cause C), FABLE-TYPES-QC-WEST, FABLE-CLOSURE-STRATEGY (section 3 item 1), handoffs TYPE-QCCOLLN, DIE-QC-103, QC-CORES-HEAD. Plan read: `zz_s29_qc103_s3r3b.json` (epyc9 tree6).

## 0. Verdict

Blockers 1 (GRT) and 2 (setup) are one defect, and it is in one generator file, not in the plan:
`tools/die_plan/core_input_chain.tcl` (OT_NK_CHAIN) spreads the stages of a tile-to-tile pipe along a route round the tile, but leaves the cells of the **head hop** (the polarity inverter after `r[0]` and its repair buffers) where global placement put them (line 161: "the head hop's buffers ... left where GPL put them"). For the one link per quad that leaves a margin-facing tile, those cells sit across the tile, so 514 bits cross the tile twice.

The mirror is not the fix. Mirroring t00 and t11 triples the nets that cross a tile (421 -> 1,357). Re-siting the head hop alone takes GRT overflow from 102,780 to 2,480 and the bus from 514 setup violations at -770 ps to 0 at +452 ps (what-ifs on copies, section 1). No re-facing, no plan event, no added cycle is needed for blockers 1 and 2.

Blocker 3 (hold) is a separate, smaller item with a second generator defect: the residue is the lock-up pair `u_pc_nk_* -> u_lk_nk_*` on two taps, and `core_input_anchor.tcl` anchors 0 of the 6,148 pipe registers.

## 1. Measured cause per blocker

All numbers below are MEASURED unless marked INFERENCE. What-if work dir: epyc2 `/srv/opentallas-scratch3/claude/fable-qc-cb/` (copies only; logs intel2 `~/fable-qc-cb/`).

### 1.1 The what-if outputs nobody read

Both TYPE-QCCOLLN place what-ifs finished: epyc2 `/srv/opentallas-scratch3/claude/type-qccolln/cbnq00/{asis,mir}/cbn_q00__cld7bf7197/run/results/asap7/dp_cbn_q00__cld7bf7197/base/3_place.odb` (20:42 and 20:34). `mir` = t00 MY and t11 R0.

Tile pin faces (LEF `qfd_tile_nk_a0c`, 457.92 x 1157.76): data on the W face in R0 (n_a, n_b in; t_out, n_y out; 2,056 M4 pins at local y 700-1103), taps on the E face (524 pins at y 561-675). M1-M5 fully blocked over the tile.

Links of cbn_q00 (traced on the placed database): na_i00, nb_i00 -> t00; t00.n_y -> y_o00; t00.t_out -D6-> t10.n_a; t10.t_out -D3-> t10.n_b; t10.n_y -D10-> t11.n_a; t01.t_out -D6-> t01.n_a; t01.n_y -D3-> t11.n_b; t11.t_out -D3-> t01.n_b; t11.n_y -> y_o11.

| metric (placed database) | as-is | mirror t00+t11 |
|---|---|---|
| nets with pins on both sides of a tile, level with it | 421 (414 over t11) | 1,357 (894 over t00, 451 over t11) |
| what they are | 408 = `u_d3_u_t_1_1_t_out` r[0] -> r[1] | 444 + 444 = xstn `tap_d` -> `u_pc_nk_*_tap` (tap face now on the margin); 447 = t00.n_y -> `u_ist_y_o00_0` (859-um unregistered hop) |
| nets with pin HPWL > 300 um | 1,188 | 1,967 |
| hop t11.t_out -> t01.n_b (q50) | 386-388 um x 3 | 46 um |
| hop t01.n_y -> t11.n_b (q50) | 382 um x 3 | 78 um |
| zero-logic register pairs on different taps (nearest-tap model, 55,723 pairs) | 41,700 | 40,761 |

GRT comparison: section 1.5.

### 1.2 Blocker 1, GRT overflow

- cbn_q00 cl622f65d2 a7 (epyc8), re-read: the 10,069 listed gcells belong to 839 nets. Each net runs from the tile pin face into the tile (t00: x 104 -> 405; t11: x 1147 -> 850) at the pin rows (local y 691-1111), capacity 0. No channel gcell is listed. So this is not channel capacity: it is a few hundred two-pin nets whose ends are on opposite sides of a tile.
- cbn_q11 cl49ae4555 a9 (epyc10): overflow 33,959 (M6 30,102); 9,974 of 10,145 gcells over t22, 515 nets. Placed database: 385 crossing nets = `u_d3_u_t_2_2_t_out` r[0] -> r[1].
- cbn_q01 clab6e67f2 a7 (epyc8), placed database: 164 crossing nets = `u_d3_u_t_1_2_t_out` r[0] -> r[1] over t12, and 441 = xstn `tap_d` -> `u_pc_nk_*_tap` over t13.
- cbx_q10 cl94a12200 a7 (epyc7): overflow 12,928; 4,959 of 7,489 gcells over t31, 697 over t21. No placed database left to trace the nets.

### 1.3 Blocker 2, setup

STA what-if on the as-is placed copy (ideal clocks, zero skew, kit RC table, TT):

| step | `u_d3_u_t_1_1_t_out` (1,542 endpoints) | every other transport family |
|---|---|---|
| as placed | 514 violations, WNS -770 | 0 violations; worst +80 (D10), +144 (lpad nb), +296 (D6 xstn), +379 (D3 t01.n_y), +534 (D6 t00.t_out) |
| + repeaters at 120 um on all nets (43,256 buffers) | 113 violations, WNS -180 | 0 |
| r[1] moved to the corner, inverter not moved | 514 violations, WNS -235 | 0 |
| **only the head-hop inverter moved onto the route (r[1] untouched) + repeaters 120 um** | **0 violations, WNS +452** | 0 |

So at zero skew the whole setup class of cbn_q00 is one stage of one bus: 514 endpoints, the hop r[0] -> r[1] of the D3 link t11.t_out -> t01.n_b. Its path is r[0] (east margin) -> inverter in the centre channel -> r[1] (top channel): the 1,622-ps arrival of the a7 report (two BUFx3 with 63-66 fF loads, slew 960-1,037 ps).

Same stage on the other quads: cbn_q11 a9 WNS -940 at `u_d3_u_t_2_2_t_out.r[0][304] -> r[1]`; cbn_q01 a7 WNS -1,099 with start `u_d3_u_t_1_2_t_out.r[0][155]`.

Why (read from the kit copy of `core_input_chain.tcl`): the hook log says `OT_NK_CHAIN chains 4112 ... stages_moved 19018 ... max_hop after p90 391 max 444`. It moves the stage flops and the buffers of every hop except the head hop (loop bound `min(llength hopb, n)`, comment at line 161). The head hop is r[0] -> r[1]; r[0] is FIRM at the tile pin; the inverter stays at the GPL location, which for a margin-facing tile with a centre sink is the other side of the tile.

The -775 / -821 / -923 "pre-route" numbers are all before any repeater pass: `SKIP_CTS_REPAIR_TIMING = 1`, and `OT_MAXWIRE_UM = 120` only acts after global route, which no cb kit has ever passed. Post-route setup of this family is unmeasured.

cbx is a different setup path: WNS -974 from `u_u_fab_u_x_3_1.u_st.sx[1]` through 22 buffers to `u_st.tap_d[463]`. INFERENCE: the xstn of t31 is split across the tile (same picture as the 441 tap nets measured on cbn_q01 t13).

### 1.4 Blocker 3, cross-tap hold

- cbn_q00 a7: before repair 12,507 endpoints, WNS -170; class cross_tap 10,862, port_out 1,597, same_tap 46. Tap means after balance 183-275 ps over 103 glue taps (8 outside +-20), spread inside one tap up to 98 ps; tile core taps 335 ps against target 250 (pin -483 + internal 818). Repair: 33,719 cells (10 %), 8,592 s, ends at -15.6 on 21.
- cbn_q11 a9: 11,620 endpoints before; 28,747 cells; residue -175 on 1,099. All 1,099 are `u_pc_nk_*_n_a/n_b.q -> u_lk_nk_*` (699 + 400), class cross_tap. The cbn_q00 residue (21) is the same pair on the tap bus.
- The mirror does not change this class (41,700 against 40,761 pairs in the model).
- The pipe register sits 40-405 um from its latch (as-is placement: t00.n_b q50 405 um, t11.n_a 112-270 um). `core_input_anchor.tcl` is meant to anchor both at the pin, but its log says `OT_NK_ANCHOR latches 6148 pipe_regs 0`. Read from the code: the walk back from the latch D stops at the first cell whose name lacks `u_pc_nk_`, and the QN inverter between register and latch is an anonymous `_NNN_` cell, so no pipe register is ever anchored. INFERENCE: that is why the pair lands on two taps (pair affinity reach is 64 um).

### 1.5 GRT comparison

Same script and router image on each copy, placed database (no CTS, no hold cells; the clock is one unbuffered net in all three), `-allow_congestion`, 5 extra iterations. `fix` = the as-is placement with only the 514 head-hop chains of `u_d3_u_t_1_1_t_out` re-sited in the east margin (3,857 cells moved, nothing else).

| form | total overflow | M6 | M8 | crossing nets | where |
|---|---|---|---|---|---|
| as-is | 102,780 | 80,308 | 21,511 | 421 | 9,844 of 10,000 listed gcells over t11, 520 nets (408 anonymous head-hop nets) |
| fix (head hop re-sited) | 2,480 | 1,587 | 756 | 13 | t11 1,200 gcells / 10 nets, t01 866 / 12, t00 234 / 33 |
| mirror t00 + t11 | not finished at 22:35 (iteration 5 of 5, slower than both) | | | 1,357 | |

The as-is number reproduces the wave failure (a7: 90,044 = M6 79,067 + M8 10,886) from the placed database alone, so CTS and hold cells are not the cause. Re-siting one hop of one bus removes 97.6 % of it.

What is left in `fix` (2,480) is a second, small class: 6 port -> `u_cland_nb_i00` nets over t11, 6 port -> `u_cland_rsf_i` nets over t01, and `bc_i00_q` (18 nets) over t00. Not traced; it needs its own look once the main class is gone (INFERENCE: clock-landing input nets whose ring cells sit across a tile).

Still running at 22:35, same dir: the 30-iteration runs `asis/`, `mir/`, `fix/` (iterations 22, 15 and 19) and `mir5/`. Totals are the `Total` line of each `grt.log`; `python3 -I cong.py <dir>/congestion.rpt` gives the per-tile split.

## 2. Structural fix for the whole family

No plan rows, macro placement, pin faces, layer grant or core split change for blockers 1 and 2.

1. **CB-HEADHOP (generator, 0 cycles, all 16 types and every other QC type with `core_input_place`).** In `tools/die_plan/core_input_chain.tcl`, place the head-hop cells too: when every cell of the head hop has one load, put them on the same routed polyline between the head and stage 1 (the loop that already does this for the other hops). Keep the shared-load exception only where the head really has more than one load. Add the count to the `OT_NK_CHAIN` line (`head_hop_cells_moved`).
2. **CB-CROSS check (kit preflight, advisory -> error once 1 is in).** After the hook: count signal nets with pins on both sides of a hard core and level with it (`conn6.py` in the what-if dir is the reference, 40 s). Today: cbn_q00 421, cbn_q11 414, cbn_q01 635. Target: only the port -> clock-landing nets (13 on cbn_q00).
3. **CB-XSTN (generator, 0 cycles; INFERENCE until proven).** The xstn of a tile whose tap face is on the margin must sit at that tap face, so `tap_d -> u_pc_nk_*_tap` does not cross the tile (441 nets on cbn_q01 t13; cbx t31). The D6 `a_d` pipe between xstns already has the stages to go round. Do not flip tiles to cure this: every flip moves the same problem to the other face.
4. **CB-LOCKUP (generator, 0 cycles).** In `tools/die_plan/core_input_anchor.tcl`, follow the latch D back through buffer / inverter cells by cell type, not by name, until the `u_pc_nk_*` flop, and anchor it (`pipe_regs` must equal the latch count, 6,148 here). The pair is then 6 um apart and falls under the existing tap pair affinity. Expected to remove the hold residue (1,099 on cbn_q11, 21 on cbn_q00); INFERENCE until the proof.
5. **Plan, DIE-QC-103, S4c, small:** cbn_q11 / cbf_q11 bus y_o23 has no station and a planned 831-um hop from the centre face of t23 to the W face (plan census; not seen in a build by me). Give it 2 FIRM stations over the top of t23 like y_o21 has on cbx. Core tap early offset 483 -> 568 ps is the kit's own warning (effective 335 against 250); take it in the same event if R-CLOCK agrees.
6. **Not to do:** the t00 + t11 mirror (S3R4 form); allow-congestion relaunches; any cycle added to the D3 links (they close at +452 once the inverter is on the route).

Other buses checked on cbn_q00 and fine as planned: na_i00 / nb_i00 / y_o00 stations (+144 to +700 ps at zero skew), y_o11 (+714).

## 3. One-build proof and owner

Build: `cbn_q00__cld7bf7197`, as-is orientation, TYPE-QCCOLLN's as-is copy on epyc2, with the patched `core_input_chain.tcl` and `core_input_anchor.tcl`, from global placement to GRT (no bind, no plan change; about 2.5 h).

Pass, all four:
1. crossing nets (`conn6.py` on `3_place.odb`) <= 20;
2. `u_d3_u_t_1_1_t_out` 0 setup violations at CTS; family WNS reported with the repeater pass, not before it;
3. GRT overflow under 3,000 with allow-congestion on the first pass (102,780 today), and the residual nets listed; GRT-0116 gone once the small clock-landing class of 1.5 is handled;
4. `OT_NK_ANCHOR pipe_regs` = latches; pre-GRT hold residue 0 on `u_pc_nk_* -> u_lk_nk_*`; cross-tap endpoints and hold cells reported against 10,862 / 33,719.

Owners: TYPE-QCCOLLN writes the patch (branch + READY to the merge lane, test: a two-tile fixture whose head-hop inverter starts across the tile) and runs the proof; then the same patch on cbn_q11 cl49ae4555 and cbn_q01 clab6e67f2 (their D3 head hops, 385 and 164 nets). DIE-QC-103 takes item 5 into S4c. CB-XSTN proof: cbn_q01 clab6e67f2 (441 tap nets -> 0), same lane, after the first proof. The 9 cb wave routes now running unchanged cannot pass; hold them until the patch is in the wave source.

## 4. What is inference

- That the t00 share of the a7 overflow (4,857 gcells) has the same cause: on the cld7bf7197 placement only 1 net crosses t00; a7 is another cohort and its placed database was not traced.
- cbx: xstn split as the cause of both its overflow over t31 and the -974 path.
- cbf types: same plan structure as cbn per quad (plan read), no cbf build traced.
- Hold: that the unanchored pipe register is why the lock-up pair is on two taps, and that anchoring it clears the residue.
- GRT numbers in 1.5 come from the placed database after 5 iterations; they compare forms, they are not sign-off overflow. The mirror GRT total is missing; its verdict rests on the crossing-net count and hop lengths.
- The what-ifs move cells by hand on a copy. The patched hook itself has not run.
