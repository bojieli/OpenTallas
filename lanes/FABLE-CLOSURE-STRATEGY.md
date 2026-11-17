# FABLE-CLOSURE-STRATEGY 2026-11-17 13:20 PST (1320): delta on 11:20

Reviewer: FABLE-CLOSURE-STRATEGY-1320 (Fable). Read-only, no jobs launched. Technical PD only. HBM parked.
Blocking gates: DRC 0, routed TT setup >= -42 ps, internal reg-to-reg FF hold >= 0 (port hold advisory), die bind + LATCHECK.

Marking: **V** = I opened the log or file this round. **R** = reported by the named lane, not opened. **P** = my proposal, not measured.

## 0. Headline

1. **The S81 serdes 509 ps pair skew is a setup risk at route, not a hold risk (V).** It is the worst `clk`-group setup path of H17: `u_enc.p_d[*]` on tap `clk_t42` (18 buffer levels, 629 ps local insertion) into `u_txl.g_reg.r[0][*]` on tap `clk_t20` (11 levels, 359 ps, source latency -53), no shared clock path. Slack at global route is +17.9 ps on a 473 ps data path with 7 buffers and 1 inverter. With the sd9f shift (+12 % routed data delay) it lands near -39, at the gate.
2. **H17 will very likely fail routed TT in the `u_dec.u_syn` class (P, from V numbers).** That class is already at -27.17 at global route (39 ends). It is the same module family that read -73 routed in HEAD sd9f. The fix exists and is proven: the sd9f capture-skew ECO. It is not a flow tool yet.
3. **No family-wide GRT derate.** One measured case, in one saturated blob. Use a targeted form (section 3).
4. **QC and HEAD have no open timing or route failure.** Both are waiting for plan events that no kit has been built on. QC's 117 open types have 0 routed results on the current plan family: the risk there is unmeasured, not known.
5. **The serdes base DB fails `check_power_grid` on VDD before any ECO (V).** The PG notch check cannot be accepted on pass / fail; it needs a before / after difference.

## 1. Evidence I opened

| item | host, path | result |
|---|---|---|
| H17 pair skew | epyc9 `fable-fix-s81-serdes2/H17/serdes__t13/gen/serdes__t13/{grt_policy.json, postcts_gate_TT.log}` | `PAIR_max worst 509.42 signed -509.42 launch u_enc.p_d[328] capture u_txl.g_reg.r[0][328] crpr 0`. Path report for bit 528: launch clock `clk_t42` 629.42 ps at the flop, capture `clk_t20` 833 - 53 + 359.12; data 472.8 ps (7 buffers + 1 inverter); slack +17.89 MET. Hold pair 442.9 is `u_prx` macro -> `u_rxf_q` negedge flop |
| H17 worst setup | same `postcts_gate_TT.log` | `SDC_WNS_MAX -27.17, SDC_NVIOL_MAX 39`: `u_dec.u_syn.am_ok` -> `u_dec.u_syn.xs[0][9]`, clock `io_pma_rck`, capture clock arrival 3,142 ps (tree index to level 12), CRPR 71.11. Same log: TT-corner `SDC_WNS_MIN -0.07` on 2 ends (class not read) |
| H17 route | same kit, `5_2_route.tmp.log` (13:12) | Hook line: 236 bad rows, 97 guides on 92 nets moved, 308 connectors. Iteration 0 ends at 98,858 violations; iteration 1 at 30 %, no DRT-0255 |
| H17 hold probe | epyc9 `drtx/ffhold_H17/ffhold.log` | Lowest reg-to-reg ends listed are positive (0.24 ps on `u_dec.u_lpl_6_r.o[451]` -> `u_cmem/wd_in[451]`), `FFH_DONE` |
| Serdes ECO hooks | epyc9 `drtx/E1/eco.log` | `OT_PAD_IN_DIRECT 544 macro_pin input pads reconnected (1557 buffers removed)`; `OT_PG_PIN_NOTCH 6430 block signal pins, 44 with a PG stripe at their access; 44 boxes notched, 44 PG vias removed`; `ECO_DONE` |
| Serdes PG check | epyc9 `drtx/pgchk_base/pgchk.log`, `pgchk_E1/pgchk.log` | Base (no ECO): over 1,000 `PSM-0039` unconnected `PHY_EDGE_ROW_*_Left` cells at x 4.37 um and over 1,000 `PSM-0038` unconnected VDD M1 shapes at x 29.3 um, then `PSM-0069 Check connectivity failed on VDD`. E1 check still running, no verdict |
| KV hroot | intel2 `autopilot/kit_wave_state.json` row `kv3_hroot` (12:44) | `OT_CLAND no legal nonoverlapping row/site in reserved band for u_cland_raw_fs_o_kvs_hroot_Q_o_emb_0 (literal-local-reset): 2 cells reserve 0.9 um2 > band upper bound 0.0 um2` |
| S81 kv_leaf | intel2 `autopilot/kit_wave/s81_ot_s81sl_kv_leaf__t1_b0c01c0901d50/a3/place.log` (12:58) | `MPL-0041 Couldn't place u_bound.u_u_vp_u_b0. Found overlap with other macros: u_bound.u_u_vp_g_ln_9_u_l` |
| Wave rows | intel2 `kit_wave_state.json` (13:07), `tools/failure_breakdown.py` (13:10) | Current-event rows. QC L2: 63 rows = 27 enqueued, 26 FAIL kit_rtl, 3 route-held, 2 FAIL gen, 1 MPL-0034, 1 src_manifest, 2 running, 1 cancelled. HEAD NF15d2r1: 11 enqueued, 0 running. KV HG5: 10 running, 3 FAIL. S81: 106 FAIL kit_rtl, 82 FAIL kit_snap, 5 route-held |
| QC st_a / sc_v3 | same state file | `slw_st_a_v1__clfc5867a6__pvf82a6c28` MPL-0034 (unchanged). `sle_sc_v3`, `slw_sc_v3`: gen `ValueError: macro qfd_dv_s5_sc2_leaf_dn0 / up0 is instantiated with parameters but no RTL header was found` |

Not opened: the r586 frame output, the sd9f sign-off report, the D6x / D7x builds, the D20 gate, the N1B publish gate, the corridor hybrid, the lep_pair K28 run, any hub_Wi stat.

## 2. Levers, ranked by types unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | D6x applied; col released with a TT margin read | 203 col types (78 held now), plus the non-col rows failing on tree tools | S81-DIE-R3, S81-TYPES-R3 |
| 2 | QC | one tree (M5 + N1B + main tools) applied, then N2; one pilot per family to sign-off | 117 open types | FABLE-FIX-QC-N, QC-PLAN-R3, QC-TYPES-R3 |
| 3 | KV | D20 applied; hroot band; hub_C and hub_Wi shells | 50 open types | FABLE-FIX-KV-HG, KV-HUBC-SPLIT |
| 4 | S81 | D7x strip re-slot, t22 to GRT | 20 flagged types, then the 75 leaf types | S81-DIE-R3, FABLE-FIX-S81-STRIP, S81-TYPES-R3 |
| 5 | S81 | serdes: DRC 0 by the two ECO hooks, then the routed TT form | 11 serdes types | FABLE-FIX-S81-SERDES2 |
| 6 | all | capture-skew ECO as a flow tool; r586 frame line read on every kit | every type that passes GRT and fails routed TT | new lane CAPSKEW-ECO |
| 7 | HEAD | NF15f: hybrid relay rects, lep_pair K28, then the two kits | hd_lep0N, hd_mesh | FABLE-FIX-HEAD-CORRIDOR, HEAD-PLAN-R4, HEAD-TYPES-R4 |

### Lever 1. S81 col and D6x (203 types)

Evidence. pg3 SIGNED: TT -39.22, internal hold 0, 110 port ends advisory (R, S81-TYPES-R3 13:00). The 78 col items carry all four knobs and are held for `d6b-applied` (R). D6x / D7x build on main 53e4ff86 tools (R). `kv_leaf__t1` dies in macro placement on the SRAM / lane-core overlap that D6x moves (V).
Root cause of the remaining risk: pg3 passes TT with 2.8 ps to spare. It is one member of 78, and the other members differ in cl / pv.
Fix.
1. S81-DIE-R3: apply D6x. Acceptance already defined (col `config.mk` proof, `hold_sdc_guard.tcl` in every kit). Add `kv_leaf__t1` and `__t3` place to the D6x kit list: the SRAM move has no placed proof yet.
2. S81-TYPES-R3: on the first three D6x col kits, read the `OT_GRT_FRAMES` sign-off-frame TT at global route before they route. pg3's own GRT frame number is the reference (not opened; take it from the pg3 kit). If a member reads more than 10 ps below pg3's GRT number, repair TT at GRT on that member before route rather than after.
3. Do not add a col-wide margin: one signed member and no failing member.

### Lever 2. QC (117 types)

What the 117 are blocked on, technically (V rows, R causes):
- **Plan events not applied.** The live tree is D4 / L2. M5, N1B and N2 are bound but not applied. 18 cb types need the lockup rows of N1B (bind PASS: 68 pads, 68 x W(507), 0 x W(508), LATCHECK 1921 / 1921, R). 11 st_a types and the st_b rows need the N2 `HI_PAD` hold; 2 st_a types need the core move (R).
- **26 rows FAIL at kit_rtl** on filelist paths outside the tree (V). The M5-line `gen_phys.py` carries the fix (R, FABLE-FIX-QC-N 11:46). Tree content, not design.
- **3 route-held** on plan terms: `sle_ctl__cl67434795` 222,508 cells, `slw_hc0__cl4f54b7a3` 350,812 cells, `slw_st_a_v2__clf4365a62` (shared `rst_xn` reset-ring proof) (V).
- **2 gen failures**: `sle_sc_v3`, `slw_sc_v3`, parameterised macro without an RTL header (V). New since 11:20, unowned.
- **0 rows have a CTS, GRT, route or timing failure.** No QC type has routed on M5 or later.
Fix.
1. FABLE-FIX-QC-N and QC-PLAN-R3: one apply. `s4q9n1b_d2` (M5 + N1B + main tools, gate running) and M5T are two trees for the same step. Apply d2 only; M5T is its link base, not a second apply.
2. QC-TYPES-R3: the three cb pilots (`cbn_q01__clab6e67f2`, `cbn_q11__cl49ae4555`, `cbn_q00__cl622f65d2`) at once after apply, acceptance at the four `tap[0]` pins on the routed DB. Unchanged from 11:20 and still not run.
3. QC-TYPES-R3: in the same wave, the first kit of each family that has no signed member on this plan goes to sign-off with the r586 frame line read. `slw_hc0` at 351k cells and `sle_ctl` at 223k are the two closest to the 400k limit: read their GRT per-layer overflow first.
4. QC-PLAN-R3: `sc_v3` header: add the `qfd_dv_s5_sc2_leaf_dn0 / up0` headers to the kit file list in N2. Check the other `sc` types with the same grep.
5. N2 after N1B: `HI_PAD` hold, `r8_strap_pad_max 31`, st_a move (2 types).

### Lever 3. KV (50 types)

Evidence. D20 = D19 + main tools, gating (R). D19 PC dry GEN failed at kit_rtl: leaf modules `qkd_kvs_pcc`, `qkd_kvs_pcf` without a source, so the 20 station rows are still unexercised (R). hub_C: 6 ring masters SIGNED (R). `kv3_hroot` fails place on a zero-area reset band (V).
Fix.
1. FABLE-FIX-KV-HG: apply D20 on gate PASS. Read the first wave GEN of a PC type (`kit_istations`) before the PC family routes.
2. FABLE-FIX-KV-HG: `kv3_hroot`: the reserved band of `u_cland_raw_fs_o_kvs_hroot_Q_o_emb_0` has 0.0 um2 for its 2 literal-local-reset cells. Run the same band check on the D20 plan for all `*_emb_*` rings of hroot before apply. If the band is zero there too, it is a plan row (band height or the reset cells moved into the ring band), not a kit retry.
3. KV-HUBC-SPLIT: hub_C shell about 275k mapped is under the limit (R). hub_Wi is not sized: 692k - 247k leaves 445k before the `qkd_hr_*` internals. Do not launch the Wi shell until the hierarchical number exists. Yosys `stat` segfaults on the hierarchy: count cells per module from the synthesised netlist (`grep -c` of instance lines per module, or `stat` per module on a flattened copy of that module only).
4. If the Wi shell is still over 400k: rings 100 to 249 bits next (about 150k on hub_C, R), then the largest `qkd_hr_*` child as a core.
5. The 6 ring masters' reset-port hold (-27 to -35) is advisory at the master; the parent shell kit must show it closed at its own reset relay. Read it on the first shell kit.

### Lever 4. S81 strip (20 types)

Unchanged from 11:20 except the tree: D7x. t22 first to GRT from D7x with no early stop (2.175 -> 0.457 is still a model number). The four route-held leaf kits (t28, t43, t47, t8) on the old slots stay held; their GRT overflow read is still the only calibration available before D7x and has not been taken.

### Lever 5. S81 serdes (11 types)

Evidence. Guide move passes iteration 1; the proof ended at 607 (R). Hooks written: 544 pads reconnected, 44 PG notches (V). Base DB fails PG connectivity (V). Pair skew and worst setup (V, headline 1 and 2).
Root causes.
- 544 shorts: `buffer_ports` puts an input buffer between a die pin and the PMA macro pin it sits on (R).
- 63 at dchn: die M5 VDD stripe resumes 0.096 um above the macro edge beside `cw_q` pins; M6 pair over `clk` / `rst_n` pins (R).
- Pair skew: `clk_t42` reaches `u_enc.p_d` through 18 levels, with repeater chains of 5, 3 and 3 buffers at levels 1 to 3. The tap pin is far from its sinks. The policy insertion bound is 250 +/- 40 ps; the type-level insertion check is not run (`insertion_bound None`).
Fix (FABLE-FIX-S81-SERDES2).
1. PG notch acceptance: difference of the unconnected set, E1 against base, restricted to the 44 notched boxes. The base fails on its own west edge (x 4.4 to 29.4 um), so `PSM-0069` alone says nothing. Report the west-edge rails to S81-DIE-R3 as an advisory PG item; it is outside the four gates.
2. Pad reconnect: after `OT_PAD_IN_DIRECT`, re-read hold on the 544 `io_pma_rx` ends (1,557 buffers left the paths). Advisory if port-start.
3. H17 when routed: census TT by class. Expect `u_syn` under -42 and `p_d -> txl.r[0]` near -40.
   - `u_syn`: capture-skew ECO (sd9f list builder, same module family).
   - `p_d -> txl.r[0]`: delay the capture clock of the `r[0]` flops by 40 to 60 ps. Hold on this pair has more than 300 ps of clock room (launch is the late side). Check `r[0] -> r[1]` setup room per flop first.
4. For the other 10 types, before they are generated: move the `u_enc.p_d` sinks to the tap that clocks `u_txl` (or a tap inside the encoder plate), so both ends share a tree. Print per-tap insertion at CTS; a tap over 290 ps TT is the signal. 0 cycles.
5. Family default at GRT: `OT_HOLD_FF_MARGIN_PS 10` (H17 enters route with +0.12).

### Lever 6. Routed-data gap (all dies)

Section 3. Owner: new lane CAPSKEW-ECO (Sonnet), starting from epyc7 `fable-fix-head-sd9f/{us_eco.tcl, mk_eco_list.py, census.py, us_guides.py}` (R).

### Lever 7. HEAD (hd_lep0N, hd_mesh)

What they are blocked on, technically: nothing has failed. Neither type has been generated on NF15f. Open inputs (R):
- Relay rects: rs7 carries the g1e column-centre rects (4,295 unassigned, cut 0.903, 4 rects on macros, 32 on reserved sites). The bit-slice-column candidate reads 367 / 0 reach-bad / cut 0.801; the hybrid is in the allocator.
- `ot_s81hd_lep_pair` KCRED 28 rebuild and re-sign (launched 12:22).
- NF15f clock census (labels, strap values), reset seam timing, production token calendar.
Fix.
1. FABLE-FIX-HEAD-CORRIDOR: hybrid to 0 unassigned, then the stage-rect patch on rs7. Acceptance unchanged.
2. HEAD-TYPES-R4: the tree that generates hd_lep0N must carry r597 (`CLKSITE-TAP-ESCAPE`): tap pins under reserved clock sites would repeat the sd9f tap failure on a new type.
3. HEAD-TYPES-R4: hd_lep0N first to GRT with no early stop; read per-layer overflow in the y 665 to 846 relay channel (59,089 nets at a model cut of 0.80). This is the first physical test of the corridor model.
4. The 11 rows enqueued on NF15d2r1 include `hd_mesh`: NF15f changes its geometry. It stays held.

## 3. Does the GRT-to-route gap need a family-wide derate?

No.
- **What is measured (R, sd9f).** ORFS number +89; sign-off frame on the GRT DB -16; routed -106. The first 105 ps is the frame (r586 prints it). The second 90 ps is data delay: 789 -> 881 ps on the worst path, +12 %, clock equal on both sides, in the saturated encoder blob.
- **Why not family-wide.** One design, one blob. col pg3 signed at -39.22 and the six KV ring masters at +75 to +146 with no derate. A flat +12 % on every signal net would cost every unsaturated type setup repair cells it does not need.
- **What to do (P).**
  1. Scope by measurement: on the GRT DB, take the paths whose nets cross gcells over 90 % used. Print, next to the r586 frame line, `routed_risk = frame WNS - 0.12 x data wire delay` of those paths. Advisory, no gate.
  2. Where `routed_risk` is under -42, repair TT at GRT with that margin on those endpoints only (serdes encoder / syndrome plates on S81 and HEAD are the known members).
  3. Post-route fallback, automatic like the internal hold ECO: capture-skew ECO with the sd9f limits (per flop: launch-side setup room and FF hold room checked, no existing cell moved, route-only). sd9f: 309 delay cells + 43 hold pads, -105.88 -> -20.79, DRC 0.
  4. Calibrate: every signed type from now on logs frame-at-GRT and routed TT. Revisit a derate only if three unrelated families show the same +10 % or more.

## 4. Stop list (changes; the 11:20 list otherwise stands)

1. S81 serdes: accepting the PG notch on a `check_power_grid` pass / fail; another CTS + GRT restart of H17 for hold margin; GRT-level pair-row blocks (measured not to work); generating the other 10 types before the `p_d` tap fix.
2. All: a family-wide or fleet-wide GRT derate; route ECO rounds on a type whose route is clean and whose timing is not.
3. QC: applying both M5T and N1B d2; a cb kit before the apply; treating the 26 kit_rtl rows as design failures.
4. KV: launching the hub_Wi shell on the 445k estimate; a `kv3_hroot` retry on the same band; publishing D19.
5. HEAD: capacity levers on the corridor (cut widening, extra layer pair, bus serialising); any hd_lep0N or hd_mesh kit on NF15d2r1 or on rs7's g1e rects.
6. S81: releasing a held col kit generated from D5e; routing the four held leaf kits on the old slots.

## 5. Corrections to my 11:20 claims

1. **Lever 8 root cause was wrong for sd9f.** I said the GRT read differs from sign-off by SDC frame. The frame explains +89 -> -16. The -16 -> -106 step is routed data delay. They are two gaps of about the same size, and r586 addresses only the first.
2. **Lever 6 (sd9f): both of my fixes were unnecessary.** I proposed a tap regroup or +1 register stage. The lane closed it with per-flop capture skew, 0 cycles, TT -20.79. My cause (cross-tap window plus transport buffers) was incomplete: the clock cancels.
3. **Lever 5 item 2 (GRT pair-row blockage as the family form): rejected by measurement.** Both GRT-level blocks leave 216 to 306 pair-row segments. The guide move is the form.
4. **Lever 5 item 3: -25.58 was not a violation.** It is +0.12 less the 25 ps policy uncertainty.
5. **Lever 2: "D19 is ready to publish" was wrong.** Its tools were pin-old and its PC dry GEN failed at kit_rtl. D20 replaces it. Item 4 (regenerate the adp abstract with M6 / M7 detail) had the direction reversed: the generator default is M6 only; the stage had passed M7.
6. **Lever 1: "take main tools at or after r584" was too narrow.** D6b did exactly that and was superseded: 21 die-tool merges were missing (FABLE-FLOW-1300). D6x on main 53e4ff86 is the form.
7. **Lever 3: "check the other 10 st_a types" found 2 types, not 11.** My account of the 12 nm (track offset on a flush origin) was not checked; the fix moved the core 8.64 um and an SRAM with it. I also missed `cbn_q00__cldbcda913 cl_nb_i00`, 38.9 um outside the core.
8. **Lever 7: "last 367 nets" described the candidate, not rs7.** rs7 has 4,295 unassigned on the g1e rects.

## 6. Not checked

- The routed TT of H17: the -39 and the `u_syn` failure are projections from sd9f's +12 %, not measurements.
- Whether the `p_d -> txl.r[0]` path at +17.9 is the worst of its bus or only the worst reported; I read one path, not the class.
- The cause of the west-edge PG failure on the serdes base DB, and whether other S81 types share it.
- pg3's GRT frame number, so the col margin in lever 1 item 2 has no reference value yet.
- Knob names for a GRT TT repair margin; none verified in main.
- Whether the hroot zero band exists on D20.
- QC family list by signed / unsigned; I read rows, not the plan type table.
