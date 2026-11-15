# FABLE-TYPES-KV (Fable review, every unclosed qwen_kvsys type outside FABLE-HARD-KV) 2026-11-14 20:0x PST

Read-and-diagnose only: no build launched, nothing killed, no kit file edited.
MEASURED = read from the named log or file. INFERRED = my reading, not run.
Kit root (KR) = epyc2 `/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys`.
Not in scope: kv3_pc (6), kv3_io_ft_v1, kv3_hgi_v2 (2) (FABLE-HARD-KV); kv3_hub_Wi and the kv3_pc rows have no run on the current plan.

## Summary

41 types reviewed, 5 root causes. Two are new findings (causes 1 detail and 4); the others extend earlier reviews with new members.

| # | Root cause | Types | Stage it dies | Owner |
|---|---|---|---|---|
| 1 | Soft landing-ring bands sized with 0.4-2 % margin; first-fit packer fails closed on the last cells | 16 | place (3_3), about 70 fails today | KV-102, CLAND-MACRO-1, KIT-OPS-5 |
| 2 | Ring-dominated types of 230-480 k cells: global placement loops for hours, then the size wall | 14 more (and all 16 of cause 1) | place / CTS | OVERSIZE-1, KV-102 |
| 3 | Global-route overflow only in zero-capacity gcells over head cores | 7 (kv3_hg is a new member) | GRT | TYPE-KVHGI2, KV-HGI-REFLOOR |
| 4 | kv3_sys_c: macro clock pin moved to a tap 951 um away by the tap cap pass | 1 | GRT hold repair, 6 h cap | KV-102, KIT-OPS-5 |
| 5 | Ring hold padding packed in one pocket (kv3_io_cor x2, kv3_hroot) | 3 | DRT-0255 / legalize | TYPE-KVIOCOR, TYPE-KVHROOT |

The one fix that removes causes 1 and 2 together is the hard ring macro rebind (CLAND-MACRO-1 + OVERSIZE-1 masters) in ONE KV-102 plan event. Until it binds, relaunching the 16 + 14 soft-ring kits unchanged buys nothing.

## 1. Landing-ring band does not fit (16 types)

Types: kv3_pv_v12, v2, v2n, v3, v3n, v4, v4n, v5, v5n, v6, v6n, v7; kv3_hgi_v6, v7, v8; kv3_hub_Wo.
Signature: `global_place.tcl, 5 OT_CLAND no legal nonoverlapping row/site in reserved band for ...` (landing_placement.tcl line 1683). Same signature under plans kvN2 (11-13), kv102sem_ftgrid and kvgeom4 (11-14); each plan event moved the failing band.

### Evidence (MEASURED, `ot_face_flops.txt` + `landing_contract.json` of each kit)

| Kit (KR/kvgeom4/items/...) | Failing band | Band area / plan reserve um2 | Ring cells placed before the error | Foreign cells inside the band |
|---|---|---|---|---|
| kv3_pv_v3/attempt_5 | ring:i_pvw__u_ctl_cmd, rect 1159.92..1170.72 x 1466.64..1503.36 | 397 / 393 | 1,151 (of 1,336 in the netlist) | 3 of writer-start:ft0_o |
| kv3_pv_v6n/attempt_2 | ring:ft2_i | 910 / 903 | 2,680 | 3 of writer-start:o_vport_W_N_vo_d2 |
| kv3_hgi_v6/attempt_5 | ring:ft14_i | 266 / 265 | 789 | 3 of writer-start:ft21_o |
| kv3_hgi_v8/attempt_4 | ring:ft20_i | 728 / 714 | 607 | 0 (strip rule raised rows 1 -> 3) |
| kv3_hub_Wo/attempt_3, kv3_pv_v4/attempt_3, kv3_pv_v5 | literal-local-reset `u_cland_raw_fs_o_*` | 4.32-um window | 1 | window grows x2 only |
| kv3_pv_v2n/attempt_4, v2, v6 | writer-face:ft26_o / ft0_o | face strip | 2 | - |

- The plan sizes each band to its area formula with 0.4-2 % to spare (`resize: DIE-KV-64 ... (7.25*w+125) x1.10; in-place grow`). All 46 bands of kv3_pv_v3 have area >= reserve, so the plan check passes.
- The packer is first-fit with per-cell rounding to the site grid, and START-window groups placed earlier drop 3 cells into a neighbour's ring band. The ring then runs out on its last 1-15 % of cells.
- The kit stops at the FIRST failing band (10-40 min in), so each attempt shows one band. Three plan events fixed the reported band and met the next one.
- kv3_hgi_v8: `OT_CLAND strip density ring:ft18_i+x+ff: 2.67 flops/um2 at rows 1, target 1 -> rows 3 (was 1, needs 3, band fits 4)`: the strip rule (LAND-RING-2) triples the row reserve after the plan sized the band.

### Dead ends
- Another in-place band grow per reported band (done three times).
- Unchanged wave relaunches: kv3_hgi_v6 and v8 failed 8 times each today, kv3_hub_Wo 7.

### Fix
1. Structural (KV-102 + CLAND-MACRO-1 + OVERSIZE-1): bind the hard ring masters (`lanes/handoff/KV-RING-CORES-MERGED.tsv`, 50 masters) in ONE plan event for pv, hg, hgi and hub. A hard ring has no band to pack. This is also the fix for cause 2.
2. Tool, same day (KIT-OPS-5, landing_placement.tcl, class fix for every die):
   a. a ring group that runs out of band takes the band rect grown by one row/column step (up to +10 % area) before it fails;
   b. START-window and local-reset cells skip sites inside another group's ring band;
   c. on failure, run the remaining groups in the existing dry mode (`::cland_fill_dry`) and print EVERY band that does not fit, with need and capacity, in one pass.
3. Plan (KV-102, until item 1 lands): band area = reserve x 1.15, and the strip row count used by the kit goes into the reserve.
- Proof in one build: kv3_hgi_v6 (11 min to the error today) with 2a-2c reaches `3_3_place_gp` with zero OT_CLAND errors; 2c lists no band.
- INFERRED: with item 2 alone the pv types pass this stage and then meet cause 2; only item 1 closes them.

## 2. Ring-dominated oversize types: placement loop, then the size wall (14 more types)

Types: kv3_pv, pv_v1 (only infra fails on record; member by family, INFERRED), pv_v1n, pv_v8; kv3_hg_v1, v1p2, v1p3, v1p4, v1p5, v1p6, kv3_hg_v3; kv3_hub_Ei, hub_Eo, hub_C. All 16 types of cause 1 are in this class too.

### Evidence (MEASURED)
- Floorplan census (`cell_census.jsonl`): kv3_pv_v4 478 k cells / 1.42 M projected, pv_v4n 477 k / 1.37 M, pv_v5n 463 k / 1.02 M, pv_v1n 390 k / 773 k, pv 299 k / 750 k, pv_v8 297 k / 710 k, hub_Eo 374 k / 713 k, hgi_v8 256 k / 673 k, hgi_v6 230 k / 620 k, hg_v1p2..p5 285-288 k / 577-579 k. The verdict is now only `WARN OVER_CAP`.
- Ring share: kv3_pv_v4n has 48,948 FIRM ring flops and 164,978 ring logic cells of 364,260 movable (59 %). kv3_pv_v3 carries 26 one-bit `ft*_i` rings padded to ring width 64: 811 cells and 198 flops each, 21 k cells for 26 bits.
- kv3_pv_v4n/attempt_2 `3_3_place_gp.tmp.log`: started 11:57, still running at 19:33 (7.6 h). 4,310 Nesterov iterations, 11 routability passes, overflow swings 0.47 <-> 0.66 and is 0.664 now. Utilisation 2.286 %; `OT_GPL_SPARSE movable util 2.114 % (threshold 2.000 %): GPL modes unchanged`, so routability mode stays on. First routing-congestion snapshot: 532,274 overflowed tiles.
- Same loop: kv3_pv_v1n (2.06 %, iteration 1,310, overflow 0.31), kv3_hg_v1p5 (iteration 2,190, 0.52), kv3_hg_v1p4 (iteration 910, 0.48).
- Ended that way: kv3_hg_v1p3 `GPL-1010 Nesterov pass cap hit at iteration 9160 with overflow 0.424`; kv3_hg_v1p2 GPL-0307; kv3_hub_Eo GPL-0305.
- Earlier today 8 of these stopped at CTS on the cell budget (`... or harden logic into cores`, do-4_1_cts Error 1): pv, pv_v8 (x3), pv_v1n, hg_v1, hg_v1p4, v1p5, v1p6, hub_Ei.
- kv3_hub_C: 769 k cells, and `kit_rtl` fails on `AHUB boundary: native parameter signature changed: AP_OFS, FR_OFS, Z_IN_STRIDE` (7 times). It needs the 3-way split and a re-captured boundary; it cannot run flat.

### Dead ends
- Removing the cell cap moved the stop, it did not remove it: these kits now spend 2-8 h in global placement on 64-GB slots. INFERRED for the later stages: the largest design this flow has closed is 517 k cells; kv3_pv and pv_v8 (placed, queued for route at 710-750 k projected) are unlikely to close flat.
- Density and routability forms: the loop comes from 165 k ring logic cells pulled to flops fixed in pin strips.

### Fix
1. Structural (OVERSIZE-1 masters, KV-102 rebind): hard rings take 45-75 % of the cells out (OVERSIZE-1 table: pv 205-265 k after, hg 168-170 k, hgi_v7 79 k). Same event as cause 1.
2. Generator (KV-102 / RTL owner, INFERRED saving): a one-bit ft landing ring should not be padded to ring width 64. One master of the true width, or one shared ring per face group, removes about 21 k cells per pv type.
3. kv3_hub_C: OVERSIZE-1 3-way split (u_pvfin + pvfin_out core, engine core) before any kit; re-capture the AHUB native parameters in the same change.
4. Side A/B only (KIT-OPS-5): `OT_GPL_SPARSE_UTIL=0.035` in the KV die env drops routability mode for the 2.06-3.2 % types. It ends the loop, not the size.
- Until item 1 binds: stop wave relaunches of these 30 types (no unchanged relaunch after a design fail) and give the slots to the ring-master builds.
- Proof in one build: kv3_pv_v8 with hard rings: floorplan census under 250 k, global placement converges in under 1 h, CTS starts.

## 3. Global-route overflow over head cores (7 types)

Types: kv3_hgi, kv3_hgi_v1 (2 classes), kv3_hgi_v3, v4, v5; new member kv3_hg.

### Evidence (MEASURED)
- kv3_hg, KR/kv102sem_ftgrid/items/kv3_hg/attempt_14 (19:06 today): GRT-0116 with total overflow 503 at 12.88 % use (M6 246, M5 96, M8 87, M7 73). The final `congestion.rpt` holds 2 gcells, both `capacity:0 usage:1`: (763.8, 122.6) inside u_head1_e0 [656.64..872.64 x 17.28..233.28], net274613; (132.8, 397.9) inside u_head0_e2 [60.48..276.48 x 336.96..552.96], net `u_cland_i_slg_Q_N_krsp/u_ring.dch[10].u_dsel/net300554`.
- The kit ran `global_route ... -congestion_iterations 30` without allow-congestion (old kit).
- hgi_v4 and v5 early stops name `u_bound.u_cland_i_ectl_Q_N_tN` as the top net (38,674 at iteration 15 on v5, hotspot (40,1220)-(60,1240)).
- This is the class FABLE-HARD-KV section 3 measured on kv3_hgi_v2 (42 of 43 gcells inside a core footprint, capacity 0).

### Status and fix
- The test is live: KV-HGI-REFLOOR forms fh2_A (M7 adjustment 1.0 over the 16 core boxes) and fh2_C (control) on intel1, logs intel2 `~/kvhgr/fh2_{A,C}.log`. The first launch died in 11 s on a flow error (OT_GRT_NONPORT needs the FF corner), so there is no verdict yet. The mechanism stays INFERRED until A and C report.
- Add kv3_hg and kv3_hg_v3 to the batch that takes the winning setting; kv3_hg needs it for 2 gcells only.
- Dead ends unchanged: column re-floor, M9, density forms.
- Proof: fh2_A ends GRT with no congested gcell inside a core box and DRT with 0 violations; then one kv3_hg build from its 4_cts.odb.

## 4. kv3_sys_c: macro clock pin on the wrong tap (new)

### Evidence (MEASURED, epyc9 `.../kv101ns_3465fe9/items/kv3_sys_c/gen/kv3_sys_c`)
- Job b5215b6c8bc0: `OT_GRT_TIMECAP post-route repair over 21604 s, hold_ws_ps=-281.63`, last endpoint `u_bound.u_ucie_rom/tx_flit[258]`. GRT hold start: ws -281.63, 8,432 endpoints; 34,651 buffers inserted, worst still -259.8 at `u_ucie_rom/tx_flit[546]`.
- `4_cts_final.rpt`, TT min path `u_d2d_kv.fdi_tx_flit[57]` -> `u_ucie_rom/tx_flit[57]`: launch flop clock at 17.9 ps (tap clk_t42, source latency -110), macro clock pin at 548.5 ps (tap clk_t24), slack -500.13. Setup WNS at CTS is -995.36.
- The clk_t24 path holds 6 max-wire repeaters (`max_length195737`, `wire195733..36`, BUFx12f, about 44 ps each) before the tree root. `OT_TAP_BALANCE` clk_t24 = 441 (427-480) ps on 17 sinks, target 250.
- Geometry: u_ucie_rom (ot_qkvd_ucie_x64_phy, 777.6 x 777.6) at (691.308, 60.48) R0. Its clk pin is on the N edge at local (276.4, 777.5) = die (967.7, 838.0). Tap clk_t42 is at (954.2, 859.7): 35 um from the pin. Tap clk_t24 is at (664.8, 190.1): 951 um from the pin, and 156 um from the macro ORIGIN.
- `4_1_cts.log`: after the nearest-tap pass clk_t24 has 16 sinks; after `OT_CLOCK_TAPS cap 1200 sinks/tap: 6435 sinks re-assigned` it has 17. clk_t42 is over the cap (1,872).
- clock_taps.tcl: the nearest-tap pass uses the macro PIN position (DIE-KV-60, line 106-111). The cap pass (line 255) and the merge passes (lines 365, 427) use `[$it getInst] getLocation`, the macro origin. The cap pass skips macros only when OT_CORE_TAPS is set (line 236).
- INFERRED (count and geometry agree, I did not trace the single pin): the cap pass moved `u_ucie_rom/clk` off clk_t42 to the tap nearest the macro origin with room within 200 um, which is clk_t24.

### Dead ends
- Longer hold repair or a higher time cap: 530 ps of skew on 8,432 macro endpoints is not a padding problem, and setup is -995 the other way.
- The live relaunches (kvgeom4 attempt_3/4) use the same clock_taps.tcl and the same tap sites; they will repeat it.

### Fix
1. Tool (KIT-OPS-5, clock_taps.tcl, class fix for every die with pinned hard macros): the cap, group and min-merge passes never move a clock pin of a block master (make the line 236 guard unconditional), or use the pin position as the first pass does.
2. Plan (KV-102, advisory): 8 kv3_sys_c taps are over the 1,200-sink cap (clk_t40 6,048, clk_t8 4,833, clk_t13 3,809). A finer tap pitch near the PHY removes the pressure that triggers the cap pass.
- Proof in one build: CTS only from the existing `3_place.odb` with the patched clock_taps.tcl. PASS = `u_ucie_rom/clk` on clk_t42, the tx_flit[57] min path slack above -60 ps at CTS, tap spread under 120 ps. Then run to sign-off.
- Same check for kv3_phy / kv3_sys_SD kits (PHY macros): grep the tap of each block clock pin after the cap pass.

## 5. Ring hold padding packed in one pocket (3 types)

Types: kv3_io_cor, kv3_io_cor_v1, kv3_hroot. Evidence is the owning lanes' (TYPE-KVIOCOR, TYPE-KVHROOT handoffs); I re-read the job records, no new measurement.

- kv3_io_cor: DRT-0255 on `u_cland_i_host_fdi/u_ring.dch[13].u_dsel/net60559`, route box (525.5, 54.7)-(529.5, 58.7), twice (05:12, 14:24). The box holds 208 instances, 42 of them HB4 hold cells; 101 tiles of the i_host_fdi band are at 70 % or more while the band average is 14.8 %. kv3_io_cor_v1: DRT-0255 on `u_cland_ft19_i/_0464_`, box (964.4, 54.7)-(968.4, 58.7): same south pin end.
- kv3_hroot: pre-GRT hold repair added 11.7 k hold buffers for 10,246 endpoints (port_in 8,180 at -226.5, cross-tap 1,766 at -129.7); legalization failed on 79 overlaps in the FIRM rings (DPL-0033), all debt went to GRT repair, which stalled at -19.72 on 580 endpoints.
- Common cause (INFERRED from the two lanes' numbers): the hold cells of a soft ring are inserted at the ring's dsel outputs, where flops are FIRM and the band is full. The debt itself is the cross-tap ring-read pair that FABLE-HARD-KV section 2 measured on kv3_io_ft_v1.

### Fix
1. Structural (KV-102, already in the next event): `clock.tap_pair_affinity` with ring_depth for the ring read register and the stage it feeds. It removes the cross-tap debt, so the padding is not inserted. Apply to io_cor, io_cor_v1 and hroot in the same event as io_ft.
2. Hard rings (cause 1 fix) close the ring-internal part inside the master.
3. In flight and reasonable: PREGRT-LEGAL-1 (hroot attempt_5 is in route since 14:21), PG-AWARE-1, TYPE-KVIOCOR form fd (pocket blockage). Forms fa-fc on epyc10 never ran (exit 13, lec_async.sh missing); form fd died at CTS with make Error 241 (the wave classes that code as out of memory, not a design result).
- Dead end: density-only forms for io_cor; the band average is 14.8 %.
- Proof: with tap_pair_affinity, pre-GRT FF hold debt of kv3_hroot falls from 10,246 endpoints to the port_in part only, and legalization passes without fallback.

## Not done
- No STA or GRT what-if run (fleet memory-bound; the logs were enough to name each cause).
- Cause 3 mechanism waits for fh2 A/C. Cause 4 pin move is inferred from counts and geometry. Cause 2 "will not close flat" is inferred from history.
- kv3_pv_v1, kv3_hgi_v7 and kv3_hroot are in route now; their outcome may add or remove a member.
