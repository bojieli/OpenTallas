# DIEVIEW-KV-1113: KV die (qwen_kvsys) visual layout review

Stamp: 2026-11-13 05:58 PST. Lane DIEVIEW-KV (Fable), read-only. Plan of record: vN2i (plan_c md5 dc4e1207, main 66e6607e3f, wave event kvN2_66e6607). I ran no build and changed no plan.

## Verdict

The die floorplan is sound. No finding asks for a new die channel or a column re-order. The die does not close today for five reasons, in this order: the die clock is balanced only on paper; the hub band and sys row tiles have no registered transport for their control fans; the pv and hub tiles are too large to build; three whole columns (pc, phy, hg/hgi) cannot start a build on the vN2 form at all; and the SD kits were routed with the wrong GRT setting. Four of these are owned. Four items have no live owner (U1-U4 below).

Only 1 of 56 types is signed off (kv3_io_ft). All other 55 have 5 or more failed attempts. Most of the 817 logged FAILs are kit staging classes, not layout (EXPERT-REVIEW-1 lever 1). The layout causes below come from the last builds that reached place or route.

## What I viewed

Die level (copies in intel2 ~/coord/lanes/):
- kv-vn2-1112/kv_vn2_floor.png, kv_vn2_map.png, kv_vn2_dataflow.png, kv_vn2_cuts.png, kv_vn2_taps.png, kv3_hg_v1p3_vN2_wstreet.png, kv3_hgi_v7_vN2_wstreet.png (vN2c, 11-12 07:40).
- epyc4:/srv/opentallas-scratch2/claude/dkv99/draw_vN2h/kv_vn2_floor.png, kv_vn2_taps.png, kv_vn2_cuts.png (vN2h, 11-12 16:27). This is the current die render: vN2i is vN2h with kv3_pv_v2n and kv3_pv_v6 reverted, so I made no new one.
- die-proto-2/KV_vN_grt_congestion.png, KV_vN_insertion.png, KV_vN_landed_top.png (die GRT and die clock on vN, 11-12; there is no die GRT or die clock run on vN2i).

Type level (B = /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys; each .../run/layout_review/place/density.png, plus geom/auto_geom.png where named):
- epyc8:B/kvN2_66e6607/items/kv3_hub_Eo/gen/kv3_hub_Eo (density, auto_geom)
- intel1:B/kvN2_66e6607/items/kv3_hub_Wo/gen/kv3_hub_Wo (density)
- epyc9:B/kvN2_66e6607/items/kv3_sys_c/attempt_2/gen/kv3_sys_c (density, auto_geom)
- intel1:B/kvN2_66e6607/items/kv3_sys_SD/gen/kv3_sys_SD (place density, grt/congestion.png, 5_2_route.log)
- epyc8:B/kvN2_66e6607/items/kv3_sys_SD_v1/gen/kv3_sys_SD_v1 (place density, grt/congestion.png, 5_2_route.log, config.mk, m8_grant.json)
- intel1:B/kvN2_66e6607/items/kv3_hroot/gen/kv3_hroot (density)
- epyc7:B/event28w_c/items/kv3_pv_v5n/attempt_13/gen/kv3_pv_v5n (density, auto_geom; old plan, the only pv render left)
- epyc8:B/event28w_c/items/kv3_hgi_v1__cl141fc26e/attempt_4/gen/... (density; pre-vN2 form)
- intel1:B/event28w_c/items/kv3_hg_v3/attempt_8/gen/kv3_hg_v3 (density; pre-vN2 form)
- epyc9:B/kvN2_66e6607/items/kv3_pc_v1__cl23f6a148/gen/... (2_4_floorplan_pdn.log and macros/*.lef; no render exists, the kit stops at PDN)
- Not viewed by me: kv3_io_cor, kv3_io_cor_v1, kv3_io_ft_v1 (I rely on GEOM-VIS-13 03:08). No render survives for kv3_phy*, kv3_pc*, kv3_hub_C, kv3_hub_Ei, kv3_hub_Wi, and none exists on the vN2 form for any hg or hgi type.

## Part 1: the whole die

| area | judgement | basis |
|---|---|---|
| Data flow | GOOD | 9 mirrored columns phy, pc, hg, hgi, pv, hgi, hg, pc, phy x 16 rows. 528,723 of 598,087 crossing bits (88%) stay in the arrays as neighbour hops; every hub flow is under 4.3k bits. |
| Channels, die congestion | GOOD, one model risk (D2) | Die GRT on vN: overflow 0; the guide density map shows only point loads at partition seams, no band, nothing at the hub. |
| Die clock, landing rings | FAIL as measured, fix unproven on routes (D1) | Insertion map: 0.7 ns at hub_C to 7.1 ns at the N and S tips. 870 of 896 landed part pairs are over the 416.5 ps window. |
| Hub band | BAD tiles on a good band (T1, T2, T3) | hub_Eo and hub_Wo placements are diagonal relay streaks across an empty tile; hub_C is 706k cells. |
| D2D / sys row | BAD sys_c (T2), SD kits crash (T6) | sys_c logic sits on both sides of a 778 um ROM. |
| IO / PHY shore | BLOCKED before build (U2) | Both PHY types fail at kit_rtl on an empty clock tap. |
| Reset | Same family as the START fan (T1) | The raw-reset relay drives fstart flops 1.2-2.4 mm away; sys_c rst_n reaches 2.49 mm. |
| Clock taps | 31 of 54 types over the 1,200 cap in vN2h | pv_v6n 4.8k, pv_v7 2.6k, pv_v3n 2.4k, pv_v12 2.3k, hgi_v8 2.1k. |

### D1. Die clock is balanced by estimate only (rank 1)
- Seen: KV_vN_insertion.png is a clean radial gradient from the root; KV_vN_landed_top.png puts the damaged pairs across the steep contours (W pc/phy columns, the pv spine, the sys row).
- State: REACH-FIX-2's insertion balance takes landed damage from 1,031 to 78 ps in the die STA model (11-12 07:35). The same lane reported that the balance is SPEF-only pad wire that a router ignores (11-12 07:29), and COORD ruled topology B (H-tree to region roots, 08:26). I found no routed die clock and no die GRT/STA run on vN2i.
- Fix: run dieclock_regeq --routed plus die GRT (50 it) and die STA on vN2i now, inside the freeze, so the post-freeze KV event carries a measured tree. The kit tap windows (R-CLOCK contract W) should be re-derived from that routed tree, not from the model.
- Rule: METHODOLOGY 12.4a and 12.1b; R-CLOCK covers the kit side only.
- Owner: REACH-FIX-2 owned the class on 11-12; I could not confirm a live lane. See U4.

### D2. hgi N column depends on the M7-free core model (rank 6)
- Seen: kv_vn2_cuts.png. Under main's G0 model 16 hgi_N slots sit at 0.68-0.94 of the cut tracks; under the M7-free model none is over 0.50.
- This is the same abstract class as the pc PDN failure (U1): a core LEF that claims M6/M7 it does not use. The die verdict "no new channel" holds only if the kv3_head_eighth detail LEFs (M6 1.4-3.4%, M7 1.2-4.1%) are what the die router sees.
- Fix: land the core_obs checker class, and include the hgi_N column in the D1 die GRT run with the detail abstracts. If it overflows, split the L2075-type lanes across hg and hgi as PATH-KV-GRT2 planned; do not add a channel first.
- Rule: R-STREET-3 step 4 (over-the-cell where the obstruction stops at M7 or lower). Owner: DIE-KV-100 (inherited from DIE-KV-99; checker READY not seen merged).

## Part 2: hardest types, grouped by layout cause

All 55 unsigned types have 5 or more failed attempts (counts from autopilot/log.txt: FAIL events / launches).

### T1. One START register drives every landing ring of the tile (rank 2)
- Types: kv3_hub_Eo (23/36), kv3_hub_Wo (20/25) BAD; the same family at lower distance in kv3_hroot (9/20), kv3_io_cor (17/28), kv3_io_cor_v1 (14/26), kv3_io_ft_v1 (13/29), kv3_hub_Ei (10/29; routed setup -160 ps, hold -91 ps on ring to bin 1.2 mm). R-REACH counts 42 KV types under rule 1, 27 with no reader chain.
- Seen: hub_Eo and hub_Wo density maps show diagonal 20-40% streaks across an otherwise empty 1279 x 1676 tile, and a 50-70% smear between the two astk cores (Eo) or a comet from the SW pin face to the SE cluster (Wo). auto_geom: one tap holds 5,355 sinks (Eo clk_t12); the farthest sink is 2.76 mm from its clock driver. DIE-KV-100 classified 3,206 of 3,869 long captures on Eo as cland_origin to ring.
- Fix: reach_rules.py fix --rules 1,4 (share_trunk: one hub relay per 300 um ring group, trunk hops planned at 340 um), strict bind, raw-reset step. The origin's raw-reset relay (rrl_150 / rrl_216 to the fstart flops) is the same family and needs the same relay trunk; rule 1 does not cover it by itself.
- Rule: R-REACH-1, R-REACH-5. Owner: DIE-KV-100 (event), RULES-REACH-1 (hub_Eo proof place, in progress). OWNED.

### T2. Logic on both sides of a macro wider than reach (rank 3)
- Types: kv3_sys_c (8/23) BAD, kv3_hub_C (12/22).
- Seen: sys_c density map. ucie_rom fills x 691-1469; a 40% cluster sits W of it at (540, 700), the pin rings sit on the W and E faces, and a thin arc of cells runs around the N side of the ROM. 5,491 captures are over 900 um.
- Fix: declare reach_homes (d2d_kv home and the 4 link SRAMs E of the PHY pins, as DIE-KV-100's sysc_form.py does), then fix --rules 2 for stations on what must cross. Prefer moving the attn payload and kvn windows to the home side (R-REACH-3) over stations: every station is a data cycle.
- Rule: R-REACH-2, R-REACH-3. Owner: DIE-KV-100 (sysc_form, KV-HUBC-REACH). OWNED.

### T3. Tile too large to build (rank 4)
- Types: all 16 kv3_pv types (12-27 fails each; 423-724k movable cells; 16 of 17 runs failed FF hold at -306 to -731 ps after 3-5 h of CTS; pv, pv_v3, pv_v8 also GRT overflow), kv3_hub_Wo / kv3_hub_Eo (464k / 407k), kv3_hub_C (706,641 against the 517k run cap).
- Seen: pv_v5n a13. The 20 cores stand in 4 columns; the soft logic collects in one N-S spine at x 1030-1130 at 40-60%, with taps of 5,157, 2,150 and 2,028 sinks along it. The outer core columns touch the W and E outline (the 14.74 um edge slot R-STREET flags on all 16).
- Fix: the approved split (pv 4-way per lane group, pv and v8 2-way; hubs 3-way). Two cautions from the render. (a) The middle cut of the 4-way form runs through the 104 um gap at x 1028-1132, which is the spine: after the cut it must hold two pin faces, their registers and the N-S chain. Check it against R-STREET-5 (width >= transit bits / 37.5) before binding, and move the N-S chain into one of the 253 um gaps if it fails. (b) Fix the 14.74 um edge slot (a 2.6 um core move) in the same event; after the split it becomes a pin-face alley.
- Rule: R-CAP-3, R-STREET-4/5. Owner: DIE-KV-100 with KV-SPLIT-1 (pv, hub_Eo, hub_Wo). kv3_hub_C is NOT in the R-CAP list or in the split scope. See U3.

### T4. Pin face with no street: hg and hgi (rank 5)
- Types: 8 hg (kv3_hg, hg_v1, v1p2-v1p6, hg_v3) and 11 hgi (hgi, hgi_v1 x2, hgi_v2 x2, hgi_v3-v8); 5-20 fails each. Last real results on the old form: GRT overflow on hg, hg_v1, hgi (25,342), hgi_v3, hgi_v5; hg_v1p4 FF hold -476 ps.
- Seen: hgi_v1 a4 has yellow 60-80% pin pockets jammed against the W core edges at two heights and diagonal relay chains in the col-3/col-4 street. hg_v3 a8 has its logic packed at 50-70% into the central cross street around the SRAM column, with the W pockets again against the cores. The vN2 drawings (kv3_hgi_v7 / kv3_hg_v1p3 wstreet) open the W street to 60-78 um and spread the W windows; that is the right form.
- Gap: no hg or hgi type has been built on the vN2 form. None was in the 33 first launches of kvN2_66e6607; the rows are stale at kit_rtl since 11-12 06:xx. 64 of the 160 slots therefore rest on an unbuilt form. R-STREET still flags kv3_hg_v3 and kv3_hgi_v8 (macro 17-26 um behind 0.7-0.8k pins, wants 43.2).
- Fix: place two pilots now, privately, kv3_hg_v1p3 and kv3_hgi_v7, view them, then release the family (pilot-first rule). Run street_rule.py legalize on hg_v3 and hgi_v8 in the KV event.
- Rule: R-STREET-2, R-STREET-3. Owner: none live for the builds. See U4.

### T5. sys_SD and sys_SD_v1: DRT-0255 (rank 7)
- Types: kv3_sys_SD (14/21), kv3_sys_SD_v1 (16/34).
- Seen: both logs. After iteration 0: 20,091 (SD_v1) and 31,180 (SD) violations, concentrated on M7 / V7 / M8 (SD_v1: V7 cut spacing 1,301, M8 shorts 1,339, M7 shorts 701). Both kits carry an M8 grant (9,180 of 12,960 tracks), GRT ran with -resistance_aware, and config.mk has no ENABLE_RESISTANCE_AWARE line. The failing boxes are inside the cell clusters (SD_v1 x 1906-1926, y 134 and 661-673; SD in the S strip x 1659-1671, y 7-43). GRT overflow was 0 on both. This is a flow cause, not a placement cause, and I confirm RULES-FLOW-1's 05:37 reading.
- Fix: regenerate from current main (HEAD-ROUTE-1 is merged) or add ENABLE_RESISTANCE_AWARE = 0. Then two layout items remain: kv3_sys_SD takes the SD-GROW outline (its 45 um E strip and 58 um S strip hold all 17k sinks, and the SE corner is the hot spot in both maps); and the SD-GROW pilot was NOT signed off on 11-12 at setup -319 ps on the LAND-RING guard half-cycle path, so expect that class next.
- Rule: R-FLOW-6; R-STREET-2 for the outline. Owner: RULES-FLOW-1 (crash), DIE-KV-100 (outline, p3r.json). OWNED. The ring guard half-cycle has no named owner since LAND-RING-2 moved to S81.

### T6. hroot: empty slot, ring to bin hops (rank 9)
- Seen: the W 900 um of the 1901 x 838 tile is empty; logic sits at the E face and the S rings. 7 captures are over 750 um. GEOM-VIS-13 accepted it for route and I agree.
- Fix at the KV event: pin each bin flop at its ring, shrink the slot to the E 1000 um. Rule R-REACH-1/5, R-CAP-2. Owner: DIE-KV-100 (open list).

## Part 3: items with no live owner

### U1. pc column cannot pass PDN: kv3_pc x2, kv3_pc_v1 x3, kv3_pc_v3 (rank 4, 32 slots)
- Error: PDN-0006 "VSS on M5 is blocked by obstructions on M6, M7 for u_bound.u_kvpc0_f", 6 of 6 pc types, 12-21 fails each.
- Measured in the kvN2 kit (epyc9, kv3_pc_v1__cl23f6a148/gen/.../macros): qkd_kvs_pcc.lef is now a detail view (23,768 M6 rects, none large). qkd_kvs_pcf.lef (90.72 x 267.84) still has ONE rect covering 93.7% of the macro on each of M5, M6 and M7. OBS-SYNC-1 fixed pcc on 11-12 and the pcf half did not reach this event.
- Fix: stage the detail-view LEF of qkd_kvs_pcf (and pcf_h_head_p) in prov_view_sources for kvN2_66e6607 and relaunch the 6 rows. In the KV event also remove the 8.64 um pcf/pcc sliver (preflight macro_channels: 8.64 < 10.8): abut the pair or open 17.28 um.
- Rule: R-STREET-6 (sliver); core_obs class. Owner: none (OBS-SYNC-1 closed; wave rows say "die owner").

### U2. PHY shore cannot generate: kv3_phy (19/33), kv3_phy_v1 (13/21) (rank 5, 32 slots)
- Error at kit_rtl: "grid+explicit tap clk_t1 load=0/1500, radius=0/200.0, empty=True". The vN2 plan carries a clock tap with no sink.
- Before that, the old form routed at setup -76 to -244 ps with slew up to 4.7 ns: pins 550 um from the core face with no register (pin_reg p90 698 um).
- Fix: drop or re-site the empty tap in the plan (reach_fix), then one private place of kv3_phy_v1 to check that the re-faced vN2 slot puts a register column at the pins. The PHY station exemption ASK (84 street_die_leg rows) is still open and should be ruled with it.
- Rule: R-REACH-3, R-REACH-4. Owner: none named; not in DIE-KV-100's scope list.

### U3. kv3_hub_C at 706,641 cells (rank 6)
- It is the largest soft tile on the die and it also holds the clock root. R-CAP names hub_Eo/Wo and pv only; DIE-KV-100 handles hub_C for R-REACH-2 only. KV-HUBC-CORE-1 started hardening qkd_pv_fin_s on 11-12 02:27 and I found no result.
- Fix: decide one of (a) harden pv_fin (and ahub glue) into cores, or (b) a 3-way family cut like the outer hubs, and put it in the same KV event.
- Rule: R-CAP-3. Owner: unclear; needs a COORD line.

### U4. Two proof runs nobody is running
- The routed die clock plus die GRT/STA on vN2i (D1).
- The hg/hgi vN2 form pilots (T4).

## Ranked list

| rank | finding | fix | rule | owner |
|---|---|---|---|---|
| 1 | D1 die clock balanced only in the model; no vN2i die run | routed dieclock_regeq + die GRT/STA on vN2i | METH 12.4a | none confirmed |
| 2 | T1 single START register per tile (hub_Eo/Wo, io, hroot, hub_Ei) | reach_rules fix 1,4 + raw-reset trunk | R-REACH-1/5 | DIE-KV-100, RULES-REACH-1 |
| 3 | T2 macro barrier (sys_c, hub_C) | reach_homes + rule 2, move windows | R-REACH-2/3 | DIE-KV-100 |
| 4 | T3 pv x16 and hubs over the cell cap | approved split; check the x 1028-1132 seam | R-CAP-3, R-STREET-5 | DIE-KV-100, RULES-CAP-1 |
| 4 | U1 pc x6 PDN-0006, pcf LEF still blanket | pcf detail view; fix sliver | core_obs, R-STREET-6 | none |
| 5 | U2 phy x2 empty tap at kit_rtl | drop tap; pilot place | R-REACH-3/4 | none |
| 5 | T4 hg/hgi vN2 W-street form never built | 2 pilots, then family | R-STREET-2/3 | none |
| 6 | U3 hub_C 706k | harden or split | R-CAP-3 | unclear |
| 6 | D2 hgi N cut ratio rests on the M7-free model | core_obs class + die GRT | R-STREET-3 | DIE-KV-100 |
| 7 | T5 sys_SD / SD_v1 DRT-0255 on M8-grant kits | RA = 0; SD-GROW for sys_SD; ring guard next | R-FLOW-6 | RULES-FLOW-1, DIE-KV-100 |
| 9 | T6 hroot empty half | bin flops at rings; shrink slot | R-REACH-5, R-CAP-2 | DIE-KV-100 |

## Not checked
- I did not re-derive r2r pairs; capture counts are GEOM-VIS-13's and DIE-KV-100's.
- The pv seam caution (T3a) is from one old-plan render; I did not count the transit bits at x 1028-1132.
- "No owner" means I found no live lane in the queue, OWNERS.tsv or the handoffs; COORD may know one.
- METHODOLOGY section 12 was read to 12.4e only.
