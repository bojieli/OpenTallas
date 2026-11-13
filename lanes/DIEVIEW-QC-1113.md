# DIEVIEW-QC-1113: QC (qwen_compute) die-level visual layout review

Stamped 2026-11-13 06:03 PST. Lane DIEVIEW-QC (Fable), read-only, DO_NOT_COUNT. Coordinator COORD. Die owner DIE-QC-100.

Plan viewed: s28 event head `zz_gates_ev2st.json` sha 736058c458ee (HF-1c floor + s28 items; epyc9 `wt/qc-s28-event2`). 377 partitions, 125 types, die 31,216 x 25,644 um.

No current die-level render existed (the newest were `results/die_clock_1024` and the 10-28 trial plans), so I drew three from the head plan with the repo plan classes (`schema.Plan`, `check.lane_geometry`, `schema.tap_grid`), run through ot-run on epyc4. Nothing else was written or launched.

## Verdict

The die floorplan is sound and regular. The stall is in the types, and it has four structural causes that repeat across families: forwarded-clock sources picked by tap index, bus infrastructure pushing types over the cell cap, pin windows far from their consumer, and macros or pin registers packed against a pin face. Two things are missing at die level: any die GRT / clock proof on this floor, and a closed START fan (332 open G0 rows).

116 of the 124 QC types in the kit-wave state have 5 or more attempts and none is signed off (worst: sle_fw_v3 134, sle_hc1__cl22c1ff36 125, slw_su_c__cl92142dac 121). So part (2) is the whole die; I grouped it by family.

## Images I viewed

Die renders (mine, epyc4 `/srv/opentallas-scratch3/claude/dieview-qc-1113/out/`; the five marked * are also in `lanes/dieview-qc-1113/`):
- `A_floorplan.png` *, `A_floorplan_W_mid.png`, `A_floorplan_C_mid.png` *: partitions by family, lanes, stations, spine root.
- `B_clock_fwdhop.png` *, `B_clock_fwdhop_C_mid.png`, `B_clock_fwdhop_SW.png` *: taps, landing clock edges, forwarded-clock source tap to face pin for the OPEN-FWDHOP rows. Only 455 of 1,685 instance rows could be drawn (the rest have no window in the type bus table); the fill colour covers all 573.
- `C_route_supply.png` *: per-type route supply p99 from `qc-s28-dieview/out_vf` (11-12 plan estimate, not a GRT).
- Script: `lanes/dieview-qc-1113/dv_render.py`.

Type renders:
- epyc4 `kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/hcut1111/items/<t>/.../run/layout_review/place/density.png` for sle_st_a_v2 attempt_2, sle_ctl__cla4f6f12f attempt_2, coll_s attempt_2 (11-12, old floor).
- localhost scratchpad `vistriage/qc/png/<t>_full.png` (11-10/11, plan efdb36e864, measured ODB + GRT overflow) for cbn_q00__cl622f65d2, sle_hc1__cl22c1ff36, sle_stm_v2__cl7b3062fa, sle_su_l1__clc6d66f5b.
- epyc9 `qc-s28-hf1c/visform/renders/sc_echan_sle_sc_v2.png` (s28 sc form, before / after).

Not viewed: fw, fe, hc0/hc2/hc3, st_b, su_l0, su_c, cbf, cbx, coll_n/ucie/ft, glue, native59, tt_ctlm renders. Their rows below rest on the GEOM-VIS verdicts, VIS-TRIAGE-QC.tsv and the logs, and say so.

## (1) The whole die

- **Arrangement.** 12 slice columns (W5..W0, E0..E5), each 2.5 mm wide. A slice band at y 10.2-15.5 mm holds su_l1 / su_c / su_l0, then fw / stm / sc / fe, then st_a / ctl / st_b, then hc0-hc3. Above and below it sit the CB quads (cbn near, cbx, cbf far), which are about three quarters of the die. A 1.56 mm west strip holds the serdes PHYs and the collective fabric (coll_s, coll_ft x3, coll_core, coll_ucie, glue, coll_ftm, coll_ftc, native59, tt_ctlm, coll_ftn, coll_n).
- **Data flow.** Good. 1,921 lanes, 626 bit-metres, 6,467 registered hops: p50 271 um, p99 393, max 403.5, none over 405. 4,546 stations. The CB chains run vertically through the cbn_q00 centre street (longest lane 9.4 mm, 30 stations). The fabric joins the array at one seam (coll_ftc to sl_W5), which is the architecture, not a layout defect.
- **Margin.** The worst hops sit at 403.3-403.5 um (`sl_W*_fe__x_fe_stm_p1`, `sl_W4_fw__x_fw_ctl_p2`), and glue sys_face at 400-403. A lattice snap of one 8.64 step breaks them. Plan new stations at 340.
- **Where the traffic concentrates.** ctl is the hub (152,664 port bits out, 60 lanes through). sc and stm are feedthrough corridors: 91k and 57k lane-bits cross them, and one sle_sc_v2 carries 9,110 ft bits in 17 slots against 570 bits of its own.
- **Clock.** H-tree root at die centre on M8/M9, 16,486 tap drops over all instances, insertion 250 +/- 40. The CB types carry the widest tap windows on the die (150-160 ps; die median 70). The forwarded-clock hops are finding 1.
- **Reset / START.** Wavefront release from glue, root part sl_W0_sc, relay 405. The START fan is not closed: finding 3.
- **Congestion.** No die GRT exists on this floor (finding 2). The plan estimate puts the worst route supply in the CB ring regions (p99 1.1-2.06 on cbf / cbn / cbx), then su_l1 (1.46-1.70) and su_l0 (1.14-1.22). The slice band is under 1.0 except st_a / st_b (0.92-1.24).

## Ranked findings

| # | Finding | Structural fix | RULEBOOK | Owned? |
|---|---|---|---|---|
| 1 | Forwarded-clock source chosen by tap index, not position. 573 outputs on 56 families, every slice and every CB quad. Hop median 930 um, p90 1,932, max 2,870 (CB types: clk_t24..t27 feed pins on the opposite corner). 570 are cured by re-pointing to a tap 15-52 um from the pin. | Generator rule: fclk_out takes the nearest tap of the current grid, never the root; G0 error. Hand items: coll_ft__cla4a25d77 fclk_out_cland_up (567.9 um, signed type: add a tap and re-sign) and coll_core. Fix the tap renumbering at source (clk_t80 dangling on sle_stm_v1__cl27746664). | R-REACH-4 | OWNED: DIE-QC-100 s29 (one fwd_src_fix run), tool RULES-REACH-1. |
| 2 | No die-level GRT, STA or clock proof on the HF-1c / s28 floor. RELEASE_TREE still shows QC at plan_qc52 with GRT / STA / CLK BLOCKED. The last die GRT and clock map are from 10-24..10-31. The M8 grant note says "no die route guide yet". | Run the die GRT0 + clock prototype on 736058c458ee now, in parallel with the event. | METHODOLOGY 12; owner rule "freeze on die GRT0" | NOT OWNED. DIE-PROTO-2 asked DIE-QC-100 for the plan on 11-12 06:27 and got no answer. |
| 3 | START fan open: 332 clock_landings G0 rows on the head (244 CLAND START = 122 with no incoming edge + 122 hops over 405; 88 cland_mon over 405). 23 of 75 reader chains are stale after the bands moved. | `reach_rules.py fix --rules 1,4` with share_trunk, then strict bind. coll_core START sites are a hand item. | R-REACH-1 | OWNED: DIE-QC-100 (LAND / GEN-CLASS-1 relay) + RULES-REACH-1. coll_core: no named owner. |
| 4 | st_a x9: over the cap and a hold population at once. 518k instances after CTS; 11,403 FF hold violators of which 8,472 are cross-tap at a median 11 um; TT setup -465 ps already at CTS. Render: body about 12% used, four W-centre clusters, E-face pin column at 80-100% over the lower half. | Order matters. First harden the rings and the 4 regions as cores (parent about 172k), which also puts ring pairs on one tap. Then the pre-GRT hold build. Then spread the E pins (cpitch 80, row_stride 3). The hold build alone took the prototype to 543k instances. | R-CAP-3, R-CLOCK-1/2a, R-FLOW | OWNED: DIE-QC-100 / QC-S28-CTLCAP (s29), HOLD-TAP-1. NOT OWNED: the -465 ps setup at CTS (R-CLOCK says "not this rule"). |
| 5 | sle_ctl x4: 419-451k movable (547k instances), no macros, 15,906 bus bits. Render: body 10-30%, all heat on the faces (W column 70-90%, two E columns 80-90%, S bar). Rings are 42% of the cells. Also the worst forwarded-hop family (34 rows, to 2,412 um), and two variants die in gen on `u_cland_collect_rst_n_t19`. | Re-target SPLIT-1106: the 10 widest rings and u_ctl as hard children, parent to 250k. Face pins spread as st_a. | R-CAP-3 rule 3, R-REACH-4 | OWNED: DIE-QC-100 / CTLCAP (s29), GEN-CLASS-1 for the override error. |
| 6 | CB array (cbn / cbf / cbx, 14 types, 259 instances). GRT overflow lies over the upper parts of the A0 tiles (cbn_q00__cl622f65d2: 629k). In the plan, N-face inputs na_i00 / nb_i00 feed u_t00, the tile at the S end, 1.3-2.5 mm away across a 458 x 1,158 tile that leaves only M6/M7. Post-CTS FF hold to -372 ps (cbf_q11). Tap windows 150-160 ps. | Bind each face window to the tile next to that face (swap tile roles or move the windows); stations in the 100 um centre street. Windows above 100 ps: fix the die clock for the region, do not pad. cbn_q00 cl_na_i00 12.96 to 25.92 um; cbf_q00_s2 corridor 86.4 to 90.72. | R-REACH-3 / -2, R-CLOCK-2b/2c, R-STREET-2/5 | PARTLY: s28 D spine re-site is in the event. NOT OWNED: window-to-tile binding and the CB tap windows. Medium confidence: a clone with the same 9 cores passed GRT, and reach rule 2 reports 0 QC types. |
| 7 | su_l1 / su_l0 / su_c (12 types). su_l1: lane cores (obs to M6) wall the W two thirds; 20.5k overflow at the NE corner where ft_cws0 516b meets three windows. slw_su_l1 has a closed wall (cl_rsf_i 17.28 um, needs 129.6). su_c: pg macro 17.28 um behind 1.1-1.4k W pins. Routed setup -530..-630. Six su types fail kit_istations (su_l0 x_su_c_p1_o 450 wide on a 369 face). | Hand forms: break the wall with a 43.2 cross street, lift the macros to 43.2, move the NE windows apart. Legalize refuses all 30 QC types (reset contract, points under cores). | R-STREET-2/3, R-REACH-2 | PARTLY: the kit blocker is with CTLCAP. NOT OWNED: the QC R-STREET hand forms ("QC needs hand forms", no lane named). |
| 8 | stm x11: routed setup -565..-1,046 ps. On the old floor the 4 tload ROMs sat mid-type, 600 um from the 2,103-bit N window. On the head one ROM is 40.7 um from the N outline and three are still 188-421 um away; 13 ft slots (5,643 bits) cross between the ROM rows. | Put all four ROMs in one row under the N window on a 43.2 street, with the ft lanes south of them. Register the ROM output; a 600 um data path does not close in 833 ps. | R-STREET-2, R-REACH-3, R-RTL | PARTLY: DIE-QC-100 (VISFORM stm frame). NOT OWNED: the pipelining. |
| 9 | hc0 / hc1 / hc2 x16, 355-395k (NEAR the cap). sle_hc1 render: empty body, all 18k overflow in the S-face landing band, where b_hw_i 1,573 bits land in 280 um (5.6 per um) with pin-register rows at y 17 and 27. | Ring landing form, window to 4 per um or less (split S + W), band 43.2 deep. Watch the cap. | R-STREET (dense face floor), R-FLOW, R-CAP NEAR | OWNED: DIE-QC-100 (HF-1c bands). Not re-viewed on the s28 floor: no s28 build exists. |
| 10 | sc x9: a corridor type. Overflow was all in the ft corridor beside u_core, with a 23.3 um E sliver. The head plan has the E gap at 66.5 um (checked in the plan). sle_sc_v2 shows 653k on a flat count. | Done in s28. Confirm at the first s28 place and settle the sle_sc_v2 count. | R-STREET-2/5, R-CAP | OWNED: DIE-QC-100 (VISFORM). |
| 11 | Collective fabric. coll_s render: 12 SRAMs in two clusters with 10-30 um seams and a diagonal relay band between them; post-CTS hold -268.69 from 3 CTS trees. coll_core: SRAM 17.28 um behind 1,959 W pins. Glue sink bins are a proxy. native59 LEC hung 22 h. | SRAM pairs abut or take a 43.2 street; one merged clock (in the event); re-dump glue bins at its first place. | R-STREET-1/2, R-CLOCK | OWNED: DIE-QC-100. coll_core form: no named owner. |
| 12 | Attempts are being spent on staging, not layout. Last hcut1111 rows are mostly KIT_NOT_SELF_CONTAINED, KIT_TOPOLOGY_BIND_STALE, pruned paths and unclassified unit failures at kit_rtl / gen / place. | Content-addressed kit snapshot; cap retries at 3 per signature. | EXPERT-REVIEW-1 levers 1 and 5 | OWNED: KIT-STAGE-1 / KIT-OPS. |

## Recommendations to COORD

1. Switch the wave to s29, not s28. The freeze runs to 11-15 04:00 anyway, and s28 kits would be built with 0.4-2.9 mm forwarded-clock wires on 99 types and with st_a / ctl over the cap. s28 can still post as the event; s29 (R-REACH 1+4, R-CAP hardening) should be the first plan the wave builds.
2. Give DIE-PROTO-2 the plan path today (epyc9 `wt/qc-s28-event2/.../zz_gates_ev2st.json`) for a die GRT0 and clock run. It is the only missing die-level evidence.
3. Name one owner for the QC hand forms that no tool will make: su_l1 / su_c walls, coll_core, the CB window-to-tile binding, the stm ROM row.
4. Name an owner for setup that is already negative at CTS (st_a -465, stm, su): hold and cap work will not sign these off.

## Not checked

- No type was viewed on the s28 floor: no s28 build exists, so every type render is from the old floor (hcut1111 or efdb36e864).
- Forwarded-clock wire delay was not measured; DIE-QC-100 found no wrong edge on 531 rows and 42 are unmeasured.
- Route supply is the 11-12 plan estimate on a slightly older chain step, not a GRT.
- METHODOLOGY 12 was read by heading only. R-RTL and the R-CAP / R-FLOW bodies were read at rule-line level.
