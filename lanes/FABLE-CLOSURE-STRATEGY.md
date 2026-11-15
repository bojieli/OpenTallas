# FABLE-CLOSURE-STRATEGY 2026-11-14 19:3x PST: ranked closure levers for S81, HEAD, QC, KV

OWNER: close the 4 dies as soon as possible; performance, area, cycles and token rate may be spent. HBM is parked and not covered.

Read-only synthesis. Sources: explorer `/api/elements` and `/api/v1/closure/<die>` (19:16), RELEASE_TREE 19:09, FABLE-HARD-S81 / -QCHEAD / -KV, FABLE-PLAN-EVENTS, FABLE-WAVE-REVIEW, FABLE-REVIEW-COL, and the lane handoffs named per lever. No build was run for this file. "Expected" numbers are my estimates from those sources unless marked MEASURED. No predecessor file existed.

## 0. Where the count is, and what it says

| die | types signed | open types by family (explorer) | die gates (RELEASE_TREE) |
|---|---|---|---|
| S81 | 36 / 394 | col_h9 / col_h10 216 (0 signed), leaf 75 + kv_leaf 5, dsdv / svc about 40, serdes 11, slice_station 10, others 6 | bind PASS, GRT not run, STA blocked, clock todo |
| HEAD | 19 / 26 | hd_spn, hd_serdes, hd_mesh, hd_lep0N, hd_ctl, hd_host_e, hd_host_w; cores elemA / elemB | bind BLOCKED |
| QC | 4 / 127 | 87 before route (43 at start, 43 at kit_rtl), 34 waiting on the plan delta; 67 layouts when `__cl` / `__pv` are stripped | bind PASS, GRT / STA / clock blocked |
| KV | 5 / 56 | pv 16, hgi 11, hg 8, pc 6, hub 5, io 3, others | bind PASS, GRT not run |

Three facts set the ranking.

1. **55 % of the open S81 types are one family with about 26 layouts.** All 36 signed S81 types are slice_station. Not one of the 216 col types is signed. The explorer names 20 `__pv` groups holding 210 of them, plus 6 singletons. `pv` is the ROM image only (FABLE-REVIEW-COL point 5, S81-TYPE-MEASURE addendum).
2. **The wave signed off nothing in 10 h, and most of that is not design.** About 60 % of 247 route ends were recipe faults: 56 host memory kills, a clean global route thrown away, global route fatal on tiny overflow, stale kits (FABLE-WAVE-REVIEW section 2).
3. **Setup is rarely the blocker.** The explorer has one S81 row "routed, not signed (timing)". Relaxing the 833 ps clock closes few types (section 5, lever X3). The owner's new freedom is worth most as **area and cycles**: wider bands, hard ring macros, +1 register where a core move or a long face-to-face path fails a reach limit.

## 1. S81 (36 / 394)

| # | lever | closes (expected) | cost | proof in one build | owner lane |
|---|---|---|---|---|---|
| S1 | **Inheritance for all 216 col types**, not only r1 / r2. Today S81-COL-INHERIT covers 144 ids (9 representatives + 4 singletons). The explorer shows the same `pv` structure in r0: col_h9_r0 p1-p6 and col_h10_r0 p1 / p4 are 72 ids in 12 groups. | 216 types from about 26 builds (190 builds saved). r1 / r2: 144 from 13. r0: 72 from 12-13. | None in perf or area. Per sibling: LEC against its ROM image, via-mask DRC on the swapped ROM GDS. | `col_inherit.py groups` on the r0 ids: expect 12 groups with one hard-core signature and one param key set each. Then the first representative that signs credits its group. | S81-COL-INHERIT (extend), KIT-OPS-5 (hold r0 siblings), ROOT-MERGE-63 (branch `claude/s81-col-inherit-1114`) |
| S2 | **Make the r1 / r2 representatives route.** Measured cause for r1: 126 relay nets cross the bf wall (col3_c, M6 capacity 0) and 304 buffers sit in an 8.6-um slot; flips + slot blockage + buffers moved gave overflow 0 (FABLE-REVIEW-COL). Spend area: an east-west M8 grant over the macro rows, or a through street per macro row. | The 13 r1 / r2 layouts, which is 144 types through S1. Without S2, S1 inherits nothing for r1 / r2. | Area: one street per macro row (about 43 um each) if the M8 grant is not enough. | GRT only, from the r1 representative `4_cts.odb`, with `relay_polylines` + slot blockage: overflow 0 (was 26,909). | DIE-S81-92 (event B4), FIX-RELAYPOLY, TYPE-COLH9R1 |
| S3 | **col r0 class fixes**: band event B3x2d (band fill 1.041 to 0.52), resistance-aware off for every kit with hard macros, east-west M8 grant or station polyline for p6. | The 12 r0 layouts, which is 72 types through S1. | Area: deeper landing bands. | Place-only run of `fb_f9acce4c` on B3x2bd (10 min). Two 1-h GRT runs on the p2 `ff` database, with and without resistance-aware. | DIE-S81-92, KIT-OPS-5, TL-COLH9R0P* |
| S4 | **Leaf: use cycles instead of searching for a legal core spot.** Four plan events failed because every core move broke the 412 / 864-um link limits or needed +1 register. Apply the move and take the register: t34 (`leafup_o0` +1, a die lane change), t45 (strip to about 130 um), the 16 "L2 up" types and the 3 "+regs not applied" types of B4L2, t68 `ln_3`. First the plan-only rule of FABLE-HARD-S81 section 2: no station or band in a slot narrower than 86.4 um beside an M7-opaque core. | Up to 80 leaf types. 47 are in route now; I expect most of the ve-pair and edge-squeeze types (t34, t9, t73, t75, t28, t71, t51, t13, t7, t10, t74, t45) to fail there without this. | Cycles: +1 on the touched lanes (t44 +20 and t4 +20 station rows, t45 +52 already in B5). Token latency rises by the same count; rate is unchanged. | t34 on B6 with the stations moved out of the west slot: GRT vertical overflow over `ve_m` from 7.2 k to about 0, west slot below 5 k. | S81-LEAF-PLAN (B5 bind, B6), TL-LEAFT34, DIE-S81-92 for the lane table |
| S5 | **M9 grant for leaf and slice partitions** (code exists: WAVE-RECIPE-1 32d070ea315, held until the die M9 shapes are imported). Needed only where S4 leaves overflow over the ve / vs / vn cores. | Residual ve-pair leaf types (t9, t73, t75 class). | Routing resource: the type keeps about 85 % of M9 tracks (t30 static proof). No perf cost. | t30 rebuild with `OT_GEN_M9_GRANT=1`: no short against the die M9 straps (42 shorts + 14 spacing today on the signed t30 form c). | WAVE-RECIPE-1, DIE-S81-92 |
| S6 | **slice_station on B4L4 bands** (landing window at 10 um2 per bit). Scope the swap to the unsigned types. B4L4 touches 143 bands in 44 slice_station types, and the 36 signed types are all slice_station: a full swap re-keys them. | 10 open slice_station types (t27, t28, t36, t47 and others). Protects 36 signed. | Area inside the type (band 28 to 55 um deep). | t28 first kit on B4L4: GRT overflow 0 without allow-congestion, no hot gcell within 20 um of the face. t29: resume attempt 16 from `4_cts.odb` with 64 GB. | S81-LEAF-PLAN, DIE-S81-92, KIT-OPS-5 |
| S7 | **svc hi: `OT_SVC_ATT_MEM_MACRO` in the S81 bind defines** (macro form already in the RTL, LEF and lib already in the kit). Bridge: word-wide flop emit (pbuf synth 22 s). Stop the mem2reg form. | 8 svc_hi types (rs t1-t6, pvso t1 / t2); also takes a 508 k-cell type under the size that closes. | Area: 4 small SRAM macros per type. No cycles (cycle-exact form). | Re-elaborate with the define: bound file holds `dsdv_svc_mem_*`, no native pbuf / sw / wq / qmem; `1_2_yosys.log` passes pass 3.16. | DIE-S81-92 (B4 svc), TYPE-SVCMEM |
| S8 | **serdes: +2 TX stages and +1 RX stage**, not +1 (3,080 um at 0.44 ps/um needs 3 segments). `LANE_TXA` / `LANE_RXI` parameters already pass bench16. | 11 serdes types (t14: setup -719 ps at CTS). | Cycles: TX +2, RX +1 inside the column. | t14 kit with both defines: TT setup at or above -42 ps after CTS (was -718.9). | SERDES-TXPIPE, DIE-S81-92 |
| S9 | **dsdv_*_C oversize (622 k movable)**: shared xs4 engine as a hard child core, `OT_GPL_SPARSE_UTIL = 0.05`. gunit bf: setup -208 ps is cone depth, so take +1 pipeline stage (FWPIPE). | About 20 dsdv types, gunit, bk_sel, 2 open cores. | Cycles: +1 in gunit. Area: none. | dsdv_slice_iq_C place with the sparse cut: movable below 400 k (KV proof: 650 k to 293 k). | DIE-S81-92, FABLE-S81-CORES, OVERSIZE-1 |

S81 order: S1 + S2 + S3 first (216 types, about 26 builds, one plan event already in bind). S4 and S6 in the same B5 / B6 chain. S7-S9 are independent lanes.

## 2. HEAD (19 / 26): seven types, each with a known cause

| # | lever | closes | cost | proof in one build | owner lane |
|---|---|---|---|---|---|
| H1 | **hd_spn: one build that is not killed.** No open design cause; every build since the pin move died of host memory. Admit it with `--priority plan` (no memory limit, protected from the killer). | hd_spn | None. | The build itself. | HEAD-99, ADMIT-TUNE-1 |
| H2 | **hd_host_e: set the `u_epc` clock tap from the pin-referenced arcs** (latency 330-400 ps instead of 42), cut the parent M6 PG stripes 1-2 um before the core's pin face, move `rst_start_raw_0` / `_2` off the PG pair. | hd_host_e (setup -395 ps on 564 endpoints, 64 DRC). | If the output side then fails: re-sign the HE-EPC core with input registers clocked at the output depth. | STA only on the routed `ws` database with the latency set (minutes): both budgets positive. Then one reroute from the floorplan: DRC 64 to 0. | HEAD-99 |
| H3 | **hd_ctl (rp21z18): SRAMs as a 2 x 2 block with 43.2-um streets, plus one register on the fixed face-to-face classes** (about 280 source flops with captures beyond 405 um that the macro move cannot shorten). | hd_ctl | Cycles: +1 on `h_tx_o`, `rxi`, `lepk_o0`, `n_rx_i`. | G0 reach on rp21z18: 0 captures above 405 um (413 today); `cland_band_fit` passes for `a_rx_i`. | HEAD-99 |
| H4 | **hd_serdes: secondary clock radius 210** (form A passed CTS at 202.449, in route; form B queued). Put the overlay into the wave source when one signs. | hd_serdes | None. | Form A sign-off. | TYPE-HDSERDES |
| H5 | **hd_mesh and hd_host_w: hold repair before global route; hd_host_w LEC**. | 2 types | Area: hold buffers, under 1 %. | Rebuild with `OT_PREGRT_FF_HOLD=1`: internal hold at or above 0. | HEAD-99 |
| H6 | **hd_lep0N (not started, about 365 k cells)** and cores elemA / elemB (4 typed-kit forms queued). | 1 type, 2 cores. | None known. | First kit. | HEAD-99, TYPE-HDCORE-ELEMAB |
| H7 | **Die bind is BLOCKED.** HEAD is the die nearest to done, so its die gates decide its date. Run the die bind, die GRT and related-pair STA now on rp21z16 with plan-model views for the 7 open types. | HEAD die gates | None. | Bind errors 0, LATCHECK pass on rp21z16. | HEAD-99, a DIE-PROTO successor |

Also: `hd_spn_end` attempt_6 carries the pin moved by 8.64 um, which is two PG pitches; it will end with the same 3 DRC. Move it 2.16 um.

## 3. QC (4 / 127)

| # | lever | closes (expected) | cost | proof in one build | owner lane |
|---|---|---|---|---|---|
| Q1 | **Flow first: bump the QC wave source and regenerate every kit before CTS.** QC kits of events s29q102B0 / s29q103S have no PG-track hook and no strap snap; 89 `src_skew`, 77 `kit_topology`, 68 `pipeline` TypeError lines; 43 types sit at kit_rtl. The freeze ends 11-15 04:00. | Unblocks about 90 types to reach route at all. Removes the 10 DRT-0206 ends (fw / sc / stm). | None. | Three fw / sc kits regenerated: DRT-0206 gone. | KIT-OPS-5, WAVE-RECIPE-1, DIE-QC-103 |
| Q2 | **su_l0 family ECO** (stub widened to the pin width, 3 DRC to 0 proven on the seed; 4 runs live), then the S3R2 pin site for new builds. | 5 su_l0 types (12 partitions). | None. | The 4 running ECOs. | NEARMISS-ECO, DIE-QC-103 |
| Q3 | **PG-aware generation** (`OT_PG_DIE_PHASE`, `OT_PG_CELL_KEEPOUT`, wide-spacing hook as default). DRT-0255 hit 11 QC sle / slw builds and coll_n; the class is measured on 83 failures. | sle / slw hc, st_b, coll_n, coll_ucie: about 20 types. | None. | coll_n form a and slw_hc2 from `4_cts.odb`: detail route passes iteration 1. | PG-AWARE-1 (proofs running), ROOT-MERGE-63 |
| Q4 | **Hard ring children and region cores for the 345-377 k types**: st_b (4 types, 8 region blocks of 17.7 k each + rings), hc (5 types), fw (rings are 61-64 %), stm, cbn. The S3R3 masters (3 unsigned) hold 4 parent types. | About 20 types brought to 80-280 k cells. | Area: ring macro 4,591 um2 against 1,100 um2 soft, per bus. | sta_region_nb0 master x3 signed, then one st_a parent kit. | OVERSIZE-1, CLAND-MACRO-1, QC-CORES-HEAD, DIE-QC-103 |
| Q5 | **cbn / cbx / cbf (about 16 types): real overflow 30-79 k because two of four tiles face outward.** The mirror event was dropped. With area free there is a second form: widen the outer margins to a 129.6-um channel, like the centre one. Decide by the place-only what-if that is already queued. | About 16 types. | Mirror: none. Margin form: about +260 um of type width. | Place-only what-if: nets crossing a tile from 839 to about 0. | DIE-QC-103, QC-RING |
| Q6 | **repair4_leaf: take the non-slang build (synthesis 9 h to 25 s).** Last open QC core; LEC gold side on the Verilog frontend too. | 1 core and the sle_ctl types that wait on it (7 ids). | None. | rep4v sign-off. | QC-CORES-HEAD |
| Q7 | **Collapse clock-class variants** (120 ids without `pv` are 67 layouts without `cl`). Not measured: whether `cl` siblings differ only in clock taps, as S81 col did. If so, one clock landing per layout nearly halves the QC builds. | Up to 53 builds saved. | Possible skew margin; a bind and LATCHECK. | Read-only plan diff of the `cl` siblings of one family (1 h). | DIE-QC-103 |

QC order: Q1 decides everything else; no QC lever shows in the count until kits pass generation. Q2 is the only sign-off available tonight.

## 4. KV (5 / 56)

| # | lever | closes (expected) | cost | proof in one build | owner lane |
|---|---|---|---|---|---|
| K1 | **Hard ring masters, then one rebind event for pv, hub, hg, hgi.** Rings are 35-75 % of these types; synth 300-477 k becomes 80-277 k. 74 + 9 master kits are generated and running. | pv 16, hg 8, hub_Eo / Wo 2, part of hgi: about 30 types. Also ends "clock-landing band too small" (33 lines). | Area: 52-um band per landing face, outline growth. No cycles (drop-in parameters). | First signed master, then kv3_pv_v1n rebuilt on it: movable about 205 k (632 k measured). | CLAND-MACRO-1, OVERSIZE-1, KV-102 |
| K2 | **kv3_pc: CTS without insertion-delay balancing, plus early core taps** (threshold lowered so the 4 pcf cores at 193-196 ps get one too). The wave canary is blocked on an incomplete source copy; the proof does not need the wave. | 6 pc types (FF hold -385 to -441 ps on 18-31 k endpoints). | About 128 early taps. | CTS only from the existing `3_place.odb` of `kv3_pc__cl254f2e73` with `-no_insertion_delay`: all 8 OT_TAP_CORE lines within 20 ps, tap spread below 60 ps (365 today). | KV-102, KIT-OPS-5 |
| K3 | **hgi: keep signal nets off M7 over the 16 head cores** (42 of 43 congested gcells are inside core footprints; channels are below 15 % used). Keep the column re-floor parked. | 11 hgi types. | None. The parked re-floor would cost +2.3 % die and 68 lanes +1 cycle and moves no congested gcell. | GRT-only forms A and C (running): overflow 0 and no congested gcell inside a core. | KV-HGI-REFLOOR, TYPE-KVHGI2 |
| K4 | **Cross-tap ring pairs on one tap** (`clock.tap_pair_affinity`, already in the KV tree) for every landing-ring type; build C (reg-to-reg hold margin 40, full detail route) for io_ft_v1 now. | io_ft_v1 now; removes the hold class from pv / pc ring pairs. | Area: about 500 hold cells (0.8 %) in the bridge form. | Build C: internal FF hold at or above 0 with TT at or above -42. | TYPE-KVIOFT, KV-102 |
| K5 | **kv3_hub_C (769 k): 3-way split.** | 1 type; hub_Ei / Wi wait on the plan delta. | Area for child core halos. | Child `u_pvfin` core kit. | OVERSIZE-1, KV-102 |

KV order: K2 and K3 need no plan event and have a proof that runs from an existing database: do them tonight. K1 is the large one and is gated by master sign-offs.

## 5. Levers for all four dies

| # | lever | effect | cost | owner lane |
|---|---|---|---|---|
| X1 | **Memory kills** (56-60 builds per 10 h, 273 build-hours). ADMIT-TUNE-1 is live; stage-peak accounting is still off. Free memory by not running what cannot count: 131 col siblings (held), deterministic retries, forms listed as dead ends. Resume at detail route when a clean `5_1_grt.odb` exists. | The largest single class of lost builds. | None. | ADMIT-TUNE-1, WAVE-RECIPE-1 (kit_wave.py not yet live) |
| X2 | **Die gates in parallel with types.** DIE-PROTO-1 showed QC and KV die GRT at 0 overflow and positive setup with the regional clock. S81 and HEAD have no such run on the current plans. Open in QC: 468 crossings without landed tap pairs. | Finds die-level blockers now, not after the last type. | One plan-priority job per die. | A DIE-PROTO successor, die owners |
| X3 | **Relax the clock period** (for example 833 to 1000 ps). Closes only setup-limited items: S81 serdes, gunit bf, HEAD hd_host_e, QC st_b_v1 (-199 ps estimated). It does not help hold, congestion, DRT-0255 or memory. | Under 20 types. | Token rate falls in proportion (17 % at 1000 ps), on every die. | COORD decision |

X3 proof: re-run sign-off STA at the longer period on the routed, unsigned databases (minutes each). I rank it last: S8, S9 and H2 close the same types for a few cycles.

## 6. What to stop

- Wave retries of unchanged kits after a deterministic GRT or DRT failure (attempt numbers reach 17-19).
- S81: leaf t34 a14, t75 a5, t9 a2, t73 a6 on M8 kits; slice_station t27 / t28 / t36 on the old bands; col_h9_r0 p1 / p2 routes sitting in GRT iteration 21-30; svc mem2reg copies.
- HEAD: hd_host_e density and blockage forms; hd_spn_end attempt_6.
- QC: DRC-only route passes on su_l0; coll_n hook, density and edge-blockage forms; waiting on repair4 form d.
- KV: the hgi column re-floor; io_ft round 4 on margin 5 / 15; waiting on the kvtap canary for pc.

## 7. Not checked

- That the r0 col `pv` groups share one hard-core signature and param key set (S1). The r1 / r2 check was done by S81-COL-INHERIT; r0 rests on S81-TYPE-MEASURE section 2.
- Whether B4L4 changes the blocks of the 36 signed slice_station types (S6).
- QC `cl` variants (Q7) and the QC family counts in Q3-Q5, which I read from handoffs, not from kit logs.
- Every "expected types closed" figure: these are family sizes, an upper bound, not a forecast of first-pass sign-off.
