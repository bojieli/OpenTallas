# FABLE-CLOSURE-STRATEGY 2026-11-21 23:25 PST (Opus stand-in for Fable, which is limited until 11-28): S81 col J8 needs four fixes in one row set, since no single fix routes; kv_leaf t5 is blocked by cores, not short of area; hd_ctl hold is repaired at GRT but carries 63k pad cells; KV hgi lockup_regions still fails in bind

Supersedes the 21:45 round (`git log -2 -- lanes/FABLE-CLOSURE-STRATEGY.md`). The 21:45 levers and stop list still hold unless a line below changes them.
Reviewer: Opus (FABLE-CLOSURE-STRATEGY stand-in). Read-only: nothing was launched, cancelled, patched or deleted, and no helper files were written on the gen hosts.
Gate (unchanged, not a new gate): DRC 0, TT setup >= -42 ps at 833 ps, internal FF hold >= 0, LEC, bind + LATCHECK. No die or outline growth.
Marking: **V** = read by me this round from the named file. **R** = reported by the named lane post (hub, 21:40 to 23:12). **I** = my inference. **P** = proposal.

## 0. Measurements this round (V)

| Item | File (host) | Reading |
|---|---|---|
| S81 col_h10_r1 kit D (88 xd stations seated per flop, J7 tools) | epyc9 `.../private/FABLE-FIX-S81-COLROM-R5/col_h10_r1__t1__cld01bb4ae_1121214130/.../4_cts_post_hook.rpt` | setup_ws **-81.07**, TNS -47,471; hold_ws -66.23 (post-hook, before CTS repair) |
| S81 col_h10_r1 kit E (refined `OT_RELAY_MID_RE` env row) | same, `_1121220326` | setup_ws **+22.23**, TNS 0; hold_ws -63.79 (post-hook, before repair). Best col CTS read so far |
| S81 col_h10_r1 kit F (seats + spread + 50 GRT iterations) | same, `_1121223001` | still in gen, no stage logs |
| S81 col_h9_r0_p2 KEEP rep (keep list + `ot_s81_rly:rq`, no STAGGER) | epyc8 `.../FAM-S81-COL-H9R0-R4/col_h9_r0_p2__t1__cl9f71e63d__pva4376595_1121191754/.../5_1_grt.log` | **GRT-0116, total overflow 944** (M8 344, M6 227, M5 210, M7 117) on attempt 1; residual retry running (extra iteration 1/10) |
| HEAD hd_ctl wave-env WRCAP kit | epyc9 `head-ctl-r1/kit/gen/hd_ctl`: `4_cts_post_hook.rpt`, `5_1_grt.log`, `5_global_route.tt.rpt`, `5_2_route.tmp.log` | CTS post-hook hold_ws **-133.63**, hold TNS -813,623, setup -92.00 (pre-repair). GRT: 1,666 hold ends found, +201 buffers, hold ws **+2.66, 0 violators**; design holds **63,257 HB4 pad cells** of 265,137 instances; TT worst slack +89.53, no setup violation; antenna 0. DRT iteration 0 at 70 % with 31,990 violations |
| KV hgi R6d3 gate chain | intel2 `~/tmp/opusfixkvhgir6/gates_r6d3.log` | G0 PASS; **RC_BIND 2**: plan_gate_pre input JSON truncated (line 1,546,512); R8 FAIL (32 groups unequal, 7 types conflicting); BPC 1 error; **LOCKUP_CHECK hgi_v2 and hgi_v1: 11 copies + 1 rest**, not 18. The bind did not complete, so the lockup read may be of stale output (I) |
| KV D28 row drop | epyc8 `kv-plan-r6/d28/rows/` | only `ROWS_KV-WAITBIND-R1.py` (+ `-cbc`). No pv split row and no hgi row. The pv split work dir was last written 21:10 PST |

## 1. Levers, ranked by types and dies unblocked

### Lever 1. S81 col J8 entry: one row set with all four fixes (col 216 types; S81 J8)
- Evidence: V section 0 (D -81, E +22, p2 KEEP overflow 944). R FAM-S81-COL-H9R0-R4 22:43: STAGGER without keep gives overflow 829 (from 5,401), the ROM e2 strip is clear, and the rest is 93 vertical boxes at x 850-1000, y 900-1100 in the `u_y_xd_` ROM-stage area (the 15 off-seat xd stations, worst 391 um). R COLROM-R5 22:31 kit F anatomy: the 1,264-bit `frame_int_i1` pad chain ends in a 56 um channel (x 635-691) with `u_lpl_0/1_r` (549 flops), `rt_10a_2/3` + `rt_16b_5` at one point (650, 44), and `u_lpl_32_r` (536 flops) parked 100 um off its 65-um source-sink line, so 2 x 536 nets cross the hotspot and back.
- Root cause: three effects add up on the same south channel and ROM area. (a) The relay-midpoint fallback pulls seat-keyed ROM stages off their seats. Kit B (all xd excluded) proved this, at the cost of -147 ps on the plain `n24` relays. (b) Station clusters stack at one point. (c) xo reset recovery fails without the kept rq flops. Fixing only one of them leaves 829 to 944 overflow or 80 ps of setup.
- Fix (P), one J8 col row set for col_h9_r0 p1/p2/p4/p5 and col_h10 (and every type with the xo chains):
  1. Rebind on main >= aa0cde9d13: the seat fix 643ffb9932 plus no-merge.
  2. Kit E's `OT_RELAY_MID_RE` (seat-keyed families only), in place of the old regex in `item_env`.
  3. `OT_KEEP_WIRES` with `ot_s81_rly:rq`. This works only if the no-merge default covers it. FLOW-OPS-R2's narrowing 5a966bb45b drops the clk_landing keep, so check that it does not also drop rq.
  4. `OT_RELAY_MID_STAGGER=1` (rt >= c54a7596fc).
  5. Kit F's five FIRM seats on col_h10_r1, if F reaches GRT with overflow 0.
- Kit C (H9R0-R4 J8 rebind) is the only build that combines items 1, 3 and 4. It must also carry item 2, or it repeats kit D's -81 ps.
- Decide on the first `5_1_grt.odb` with TT >= -42 and overflow 0, among C, E and F.
- Owner: FABLE-FIX-S81-COLROM-R5 -> OPUS-FIX-S81-COLROM-R6 (D/E/F), FAM-S81-COL-H9R0-R4 (C), FAM-S81-COL-H10-R4 (lever-1 kit, proof A), FAM-S81-COL-R6 (p4/p5), S81-J6-ASSEMBLY-R5.

### Lever 2. S81 C-layer xg/xf form, shared by all dsdv C slices (c1x_C x9, lepw x4, iq_C, lepe mu_C / nh_mus_C / nh_mus_LP; about 17 types; S81 J8)
- Evidence (R): DSDV-R1 22:55: all of these are ROUTE-HELD at geom, with 61-126 groups over 405 um, max 1.4-1.55 mm, setup estimate -660 / -706. LEPE-4 22:54: nh_mus_C has 66 NEED-STATION groups and 16,643 bits; 10,088 of those bits are inside `u_s_7S_u_sl_u_xg`, and the xf single-bit control legs reach 1.56 mm (estimate 1.93 ns).
- Root cause (R LEPE-4 22:58, accepted): `ot_s81sl_rstop` is a single register stage, and every output mixes the W-face, E-face and rung inputs. On a 1,442.88 um tile, each output therefore sits 1.1-1.7 mm from one of its inputs. This is an architecture-to-floorplan mismatch, not placement noise. J7 does not change it.
- Fix (P): one form with one set of row IDs across all slices:
  - XG-1: an rstop XMID mid stage (RTL define `OT_S81SL_RSTOP_XMID1`, +1 cycle on every rstop path, pre-approved).
  - XG-2: an xg region centred between the ring faces.
  - XG-3: D1 relays on the remaining centre-to-face legs.
  - XF-1: FIRM-site relays on the xf control legs.
  - RST-1: FIRM reset relay sites.
- No split is needed: nh_mus_C is 328k cells.
- DSDV-R1 must confirm the rstop signature on the c1x_C placed scan before copying the rows. If c1x_C differs, its rows go in separately and must not inherit an unproven form.
- Owner: FAM-S81-LEPE-4 (form + XG-1 RTL), FAM-S81-DSDV-R1 (c1x / lepw / iq_C rows), FAM-S81-SLICE-R4.

### Lever 3. S81 START and reset reach rows, then one die relay re-plan (writer 104 types, reader 38, raw reset 73; unchanged rank; S81 J8)
- New evidence (R S81-DIE-R5 22:59): slice_station__t45 stops at place with setup -554.53 ps on `u_cland_origin/s2 -> u_cland_reader_start_ft2_i_0`, path 1,992 um, span 1,439 um, 20 stages, longest hop 143.6 um. So this is a reach and fanout path, not a hop. Also iqf__t1: three reset relay hops from `u_rrl_67` at 571 / 570 / 483 um (R IQF-R1 22:34). Serdes START rows are gated green: strict bind RC 0, LATCHECK 873/873 (R SERDES-R8 22:44).
- Fix (P): unchanged from 21:45. Put in every family's START and reset rows, then run one die relay re-plan on the J8 plan, then bind. The reader_start fanout on slice_station needs a registered start-distribution tree (+1 to 2 cycles), not more buffering. Reset relay hops over 405 um go to `reset.die_relays` with sites, not to `internal_stations` (IQF-R1 already split them that way).
- Owner: each S81 family lane; S81-J6-ASSEMBLY-R5 (order); S81-DIE-R5.

### Lever 4. One-hotspot GRT class: move the macro or move the bus (QC sle_ctl + su_c x3 for V4; KV hg / hgi for D28; S81 leaf)
- Status since 21:45 (R, FAM-QC-SLWSLE-R1):
  - sle_ctl hot bins = the **8.64 um slit between u_tap and u_ctl**. The V4 full-type row moves u_tap to (56.16, 328.32) and u_ctl to (514.08, 336.96), opening a channel of about 138 um. The `b_hw_hc*_o` / `b_tw_data_st_a_o` stations are re-sited core-free, worst hop 291 um, 0 cycles.
  - su_c: the **121 um street (y 276-397) carries all five su buses**. CAP-2 moves `x_su_l0_p1_o` / `x_su_l1_p1_o` to bottom-margin bands and the E/W margins: 0 routes over cores, max hop 300, +1/+1 to +2/+2 cycles. The bound check (V3p7b + CAP-2) is running on epyc10.
  - This confirms the 21:45 classification: both are capacity holes made by macros, not density.
- Fix (P): V4 takes both rows as written. Two checks on the su_c rows:
  - The +2-cycle variant on cl19bb38ef must clear LATCHECK.
  - cl92142dac also carries a setup stop of -504 ps (21:45 stop 3). Do not count it unblocked by CAP-2 until a placed setup read exists.
- KV hg / hgi hotspot re-sites now ride in the single OPUS-FIX-KV-HGI-R6 script (KV-PLAN-R6 21:53); see lever 5.
- Owner: FAM-QC-SLWSLE-R1, QC-PLAN-R13 (V4), OPUS-FIX-KV-HGI-R6, OPUS-FIX-S81-LEAF-R10.

### Lever 5. KV D28: four structural rows, of which only one has been dropped (pc_v1 x3, hroot, hg / hgi 19, pv 16; KV D28 11-22 12:00)
- pc_v1 (R KV-WAITBIND-R1 23:09): the three `kv3_pc_v1__cl*` kit_topology failures come from the plan carrying both `bit_sites_um` and `face_bit_sites_um` on 18 packed input buses per type, and packed exact banks cannot also move face registers. The row is dropped (V: `ROWS_KV-WAITBIND-R1.py`) and compose-tested with 0 cycles. Done for D28.
- hroot (R FAM-KV-HROOT-R1 22:27): variant A has a clean bind, 84k cells, and is routing. Reset relay `u_rrl_25` hops up to **954 um** to efault / bin. P: add `reset.die_relays` sites (ceil(954/405) - 1 = 2 relays, about 318 um hops) to the D28 row now. Do not wait for route to show recovery or removal failures.
- hg / hgi (V section 0): the R6d3 bind did not finish (truncated plan_gate_pre JSON, R8 32 unequal groups, BPC 1 error), and LOCKUP_CHECK still reads 11 + rest. The lockup_regions defect is still the gate for all 19 types. P: re-run the bind on a fresh out dir first; the 21:55 debug rebind into a seeded dir did write 18 regions. If 18 regions show there, send the single HGI script with the 17 ectl re-site rows and the hotspot rows. If not, D28 carries hg / hgi without lockup rows and they go to D29. Do not ship rows whose effect is unproven in bind.
- pv (V: nothing dropped, no pv work since 21:10): the shared-vo-crossing row (21:45 lever 4) is still the fix for both `expected one outgoing lane` and the v1n cut overflow (8,100 of 16,191 cut pins). With under 13 h to the cut, P: drop the split + shared crossing for the v3 representative only, and leave the other 15 pv types on their D27d3 form for D29. That is the easiest path to closure.
- Owner: KV-WAITBIND-R1, FAM-KV-HROOT-R1, OPUS-FIX-KV-HGI-R6, OPUS-FIX-KV-PV-R7, KV-PLAN-R6.

### Lever 6. QC V4 package: coll v3 seats with half-cycle pricing, retap + anchor re-record, hc0 / st_a stations (coll 3, cb 17, hops 19, st_a family; QC V4)
- coll_core (R FABLE-FIX-QC-COLL-R2 22:38): package v2 seats placed FIRM 49,744 / 49,748. Detailed-place TT is -170.23 against -402.98 without seats, and the -193.82 reset-recovery class is gone (+37.69). The worst group is the `OT_TP8S_INLOCK` lock flops: **5,411 half-cycle connections** (negedge `ir_n / srr_n / drr_n` -> `*_q`), 2,110 over 150 um and up to 380 um. The solver priced them as full-cycle paths. v3 limits half-cycle edges to 120 um: 5,298 of 5,411 come out at or under 150 um, and 110 bits stay at 226 um across `g_xf_1`. P: v3 replaces v2 in V4 only if its bind is clean. The 110-bit `in_data -> ir_n -> ir_q` residue needs the lock pair seated on the same side of `g_xf_1`. A 226 um half-cycle hop (about 416 ps budget) is borderline at TT with OCV (I).
- Bind blocker for V3 / V4 (R TAP-GRID-R5 22:48 / 22:53, QC-PLAN-R13 22:36): 99 RESET_ANCHOR errors and 1 EMIT. The new tap set renumbers the reset relay tree, but `reset_tree_anchor` keeps the old names. Class fix on main 2fd0ab57c1. sle_sc_v1 cl115da35f needs `retap.py` (stale published collector_tree after tap_split). Every V4 compose must run on tools >= 2fd0ab57c1, or run `reset_anchor.py record` after the tap rows.
- slw_hc0 (R FAM-QC-HCST-R3 rows): 133 r2r captures over 405 um, max 532 um. The worst is `u_u_xl0_4.q_bad -> u_bout_x_ctl_o/q[5]`, from the core to an output register already within 7 um of its pin. V3 has no station for `x_ctl_o`, `x_hc1_i` or `cland_tstart_in`. P: the 1-stage `x_ctl_o` row (+1 cycle) goes in V4. The other 132 captures were not exported, so trace them on the V4 placed scan before claiming slw_hc0 closes.
- slw_st_a (R FABLE-FIX-QC-STRAP-R2 21:45 / 21:49):
  - The R8 seat (row 2a) is proven at GRT RC.
  - The type is still -195.32 ps, with 22 ends on `btab g_read -> u_u_r3`.
  - New class: `b_tw_data_i -> pd1`, -43.6 on 5 ends, a 925-931 um hop with a single pad stage.
  - P: one more pad stage or a pd1 mid seat (+1 cycle) on the 2b family, together with the btab column move.
- Owner: OPUS-FIX-QC-COLL-R3, QC-PLAN-R13, TAP-GRID-R5, FAM-QC-HCST-R3, FAM-QC-CB-R4.

### Lever 7. Landing bands blocked by cores: plan geometry check, not strip tuning (S81 kv_leaf t1 to t5; same class as KV io_cor_v1 band and KV pv CLAND x5; S81 J8)
- Correction to 21:45 lever 7 (R FAM-S81-MISC-R4 21:41): t5 is not an area misfit.
  - The vp lane cores `g_ln[4]` (43.2, 1105.92) and `g_ln[0]` (181.44, 1105.92), each 114.48 um square, sit on the N-face bands: they cover 100 % of ft0_i, 52 % of ft1_i and 88 % of monitor_0.
  - J5 had them at y 985, clear of the bands; the C1n regrid moved them.
  - This also explains monitor_0 failing at 0.47.
- Fix (R, accepted): re-pitch both 8-lane vp columns from 155.52 to 142.56 um and move ft0_i / ft1_i to y0 1152.36 (3,438 um2, fill 0.696). Move monitor_0 to x 187.56 and clk_t21 / t26 / t35 off the closed gaps. The row is merged three ways onto the J7 t5, keeping the J7 monitor_1 reseat and reset anchor. Gate running. Worst ft hop 369 um, no extra stage.
- P (class): add a G0 static check, `landing band ∩ core box = 0` and `band fill <= 0.70`, for every type. A regrid that moves cores onto bands is caught today only by a failed global place. KV io_cor_v1 (FAIL-CLASS f5fa4d600f, "band too small or blocked") should get the same overlap read before anyone resizes its band.
- Owner: FAM-S81-MISC-R4 (t5), OPUS-FIX-S81-LEAF-R10 (t1 to t4), KV-RINGMAC-R1 / KV-AHUB-RH1 (io_cor_v1), PRECHECK-1119 (static check).

### Lever 8. Hold by early capture taps, not pad volume (HEAD hd_ctl; S81 col CTS hold; S81 serdes t4)
- Evidence: V hd_ctl closes hold at GRT only with 63,257 HB4 cells, about 24 % of instances. Its post-CTS hold was -133.63 with TNS -813,623, so the 21:45 "port-start class" reading of -134 ps on 7,608 ends is the pre-repair number. hd_ctl now passes GRT. The risk has moved to detailed route: 63k pad cells in a 587.52 x 518.4 um die, iteration 0 at 32k violations (V, early DRT, not yet a verdict).
- R S81-GEOM-OPUS 23:06 (D8i col): CTS FF hold after CORETAP is -53 to -120 ps. col_h9_r1 signed off at routed TT -83.5 / FF -162.3.
- R SERDES-R8: t4 had -762 ps hold from shell to child, because the child's internal insertion sat on a late parent leaf. The fix is early core clock taps at `u_core.u_dec.ck` / `u_core.u_enc.clk`.
- Root cause: the capture clock is late relative to launch (tap overload, or a child core hung on a deep leaf), and hold then tracks capture latency one-for-one (21:45: t39 r = -0.988).
- Fix (P): for hd_ctl, let the route run, and judge it on DRT convergence by iteration 5. If DRC does not converge, apply the early-tap or tap-split row on the port-start capture group. Do not use a pad ECO. For col: the kit E hold of -63.79 is pre-repair; read the GRT hold before adding any rows. Apply the serdes early-tap form to every hard child core that sits on a parent leaf.
- Owner: HEAD-CTL-R1, TAP-GRID-R5, FAM-S81-SERDES-R8, col lanes.

## 2. Stop list (new or changed; earlier lists stand)

| # | Dead end | Why |
|---|---|---|
| 1 | Any single col fix as the J8 entry (seat fix alone, STAGGER alone, keep alone, all-xd regex) | D -81 ps, KEEP overflow 944, STAGGER 829, all-xd -147.71 (V / R) |
| 2 | Kit C without kit E's `OT_RELAY_MID_RE` | It would repeat D's midpoint pull on the ROM stages (V D vs E) |
| 3 | Canary narrowing that drops `ot_s81_rly:rq` keep | The col xo recovery class comes back (R H9R0-R4: 552 ends at J5) |
| 4 | `OT_CLAND_STRIP_DENS` / band resizing on kv_leaf t5 or io_cor_v1 before reading the core-band overlap | t5 was 100 % covered by cores (R) |
| 5 | Station rows on c1x_C / lepw / iq_C that place relays inside a single-stage rstop | The rstop output mixes faces 1.1-1.7 mm apart; needs XG-1 (R) |
| 6 | Pricing the coll lock flops as full-cycle, or routing coll v2 to settle it | 5,411 half-cycle edges up to 380 um (R) |
| 7 | Composing V3 / V4 / J8 tap rows on tools older than 2fd0ab57c1 without `reset_anchor.py record` | 99 RESET_ANCHOR errors (R) |
| 8 | Any hg / hgi kit, or hgi rows in D28, until LOCKUP_CHECK shows 18 regions on a completed bind | R6d3 bind RC 2, still 11 + rest (V) |
| 9 | Reading hd_ctl's -134 ps as an open hold class | GRT +2.66, 0 violators (V); the open risk is DRT with 63k pads |
| 10 | Judging any kit on `4_cts_post_hook.rpt` or `4_cts_final.rpt` slack | Pre-repair (V hd_ctl -133.6 -> +2.66) |
| 11 | kv_leaf t2 as 28 store pieces for J8 | Hub piece p24 carries 89-114k cut bits, density 1.13, no parts RTL (R LEAF-R9); J8 = A/B cut only |
| 12 | Re-binding serdes PHY/ENG with bit sites moved but `regs_um` stale | G0 reads `regs_um`: false 924 um hop (R) |

## 3. Changes since the 21:16 round (21:45 file)

- S81 col: kit B withdrawn. Kit D measured: seats on, -81 ps at CTS. Kit E measured: best form, +22.23 at CTS. Kit F launched for the hotspot. p2 KEEP reached GRT with overflow 944 (V). Lever 1 now asks for all four fixes in one set.
- S81 dsdv: the root cause is now identified as the single-stage rstop that mixes faces. The XG/XF form is published (`lanes/handoff/FAM-S81-LEPE-4-xgxf-form.json`). DSDV-R1 follows it for c1x / lepw / iq_C. New lever 2.
- S81 kv_leaf t5: the cause changed from an area misfit to cores on the bands. A row and a gate are running. 21:45 lever 7 is corrected.
- S81 canary: the A/B pins it on `8a2a7b31a97` (class keep on 109.93 vs off 130.39; GRT slew 14 vs 0). The narrowing is in 5a966bb45b. Closed as a cause; open as a risk to the rq keep (stop 3).
- S81 serdes: START rows gated green. PHY/ENG has one false hop (stale `regs_um`); the fix is gating. t4 gets early core taps for its -762 ps hold.
- S81 START: slice_station t45 stops at -554 ps on a 1,992 um, 20-stage start-fanout path.
- QC: sle_ctl slit and su_c street rows written for V4. coll v2 placed at -170 (from -403); the half-cycle class was found and v3 seats are in bind. The reset-anchor class fix is on main. V3 strict bind ETA is about 01:30 after the retap.
- KV: pc_v1 face/bank row dropped. 9 hub_C ring masters signed (hub_C ring rows moved to D29). qkd_ahub strap GRT is TT +28.89 / FF +2.84. hroot A is routing with a 954 um reset hop. hgi lockup is still failing (V). pv has had no activity since 21:10 (V).
- HEAD: the hd_ctl wave-env kit passed GRT (TT +89.5 worst slack at GRT, hold +2.66) and is in DRT. The old rows-1 kit is abandoned (TT -104.06).

## 4. Not checked

- Kit E and kit D after CTS repair or at GRT; kit F at any stage; whether kit C's env carries kit E's regex.
- The p2 KEEP residual retry result, and where its 944 overflow sits (x 850-1000 xd area or the south channel).
- Whether 5a966bb45b keeps `ot_s81_rly:rq`.
- hd_ctl DRT convergence past iteration 0.
- The coll v3 bind result (several pk4 bind runs died at 22:38-22:42 PST with rc 127 / 143 / 3).
- The su_c CAP-2 bound check and the V3p7b retap bind.
- The rstop signature on the c1x_C placed scan.
- QC 66-hop list and cb row A bind: unchanged since 21:45, not re-read.
