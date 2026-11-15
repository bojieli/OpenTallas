# FABLE-CLOSURE-STRATEGY 2026-11-14 21:3x PST: closure strategy for S81, HEAD, QC, KV

Read-only review. No build, no kill, no git in the owner checkout. HBM is parked and not covered.

Sources: explorer `/api/elements` and `/api/v1/closure/s81_head` (rtx-pro localhost:8765, 21:16; the explorer is NOT reachable from intel2), `failure_breakdown.py` 21:13, RELEASE_TREE 20:50, COORD-REVIEW-QUEUE 19:30-21:15, COORD-SNAPSHOT 21:15, the lane handoffs, all FABLE-*.md written since 19:30, `docker ps` on the 7 hosts at 21:20. MEASURED = read from one of these. INFERENCE is marked. Not found: handoff files for KIT-OPS-6 and HEAD-REMAP-1 (neither exists), and no KIT-OPS-6 post in the queue.

Blocking gates only: DRC 0, TT setup >= -42 ps, internal FF hold >= 0, bind + LATCHECK + die token.

## 1. Signed delta since 19:27, and ETA per die

I did not re-run the forced AGIdock count (AGIdock is not reachable from this session). The table is the explorer's archive-gated count; the archive records are from the lane ARCHIVED-BOTH posts.

| die | types 19:27 -> 21:16 | plan cores | archived since 19:27 that are not plan elements yet | waiting for archive only |
|---|---|---|---|---|
| S81 | 36 -> 36 of 394 | 62 of 64, no change | `ot_s81_rck_tx` (counts when the RCK split is adopted) | `dsdv_gunit_l1f_bf` g4 (COORD 19:5x: counts on R-MINIMAL; still "not started") |
| HEAD | 19 -> 19 of 26 | 3 of 5, no change | none | `ot_s81hd_elemA_cv`, `ot_s81hd_elemB_cv`: explorer says "signed, pending archive" |
| QC | 4 -> 4 of 127 | 64 -> 65 of 65 (`qc_cland_w515_n_d8_local32_codex`, archived, no build) | none | none |
| KV | 5 -> 5 of 56 | 34 of 34 | 9 ring masters (count as plan cores at kvgeom6) | none |

Type sign-offs on the 4 dies in the 2 h: 0. In the last 12 h: 1 (hd_spn_wshim_rx, late ECO). Every archive record since 19:27 is a core or ring master.

ETA (all INFERENCE; each assumes the named event binds clean and the first rebuild passes; a type build is 8-14 h):

| die | first type sign-offs | all types | what decides it |
|---|---|---|---|
| HEAD | 11-15 evening (hd_ctl, hd_host_e) | 11-16 to 11-17 | rp21z19 bind tonight; hd_lep0N and hd_mesh are NOT in z19 (SKIP_LEP, SKIP_MESH), they wait for rp21z20 |
| KV | 11-15 afternoon (pv, pc on kvgeom6) | 11-17 to 11-18 | kvgeom6 cut tonight; 41 of 50 ring configs still soft (kvgeom7); hub_C split; hgi verdict |
| QC | 11-15 evening (su_l0 on the S3R3b pin site) | 11-18 to 11-19, cbn family later | S3R3b + S4a adoption, kit regeneration, PG keep-out proof; cbn/cbx/cbf have no fix (section 3) |
| S81 | 11-15 evening (first col representative, serdes t12) | 11-18 to 11-20 | B6c clean G0, then B6d (C2, C4), leaf core shift, tap window SDC |

## 2. Closure levers per die, re-ranked

### S81 (358 open types)

| # | lever | closes | cost | one-build proof | owner |
|---|---|---|---|---|---|
| S1 | col clock C1 (core taps: 40 of 79 core clock pins outside +/-20 ps on col_h9_r2) in B6c, then inheritance | r2 representatives end in hold repair today; with S1 the r1 / r2 / r0 representatives credit 216 types from about 26 builds | none | col_h9_r2 cl87f3ff59 rebuilt on B6c: OT_TAP_CORE all pins inside +/-20 ps, hold repair ends | DIE-S81-92 (B6c2 running), S81-COL-INHERIT |
| S2 | col r0 on B3x2d bands + M8 east-west grant (24 p5 / p6 types in B6b) | 72 r0 types through 12 builds | band area | p3 place on B6b: ft0_i band overflow 157,505 -> near 0 | DIE-S81-92, WAVE-RECIPE-1 |
| S3 | col_h10_r1 lane pad (C4) and flush / reset replication (C2) | 24 col_h10 types; C2 is the worst setup endpoint (-360 ps) in col_h9_r2 too | +0 cycles | see section 3, item 2: no mechanism yet | DIE-S81-92 (B6d), needs a generator lane |
| S4 | leaf: tap-port window over related tap pairs only + one balanced landing per leaf partition | 13 of 13 leaf builds fail setup -164 to -267 ps on this | none | STA on the t69 GRT database: -201 -> -114 ps measured by Fable; with the landing, >= -42 | KIT-OPS-5 (SDC), DIE-S81-92 (B6c / B6d) |
| S5 | leaf t34 / t28 / t75 / t13 / t71: core block shift 86.4 um off the faces, bus rows take +1 | 5 types now, the slot class of 61 types later | +1 cycle on at most 8 lane rows | `slot_rule_leafplan.py` TOTAL 0, G0 same set, LATCHECK_RC 0 | S81-LEAF-PLAN (3 `core_place` changes in FABLE-LEAF-FTSLOT section 3) |
| S6 | PG cell keep-out into the S81 die_gen_env | 14 leaf builds on 8 types died in detail-route iteration 1 (DRT-0255) | none | PG-AWARE-1 proofs leaf_t69 / leaf_t25 (intel1, in GRT at 21:13): detail route passes iteration 1 | PG-AWARE-1, KIT-OPS-5 |
| S7 | serdes clock partition: balance 450, tap groups, RXNEG, TXPIPE, island root with `min_early_ps 175` | 11 serdes types | TX +1, RX <= +1 rck cycle | t12 to CTS: u_chn/clk >= 175 ps early, OT_TAP_BALANCE spread <= 60, hold gate FF >= -150 | DIE-S81-92 (B6c3), SERDES-TXPIPE, PLAN-READERS-1 |
| S8 | serdes__t1 RCK split: RXB hold ECO on the routed `rxb_vC`, RXS from the placed `rxs_vD` | serdes__t1 x2 (172 k + 68 k leave the type) | none | RXB ECO: FF hold -35.10 / 219 -> >= 0 | TL-SERDEST1 (queued on epyc7 memory: move it, section 6) |
| S9 | svc define `OT_SVC_ATT_MEM_MACRO`, gunit FWDOWN, bksel_q PG fix | 8 svc_hi types, 2 cores | none | B6c bind elaborates the macro form | DIE-S81-92, S81-CORES-2, TYPE-GUNIT-L1F |

Order: S1 + S2 are in B6b / B6c now. S4 and S6 gate every leaf route, so no leaf route should start before them. S3 has no mechanism and is the item to staff tonight.

### HEAD (7 open types, 2 cores to archive)

| # | lever | closes | cost | one-build proof | owner |
|---|---|---|---|---|---|
| H1 | Archive elemA_cv and elemB_cv | 2 cores, no build | none | INDEX rows on AGIdock + rtx-pro | TYPE-HDCORE-ELEMAB |
| H2 | rp21z19: hd_ctl stations (+1 on 4 lanes), hd_host_w pair move, hd_serdes receiver over the pma_rx pins + rck entry x 2090 + PG floor 400, 34 lanes priced | hd_ctl, hd_host_w, hd_serdes | cycles on the 34 lanes | `head_bind_latcheck z19` 329 / 329; hd_serdes place + CTS: rck insertion < 600 ps | HEAD-99, HEAD-BIND-1, TYPE-HDSERDES |
| H3 | hd_host_e: u_epc tap from pin-referenced arcs + PG face cut (82 strap cuts in the proof) | hd_host_e | none | PG-AWARE-1 proof `hd_host_e_ws` (intel2, CTS at 21:13): TT >= -42, DRC 0 | HEAD-99, PG-AWARE-1 |
| H4 | rp21z20 remap: hd_lep0N two tx rows + hd_mesh pair move, with `landing_remap.py` (merged 21:05) renaming the reset / forwarded-clock stages by xy | hd_lep0N, hd_mesh | none | prep passes without "no registered wavefront driver" / "not a planned physical tap input" | HEAD-REMAP-1, HEAD-99 |
| H5 | hd_spn: one build under plan priority | hd_spn | none | the build | HEAD-99 |

### QC (123 open types)

| # | lever | closes | cost | one-build proof | owner |
|---|---|---|---|---|---|
| Q1 | Adopt S3R3b, regenerate the kits on the swapped `relay_bay.py` (OT_MAXWIRE_UM 120, not 33 / 62 / 75) and the nearest-raw-copy reset start | unblocks about 90 types that sit pre-route; removes the 1,346-1,429 um reset-start wire (worst pair in 13 kit dumps) | none | one sc_v3 kit: no reset wire over 600 um | DIE-QC-103, KIT-OPS-5 / 6 |
| Q2 | S4a: one internal station per long lane (42 lanes) | fw x6, su_c x2; stm x6 with S4b | +1 cycle on 42 lanes | fw_v2 GRT STA: WNS -446 -> >= -42 | DIE-QC-103 |
| Q3 | su_l0 on the S3R3b pin site (pin off the M6 PG pair) | 5 su_l0 types; the ECO route is closed (section 3, item 3) | none | PG-AWARE-1 proof `su_l0` (intel2, GRT at 21:13): DRC 0 | DIE-QC-103, PG-AWARE-1 |
| Q4 | PG keep-out + die phase as the QC default | 12 east types that end in DRT-0255 | none | fw_a / fw_b / fw_c, slw_hc2, coll_n_pgtt proofs | PG-AWARE-1 |
| Q5 | vmr view v2 (pin access window) into the wave views | su_c x3 (DRT-0073) | none | A/B already reproduced and fixed on one instance | QC-CORES-HEAD |
| Q6 | st_a / st_b region masters and hc lane masters | about 20 types under 280 k cells | area | 6 sta_region_nb0 kits running (TL-QCSTAV2) | TL-QCSTAV2, OVERSIZE-1 |
| Q7 | cbn / cbx / cbf | 16 types | unknown | none exists: section 3, item 1 | none |

### KV (51 open types)

| # | lever | closes | cost | one-build proof | owner |
|---|---|---|---|---|---|
| K1 | kvgeom6: early core taps + `tap_pair_affinity` + u_pvfin slot + signed ring masters | pc x6, io_ft_v1, io_cor x2, hroot; pv / hg / hub as their rings sign | ring band area | canary 2 on a kit regenerated from plan_aff2: 8 of 8 OT_TAP_CORE within 20 ps (canary 1: 0 of 8, 305-974 ps) | KV-102 |
| K2 | STB-EDGE-1 in the generator's `subtree_balance.tcl` (proved: w269 and w257 signed, fclk spread 437 -> 16 ps) | every ring core with WFALL=1 and CONTROL_STATUS_COPY=1 (INFERENCE: also HEAD rings) | none | done on 2 cores; not yet on main | OVERSIZE-1, KIT-OPS-5 / 6 |
| K3 | The other 41 ring configs to sign-off | pv x16, hg x7, hgi_v6 / v7 / v8, hub x4 (30 types) | none | first pv_v1n on hard rings: movable about 205 k | CLAND-MACRO-1, OVERSIZE-1 |
| K4 | hgi / hg: no signal M7 over the 16 head cores | 11 hgi + hg_v3 | none | fh2 A against C (intel1, section 3, item 5) | TYPE-KVHGI2 |
| K5 | kv3_sys_c macro clock pin guard (`clock_taps.tcl` line 236) | kv3_sys_c (macro clock 548 ps against launch 18 ps) | none | CTS only from the placed database | KV-102 |
| K6 | kv3_hub_C: u_pvfin (267 k, 54 %) as a hard core | hub_C | halo area | `kv3_pvfin_s` kit (epyc9 oversize-1/kvr) | OVERSIZE-1 |

## 3. Open structural failures with no fix in flight, or more than 2 rounds

1. **QC cbn / cbx / cbf, 16 types: no fix in flight. NEW FABLE REVIEW NEEDED.**
   Evidence (MEASURED): three stacked blockers on cbn_q00 a7: GRT overflow 90,044 with 9,998 gcells at capacity 0 over tiles t00 / t11; CTS setup -775 ps on 2,046 endpoints (a zero-logic pipeline stage arriving at 1,622 ps); cross-tap hold -112 to -237 ps on 7-30 k endpoints. The mirror event S3R4 was cancelled at 20:10 because the plan connectivity does not show the consumers; the decision was handed to a place-only what-if. Both what-ifs FINISHED (epyc2 `/srv/opentallas-scratch3/claude/type-qccolln/cbnq00/{asis,mir}/cbn_q00__cld7bf7197`, `3_place.odb` 20:42 and 20:34). Their ot-run clients were killed by a pattern kill on intel2 (`pkill -f 0`), the waiter posted "ended" at 20:03 while they still ran, and nobody has run the GRT comparison. Meanwhile 9 wave routes of the family run unchanged.
   Fix: run GRT on both placed databases now (30 min each); give both to a Fable review that settles tile orientation, the split-pin re-export for u_t00, and anchors for the u_d3 stages in ONE plan event.

2. **S81 col_h10_r1 lane pad (C4) and flush / reset fan-out (C2): diagnosis done, no mechanism. No new review; needs a lane.**
   Evidence (MEASURED, FABLE-TYPES-S81-COL): 44,569 overflow in 2,509 gcells, all at x 680-900, y 0-120 = `u_lpad_frame_int_i1`, 5 stages x 1,265 bits sited along the bf wall; C2 worst endpoint -360 ps at GRT. DIE-S81-92 (21:1x): "C4 and C2 are NOT plan data", moved to B6d, with no way to express them.
   Fix: a generator change (lane-pad stage siting key read by `kit_istations.py`; per-region replication of the last flush stage in the bind generator). Assign it to PLAN-READERS-1 or a new lane tonight; without it B6d has no content.

3. **QC su_l0: 4 rounds (DRC-only route, stub ECO, RECT patch + late ECO x4). The structural fix is in flight (S3R3b); the ECO tool is broken.**
   Evidence (MEASURED): all 5 NEARMISS-ECO runs since 20:28 end "ECO t5 route / clock-freeze check / finish failed" and `prd_result.json` is `{"passes": []}` (epyc2 `/srv/opentallas-scratch3/claude/nearmiss-eco/slw_cl76fb247e_a4/eco/i1t/prd_result.json`). Zero passes ran: this is a flow fault, not a design verdict. slw_su_l0 cl76fb247e stood at TT +21.39, FF +0.93, DRC 3.
   Fix: one owner debugs `prd_mk.sh` under the admission_tools copy (INFERENCE: tool copy `7513682b92f0b438b5cb` is stale against the eco_loop that calls it). No review.

4. **S81 leaf t34 / t28 / t75 / t13 / t71: 5 plan rounds (B4L, B5, cp15, B6s, B6t) without closing. Fix issued 21:04, not yet applied.**
   FABLE-LEAF-FTSLOT: more stations cannot close (10 S0 registers sit under near-face cores; closed strips 535-1,048 um against a 360-um hop). Core shift closes the feed-through slots at the same station count in 4 of 5; `--take-regs` must accept bus rows. No new review. 6 routes of these types run on the unchanged plan (section 4).

5. **KV hgi: 3 rounds (re-floor, fd forms, fh2). Verdict orphaned.**
   The fh2 A / C containers are up on intel1 (`fh-A-3702488`, `fh-C-3703120`, 2 h, GRT extra iterations); their clients on intel2 were killed by the same pattern kill, so the waiter reading `~/kvhgr/fh2_{A,C}.log` never ends. TYPE-KVHGI2 must read the result from the kit dir. If A fails: Fable review (the lane's own rule). The wave launched hgi_v3, v6, v8 in the last 5 minutes on kvgeom5.

6. **HEAD hd_lep0N and hd_mesh: not in rp21z19.** hd_lep0N relayout: GRT overflow 24,813 flat from iteration 5 (MEASURED, FABLE-TYPES-HEAD). Both were skipped in z19 because a macro move renumbers the density-derived reset and tap names. `landing_remap.py` is merged; rp21z20 is the fix. Standing rule: Fable review of z20 in parallel with its bind. No extra review now.

7. **S81 serdes: more than 4 rounds (kitH, kitH2, kitI, kitI3, t4B3, t14 i1).** Fix in flight in B6c3, with two open ends: the island root / `min_early_ps` needs a gen_phys reader (ASK to KIT-OPS-5, no answer seen), and FABLE-PLAN-B6B F2 (14 TX rows raised by hand; LATCHECK cannot see TXPIPE / RXNEG). No new review; B6c gets its own.

8. **Cross-tap hold as a class in QC (INFERENCE that it is one class):** su_c -397 ps on 3,667 register-to-register endpoints (MEASURED, QC-CORES-HEAD 21:07), cbn -237, st_b_v1 -101. KV fixed the same class with `tap_pair_affinity` + early core taps. QC has no such item in S4a / S4b. Put it in the item-1 review.

9. **PG keep-out proof: 3 h, no form has reached detail route** (first set sat in inline LEC until 20:55). It gates lever S6, Q3, Q4, H3 and the COORD leaf-route hold. Give the 12 proof forms plan priority.

## 4. Stop list (dead-end builds running at 21:20)

Stop by exact container / ot-run job, never by pattern. `ot-jobs/<job>/work` is the wave attempt mount.

| host | container | job dir or kit | why it cannot close |
|---|---|---|---|
| intel2 | dpkit-hd_lep0N-622976 | `/srv/opentallas-scratch2/claude/ot-jobs/hd_lep0N-place-tolerant-swine-622399-1794718821` | relayout does not route; fix is rp21z20 |
| intel2 | dpkit-hd_serdes-616924 | `.../ot-jobs/hd_serdes-place-tolerant-swine-616228-1794718808` | unchanged form; rck tree 33 levels, setup -2525; fix is rp21z19 |
| epyc2 | dpkit-hd_host_e-2325356 | `.../ot-jobs/hd_host_e-route-dear-crayfish-2321600-1794719836` (wave attempt_13, generated 21:07, before the PG rule merge) | u_epc tap 42 ps against 442: setup -395 on 564 endpoints (INFERENCE that a13 is unchanged) |
| intel2, epyc10 x2, epyc2 x3 | kv3_pc_v1__cl4ea58a5c-690474; kv3_pc__cl254f2e73-86302, kv3_pc_v1__cl23f6a148-4100220; kv3_pc__cl5a95b461-2695086, kv3_pc_v1__cl7f648944-2777314, kv3_pc__cl5a95b461-2069926 (`/srv/opentallas-scratch3/claude/type-kvpcf/cl5a95b461`) | `.../ot-jobs/kv3_pc*` | kvgeom5 has no early core taps: canary 1 gave 0 of 8 core pins in window; FF hold -385 to -441 |
| epyc2 | kv3_hg_v3-2651474 and -315863 | `/srv/opentallas-scratch3/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/kv101ns_3465fe9/items/kv3_hg_v3/attempt_13` and `.../kv102sem_ftgrid/items/kv3_hg_v3/attempt_14` | two attempts of one type, 13 h and 7 h, on two superseded events |
| epyc2 | kv3_hgi_v5-2635186 | `.../kv102sem_ftgrid/items/kv3_hgi_v5/attempt_6` | 13 h, superseded event |
| intel2, epyc10 | kv3_hgi_v6-1019937, kv3_hgi_v8-1051012, kv3_hgi_v3-240765 | `.../ot-jobs/kv3_hgi_v{6,8,3}-place-*` | soft ring bands 0.4-2 % over reserve (v6 / v8) and over-core congestion, verdict pending (INFERENCE for these attempts) |
| intel2, epyc9, epyc2 | ot_s81sl_leaf__t28-352780, -3490791, -904300 | `.../ot-jobs/ot_s81sl_leaf__t28-route-tolerant-swine-339335-1794717881`, `.../ot-jobs/ot_s81sl_leaf__t28-route-renewed-glider-3430447-1794708999`, `/srv/opentallas-scratch2/claude/type-s81-t28/f1` | three copies; slot class, needs the core shift |
| intel2, epyc9 | ot_s81sl_leaf__t71-3743115, -2051062 | `.../ot-jobs/ot_s81sl_leaf__t71-route-*` | two copies; same class |
| intel1 | ot_s81sl_leaf__t13-2548513 | `.../ot-jobs/ot_s81sl_leaf__t13-route-key-cardinal-2537004-1794708262` | same class |
| intel1 | serdes__t1__clfe1f0815-4089644, serdes__t14-2538819 (`/srv/opentallas-scratch2/claude/tl-serdest14/i1`), serdes__t15__cla2127225-1054791 | `.../ot-jobs/serdes__t1__clfe1f0815-route-key-cardinal-4076191-1794711690` | recovered-clock structure; t14 stuck at -454.9 ps for 810 repair iterations ("no new information expected", its own lane) |
| epyc10, epyc9 x3, epyc8 x3 | cbf_q00__cl1b5a6458-2300669 (`.../s29q103S/items/cbf_q00__cl1b5a6458/attempt_24`, 14 h); cbf_q00__cl870de686-1307360, cbf_q00_s2-3955125, cbn_q11__cl5cc92dfe-2152587; cbn_q01__cldd6ea846-2995737 and -3562777 (two copies), cbn_q01__clab6e67f2-2920128 | `.../ot-jobs/cb*` | section 3, item 1; attempt 24 |

Also stop, as classes: every new S81 leaf route on a kit without `OT_PG_CELL_KEEPOUT` (leaf t55 attempt_5, intel1, submitted 21:13, has `OT_PG_TRACK_TRUTH` only); every NEARMISS-ECO launch until item 3 is fixed; QC wave launches on the events s29q103S / s29q103S3R (sle_hc1 cl7d360508 launched 21:14, slw_su_c 6 replicas 21:07) until S3R3b is adopted.

Keep running: the 12 PG-AWARE-1 proofs, fh2 A / C, the 6 sta_region_nb0 kits, hd_ctl route (epyc7), the RCK RXB / RXS jobs, all plan binds.

## 5. Advice not followed

| advice | from | state | who |
|---|---|---|---|
| No relaunch of unchanged kits after a deterministic failure | 19:27 section 6, FABLE-WAVE-REVIEW | Not followed: cbf_q00 attempt_24, hd_lep0N attempt 16, kv3_hg_v3 a13 + a14 at once, 3 copies of leaf t28 | wave config: KIT-OPS-5 / KIT-OPS-6 (hold_items), KIT-WAVE |
| HEAD stop list: no hd_serdes / hd_lep0N relaunch before the event | FABLE-TYPES-HEAD 20:03, HEAD-99 20:35 | The lanes stopped them; the wave relaunched both at about 21:00 | KIT-OPS-5 / 6: no hold entry |
| No new leaf route without the keep-out | COORD ruling 20:15 (C) | Not followed: t55 a5 at 21:13 | KIT-OPS-5 / 6 |
| kv3_pc: wait for the early-tap plan | 19:27 K2, FABLE-PLAN-EVENTS | Canary done as asked; 6 pc kits still launched on kvgeom5 | KIT-OPS-5 / 6, KV-102 (no hold asked) |
| QC: regenerate before building (Q1) | 19:27 | Partly: `relay_bay.py` swapped 20:14; the 12-kit regeneration is "NOT done" (KIT-OPS-5 20:23); the wave still builds old events | KIT-OPS-5 / 6, DIE-QC-103 |
| QC `cl` variant plan diff (Q7, 1 h, up to 53 builds saved) | 19:27 | Not done, no post | DIE-QC-103 |
| Die GRT + related-pair STA in parallel on the current plans (X2) | 19:27 | HEAD: done (HEAD-BIND-1, strict bind PASS on rp21z18d). S81, QC, KV: no run, no lane | COORD |
| cbn mirror "must not stay dropped without a replacement" | FABLE-TYPES-QC-EAST 19:58 | Dropped; the what-if result is unread since 20:42 | TYPE-QCCOLLN, DIE-QC-103 |
| Tap-window SDC change for leaf (order A) | COORD 20:15 | No post since | KIT-OPS-5 (split to KIT-OPS-6: no handoff file, no post) |
| STB-EDGE-1 into the generator; audit `pair_skew.tcl`, `orfs_hold_mm.tcl`, `vclk_measured_hold.tcl` for the same edge error | FABLE-KVRING-HOLD | Proved on 2 cores from a private file; no branch, no audit seen | OVERSIZE-1, KIT-OPS-5 / 6 |
| Stage-peak admission accounting (X1) | 19:27 | Shipped disabled. Kills are 0 in the last hour, so it is not urgent | ADMIT-TUNE-1 |

Two process faults that hide results:
- A second pattern kill ran on intel2: `bash -c cd ~/coord; pkill -f 0` (about 19:57). It killed ot-run clients; the units kept running. The block-pkill hook exists only on rtx-pro. Every intel2 client log that ends "interrupted (signal 15 ... pkill -f 0 ...) STILL RUNNING" has a waiter that will never fire: cbn what-ifs, fh2 A / C, three OVERSIZE-1 ring kits (re-attached by that lane). Sweep `~/*/**.log` on intel2 for that line and re-attach.
- DIE-S81-92 stamps its posts about 2 h ahead of the hub clock ("23:1x PST" at 21:1x). Time-window scans and the snapshot's "no later COORD post" list misorder them.

## 6. Fleet use (COORD-SNAPSHOT 21:15 and the brief)

| host | admits | load / threads | waiters | reading |
|---|---|---|---|---|
| epyc2 | 416 GB | 56 / 128 | 0 | STARVED: the largest free block on the fleet |
| intel2 | 446 GB | 121 / 112 | 0 | memory free, CPU full |
| epyc10 | 105 GB | 199 / 96 | 0-2 | CPU overloaded 2x, no queue |
| epyc8 | 158 GB | 169 / 96 | 0 | CPU overloaded |
| epyc7 | 122 GB | 76 / 96 | 26 (330 GB) | memory-bound with idle CPU; plan jobs and the RCK jobs are pinned here |
| epyc9 | 53 GB | 268 / 96 | 22-36 (330 GB) | overloaded on both; 177 running |
| intel1 | 162 GB | 131 / 112 | 15-19 (292 GB) | memory-bound |

- The queue is not short of memory, it is pinned. 63-81 waiters sit on epyc7 / epyc9 / intel1 while epyc2 + intel2 admit 860 GB. Jobs are pinned to the host that holds their tree (S81 plan tree and `tl-serdest1/keep` on epyc7, QC tree6 on epyc9). Copy the kit to epyc2 and launch there: first the RXB hold ECO, RXB-M and RXS (TL-SERDEST1), then the QC region masters queued on intel1 / epyc9.
- The stop list frees about 35 containers, most on intel2, epyc2, epyc9 and epyc8. Six are duplicates of the same type.
- epyc9 at load 268 on 96 threads slows every job on it by about 3x (INFERENCE from load alone): route new wave jobs away from it until it is under 150.

## 7. Previous version (19:27), short

- Ranking then: S81 col inheritance first (216 types from about 26 builds), QC kit regeneration first, KV pc / hgi proofs from existing databases, HEAD die bind.
- What moved: inheritance covers r0 (merged f7bca8ad422, siblings cancelled); HEAD strict bind + LATCHECK driver exists and passed on rp21z18d; KV ring hold was a measurement error and is fixed (9 masters signed); S81 B6a G0 has 0 new errors against control (250 total, 24 gone).
- What was wrong then: I ranked the su_l0 ECO as "the only sign-off available tonight"; all 4 ECOs failed on the tool. I counted col r1 / r2 as blocked only by routing; r2 routes clean and fails on core clock taps (C1).
- Not checked in this version: the forced AGIdock count; whether the wave's hd_host_e attempt_13 and the hgi attempts carry any change; the KIT-OPS-5 tap-window work (absence of a post is not proof of no work).
