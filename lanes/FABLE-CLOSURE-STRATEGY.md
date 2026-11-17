# FABLE-CLOSURE-STRATEGY 2026-11-16 21:00 PST (2100): hold is now a flow class with a proven fix; the open walls are RC agreement, cross-tap insertion and S81 relay depth

Reviewer: CLOSURE-STRATEGY-2100 (Opus; Fable is at its weekly limit until 11-22). Read-only. Technical PD only. HBM parked.
Read 19:10-19:40 PST: FABLE-CLOSURE-STRATEGY 1730, FABLE-PD-S81-BKSEL (17:47), FABLE-PD-QC-HEADSEG44 (18:34), FABLE-FLOW-1900
(technical parts only), `failure_breakdown.py` 19:10, COORD-REVIEW-QUEUE RESULT/STATE 17:00-19:10, handoffs S81-DIE-R (+R2),
S81-TYPES-R / -R2 / -R-IFN0 / -R-STRIP, S81-CORES-1115, S81-SERDES-R / -R2, HEAD-DIE-R, HEAD-TYPES-R / -R2, FABLE-DIE-QC(-R),
KV-CLK-R2, HOLD-FLOW-R. MEASURED by me: bksel fx6 `run_finish.log` on epyc2 (route DRT-0199 0 violations, antenna 0, final RCX +
IR written 19:09; sign-off not yet run; `FAIL_POSTCTS` = "legacy grt gate: missing postcts gate", a harness line, not a timing
fail). Everything else is REPORTED by the named lane; INFERENCE is marked.

Gates: DRC 0, routed TT WNS >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK.

## 0. Verdict

1. **The hold class has a complete, measured fix.** CTS-stage repair now honours reg2reg scope (r399), pre-route margin is 10
   (r394) and the post-route internal HB4 ECO is in the flow (opt-in). headseg44: CTS hold buffers 16,494 -> 2,403, DRT
   9998 / 1098 / 552 / 10 / 0 (old form plateaued 833-1,231 for 50 iterations). coll_n and four tail1 masters signed with it.
2. **The next class is RC disagreement between repair and sign-off**, not hold itself: bksel reads the same netlist -28.38 on the
   kit table and +6.92 on the hold-repair table (35 ps from M6/M7 C alone); QC/HEAD show 9-17 ps estimate-to-RCX drift.
3. **Cross-tap insertion skew is the S81 SerDes limiter, not distance.** H2 tap balance removed the clk_t29 class (24 -> 15
   endpoints under -42); the rest are half-cycle reset-relay hops that cross taps. The 785 ps t17/t26 trees are FF-side only.
4. **S81 col (216 types) is now gated by relay depth / station sites in the plan**, not by halves, leads or reset: halves read
   0 internal violators at GRT, reset class gone, but h10_r0_p1 reads -508.5 with 18 of 95 relay groups NOFIT.
5. **HEAD die gate is blocked by 7 stand-in views**, of which 2 are routed DRC 0 and in sign-off, 2 have a named geometric /
   port-timing defect, 3 have no current kit.

## 1. The 17:30 levers: done, open, wrong

| # | 17:30 lever | state | evidence |
|---|---|---|---|
| 1 | routed internal hold: HB4 ECO stage + 10 ps pre-route | **DONE in flow; one premise WRONG** | r394 merged (margin 0 -> 10, OT_PRD_HOLD_PLAN ECO, fails closed on lost cell). coll_n hold80 SIGNED (TT -1.39 / FF +0.47 / DRC 0). tail1 h15/h16/h17 x4 SIGNED with one nonport ECO. WRONG: 17:30 assumed the in-flow scope already covered CTS; the helper was gated on 4_cts.sdc while CTS runs on 3_place.sdc, so CTS repair padded port paths (fixed r399). OPEN: HOLD-FLOW-R proof1 (86 HB4 on the coll_n copy) routed result; W0/W1 endpoint tables; P3 relaunched at margin 10 |
| 2 | S81 col: IR group in CTS, lead 40, reset v5 | **DONE** | splitbal (IR on own BUFx12 root child): GRT internal reg2reg 0 violators TT and FF on both halves; IR 388-403 (was 407-470). Lead 40/ROM 255 kits: r2 -46.8 (1 ep), ROM q -11.4. Reset v5: 206 chain flops, longest hop 317 um, class gone. New limiter -> lever 4 here |
| 3 | QC head: rebuild with CTS scope, no port hold cells | **DONE** | runs_hf DRT 0 at iteration 4. 17:30 said "rebuild from CTS with the a03 fix"; the first rebuild (runs_np) did not reach CTS (byte-identical 4_1_cts.odb) - the lever was right, its first execution was not |
| 4 | QC Kf + L plan of record; +1 K on 3 serdes crossings | **bind running; +1 K WRONG** | S4q9l2 = L + tol need+10 on 15,391 ports + 24 tail1 rows, bind S4Q9L2BQ. The -107 ps was the ca_named_pairs None fallback; with dec8cc442a the CA planner picks K 3 -> 4 itself, CA 2993 PASS |
| 5 | KV: pilot CTS reads, rows B', E4 DME | **B' and E4 DONE; pilots OPEN** | HG2 e6a: per-port window max 202 vs cap 208.25 (was need 277), slew max 76, GRT0 0, rows B 0 walls / 19,309 rects. Pilot CTS reads not posted (kit-input-missing 6, waits-on-child 14) |
| 6 | HEAD: M8 grant everywhere, sd9A GRT read, hw4 by lever 1 | **grant DONE; types OPEN** | NF15c adopted (grant on all 26, die GRT0, guide a8dc locked). sd9A GRT read = FAIL TT -189.6 (start_o_0 / rst_o_0). he12h DRT 64 iterations -> 60 DRC. hw4 i1t routed DRC 0, sign-off running |
| 7 | S81 non-col: t34/t43 strips, svc, serdes cohort guard | **PARTLY; serdes framing WRONG** | t28/t34/t47/t62/t72/t75 launched, t8 row defect fixed (t8fix PASS-COND, routing), t43 waits on two-station rows (F2s5d). svc lo7 needed an RTL fix (u_mq 128x23 + 12-stage FF tail). Serdes: the cohort guard alone did not close; the measured class is cross-tap insertion (lever 3 here) |
| 8 | clock rows at need + 10; one region tree per type | **QC/KV rows DONE; template OPEN** | QC l2 and KV rows C at need + 10. QC form 2 (template region tree) + exact SPEF readout in chain s4q9m_r (about 3 h 20 from 18:08). S81 seam 290 vs 40 still open |
| (9) | bksel (17:30 stop list / 09:25 #8) | **routed, number pending** | fx6 DRC 0 at route; fx7 re-land moved g_bank[0] only -76 -> -104 (no earlier tap within 420 um) |

## 2. Levers now, ranked by types / dies unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | all | one RC table for repair and sign-off (hold and setup) | every routed residue; bksel (7 bk_sel types behind it); all ECO sizing | HOLD-FLOW-R, S81-CORES-R (bksel) |
| 2 | S81 | col relay depth / station sites as a plan row; NOFIT fails at gen | 216 col types | S81-DIE-R2, S81-TYPES-R2 |
| 3 | S81 | SerDes: cross-tap launch relays plain-posedge (H3) + tap re-pitch (G3) + bind rule | serdes family (H/J/G forms, about 15 types) | S81-SERDES-R2, S81-DIE-R2 |
| 4 | all | CTS-stage hold to the gate on every two-mode / hand-driven build, checked before DRT | QC head group (96 heads, 9 SU types, W0..W7), S81 halves, core kits | HOLD-FLOW-R, QC-TYPES-R |
| 5 | HEAD | close the 7 stand-ins by defect, then real-view die STA | HEAD die clock gate (585,476 hold pairs) + 6 open types | HEAD-TYPES-R2, HEAD-DIE-R |
| 6 | QC | template region tree + exact SPEF readout -> rows from exact numbers | about 100 QC types on rows with 0-5 ps margin | FABLE-DIE-QC-R, QC-PLAN-R |
| 7 | KV | bind HG2 e6a, then pilots; build the 5 child cores first | 31 held keys + 14 waiting on child cores | KV-R, KV-CLK-R2 |
| 8 | S81 | bksel structural landing (no wire-built offset) if fx6/fx7 miss | dsdv_bksel_q (last open S81 core) + bk_sel types | S81-CORES-R, S81-DIE-R2 |

### Lever 1. Repair RC = sign-off RC (all dies)

Evidence. bksel fx6: same netlist FF hold -28.38 on `setRC_rcx.tcl` (C x1.40 M2-M7) vs +6.92 on `OT_RC_CAL hold`; the tables
differ only in M6/M7 C (0.183/0.130 vs 0.105/0.105 fF/um). Pass 1 shows the same gap (-73.13 vs -39.36). Measured routed clock-net
C (M6 0.132, M7 0.087) lies between. QC W0 / HEAD hw4: GRT-repaired endpoints at +0..+15 land -9..-17 after RCX. QC FABLE-DIE-QC-R:
`estimate_parasitics -global_routing` snaps pins to 10.8-um gcells; per-instance grid phase adds +0..21 % wire on every net (two
copies of one tree read 1,122 vs 1,230 ps).
Root cause. Hold and setup repair, and their estimates, run on a table the sign-off does not use; the hold table is the optimistic
side. Every margin the repair reports is therefore a margin on the wrong table.
Fix (flow).
1. HOLD-FLOW-R: one RC source per kit for every repair_timing pass = the routed-fit table the sign-off reproduces (`OT_RC_CAL=0`
   on hold, as fx7 does), and print both-table WNS in the repair log until the drift is under 5 ps on three types.
2. Size the post-route ECO for +10 on the sign-off RCX, never on the repair table.
3. Where pins sit on a gcell grid (QC replicated types), take clock readout from exact placed RC (`clock_spef.py`), not GRT.
4. bksel: read the fx6 sign-off first; if internal FF <= about -30 on a few hundred endpoints, one hold-only HB4 ECO (r394 form, no
   repair_design, no allow-setup). fx7 (OT_RC_CAL=0, margin 10, cap 4 %) is the parallel form.

### Lever 2. S81 col relay depth (216 types)

Evidence (S81-TYPES-R / -R2). Relay regex fix `[._]`: h10_r2 stations 5 -> 80, CTS under -42 2 (was 14). Per-bit istations
(gen_rm3 h10_r2, 6 flops, 0 cycles): CTS -39.0, 0 under -42, in route = sign-off candidate. gen/col_h9_r2 at GRT: TT -3.9,
overflow 0, hold -10.0 pre-route. But gen_rm2 h10_r0_p1 CTS: -508.5, 1,569 under -42; relay_mid NOFIT on 18 of 95 groups; hops
y_xb -> bs i_x 1,277 um (266 ep, -508), bn d_st -> ist_frame_int_o 1,561 um (-439), y_xa -> t xai 1,118 um. h9_r0_p2: 557 of
659 failing endpoints on one mirrored pair bs1 -> e1_u_w xs_q (262 um, 4 buf, the other bs->e pairs +31..+70); bs0/bs4 off their
e_w pin centre by 215/176 um.
Root cause. The plan's relay stage count assumes station sites that do not exist on the 1,589.76-wide p1 outline; NOFIT groups fall
back to one long hop. The bs mis-site is a mirror error in the e|w pair mapping (INFERENCE from the 1-pair concentration).
Fix.
1. S81-DIE-R2: one plan row per NOFIT group: relay stage count so every hop <= 405 um (cycles pre-approved) and legal sites for the
   18 groups; per-bit istation rows for frame_int_o0 u_t*/so bits (proved on h10_r2, also on r1 at 894 um).
2. S81-TYPES-R2: gen fails closed on any relay_mid NOFIT and on any planned hop > 405 um; fix the bs1 mirrored-pair site map (bs
   site = its e_w pin centre) before the next r0 kit.
3. Merge c0ddf60 (relay regex default) so every col kit gets the 80-station form.

### Lever 3. S81 SerDes cross-tap insertion

Evidence (S81-SERDES-R/-R2). H CTS: 24 under -42, worst -147.62, none through clk_t17/t26; 25 are u_txl r[1] -> q, launch tap
clk_t29 at 543 ps vs capture t23/t30 184/276. H2 (tap balance, spread 233 ps): 15 under -42, clk_t29 class gone; 12 left are
ot_dp_rrelay_nl q(fall) -> next state(rise) across taps (rrl_33 t4 -> rrl_38 t11 -150.1: launch 297 vs capture 182, hop ~350 ps).
34 of 127 nl hops cross taps; same-tap nl hops of 375 um pass. North-strip FFs: own taps cut t17 785 -> 407 ps; they appear only on
the FF side (18 endpoints). G3: tap insertion 219-1,240 ps, TT -974.56 (1,022 ep), FF -645.75; OT_TAP_CHECK says pitch <= 117 um.
Root cause. A half-cycle relay hop has half the budget, and crossing taps adds the full insertion difference (100-300 ps) to it.
G3's tap plan is too sparse for its 6,129-sink taps.
Fix.
1. S81-SERDES-R2: H3 = launcher of every cross-tap hop becomes plain posedge ot_dp_rrelay (25 launchers; same latency, LATCHECK
   unchanged). Route H2 for the residue read; H3 is the sign-off candidate.
2. S81-DIE-R2: the bind/reset generator emits that rule (cross-tap hop -> plain launcher) so H3 is countable; same rule for J/G.
3. G3: re-pitch taps to <= 117 um and carry the J5 rd.q-local + H3 relay fixes before another CTS. No G3 route on the current taps.

### Lever 4. CTS-stage hold on every build that runs it

Evidence. headseg44 as in section 0. HOLD-FLOW-R: affected = two-mode core_flow kits without SKIP_CTS_REPAIR_TIMING and hand-driven
ref_tile / abi3 / closure_loop builds; gen_phys type kits skip CTS repair. Live count not measured. Remaining headseg44 parts not
yet used: HB2/HB4 pad at CTS (`OT_CTS_HOLD_PAD`), density screen.
Fix.
1. HOLD-FLOW-R: list every running or queued two-mode / hand-driven build that started CTS before r399 (QC W0/W1..W7, S81 halves
   form, core kits); each one picks up r399 on its next CTS, not after route.
2. Every such build checks "Inserted N hold buffers" at CTS against the previous form before DRT; > 2x the gate need = stop.
3. QC-TYPES-R: W1..W7 248-output group forms start with r399 + margin 10 + spread south pins (4-track pitch, 104 um needed for 541
   pins); OT_CTS_HOLD_PAD=HB4 on the first, compare cell count and window fill.

### Lever 5. HEAD: the 7 stand-ins by defect

Evidence. NF15c die proto: GRT 0 overflow, intra TT +569.5, seam TT +654.9; clock gate BLOCKED on 585,476 hold pairs without signed
views. Per stand-in (HEAD-TYPES-R2): hd_host_w hw4 i1t routed DRC 0, sign-off running (31 internal endpoints, TT room >= 173);
hd_spn (spn_end PRD3) in DRT, pre-DRT session hold +20.0 with 370 buffers, RC sentinel exact; hd_host_e he12h 60 DRC after 64
iterations (M6 at the u_epc W edge x = 423, M7 y ~ 60, M2 W-edge clk_t7/t8 tb0 + relay nets); hd_serdes sd9A GRT TT -189.6 after
repair on start_o_0 / rst_o_0; hd_mesh, hd_lep0N, hd_ctl: no current-tree kit (cancelled superseded).
Fix.
1. HEAD-TYPES-R2: he12h - no more DRT iterations; fix the u_epc W-edge pin access (spread the clk_t7/t8 tb0 and relay pins, or a
   partial blockage at x 415-430 under the M6/M7 hot spot) and re-route touched nets only.
2. sd9A: start_o/rst_o are register-to-port paths; put the launch flop at the face (pin-adjacent placement or one face register,
   cycle pre-approved) instead of more repair. sd9B stays dropped.
3. hd_mesh / hd_lep0N / hd_ctl: generate on NF15c with the M8 grant now; they carry no known defect.
4. HEAD-DIE-R: swap each signed view into real_sta as it lands; the gate is per-pair, so partial swaps already shrink the blocked set.

### Lever 6. QC: rows from exact readout

Evidence. FABLE-DIE-QC-R: same-type half range 15,391 ports, GRT readout max 104.1 / 2,440 ports over 10 ps; exact RC max 76.9 /
347 over 10 ps, all on the 3 refused types (cbn_q00 7, cbx_q10_h 8, cbf_q11 2 refused copies) + H-tree sc_v2/fe (<= 28 ps).
Every fully templated type is under 6 ps. 0 of 69,979 clock nets detour.
Root cause. The 129 ps spread that forced need+10 rows was a gcell-phase readout artefact plus per-instance tree embedding.
Fix (FABLE-DIE-QC-R -> QC-PLAN-R). Finish s4q9m_r (template=2 + comb feed + SPEF); want 0 refused templates; then cut tol =
ceil(half range + 10) from exact RC. Re-sign risk on 52 QC types at each tap move drops to the 3 refused types.

### Lever 7. KV: bind HG2, child cores first

Evidence. KV-CLK-R2: e6a GRT0 0, setup +482/+543, windows 0 over 208.25 (max 202, i.e. 6 ps under the guard), seam need 155.3 ->
170, CA 3915/3915. Real-view hold 4,096 pairs, 27 negative (worst -38.5), all capturing at landing cores whose D is a partition
input port; the reviewer traced all 27 cones and found no launch core. e6a needs a 31 ps wider FF intra hold window than e6b.
14 parent types wait on 5 child cores without a routed view (kv_cland_w1057_ew / w288_ns / w781_ns, qkd_hr_core_order / _peer).
kv3_hub_Wo fails "clock-landing band too small or blocked".
Fix.
1. KV-R: bind HG2 c15e87e46597 + LATCHECK; first pilot kv3_pv_v1n on rows B.
2. KV-CLK-R2: make die_sta_related drop the 27 non-edge pairs by netlist connectivity, not by argument, so the gate reads them as
   absent rather than negative.
3. Build the 5 child cores now (they gate 14 types; nothing else does).
4. kv3_hub_Wo: band sized from e6a's own window for hub_W, not HG1 (INFERENCE: the band predates e6a).

### Lever 8. bksel landing (S81 core)

Evidence. 16 of 17 ETM macros land -149..-202 vs the -180 target; g_bank[0] -78.9 (fx6) / -104.4 (fx7, best tap within 420 um).
4,170 HB4 overall in fx6; the offset is built from unbalanced wire (one BUFx24 per pin over 28-210 um).
Fix. If fx6/fx7 sign-off misses: let CTS balance the macros natively (both ETM libs carry `clock_tree_path`; the post-CTS re-hook
bypasses it), or add the existing low-phase `g_lat` stage on the g_bank[0] input bus only. The die-side early tap for g_bank[0]
(S81-DIE-R2 conditional row) is the plan form if the core-side fix cannot reach -150.

## 3. Stop list

1. Any relaunch from a placed / CTS DB with a flag that only the GRT helper reads; any DRT on a build whose CTS hold-buffer count
   was not compared with its previous form.
2. Quoting FF hold from the hold-repair table as progress; any hold or setup repair on a table other than the sign-off fit.
3. More bksel re-land tries from wire (no tap earlier than -104 within 420 um); route-keep ECOs with repair_design / allow-setup.
4. G3 route or CTS on the current tap pitch; nl reset relays on cross-tap hops in any new serdes kit; any t17/t26 TT fix (FF only).
5. Routing S81 col kits with relay_mid NOFIT groups (h10_r0_p1 form); bs site maps from the mirrored e|w table.
6. The +1 K plan row on QC io_serdes_2 -> c_W5_bf_01 (CA planner already picks K 4).
7. Further DRT iterations on he12h; relaunching sd9A unchanged; sd9B.
8. Row tolerances from GRT-readout spread on QC replicated types; rows cut at exact measured need (0 margin).
9. Hold-cell fixes on the 27 KV landing-core pairs (they are not data edges).
10. Still valid from 1730: S81 numbers from the old ICG-bypass halves; KV rows B as merged; a 20 ps pre-route hold target; hold cells
    on port-only paths; F2s3 col GEN outputs; the K2 clock kit.

## 4. Not checked

- bksel fx6 routed TT / FF: route done (DRT 0), sign-off not run when I read (19:09).
- HOLD-FLOW-R proof1 routed result on the coll_n copy.
- headseg44 hf sign-off numbers (in 6_report at 19:04).
- QC "other flow error 26" (phy_serdes, +25) and KV "other flow error 16": not opened; KV's are plan-contract metadata
  (core_cloc) and KIT_NOT_SELF_CONTAINED, not physical.
- The bs mirrored-pair cause and the kv3_hub_Wo band origin are INFERENCE.
- S81-SERDES-R2 lines stamped 19:2x / 19:3x (H3, G3 census) were in the handoff at 19:10; read as reported.
