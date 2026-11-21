# FABLE-CLOSURE-STRATEGY 2026-11-21 01:50 PST (lane FABLE-CLOSURE-0130, the 01:30 round): 141 of 307 running jobs sit in global route, and the overflow there is five local layout classes, not cell count; the S81 col ROM fix now has four rows and waits on one re-hardened core

Previous rounds (23:45 and all earlier ones) are in git: `git show 9f476d361c1:lanes/FABLE-CLOSURE-STRATEGY.md` (coord/state).

Reviewer: FABLE-CLOSURE-0130 (Fable). Read-only: nothing cancelled, signalled, patched or launched except seven small ot-run read jobs (section 7). Scope: technical physical design on S81 / HEAD / QC / KV. HBM parked.
Gate: DRC 0, TT >= -42 ps at 833 ps, internal FF hold >= 0, LEC, bind + LATCHECK. No die or outline growth. Nothing below is a new gate or hold.
Marking: **V** = I read the file or computed the number this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Clock and setup numbers are post-hook (`OT_CTS_POST_TIMING`) or GRT.
Data (V): `scan.py` over the newest `congestion-N.rpt` of every `ot-jobs/*-route-*` work dir younger than 30 h on epyc2/7/8/9/10 and intel1 (not intel2): 79 reports, 62 types, mixed plan events. Per report: overflow (usage minus capacity per gcell), H / V split, 43-um bins, share by gcell capacity, share by net class of the nets named in the overflowing gcells. Raw: `<host>:/srv/opentallas-scratch2/claude/fable-closure-0130/scan_out.txt`, detail `epyc10:.../out1.txt`; copy and scripts in localhost scratchpad `c0130/s/`. A report lists at most 20,000 gcells, so totals of 20,000-gcell rows are lower bounds. N in `congestion-N` is the GRT iteration: a read at 5 is early, a read at 10 or later is the flat level.
Also read: lanes/FABLE-VISUAL-0030.md (01:15, 24 rendered kits), FABLE-FLOW-2350.md, FLEET-MIX-2340.tsv, CANCEL-GRT-FLAT.tsv (26 rows), ROUTE-REACH-0020.tsv, the FAM-* and FABLE-FIX-* handoffs and posts to 01:20, failure_breakdown 01:12.
Count (failure_breakdown 01:12, V): S81 44/394 types signed, QC 33/125, KV 6/56, HEAD 25/26.

## 0. Headline

1. **Global route is where the fleet stands, and the cause is local (V).** FLEET-MIX-2340: 141 of 307 jobs are in GRT (S81 73, QC 43, KV 14 with a median of 15.1 h in the stage, HEAD 6). ROUTE-REACH: 324 of 350 unsigned S81 types, 47 of 92 QC and 48 of 50 KV never reached detailed route. In the 79 congestion reports the overflow is not spread with cell density. It sits in five places: the S81 leaf vp block (section 2), one pin bank per S81 col sub-family (section 1), a station column or a station row inside hard cores on QC (section 3), zero-capacity gcells at core pin faces on KV hgi (section 4), and landing-ring cell clusters on all four dies (section 5).
2. **The 23:45 col lever stands and grew (R, read V).** The routed col_h9_r1 kit (DRC 0, TT -274) shows four end classes, not two; one of them (the `s*.q` read loop, 99 ends, -142.6) needs RD_EXTRA=1 inside the hard core `ot_s81_cfg7_seq`, so the core must be re-hardened before any J7 col row can bind. Both private proofs were still in bind at 00:42.
3. **J6 C3 does not carry a GRT fix for leaf (V).** 9 leaf types read at iteration 10 or later hold 13 k to 60 k overflow in the vp block. CFX, relay-site keys and FSTART are timing rows.
4. **Three 23:45 statements are revised:** KV hgi does not "close at CTS and die on a kill only": three hgi types have real flat overflow (section 4). The bank-tap proof and the placement A/B ended without a usable gain (section 6). The cap band is not what stops slice C: c1x_C t6 is at 103 k overflow and -1,572 ps at CTS with 503 k cells; FAM-S81-SLICE reads it as structural (R), and the scan agrees (45 % buffer nets, 36 % station nets, spread over 210 bins).

## 1. S81 col (216 types)

**Timing (R FAM-S81-COL 00:55, FABLE-VISUAL-0030; read V).** col_h9_r1 pv0bdbc3f3 routed, DRC 0, TT -274, FF hold -12. End classes: ROM-face inputs 535 ends (worst -96.6); `s*.q` read loop 99 ends (-142.6); `bn6.e_r0` 17 ends (-110, ROM `pval` output); lane-FIFO hop `t4.xai / t5.xbi` 68 ends (-274, relay rows missing). The renders of col_h9_r1 and col_h10_r0 are clean (GRT max 100 %, overflow 36 and 2); the worst paths are core to core on different taps (-46.7 ROM -> qbank, -60.8 cfg7 `s4` -> ROM). Three S-row taps carry 2,866 to 3,000 sinks against a median of 324.

State of the fix: RD_EXTRA RTL is on main (f9977af51c1 + 8a16e814dc5), bench modes pass and mutants fail (R). J7 delta `delta_c3c_rdx.json`: 216 types, 30,108 rows (22,464 ROM-input + 7,644 q-bus), unproven. `ot_s81_cfg7_seq` is a hard core signed with RD_EXTRA 0; the re-harden kit was in generation at 01:2x (R FAM-S81-COL-R2). Proof B keeps the old core, so it proves the physical closure only.

**Routing (V, new).** 31 col reports. Three single-spot classes, each one pin bank:

| Sub-family | Kits | Overflow | Where | Nets in the overflow |
|---|---|---|---|---|
| col_h9_r0_p1, col_h9_r0_p3, col_h10_r0_p1 | 6 | 54 k to 77 k at iteration 5; col_h10_r0_p1 flat at 4,553 and 4,562 at iteration 20 | N strip, x 650-780, y 1,210-1,296; at iteration 20 one 43-um bin holds 47 to 49 % | ft feed-through 49 to 79 %, `frame_int_o` stations 12 to 42 %; all in open gcells (capacity over 10) |
| col_h9_r0_p4, col_h9_r0_p5 | 5 (+2 earlier reads at 4.8 k and 8.1 k) | 1,271 to 2,084 flat at iteration 10 to 20 | x 1,382-1,470, y 605-650: one bin holds 60 to 71 % | lane pad `u_lpad_xo_i` 21 to 37 %, buffers 28 to 37 %, payload relays 3 to 11 % |
| col_h9_r2, col_h10_r2 | 3 | 1,840 to 9,658 at iteration 5 | S edge, x 302-346, y 0 | synthesised logic 68 to 81 % at the S pin row |

Root cause (I): the ft bit sites and the `frame_int_o` station bank of the N strip share one 130-um window, and the `xo_i` lane pad bank is packed at one spot; each asks for more tracks than the window has. These are the 9 col rows of CANCEL-GRT-FLAT. The other col sub-families read 1 to 99 at iteration 10 to 20 (col_h9_r1, col_h9_r0_p2, col_h10_r1, col_h10_r0_p4).

## 2. S81 leaf (75 types + kv_leaf 5)

(V) 15 leaf types scanned. 9 types read at iteration 10 or later: t29 47.8 k, t44 60.2 k, t66 53.6 k, t69 38.5 k and 39.0 k (two hosts), t73 37.7 k, t17 13.1 k, t53 55.2 k, t54 40.1 k at iteration 25, t5 36.0 k at iteration 25. Four more at iteration 5 (t25, t27, t35, t46: 7 k to 33 k). Low: t36 19 at iteration 30, t11 1,683 at iteration 20, kv_leaf t5 3.
- Place: the vp block. t44: all overflow in x 124-702, y 247-640; the 16 `vp_g_ln_*` lane cores and `vp_u_b0 / b1` stand at x 4-514, y 43-812. The top bin is at x 173-346, y 346-562 on 6 of the 9 types (t29, t44, t69, t53, t54, t5) and at x 1,080-1,210, y 432-778 on t66, t73, t17; I matched bins to core positions on t44 only.
- Capacity: 43 to 70 % of the overflow is in gcells of capacity 6 to 10 and 5 to 14 % in capacity 1 to 5. On the col N strip the same number is 0 %: leaf overflows in gcells that already lost tracks, the gaps between cores.
- Nets: buffer nets 33 to 52 %, synthesised logic 17 to 42 %, the vp source fan `g_hig_*_u_cst_gd_s_*_u_src_*_q[]` 13 to 25 %, ft 5 to 16 % on t44 / t73 / t17. Clock 1 to 2 %.
- Cell count is not the cause: t44 has 194 k non-tap cells at CTS (49 % of the cap).
- Render of t39 (R FABLE-VISUAL-0030): 27 cores packed in the SE two thirds with 8 gaps under 10 um, the N and NW 30 % of the tile holds only reset relays; one vp source register cluster feeds the 16 lane cores from 600 to 800 um away (worst setup -674 and -670 to ln_0 and ln_5); 79 taps with a median of 44 sinks.

Root cause (I): one register bank fans about 1,000 bits to 16 cores through gaps under 10 um, and the buffers that carry and hold-fix that fan fill the same gaps.

## 3. QC: stations in or across cores, and one station column

(V) sle_ctl, 4 kits (cl503337ff, cl67434795 x2, cla4f6f12f): 40.2 k to 50.6 k, station nets 65 to 71 %, top bin (605, 302). Cause and fix are known (R FABLE-FIX-QC-SLE-R2: 879 facing pins across an 8.64-um slit that do not connect to each other; 6,548 station sites inside cores; fix = u_tap west 108 um, u_ctl east 38.88 um, per-bit sites). Variant A (0 cycles) bind + LATCHECK 1,921/1,921 pass at 01:00, proof kit `k_a` in generation; variant B rebind running (R).
(V, new) The same picture on fe / fw, which has no fix lane:
- slw_fe_v1, 3 kits: 50.7 k to 56.0 k at iteration 5, 99.5 % vertical, station nets 60 to 62 %, `pd*_x_fw_i` 14 to 16 %, ft 7 to 8 %, top bins x 259-302, y 605-690, all in open gcells. slw_fe_v2: 8.9 k (station 86 %) and 6.2 k at iteration 10.
- sle_fw_v1 x2, sle_fw_v2: 4.0 k to 7.2 k at the same spot (259, 605), station 56 to 63 %, `u_core.chd_q / hr_q / ch_dn_o` 15 to 20 %. sle_fw_v2 cl69f5e854 and slw_fw_v1 are in CANCEL-GRT-FLAT (7,293 flat).
- PLACE-PRECHECK flags exactly 3 QC V1 fe types (knee) on the current plan (R).
Root cause (I): a north-south station chain west of `u_core` carries more bits per column than the column has vertical tracks. Same class by census (R station_core.py): sle_su_c 4,359, slw_su_c 4,830 and 3,978, slw_st_a_v2 920 station sites in cores.
Other QC reads (V): sle_sc / slw_sc 1 to 66, slw_su_l1 77 to 141 at iteration 30, cbf_q11 5,482 (section 5). coll_core: GRT converged, setup repair floor -82 at `out_data[22]` (R FAM-QC-COLL); the render shows a 1,175-um detour round `u_fs` for 439 um (R).

## 4. KV

(V) hgi: kv3_hgi_v1 11,809 at iteration 15, **83 % in gcells of capacity 0**, buffer nets 72 %. kv3_hgi_v4 40,510 at iteration 10, 43 % in capacity 0, `u_hst*_t*.u_reg.ti_b[]` and `u_hst*_g.u_reg.ti_b[]` 44 %. kv3_hgi_v2 44 k to 50 k flat (CANCEL-GRT-FLAT). Render hgi_v8: 49,891, all in x 0-480, y 950-1,140 at the `ectl_Q` landing core on the W face (R).
Root cause (I): buffers and bus pins sit in gcells with no routing capacity (under the M1-M5 obstruction of a core or landing macro, or in its halo), so every net there overflows on arrival. This is the station-in-core class of section 3 on KV; station_core.py has not been run on a KV plan.
(V) hroot: 6,798 -> 2,207 over 30 iterations, 80 % landing-ring nets (section 5); GRT finished and the kit went on (R FAM-KV-HUB). Port-in hold -303 is the placeholder `sender_ps -385` (R); stands from 23:45.
(R) Cap: pv 16 types split at x 1,080 in D28; hub_C 968 k, hub_Eo 449 k, pv_v3 783 k placed (FABLE-VISUAL). D26 bind green 01:18; D27c G0 green, rebind without the pvw pin running. io_cor_v1: 41 bank taps in D27c, hop max 165.7 um.
(R) Reset and face hops (FABLE-VISUAL): hub_C reset -2,395 over 4,280 um, hub_Eo -747, pc_v3 -1,508 (98 levels); face-to-logic hops pv_v3 2,411 um, hub_C 2,010, pc_v3 1,283; pc_v3 taps t1 10,960 and t7 9,982 sinks.

## 5. Landing-ring clusters (all dies) and HEAD

(V) Overflow made of the internal nets of one `u_cland_*` ring: KV hroot 2,207 flat after 30 iterations, 80 % `u_cland_i_kvs_ctl_o_hroot_Q`, at (1,858, 605); S81 col_h9_r0_p5 pv5c8f2166 22,118, 50 % `u_cland_xo_i`, at (1,382, 994); QC cbf_q11 5,482, 25 % `u_cland_na_i / bc_i`, 35 % in capacity-0 gcells.
(R FABLE-FIX-HEAD-SERDES-R3 01:17) HEAD hd_serdes sdr2c: detailed route died with DRT-0255 on a 3-pin net inside the `coll_i0` landing ring, 3.6 um east of a reserved M1-M7 obstruction column; GRT TT was -103.4. The r16 wave row has the same ring placement.
Root cause (I): the ring cells (FIRM ring flops plus their mux logic) are placed at full density beside an obstruction; the nets are short but there are no tracks or access points left.
HEAD timing (R): the encoder has 11,321 registers on about 25 taps with 50 to 94 ps windows and no CRPR; sdr2d puts the encoder on one pinned tap (`u_enc:clk_t20`) and is in global placement. hd_lep0N (V): two reports, 93,332 at iteration 10 (clock nets 34 %) and 43,051 at iteration 15; 422 k cells and 49 macros in a 330-um band (R).

## 6. What changed since 23:45, checked

| Item | Read |
|---|---|
| S81 col ROM input stage + RD_EXTRA | Confirmed, widened to four rows (section 1). The re-hardened seq core is the critical item. |
| QC sle_ctl core-slit fix | Variant A bound, in proof. The scan shows the class on 8 more reports (fe, fw). No GRT number yet. |
| LATCH-SWAP restore | On main e88352084d; 208,952 routed netlists and 1,241 signed records scanned, 0 swaps (R). Lockup rows stay held until proof6 (t39) and QC2 are no worse than baseline (t39 TT -354.6, 47,483 hold cells; R LOCKUP-STATION-R3). |
| GRT iteration cap 10 | Right for the flat classes: kits read at iteration 15 to 25 still hold 13 k to 55 k (t17, t53, t54, t5), and the CANCEL-GRT-FLAT rows moved under 15 % per 5 iterations. Cost (V): 13 scanned kits were past iteration 10 and at or under 500 (t36 19 at 30, slw_su_l1 77-141 at 30, col_h9_r0_p3 13 at 20, col_h10_r1 451 at 15, col_h9_r2 18 at 15, kv_leaf t5 3 at 20); hroot needed 30 to fall from 4,941 to 2,207. With the cap and no `-allow_congestion` these stop at iteration 10 with a residual that detailed route can usually take. (P) set `OT_GRT_ALLOW_CONGESTION=1` on rows whose iteration-10 overflow is under about 500 and in at most 3 bins; routed DRC decides. Not checked: what `grt183_make.sh` does after a failed round. |
| PLACE-PRECHECK | Clean on S81 J5 / J6 candidates, QC V2b, KV D25e3 / D26 / D27c, HEAD r16; 3 QC V1 fe knee types = the fe class of section 3. It cannot see sections 2, 4 and 5 (they need the placed netlist). |
| KV D26 / D28, S81 svc split | Section 4. svc: the cut exists on main (`OT_SVC_ATTCUT`, bench passes; S_att about 261-269 k and S_rs about 179 k synthesised, R); the unsplit H8 shell places at 555 to 819 k, so S_att may land in the 400-517 k band: lo types need a third part (R). Hierarchy census died twice on lo rs t7 (rc 137, rc 1). |
| Tap pairing, convergence, bank taps, GPL A/B | Bank-tap proof on t39: kit ended without `3_place.odb` (R TAP-GRID-R2); no read. GPL reweight: leaf WNS +85 with TNS -24.3 k -> -44.9 k; col rw4 +87 on one kit; defaults unchanged (R). Both closed as no gain. |

## 7. Levers, ranked by types unblocked

| # | Lever | Types | Measured evidence | Root cause | Fix (P) | Owner |
|---|---|---|---|---|---|---|
| 1 | **S81 col ROM loop: four rows + re-hardened cfg7 seq** | col 216 | Section 1 timing: 535 / 99 / 17 / 68 ends | Half-cycle ROM halves at 0 pin cycles; read loop inside a hard core | (a) re-harden `ot_s81_cfg7_seq` with RD_EXTRA=1, same pins and outline, LEC against RD_EXTRA=1, new signed view; (b) J7 rows: ROM-input stage, q-bus stage, ROM `pval` output register, RLYBR relay rows on `xai / xbi` from relay_depth.py; (c) lane cycles +1 through lanefix.py, strict bind + LATCHECK; (d) proof = one col_h10_r0_p1 and one col_h9_r1 kit to GRT, both ROM directions read. Fix B (move `c*_k` near `s*`) only for the six pairs over 250 um | FAM-S81-COL-R2 (core, rows, proof); S81-J6-ASSEMBLY-R2 (J7, tok/s number) |
| 2 | **S81 leaf: vp source bank per lane core + cores spread north** | leaf 75, kv_leaf 5 | Section 2: 9 types at 13 k to 60 k, in reduced-capacity gcells of the vp block | One source bank fans to 16 cores through gaps under 10 um | RTL: replicate the vp source register per lane core (same cycle, no latency change), seated at that core's pin face. Plan: move lane cores into the empty N third so no gap between two cores with facing pins is under 30 um (moves only, shapes kept). Proof: t44 or t29 to GRT iteration 10, target under 1,000. Until then no leaf volume is expected to route: J6 C3 is timing content | FABLE-FIX-S81-LEAF-R2 (RTL + rows, J7); FAM-S81-MISC (kv_leaf: 40-um street between the lane columns) |
| 3 | **QC stations out of cores and out of one column** | sle_ctl 4, su_c 3, st_a_v2 1, fe 9, fw 10 = 27 | Section 3: 40 k to 56 k on sle_ctl and slw_fe; 4 k to 9 k on fw / fe_v2; census 920 to 6,548 sites in cores | Station sites generated without regard to cores and to the tracks of one column | sle_ctl: variant A or B from its proof into V2. su_c, st_a_v2: the same delta script on V2. fe / fw: split the west station chain into 2 to 3 parallel columns at 40-um pitch (or the knee-site fix), then re-run station_core.py and place_precheck; proof slw_fe_v1 to GRT iteration 10 | FABLE-FIX-QC-SLE-R3 (sle_ctl, su_c); QC-PLAN-R8 (V2 rows; fe / fw has no family lane: assign); FAM-QC-HCST (st_a) |
| 4 | **Type splits over the run cap** | S81 svc 16; KV pv 16, hub_C, hub_Eo, hub_Wo | svc 3.3-5.1 M flat; pv 597-783 k, hub_C 968 k, hub_Eo 449 k placed | one flat run per type | KV: D28 pv split at x 1,080; add hub_C (and Eo / Wo if D27c reads stay over 450 k). svc: write the `OT_SVC_ATTCUT` partition rows (two parts per type, third part on lo), bind one hi type, place both parts; fix the census run first (64 GB was not enough for lo rs t7) | KV-PLAN-R4, OPUS-FIX-KV-PV-R4, FAM-KV-HUB; FABLE-FIX-S81-SVC (J7) |
| 5 | **Reset relay per bank and stations by placed length** | KV hub 5, pc 6, io 2; S81 lepe 4, bk_sel 2, slice C 16, serdes 11; QC cb 17 | Worst path is a reset relay on 7 of 24 rendered kits (-438 to -2,395); face-to-logic hops 1.2 to 2.5 mm on 17 of 24 (R) | one relay per reset leg; face registers placed away from their consumer | `bank_reset_delta --landing --pins --reach-um 300 --local-taps` on the bind of each event (io_cor_v1 form: 41 taps, hop max 165.7). Stations from placed length (one per 300 um) on the buses FABLE-VISUAL names: bk_sel `u_tx / u_q`, lepe `rop -> roq`, c1x_C N-face `xg`, serdes syndrome pipe, cb `bc_i00`. Slice C: rows R1-R4 of FABLE-FIX-S81-SLICEC before any split | RESET-RELAY-GEN-R3; KV-PLAN-R4 / FAM-KV-HUB / FAM-KV-IOPC; S81-BKSEL-R5, FAM-S81-SLICE, FAM-S81-SERDES; FAM-QC-CB |
| 6 | **KV hgi / hg: nothing in zero-capacity gcells at core faces** | hgi 11, hg 8 | Section 4: 83 % and 43 % of the overflow in capacity-0 gcells; 44 k to 50 k flat on hgi_v2 | buffers and `ti_b` pins under core or landing-macro obstruction | Run station_core.py on D27c for hgi / hg; hard placement blockage over the obstruction footprint plus one gcell at the `ectl_Q` and `hst` faces; `ti_b` stations on a row outside the face. Proof: hgi_v1 to iteration 10. Then the measured `sender_ps_types` rows for port-in hold | FABLE-FIX-KV-HGI; KV-PLAN-R4 (D28 rows) |
| 7 | **S81 col pin banks spread** | col_h9_r0_p1 / p3 / p4 / p5, col_h10_r0_p1, r2 (14 kits; type count per sub-family not taken) | Section 1 routing table | ft sites + `frame_int_o` stations in one 130-um window; `xo_i` pad bank at one spot | N strip: ft bit sites on two rows and the `frame_int_o` bank beside, not on, the ft window (ft_spread pitch). `xo_i` lane pad: two rows or double pitch. r2: read again at iteration 10 before any row. Rides the J7 col event of lever 1 | FAM-S81-COL-R2; S81-J6-ASSEMBLY-R2 |
| 8 | **Landing-ring density, and HEAD encoder on one tap** | KV hroot, S81 col_h9_r0_p5 (1 variant), QC cbf_q11, HEAD hd_serdes; every type with a ring beside an obstruction | Section 5: 2.2 k to 22 k of ring-internal overflow; DRT-0255 in the ring on sdr2c | ring cells at full density beside an obstruction | Ring generator: cell padding (one site each side) for ring flops and mux cells and one gcell of keep-out from reserved obstruction columns; proof on sdr2d (local ECO of the boxed cell is the allowed near-miss route for that kit only). HEAD setup: sdr2d one-tap encoder, fallback two adjacent rank taps, then `ENC_PPCYC` (+1 TX cycle) | FABLE-FIX-HEAD-SERDES-R3 (proof, generator change); FAM-KV-HUB (hroot routed read); OPUS-FIX-HEAD-LEP0N-R2 (lep0N band) |

Tap load (FABLE-VISUAL cause 5: col S-row taps at 3,000 sinks, pc_v3 10,960, slw_hc3 9,196) stays open under TAP-GRID-R2 with no proof read; it is not ranked because no measured gain exists yet.

## 8. Stop list (earlier lists stand except where named)

- No col volume and no col sign-off expectation before the re-hardened cfg7 seq view exists. No J7 col row that sets `OT_S81_CFG7_RDX` against the RD_EXTRA 0 view.
- No output-side-only register on ROM `pval` (23:45 stands).
- No leaf volume read as a J6 verdict on routing: the 13 k to 60 k overflow is not addressed by C3. No more GRT iterations, layer grants or NDR drops on leaf: the overflow is in gaps that have no tracks.
- No retry of sle_ctl, fe, fw, su_c or hgi kits on unchanged station sites (CANCEL-GRT-FLAT already says no unchanged retry; the scan shows why).
- No reading of `GRT-0273` (clock NDR dropped) as a clock problem: clock nets are 0 to 2 % of the overflow on the leaf, col, sle_ctl, slw_fe_v1 and hgi kits (hd_lep0N 34 % and slw_fe_v2 clf110fab2 61 % are the exceptions).
- No split of slice C for size before rows R1-R4: c1x_C t6 fails on structure at 503 k.
- No tap pair pass, no load-centre pads, no GPL reweight or `-overflow 0.1` rows (measured, no gain). No lockup rows before proof6.
- No svc kit of the unsplit form for sign-off; the running H8 shell proof measures size only.
- No KV pv, hub_C volume before D28. No `Error 247` row read as overflow.
- No `-allow_congestion` on a kit over about 500 at iteration 10: it moves a flat GRT into a looping detailed route (col_h10_r2: 56 iterations at 17 violations, R).

## 9. Not checked

- The scan is one newest report per job from 30 h of job dirs on 6 hosts; cancelled jobs whose work dir was removed are missing (leaf t43, t47, t55, t62; hgi_v2; sle_fw_v2 cl69f5e854), and plan events are mixed, so a count of kits is not a count of current-plan types. Reads at iteration 5 overstate the flat level.
- Capacity bands are from the report's own capacity field; I did not overlay core outlines, so "gaps between cores" for leaf rests on the capacity band plus the FABLE-VISUAL render of t39, not on a per-gcell geometry check. The 130-um N window on col is from bin positions, not from the plan's ft site table.
- Net classes come from net names in the overflowing gcells, weighted equally per gcell; a `netNNN` buffer net is not traced to hold or setup repair.
- No leaf RTL was read: whether the vp source bank can be replicated per core without a latency or LEC cost is a proposal. The fe / fw station column split was not checked against lane cycles.
- Proof A / B (col), `k_a` (sle_ctl), sdr2d, proof6, the cfg7 seq re-harden and the D27c rebind had no timing or GRT result at 01:45.
- intel2 jobs were not scanned. HEAD has one unsigned type in the count; I did not check which of hd_serdes / hd_lep0N it is.
- Seven read jobs of mine ran through ot-run (units oth-ubuntu-3159794-1795252489 and one `runscan.sh` per host, 4 GB, 1 thread, all rc 0); outputs in `fable-closure-0130/` on each host.
