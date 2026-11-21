# FABLE-PD-KV-2230 (2026-11-20 21:35-21:55 PST): KV D26 (R3e) + D27 (D27b run 6 / D27c) structural review

Reviewer: FABLE-PD-KV-2230 (Fable). Read-only. Nothing cancelled, signalled or patched. One private census through ot-run
(unit oth-ubuntu-1057457-1795239803, epyc8, 5 s): `event_census` + `event_adopt_diff` on the D27b run-6 plan fac662d8c549 against
R3e a9f605cb1acf, tools of the D27c tree (main 389231a5c1 + typed patch). Output epyc8
/srv/opentallas-scratch2/claude/fable-pd-kv-2230/out (plan copy plan_d27b6.json). `plan_geom_census` read from the D27b run-6 compose
(epyc8 kv-plan-r2/d27b/out/census, 21:38). D27c had produced nothing at 21:46: its compose was still queued (section 3, item 1).
Marking: **V** read this round, **R** reported by the owning lane, **I** inferred, **P** proposal.
Clock numbers are post-hook only (`OT_CTS_POST_TIMING`, `OT_TAP_BALANCE done`, pregrt logs); no `4_cts_final.rpt` number is used.
Earlier reviews stand: FABLE-PD-KV-1500, -1840, FABLE-CLOSURE-STRATEGY 21:30.

## 0. Verdict

1. **D27 as composed adds an unproven lockup form to 37 types (V).** Row r5 (LOCKUP-STATION-1130 lever 2) takes die
   `clock.ft_hop_lockup` from 1 type (io_ft_v1) to 32 types and `clock.zl_lockup` from none to 37 types: 5,341 latch hops, 280,204 bits.
   5,158 of the 5,341 latch hops are over 200 um (median 283 um). That is the form the 21:30 stop list forbids (no latch on hops
   over 200 um; no lockup rows to D27 before proof4) and LOCKUP-STATION-R2 itself holds (20:28: proof2 TNS -16k -> -134k, 3,738
   failing latch -> capture ends on 250-400 um hops). It is in both D27b and D27c.
2. **pv (16 types) has a clock problem no D27 row touches (V).** The two pv_v8 proofs, post-hook: `OT_TAP_BALANCE done: 1589 delay
   cells; tap mean insertion 229..983 ps (spread 754, target 250)` (v8c; v8m 236..1003, spread 767). Iteration 1 = iteration 2 (the
   balance stalls). 15 of 24 core clock pins are outside target +/- 20 (clk_c0 239 -> 330, clk_c14 209 -> 373: the same core-tap pad
   overshoot as hgi). `OT_CLOCK_TAPS cap recheck after hop latches: 87 taps over cap 1000` (up to 1,215). D27 adds latches on top:
   `pad_min_stations 16` (+12.2k on pv_v8, R) and r5.
3. **The r12 reset rows are single-pass on the wrong bind (V, tool text).** `bank_reset_delta` reads tap sites from the D25e3 kit
   bound RTL and writes `bank_taps` by tap index; with `--local-taps` the far banks only get a `local_taps_um` terminal and are seated
   "by a second pass on the bind of the new plan". So in D27c the far banks stay on the leaf tap, and the near banks carry D25e3 tap
   indices into a tree that the new terminals re-solve.
4. **hgi closes at CTS; it has never finished GRT (V).** Section 1.
5. **50 unsigned types sit in 8 families; pv + hgi + hg = 35 (V).** Section 2.
6. The per-class CTS proof rule is satisfiable for D27 only for the short classes, and only if the proofs start tonight. Section 4.

## 1. Evidence per family (newest kits, post-hook)

| Family | Unsigned | Newest evidence (V unless marked) | Closes after D26 + D27c? |
|---|---|---|---|
| pv | 16 | v8c / v8m (v8p plan, epyc7 fable-fix-kv-pv-r2/kit): CTS hooks ended 21:14-21:21 after 6.6 h; tap spread 754 / 767; 87 taps over cap; no `OT_CTS_POST_TIMING` line yet. v8q in global placement. 10 held D25e3 rows at place only. | **No.** Tap spread, core-tap pad, tap cap; far-bank reset (item 3); 150 `relay_depth` legs 330-403 um on 15 types untouched (`pv_u_g*_j.sf/.ts*`, path 636-989 um at D 1-2); v6n, v8, v12 not re-sited (no placed geom). |
| hgi | 11 | hgi_v2__cle0015330 a3 (D25e3): `OT_CTS_POST_TIMING setup_ws -3.54 hold_ws -96.69`; after repair TT +1.42, pregrt `port_in 160 ws -82.96, same_tap 0, cross_tap 0`. b8 / b8d (v8): FF hold -82.97 / 1,040 ends, TT +2.45, no head-core end (R). hgi_v4 (D25d): TT +0.21, port_in 1,091 at -82.0. hgi (D25d): TT -312.5, not repaired. | **CTS yes, GRT unknown.** 4 of 4 kits that reached GRT ended `do-5_1_grt Error 247` in extra iteration 2-10 of 30 after 0.8-4.3 h (hgi_v2 cle, hgi, hgi_v4, hroot). kR: GRT TT -310 (R). The port-in class (-83, 160-1,091 ends) is a seam contract, not a kit fix. |
| hg | 8 | none: no hg kit past prelint on D25e3 (8 hold_items). D27b census: 210 HOP rows, 136 forward legs at 380 um (r9 is meant to clear them; not gated). | **Unknown.** No placed or CTS evidence on any plan since D25d. |
| pc | 6 | pc_v3 a3 (plan KV-HG6, epyc7): `OT_TT_SETUP_REPAIR after TT setup wns -1491.99 tns -432433` (repair stalled at 800 iterations), hold cells 21,328; GRT ended with `OT_VCLK_MEASURED_HOLD` error after 28.8 h (intel1 copy). pc split views: re-export has M1-M5 one block, M6 23,768 / M7 9,715 rects = the signed form. | pc x2 (PDN) and pc_v1 x3 (kf): gen should pass. **pc_v3: no.** -1,492 at CTS has no row; cause not read. pc_v1 keeps 5 HOP rows per clone (exact banks, 300-359 um, single-bit fault buses). |
| hub | 5 | hub_Ei a4 in CTS (placed 18:20); Wo / Eo placed only; C, Wi failed at gen / place. | Wo: efault yes; reset only if item 3 is fixed. **Eo: no** (core `u_astk_EN` reset port, form M, D 8: not in the D27c list). C, Wi: gen only. |
| io_cor | 2 | io_cor_v1 a8 DRT-0255 (R); a11 queued on unchanged inputs. io_cor: logs stop at place 11-18. | r10 is a route fix; only a route proves it. |
| sys_c | 1 | placed, held. | Worst path yes; 16 `cland_fstart` groups at -241.8 (place, I) have no row. |
| hroot | 1 | a5 (D25d): `setup_ws -39.71 hold_ws -303.02`; pregrt port_in 7,857 ends at -226.9; GRT Error 247. | **No:** port-in hold of -227 on 7,857 ends needs the seam contract / sender, not a kit. |

Census (V): `plan_geom_census` on fac662d8c549: HOP 409 rows / 38 types = hg 210, pv 150 (all `relay_depth`), hgi 32, pc_v1 15, sys_c 2.
`event_census` against R3e: 0 REGRESS; HOPS_300 improved on 28 types (pv 14-40 -> 0, hub_C 37 -> 0, hub_Eo 25 -> 0, hub_Wo 24 -> 0);
left: hg 18-28 a type, hgi 2-3, pc_v1 5, sys_c 2. `event_census` does not count `relay_depth` or ft slots.
ft slots (V, r5_rows.json): 706 of 813 slots are still 405-era (hop 302-400 um, median 349; pv 505, hub 159, io 19, hroot 14, pc 8, phy 1)
and need +1,168 stations; D27 applies only their latch list, not the stations. Not a D27 item (each is a lane cycle): next event.
`event_adopt_diff` (V): tree pin 315cc722d686 -> main 389231a5c197: LAG 30 (carried), BOTH 14: 8 S81 / HEAD RTL files (no KV use) and 6
die_plan tools (`clock_landing_verify.py`, `clock_landings.py`, `die_plan.schema.json`, `gen_phys.py`, `landing_place.py`, `schema.py`).

## 2. Families ranked by types unblocked (50 unsigned)

| # | Family | Types | Blocking class | Owner |
|---|---|---|---|---|
| 1 | pv | 16 | tap spread / tap cap / core-tap pad; far-bank reset; relay_depth legs | OPUS-FIX-KV-PV-R4 |
| 2 | hgi | 11 | GRT never completed (Error 247); core tap at GRT | FABLE-FIX-KV-HGI |
| 3 | hg | 8 | no evidence at all | FABLE-FIX-KV-HGI |
| 4 | pc | 6 | pc_v3 -1,492; kf; PDN | KV-PLAN-R3 |
| 5 | hub | 5 | Eo form M; reset banks; views | KV-PLAN-R3, RESET-RELAY-GEN-R3 |
| 6 | io_cor 2, sys_c 1, hroot 1 | 4 | route pocket; fstart; port-in hold | KV-PLAN-R3 |

Three families hold 35 of 50; five hold 46.

## 3. What will make D27 refuse or fail (ranked fixes)

| # | Item | Evidence | Fix (P) | Owner |
|---|---|---|---|---|
| 1 | D27c compose not running | queued since 21:10 at default priority (`admissible 0 GB`); the D27b run-6 G0 + bind (2 x 56 GB, `--priority plan`) were admitted at 21:38 in 0 s (V) | Relaunch the compose with `--priority plan`. Decide one D27: two lanes compose it now. | KV-PLAN-R3 |
| 2 | r5 lockup rows | verdict 1 | Drop r5 from D27c (R3e keeps io_ft_v1 only). The D27b run-6 proofs carry r5: read them as the KV lockup proof; rows return in the next event if TNS and hold are no worse. | KV-PLAN-R3; LOCKUP-STATION-R2 |
| 3 | r12 reset rows | verdict 3. R3: u_bout unplaced on all 14 types, 9-16 hierarchical `u_bin_i_astk_*` unplaced on pv, hop over 300 on v3 / v3n (396.8) and v7 (355) | Two passes: (a) `local_taps_um` terminals only; (b) tap sites from the tree of THAT plan (`reset_tree.for_type`, or a bind), then `bank_taps`. Compose check: tap id -> xy equal between the row source and the plan, else refuse. If there is no time, ship (a) + near banks only after that check. | RESET-RELAY-GEN-R3 |
| 4 | pv clock | verdict 2 | Read `OT_TAP_INSERTION` on v8c when the log closes (which taps are at 983). Extend the `OT_TAP_CORE_DIRECT` A/B to pv cores. Tap rows for the 87 taps over cap before `pad_min_stations 16` adds sinks. | OPUS-FIX-KV-PV-R4; FABLE-FIX-KV-HGI (tool) |
| 5 | pv `relay_depth` 150 rows | section 1 | D = ceil(path / 300) - 1 on the 23 distinct `pv_u_g*_j` paths (D 1 -> 2, 2 -> 3), cycles with them. | OPUS-FIX-KV-PV-R4 |
| 6 | hgi / hroot GRT Error 247 | section 1 | Read the guard journal and overflow of one kit (hgi_v2 cle run_route.log) before any hgi route volume; b8 / b8d GRT are the first read. | FABLE-FIX-KV-HGI; FLOW-NOADV-R3 |
| 7 | r9 hg rows un-gated | handoff (R): `kp_o -> u_kt` 2 -> 5 stations | Check the kt latency parameter in param_regen before the bind; drop those 2 rows a type if refused. | KV-PLAN-R3 |
| 8 | hub_Eo form M | not in the D27c list | Add the core reset port row (D 8) or accept Eo stays held. | RESET-RELAY-GEN-R3 |
| 9 | Tool defaults from the re-pin | main now defaults reset-stage lockup latches (2aad63e13d) and lever 2 rows (3e831b7084) (I for KV effect) | State the keys in the plan; confirm the 6 BOTH tool files are main + typed patch. | KV-PLAN-R3 |
| 10 | pc_v3 -1,492 | section 1 | Read its worst path on the KV-HG6 kit; no row exists. | KV-PLAN-R3 |

Asked items: **u_bout** and **local_taps**: not closed by r12 as written (item 3). **io_cor_v1 ft11_o**: r10 is geometrically consistent
(bank 3 from 2 to 12 columns, ft13_i band moved, 0 cycles); it does not refuse; proof = route only. **PDN-0006**: the re-export matches
the signed obstruction form; check that `signed_view_sha_kv.json` carries the new LEF sha.

## 4. One CTS proof per class by D27 apply

Not satisfiable for pv from D27c: the bind needs about 3 h (R3e: started 19:00, still running 21:46) and pv took 6.6 h in the CTS hooks
alone. A D27c pv proof cannot read before about 16:00 on 11-21 if nothing refuses. hgi, hub, sys_c, hroot fit (CTS in 1-3 h).
Launch order (P):
1. **pv_v2** from the D27b run-6 bind (its chain does this) tonight; **pv_v8** on D27c when bound. Longest, 16 types.
2. **hg_v1** from the D26 tree at apply (8 types, no evidence).
3. **hgi_v8** to GRT, not CTS (CTS is proven; b8 / b8d running).
4. **pc_v1__cl23f6a148** and **pc__cl254f2e73** to floorplan PDN only (minutes).
5. **hub_Wo**, then **sys_c**, **hroot**. **io_cor_v1** to route.

## 5. Stop list

- No r5 lockup rows in the applied D27. No D27 volume on pv before a post-hook tap spread under 100 ps on one pv kit.
- No `bank_taps` rows whose tap ids were not checked against the tree of the plan they go into.
- No second D27 compose race: one owner, one tree.
- No hgi route volume before one hgi kit ends GRT without Error 247.
- No relaunch of pc_v3 on KV-HG6 (TT -1,492 at CTS, measured unable to sign); the cancel decision is COORD's.
- No ft-slot re-station (706 slots) inside D27.
- OWNERS-SWEEP rows "running" for kv3_hroot (24.8 h), kv3_io_cor (68 h): their kits ended (FAIL_route 11-19 15:25; logs stop 11-18). Verify before counting them as owned.

## 6. Not checked

- No D27c output exists; every census number is D27b run 6 (same r1-r8 rows; lacks r0, r9, r10, r11, r12).
- Error 247 cause (guard kill or overflow) and the pv taps at 983 ps: logs not read to that depth.
- Whether the reset tree renumbers taps when `local_taps_um` is added (tool text says the second pass is needed; not run).
- The D26 bind result (gate.out held START + RC_ELAB only at 21:46). pc_v3 worst path. sys_c fstart at CTS.
