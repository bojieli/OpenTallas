# FABLE-PD-S81-0830 (2026-11-21 08:15 PST): is S81 J7 close-by-construction?

Reviewer: FABLE-PD-S81-0830 (Fable). Read and analyse only. Nothing built, cancelled, patched or signalled. Three small static jobs via ot-run on epyc10 (units 503492, 676537, 1064216).
Marking: **V** = I computed or read it this round. **R** = reported by the named lane. **I** = inferred.
Plans read: J6 base `s81-j6/candC1n_pf` 44be6051; J7b `j7/v2/out/plan.json` 07c4124c; J7 v3 `j7/v3/out/plan.json` d245f293 (J7b + x2 t2_payload + u_cf MX, built 07:44).
Tools: main a9ed808a98 (contains 8bc23a5a90) from my lane clone `epyc10 fable-pd-s81-0830/repo`. Outputs: `epyc10 /srv/opentallas-scratch2/claude/fable-pd-s81-0830/{base,j7,v3}/{pre,pp}`, scripts in the same dir and my scratchpad.

## 0. Verdict

**The col / gunit / strap / FT rows already in J7b are close-by-construction at plan level and can go. Four of the listed row sets are not, and each fails for a measured reason: leaf re-grid, t5 v1f, u_cf MX without its re-solve, and the lepe_mu_C split with the xg move.** bk_sel and the serdes split have no J7 rows at all.

| Check | J6 base | J7 | Result |
|---|---|---|---|
| place_precheck OVERLAP / KNEE / MACRO (V, 395 types) | 0 | 0 | no placement guard will trip on a J7b row |
| place_precheck STATIONCORE (V) | 302 | 301 | all inherited; 0 on a new family |
| precheck findings new in J7 (V) | - | 0 | REACH over 300: 3,395 -> 2,585 |
| precheck REACH over 405 (V, worst bit of the pin window) | 333 | 333 | J7 fixes none and adds none (leaf 276, lepe/lepw C 20, kv_leaf 11, slice_station 9 max 501.9, svc 8, serdes 7) |
| relay_depth rows with path / (D + 1) over 405 (V) | 385 (col_h10 85, col_h9_r0 300) | 144 (col_h10 0) | mkdepth405 works; the 144 left are the xo D3 rows, which carry `stages_existing: 2`, so 6 hops, max 370 |
| precheck TAP-CAP, planned sinks per tap over 1,000 (V) | 32 types | 31 | unchanged: leaf t31 2,335, slice_station t45 1,936, serdes t3 1,373, t4 1,299 |
| col `tap_max_sinks` (V) | 3,000 on 216 types | 3,000 on 216 | no J7 row |
| G0 with tap-net sink inventory (8bc23a5a90) on v3 | - | not obtained | my run (unit 1064216) crashed after 20 min in the census step: I passed the plan from `j7/v3/out`, outside a tree, so `census/s81_lanes.tsv` was not found. No tap-net or street numbers from me; read them from the candJ7c gate G0 |

**Addendum 08:20 PST: the J7b gate failed at strict bind (exit 11, 6 errors, V).** `landing_local_resets: bad or duplicate name` on leaf t23 (`fstart_1`), t70 (`fstart_1`), t72 (`fstart_3`), plus 3 follow-on `LF_CS_DEPTH ... no bound module file` on the same types. In the v3 plan these are the only 3 types with a duplicate name: same name, raw reset and consumers, sites 20 to 28 um apart (t23 x 1,420.5 and 1,440.7). The leaf local-reset delta and the C3g FSTART delta each add the row. v3 has the same rows, so it fails the same way. S81-J6-ASSEMBLY-R4 has the cause and is rebuilding (v4 / v5). No LF_CS_DEPTH on kv_leaf appeared, so the vp_sr delta itself binds on kv_leaf; item 2 stands for the t5 row only. LATCHECK, G0 and PRE were not reached.

Limits of this review: plan-level only. No J7 kit is placed, so "placed-hop 405" is a plan read plus the lanes' placed reads (R). No J7 tree has a G0 or LATCHECK result yet.

## 1. Leaf re-grid (72 types, +1 ho on 11): will fail if stacked on J7 (V)

- rg3 (`fable-fix-s81-leaf-r5/rg3/plan_rg_ls.json`) is built on the J6 base 44be6051, not on J7.
- It moves the 16 `u_vp.g_ln[*]` lane cores per type. On t39: g_ln[5] x 764.6 -> 1,179.4 (415 um), g_ln[2] y 717 -> 955.
- J7 re-sites the same rows. On the 79 leaf / kv_leaf types both plans change `regs_um` on **9,211 `internal_stations` rows** (120 to 153 per type), 975 `relay_sites` keys on 56 types and the `clock` key on 60 types. J7 changes them through vp_sr, leaf keys, reach1, FSTART and local resets, all sited against the old core positions.
- Overlay of rg3 cores on J7 sites, 73 types (the 79 types rg3 changes, minus the 6 held back):

| J7 site class | sites | inside an rg3 core |
|---|---|---|
| station registers on rows J7 re-sited | 25,092 | **6,342 (25 %)**; 19 against the old cores |
| relay sites J7 changed | 1,275 | 352 |
| clock / reset sites J7 added (landing_writer_start, landing_local_resets, reset_tree_anchor) | 2,824 | 114 |
| rows whose last J7 register to the moved capture pin is over 405 um | 8,443 rows with a moved target | **1,181 on 62 types, max 1,032 um** (t8 g_ln[8]; was 160) |

- All 73 types have sites inside moved cores. Worst: t46 227, t43 202, t66 184.
- So a 3-way merge either refuses (both sides changed the row) or keeps J7 sites under the new cores. Detailed placement then moves the flops off the cores and the routes cross them: the STATIONCORE and flat-GRT class.
- The +1 ho stage on 11 types is a class-depth change. The same class just failed bind on t5 (section 2).
- **Fix (FABLE-FIX-S81-LEAF-R5):** regenerate on the J7 plan d245f293, as a SUPERSEDE of the vp_sr / reach1 / leaf-key / local-reset / landing rows of each type (re-grid first, then re-solve those against the new cores), one delta with its `verilog_defines` ops. Check with the overlay script `leaf3.py` (0 sites in cores, 0 last hops over 405) before the 72-type bind.
- **For J7:** out. The t39 private proof continues. Rows are a J8 item unless the regenerated delta and its bind exist before the cutoff.

## 2. t5 v1f (kv_leaf t5): bind error, define missing (V)

- `candMISC2` gate died rc 11 at 07:35: `LF_CS_DEPTH ot_s81sl_kv_leaf__t5 ho: plan 2 stage(s) (deepest row), bound RTL 1`, 1 error (`fam-s81-misc/gate_misc2.log`).
- J7 v3 carries `OT_S81SL_VP_SRAMREG` on 75 of 75 leaf types and on **0 of 5 kv_leaf types** (all five have only `OT_S81_VN_CONST_ZERO`). J7 changes `internal_stations` on 4 kv_leaf types.
- **Fix (FAM-S81-MISC-R2):** `vp_sr_t5_resited_v1` goes in only as one delta with the `verilog_defines` op for kv_leaf t5 (vp_sr RTL and ho stage), after vp_sr in the step order. candMISC3 is the gate for it (R, running).
- **Watch (S81-J6-ASSEMBLY-R4):** read the J7b bind for `LF_CS_DEPTH` on kv_leaf t1 / t3 / t4 / t5 first. If it appears there, the vp_sr delta itself lacks the kv_leaf defines.
- Plan hops over 405 on t5 stay: `leafdn_i0` hop 0 at 422.6 and 412.3 (window worst bit, V).

## 3. u_cf MX on 12 types: right move, but v3 has it without the station re-solve (V)

- v3 `steps.txt` applies the MX delta after the four col GENs. Only `orient` changes. Every stored coordinate is still the R0 one: p4 `bus:ret_o0` `from_um` y 449.292 is the R0 south face.
- Static tools read the stored coordinates. v3 precheck on the 12 types gives the same 126 rows as J7b (diff empty), so neither G0 nor PRE will see the item.
- Pin faces from `inputs/core_pins/dsfd_cfifo_crs4.json`, R0: north = xa 283, xb 266, x2 536, ri 66, cc 15, st 2, rs, cr. South = xl0-3 4 x 276, rd 70, xk 4, cr_s. Macro 280.8 x 69.12, obstructed to M5.

| Leg (bits) | types | R0 | MX | |
|---|---|---|---|---|
| x_i0 pad stage -> u_cf.xl0 (276), p1 | 6 | 436 worst / 371 best | 367 / 302 | better |
| xa / xb <-> u_t0 (283 + 266) | 12 | 243 / 270 path (plan row) | about 69 shorter (I) | better; removes the body crossing behind the 26 M5 shorts (R H10-R2) |
| **u_cf.rd -> ret_o0 E face, no station row (70), p1** | 6 | 374 / 358 | **443 / 427** | all 70 bits over 405, and round the macro |
| **u_cf.rd -> ret_o0 station hop 0 (70), p4** | 6 | 393 stored, 411 / 395 by pin | **480 / 464** | over 405 |
| u_cf.rs -> frame_int_o0 first station (1) | 12 | 490 (p1), 367 (p4) | 559, 436 | 1 bit, buffered leg; over the 550 CBC limit on p1 |

- Not measured: peers of ri (66), cc (15), st (2), x2 (536), which also move north -> south. H10-R2 should read them on pvcc166a6d the way it read xa / xb / xl.
- **Fix (FAM-S81-COL-H10-R2, then S81-J6-ASSEMBLY-R4):** one `j6_donor_delta.v1` on d245f293 with (a) ret_o0: a station at the NE corner of u_cf on p1 and a re-sited hop 0 on p4 (+1 cycle on the ret lane, lanefix from LATCHECK); (b) frame_int_o0 `from_um` and first station for rs; (c) regenerated `from_um` / `to_um` on every u_cf-pin row. Order: MX, then this delta, then gate.
- **Rule for the cutoff:** MX and its re-solve go in together or not at all. MX alone swaps 26 shorts for a 70-bit leg over 405 on all 12 types. The waveC proof kit (rep pvb095fa2f, preflight PASS 07:33, R) must reach a routed read of ret_o0.

## 4. lepe_mu_C t1 split and the xg move: no row can carry it, and +90 um collides (V)

- The plan has 10 hard cores on this type (u_cap, u_xr, 3 eg, 5 xf) and **no xg macro**. The 37 xg memories are kit-placed, so "move the xg macro block" is not a plan op today.
- Rigid shift of the 37 placed macros (`fam-lepe/split_C/C_place.tsv`) against the J7 hard cores:

| shift (x, y) um | macros on a hard core | macros inside the 130-um band |
|---|---|---|
| 0, 0 | 1 (xf.g_cp[0]) | 10 |
| +90, +90 | **13**: u_cap 4, xf.g_cp[0] 6, xf.g_cp[1] 2, u_xr 1 | 0 |
| +90, 0 | 5 | 7 |
| 0, +90 | 12 | 3 |

- The claimed room is not there: u_cap starts at y 760.3 and the memory stack already reaches y 724 to 967; xf.g_cp[0] starts at x 466.6 and the stack reaches x 475 to 647.
- No macro is nearer the outline than x 90.6 / y 65.6. A strip of 65 um on S and 90 um on W clears all 37 macros with no move.
- Caveat: the placed kit is plan 224567138ab; one macro already overlaps g_cp[0] at zero shift, so core origins differ a little from J7. Repeat on a J7-plan placement.
- The split itself is a proposal: not bound, not gated, and bind has no strip / body sub-tile schema (R FAM-S81-LEPE-2). The type is 499,795 non-tap cells at place (R), over 400k.
- **Fix (FAM-S81-LEPE-3):** drop LC-G1 as written; use strip depth 65 um S / 90 um W on the macro faces. **For J7:** out. The lepe rows J7 does carry (f0_q v2, LP relay rows) are unaffected.

## 5. Other row sets

| Row set | Evidence | For J7 |
|---|---|---|
| col RDX / rom_pval / depth405 / xalign / xo D3 (216 types) | 0 new static findings (V). xo: 6 hops <= 370 um on 36 types, path lengths are the p2 rep values used for p1 / p4 / p5 (I). Proofs: h9_r0 bind2 kit BIND / LAT green and routing; h10_r2 rep J5 sign-off TT -99.84 is the RDX class these rows target (R) | go |
| h9_r1 / h9_r2 relay-branch rows (360 + 360) | rep bind green, LATCHECK 873 / 873, 0 cycles (R). **Not in v3 steps (V).** They must sit after mkdepth405 and before mkxalign, because mkxalign reads the kept list. The rep kit has no placed read yet: run-item ended 07:13 with no result.json and was relaunched (R) | add as a GEN in that slot, not as a late DELTA (S81-J6-ASSEMBLY-R4, FAM-S81-COL-R4) |
| x2 t2_payload branch copy (6 p4 types) | in v3; proven J5 + row strict + LAT (R) | go |
| gunit landing_reader_start | one op, depth 14, stage pitch about 318 um (V); gate PASS on a C1n copy (R) | go |
| bk_sel | J7 v3 changes only local resets and the reset anchor on bk_sel__t2 (V). R6 rows not handed; sk1 runs died rc 11 / 13 at 07:38 / 07:41 (R) | no rows until the place_r6 hop read |
| serdes enc / dec split | not bound; v3 changes only local resets on 6 serdes types (V). t4 is 407,738 cells (R); private t4 kit launched 07:45 (R) | out unless bound and past place |
| leaf local resets (52), t40 / t45 straps, FT v3, q-pair, south strip | in J7b; 0 new static findings (V) | go, on the J7b gate result |

## 6. Not fixed by J7 (V unless marked)

- Cell cap: lepe_mu_C t1 499,795; c1x_C t9 480,720, t3 477k, t6 503k; serdes t4 407,738; kv_leaf t2 never synthesised, part B about 9.3M by census (all R). J7 has no split row for any of them, so these types cannot sign on J7.
- 333 plan hops over 405 (window worst bit), unchanged.
- Tap caps: 31 types over 1,000 planned sinks per tap, unchanged; col still at 3,000 on 216 types. J7 has no tap row. slice_station t45 gets its strap row in J7 but keeps 5 taps at 1,600 to 1,936.
- Inherited STATIONCORE on col: col_h10_r0_p1 ft2-ft5 (3 of 70 bit routes cross the ROM cores, 24 rows), col_h9_r0_p1 / p2 (24 rows).
- lepe_mu_C t1: 5 of 39 station register sites and 1 of 50 taps lie inside placed xg macros at the current placement.
- Tap sink caps per tap net and street / channel capacity under the added stations: not measured by me (G0 run failed, see section 0). The planned-sink estimate above is the only tap number here.

## 7. Ranked fix list

| # | Fix | Owner |
|---|---|---|
| 1 | Keep the leaf re-grid out of J7 as a stacked delta. Regenerate on d245f293 as a SUPERSEDE with re-solved vp_sr / reach1 / keys / resets and define ops; prove with the core-overlay count = 0 | FABLE-FIX-S81-LEAF-R5 |
| 2 | u_cf MX only together with the ret_o0 / rs / stored-coordinate re-solve delta; otherwise pull the MX step from v3 | FAM-S81-COL-H10-R2, S81-J6-ASSEMBLY-R4 |
| 3 | t5 v1f only with the kv_leaf `verilog_defines` op; read J7b bind for LF_CS_DEPTH on kv_leaf | FAM-S81-MISC-R2, S81-J6-ASSEMBLY-R4 |
| 0 | Leaf local resets vs FSTART: take the local-reset delta as a replace per name on t23 / t70 / t72 (one row per name), rebuild, and check 0 duplicate names in the plan before the gate (`dup.py`) | S81-J6-ASSEMBLY-R4 |
| 4 | Insert the h9_r1 / h9_r2 relay-branch rows between mkdepth405 and mkxalign and rebuild (candJ7c) | S81-J6-ASSEMBLY-R4, FAM-S81-COL-R4 |
| 5 | lepe_mu_C: replace the +90 um move by 65 / 90 um strip depth; split rows to J8 with the c1x_C sub-tile schema | FAM-S81-LEPE-3, FAM-S81-SLICE-R4 |
| 6 | Read ri / cc / st / x2 peers of u_cf on the routed pvcc166a6d before the MX re-solve is frozen | FAM-S81-COL-H10-R2 |
| 7 | xo D3: confirm the p1 / p4 / p5 hop sums on a placed read (p1 max 1,709 R) | FAM-S81-COL-H9R0-R2 |
| 8 | col taps at 3,000 and the 31 over-cap types: bank taps of 1,000 as a private proof, rows next event | FAM-S81-COL-R4 |
| 9 | bk_sel rows after the place_r6 hop read; serdes split after bind + place | S81-BKSEL-R6, FAM-S81-SERDES-R4 |
| 10 | Gate hygiene: `python3 -I` ignores PYTHONDONTWRITEBYTECODE, so gate.sh writes `tools/die_plan/__pycache__` into candidate trees (candJ7b, 15:47Z, nlink 2). Add `-B` | S81-J6-ASSEMBLY-R4 |

## 8. Stop list (do not put into J7)

1. Leaf re-grid rows on the 72 types and the +1 ho stage on 11 types, in their rg3 form.
2. `vp_sr_t5_resited_v1` without its define op.
3. u_cf MX without the re-solve delta.
4. lepe_mu_C t1 strip / body split and any xg +90 um move.
5. serdes enc / dec core split while unbound.
6. bk_sel R6 rows before the place read.
7. xo D2 and the kv_leaf t2 x = 1684.80 cut (already stopped).
8. Relay-branch rows as a DELTA after mkxalign.
