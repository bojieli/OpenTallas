# FABLE-PD-QC-S4q8: r199 review-before-adopt of QC events S4q6e and S4q8 (LPC 40 select replication)

2026-11-15 23:15 PST, FABLE-FIX-QC-HCFE. Nothing in DIE-QC-103's tree or in any kit was changed. Jobs run by me (ot-run,
kits mounted read-only): three STA sessions and one repair experiment, outputs on the build hosts under
`/srv/opentallas-scratch2/claude/fable-fix-qc-hcfe/` (hc2_s3r and hc2_e1 on epyc10, fe1_s3r on intel1, hc1_grt on epyc8).
MEASURED = read or computed by me tonight. INFERENCE is marked.
Subjects: epyc9 die-qc-103/treeA plan_of_record `zz_s29_qc103_s4q6e.json`, `zz_s29_qc103_s4q8.json` (+ sidecars);
treeA `rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv` (working-tree diff, branch claude/die-qc-103-hcsel-1115 @079c81122f1).
State when written: first bind S4Q8BR ended as expected (R8_STALE, 06:56 UTC); the pinned rebind S4Q8BQ is in elaboration.
No bind gate of S4q8 exists yet, so bind 0 / LATCHECK / hard_core_param are NOT reviewed here; they stay DIE-QC-103's gates.

## 0. Verdict

| event | verdict | reason |
|---|---|---|
| **S4q6e** | **NON-BLOCKING** | The plan differs from adopted S4q6d in 48 values = 16 rows (4 st_a_v2 types x u_r0..u_r3) x (module, physical_master, HI_PAD 17/18 -> 15/16). No rect, lane, station or clock value changes. The 4 types stay held until the h15 / h16 masters are signed. |
| **S4q8** | **NON-BLOCKING, and NOT SUFFICIENT** | Plan JSON byte-equal to S4q6e (sha256 8ceefaf7a271, all four files). The RTL change is safe (no latency change, the D side of the select flops has more than 150 ps of slack). It does not close hc2 by itself: 31 endpoints below -42 ps do not start at a select flop, and the select class is a drive / RC problem that replication only shortens. Adopt it; do not release hc kits on it as "the fix" without item F3. |

## 1. What the routed hc2 kit shows (the full endpoint distribution)

Kit: sle_hc2__cl9c4c4509__clf60c5152, S3R attempt_3, epyc10, routed DRC 0. My session = the sign-off session up to
`set_propagated_clock` (TT libs, 6_final.odb, 6_final.spef, golden SDC); it reproduces the sign-off: WNS -178.75, TNS
-18,413.54, 494 endpoints.

| class (start -> end) | endpoints < 0 | endpoints < -42 | worst | leading buffer tree | launch - capture clock |
|---|---|---|---|---|---|
| select flop `g_lv[*].g_c[*].f` -> `asm_d` / `q` / `q_bad` / `asm_v` | 381 | 164 | -178.8 | mean 437 ps, max 627, 4.9 stages, slew to 285 | mean +30, max +68 |
| `wv` (write valid, one flop per leaf) -> entry `m[*]` / `v` | 83 | 31 | -67.1 | every stage is an x1 / x2 gate on 20-38 fF | mean +54, max +61 |
| `wep` (write epoch) -> entry `m[*]` | 30 | 0 | -33.9 | same | mean +37 |

- All 494 violators, and every endpoint under +50 ps except 16 landing-ring bits at 0, are inside the eight
  `u_u_xl2_*` leaves (ot_qfd_xs_leaf). Nothing else in hc2 is near the limit.
- Select class by level: lv3 235 endpoints (worst -178.8), lv4 95 (-107.7), lv1 46 (-82.8), lv2 4, lv0 1. So the
  levels with ONE copy today (lv3, lv4) carry 330 of 381. LPC 40 gives lv3 4 copies and lv4 2.
- By leaf: xl2_4 168, xl2_2 96, xl2_1 73, xl2_6 72, xl2_3 33, xl2_7 31, xl2_5 21, xl2_0 0.
- The `wv` path (worst -67.1): flop x1 driving 22.7 fF (130 ps, slew 234) -> INVx1 19.6 fF (187 ps) -> AND3x1 21.5 fF
  -> BUFx2 38.3 fF -> NAND2x1 22.3 fF (slew 246) -> BUFx2 -> OA21: 835 ps of data with no cell above x2.
- Placement (instance origins of the routed DB): the leaves are not compact. Named cells of one leaf span 172 x 177 um
  (xl2_0) to 110 x 364 um (xl2_4); the eight boxes overlap each other in x 206-508, y 72-446. A net of 5-10 loads is
  20-43 fF. That is where the cap comes from; the type is 613 x 717 um at about 10 % fill and global placement is
  neither timing-driven nor grouped by leaf.
- Hold (plain SDC, FF not run by me): TT 5 endpoints, worst -8.53. Not part of this review (cross-tap guard, r211).

## 2. Why the flow did not repair it (E1, MEASURED on the same kit's 5_1_grt.odb, TT libs, kit SDC)

| signal C on M2-M7 | TT setup WNS | endpoints |
|---|---|---|
| kit `setRC_rcx.tcl` (x1.0) | +2.48 | 0 |
| x1.2 | -76.81 | 25 |
| x1.3 | -116.36 | 155 |
| x1.4 | -155.19 | 314 |
| x1.5 | -194.29 | 537 |
| x1.6 | -232.79 | 869 |
| routed sign-off (SPEF) | -178.75 | 494 |

- x1.0 reproduces the gate exactly (+2.48). The routed result sits at about x1.46. FABLE-FIX-S81-BKSEL measured x1.40
  on an S81 core tonight: the same factor on two dies.
- At the GRT stage the kit ran `repair_design` on FF libs and this RC: 6 slew violations found. Sign-off TT has 465.
  `repair_timing` printed "No setup violations found" twice. OT_TT_SETUP_REPAIR (default since 18:14) runs
  `repair_timing` only, on the x1.0 RC: on this kit it would start from +2.48 and do nothing.
- At x1.5: `repair_design` finds 118 slew violations (169 buffers, 54 resizes) and moves WNS -194.29 -> -150.46 (517
  endpoints). The TT `repair_timing` at margin 30 on the same RC is running; its result goes in the post, not here.

## 3. Findings on S4q8 itself

| # | finding | mark | owner |
|---|---|---|---|
| F1 | **The RTL change is correct in form and has room on its input side.** Copies per level 28 / 14 / 7 / 4 / 2 / 1 / 1 (was 5 / 3 / 2 / 1 / 1 / 1 / 1). By `k * NR / NODES` a copy serves 2 or 3 mux nodes at lv0-lv2 (34 or 51 loads, so the real maximum is 51, not 40), 2 nodes at lv3 / lv4 (34), 34 at lv5 and 17 at lv6. `nsel[lv]` then feeds 57 D pins per tile instead of 14: no select-flop D endpoint is under +150 ps in the routed kit, so that side has the room. The copies are `(* keep *)` and all 14 per tile survive in the routed netlist of the old RTL (8 leaves x 2 tiles), so synthesis will not merge the new ones. | MEASURED (netlist, endpoint list); the loads-per-copy arithmetic from the RTL text | none |
| F2 | **The change reaches 16 types, not 8.** `ot_qfd_xs_leaf #(.FILL_PIPE(1), .NCH(4), .READ_PIN_PIPE(1))` (flat form) is instantiated in 16 bound types of S4Q6DBQ: sle_hc0 x3, sle_hc1 x2, sle_hc2 x3, slw_hc0 x2, slw_hc1 x3, slw_hc2 x3. The READY post names the 8 sle types. All 16 regenerate and need the LEC of the first kit; slw hc0 / hc1 / hc2 must be in the release list and in the hold terms. | MEASURED (`native_internal_stations/*/*.sv` of the S4Q6DBQ bind) | DIE-QC-103, WAVE-HOLDS-1115 |
| F3 | **Replication does not touch 113 endpoints (31 below the -42 limit, worst -67.1): the `wv` / `wep` write-enable fan-out.** After S4q8 the type still fails R-MINIMAL at sign-off unless the repair sees the real load. Same cause as the select class (x1 / x2 cells on 20-40 fF), different start flop. Fix is flow, section 4 item 1. If a second RTL step is wanted: `wv` / `wep` replicated per tile and per 32 entries (one flop each today for 2 x 128 entries x 17 bits). | MEASURED | FABLE-FIX-QC-HCFE (flow + proof), DIE-QC-103 only if the proof kit says so |
| F4 | **For the select class LPC 40 shortens the tree but leaves the cause.** 34-51 loads spread over 110-364 um are still buffered by ABC with BUFx2 / INVx1. Expected from the path table: lv3 / lv4 lose 2-3 of their 4.9 tree stages (about 200-300 ps of the 437 mean); lv1 (46 endpoints, -82.8, already 3 copies) gains less. Whether the remainder is under -42 is not decidable from this kit. The proof is a routed S4q8 hc2 kit read at sign-off. | INFERENCE from MEASURED stage delays | FABLE-FIX-QC-HCFE |
| F5 | **hc kits generated now will ignore the S4q6d strip-density rows.** QC `die_gen_env` and 17 of the 18 hc `item_env` rows still carry `OT_CLAND_STRIP_DENS=1.0`, and `gen_phys._cland_strip_density` lets the environment win over `budgets.cland_strip_density_types` (0.45 for hc1 / hc2). QC-HC-STRIP-1115 said so at 14:15. The hc1 kit at the gate tonight (sle_hc1 cl22c1ff36 S4Q2 a8, -486.88, 182 endpoints) is this class: of 182 violators 151 are b_hw_i landing-ring bits, 22 the `u_u_xh1.s_d -> bout_cw_s1` run (5 buffers, 1,165 ps), 9 other; none is in a leaf. Remove the key from `die_gen_env` and from the hc `item_env` rows before the first S4q6d / S4q8 hc kit. | MEASURED (kit_wave.json, gen_phys.py text, my gate-RC STA of that kit) | KIT-OPS-5 / WAVE-HOLDS-1115 |
| F6 | S4q6e: 16 rows only; outline and core rects are unchanged, so the h15 / h16 masters must be built to the old rects. Not checked by me (builds in flight). | MEASURED diff; master state REPORTED | DIE-QC-103, CORE-ROWS-1115 |

## 4. Ranked fixes

1. **Flow (mine, FABLE-FIX-QC-HCFE): the TT repair at GRT runs on signal C x1.45 and includes `repair_design`, setup
   margin 30.** One key in the kit (`tt_setup_repair.tcl`), default off, on for QC hc / fe / stm. Proof = routed
   sign-off of sle_hc2__cl9c4c4509__clf60c5152 on the S4Q8BQ bind, then one more hc type.
2. **DIE-QC-103: adopt S4q8 when its own gates pass; list all 16 leaf types (F2).**
3. **KIT-OPS-5: drop `OT_CLAND_STRIP_DENS=1.0` for QC hc (F5).** Without it hc1 stays at about -450 at the gate.
4. **If the proof kit leaves the leaf above -42 after 1 + 2:** `wv` / `wep` copies (F3) and a placement group per
   leaf (each leaf is about 7,000 named cells in 30,000-40,000 um2 today). The existing `BANK_PIPE` form (+1 read edge)
   is the last step, because it changes lane latency on 16 types.

## 5. fe (for the record; not part of S4q8)

sle_fe_v1__cl8210183c S3R attempt_3 (intel1, routed DRC 0), my session reproduces -60.62 / 38 endpoints. Only 2
endpoints are below -42. All 38 are zero-logic wire runs through 10-13 buffers (631-758 ps of buffers):
`bin_x_sc_i -> bout_sc_wo` 21 (worst -60.6), `cland_dd_wi dsel -> bin_dd_wi` 5 (-38.5), `u_core.se_q -> bout_x_stm_o`
8 (-35.8), `bin_x_stm_i -> bout_st_wo` 4 (-15.9). The S4q8 plan already carries stations on three of the four runs
(x_sc_i 2 + sc_wo 1, x_stm_o 2, x_stm_i 1 + st_wo 1; S4q4c rows); the fourth (landing ring to the dd_wi pin register,
-38.5) has none and is inside the limit. So fe_v1 setup is closed by the adopted plan, by structure (INFERENCE until a
routed S4q6d kit); what it still needs is the cross-tap hold guard (routed non-port FF hold -9.98) and the first
routed S4q6d kit. No new fe row from this review.

## 6. Stop list

- Do not post hc2 as closed on the S4q8 gate read: on this family the gate is +2.48 where sign-off is -178.75.
- Do not relaunch hc kits with `OT_CLAND_STRIP_DENS=1.0` in the environment.
- Do not hold S4q8 for F3-F5: they are kit / flow items.
- Do not switch the leaves to `BANK_PIPE` now: +1 read edge on 16 types before the cheaper steps are measured.

## 7. Not checked

- S4Q8BQ bind result, LATCHECK, hard_core_param, R8 pads: no rebind finished.
- FF corner and hold on any of the three kits. The x1.45 factor on FF.
- Formal equivalence of the LPC change (benches only, as DIE-QC-103 posted). The kit LEC of the first S4q8 kit covers it.
- hc0: no routed hc0 kit exists (all stop at DRT-0255); the leaf findings are assumed to carry over (same leaf, same
  parameters), not measured.
- Whether GPL honours an instance group per leaf in this OpenROAD build.
