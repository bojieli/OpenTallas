# FABLE-RCK-RX: S81 serdes__t1 RCK split, RXS and RXB review (2026-11-14 20:4x PST)

Scope: diagnosis only. Two read-only STA what-ifs through ot-run on saved DBs (epyc7, units oth-ubuntu-1547115 and
oth-ubuntu-982581, logs intel2 ~/coord/tmp/fable-rck-rx/, work dir epyc7 /srv/opentallas-scratch2/claude/fable-rck-rx).
No build, no kill, no git in the checkout. MEASURED = read from a report, log or DB. INFERENCE is marked.

## 0. What changes the picture (all MEASURED)

1. The brief's "last results" are not the last results. Two later builds by DIE-S81-85 (11-09) survive on epyc7 and
   both are far closer than the handoff says:
   - RXB `rxb_vC_cons` is ROUTED: DRC 0, antenna 0, TT setup +36.46, LEC exit 0, face guard 1456/1456, pin audit
     1461/1461. Only FF hold fails: -35.10 ps / 219 endpoints with the 25 ps hold uncertainty; at 0 uncertainty it is
     -10.10 ps / 14 endpoints. (epyc7 /srv/opentallas-scratch2/claude/die-s81-85/rxb_vC/signoff/signoff.json; my census.)
   - RXS `rxs_vD` (whole-unit floorplan guide) is PLACED: GRT estimate 0 overflow, placed TT +200.87 ps, LEC
     EQUIVALENT 18733/18733. It was never taken past place. (epyc7 .../die-s81-85/rxs_vD, .../rxs_analysis.)
2. FACE_RET was built. Every RXB form since vC (11-08 05:20) carries OT_S81_RCK_RXB_FACE_RET: RAW face guard
   592/1456 -> 1456/1456, kit LEC EQUIVALENT 21449/21449, placed TT +41.62. It is in vE_rq_local's spec.json and in
   rxb_vC_cons. It is right and it is not the open problem.
3. The RXB 21.6k GRT overflow was hold padding, not wiring. First GRT pass 0 overflow; 21,571 came after hold repair
   added 7,398 HB4 cells (DIE-S81-85 11-09 03:47). The same design at margin 0 / density 0.30 routes at 10.0 % use.
4. The RTL in both surviving kits is byte-identical to main 22c217df540 for ot_s81_rck_reform.sv, kp4_ddly, kp4_dout,
   kp4_bm, kp4_dsyn (md5 compared).
5. Both kits are idle since 11-09 on a fleet host under aggressive cleanup. Copy them before anything else.

## 1. RXB (ot_s81_rck_rxb, 725.76 x 280.8, 3 macros)

### History, each failure with its measured cause
| form | result | measured cause |
|---|---|---|
| vB | FAILED_RAW 592/1456 | 864 input bits (x_q 544, k_v 4, k_lo 310, k_L 5, k_any 1) each drive 4 ring-bank write muxes. Fixed by FACE_RET. |
| vC (FACE_RET, M6) | GRT 770 overflow (M3 484, M5 244) | All 770 gcells over the dchn macro x 280-390, y 60-180. 4 nets. dchn has OBS M1-M5 over 276.48 x 138.24 and interior M5 clk/rst_n pins at its centre (macro 138.3, 68.9); with top layer M6 there is no vertical track over it. Fixed by M7. |
| vD_m7 | routed TT -98.51/32, FF -29.90/95 | dmem rd_out[456] -> lpl5 writer bank: macro clk-to-Q 364.6 ps then buffer stages 108 + 133 + 255 ps; the dmem read pins are on its W face and the banks were far. Fixed by RQ1 capture beside the pins (0 external cycles). |
| vE_rq_local / vF_dmem_north (margin 15) | GRT 21,571, max 146 % | Hold padding: first pass 0, then 7,398 HB4. Hot at the SW clock-entry corner and in the channels beside the centre macro, which is where the pads landed. The two posts (S81-TYPES-11 22:25 for vE, DIE-S81-85 03:47 for vF) give the identical number; INFERENCE: one run, one of the two labels is wrong. |
| vC_cons (vF place, margin 0, PD 0.30, M7) | ROUTED, DRC 0, TT +36.46, FF hold -35.10/219 | See below. |

### Why the pads exist (MEASURED on rxb_vC_cons)
- dchn's view has min/max_clock_tree_path 202.79 / 250.14 ps (FF lib) and hold_rising 62.9-148.5 ps on 321 input pins.
  CTS balances the 14,617 registers to that insertion with delay buffers (delaybuf_otstb_*, delaybuf_*_clk). Core
  insertion becomes TT 574.0 mean (549.0-628.5), FF 453.9 (432.3-508.7).
- The kit times the IO virtual clock at the bound 250.0 TT / 202.5 FF (config.mk OT_VCLK_TT/FF, vclk_ff.sdc,
  sdc_lint insertion_ff_ps). The kit has OT_HOLD_MM = 1 but not OT_MM_MEASURED_HOLD. Insertion band: FF dev 246.39 ps.
- So every input port looks 246 ps early against its capture flop. Pre-repair FF hold: -232.86 ps over 1,505
  endpoints, of which register-to-register is only -68.47 over 571. Repair inserted 5,700 HB4 (3 chunks, 5,134 s).
  The 934 port endpoints are the 864 face bits plus resets.
- The cost shows in setup too: the TT worst path is lpr_out -> u_lpl_5_r.g_ck[8].u_local/rq, +36.46, through seven
  HB4 pads (about 330 ps of pad delay).

### What is left on the routed DB (my census, FF, SPEF, sign-off session)
| endpoints | 25 ps unc | 0 unc |
|---|---|---|
| u_out.u_cmem/wd_in[*] (from u_lpl_6_r.g_ck[*].u_local/o[*]) | 93, worst -35.10 | 12, worst -10.10 |
| u_out.u_cmem/r_addr_in, w_addr_in | 7, worst -25.05 | 1, -0.05 |
| u_lpl_{0,2,3,4}_face.cap (port starts x_q, k_lo, k_L, k_any) | 83, worst -16.07 | 1, -3.57 |
| u_face_q_d.q | 17, worst -15.34 | 0 |
| u_chn/k_lo | 13, worst -6.82 | 0 |
| other (read_oh, warm, os) | 6, worst -5.17 | 0 |
| total | 219 | 14 |

- The cmem class is a local clock seam. Worst path: launch flop CLK at 441.03 ps, 58.6 ps of data
  (QN 43.6 + INVx1 14.3 + 0.7 wire) to wd_in[237]; u_cmem/clk arrives at 490.81 ps, 49.8 ps later, through
  clkleafrep_4019624 -> wire19559 (34.2) -> wire19558 (57.5) -> clkleafrep_1319597 (34.8). cmem's clk pin is M4 on
  its W face at core (518.4, 43.97); the ck port is M5 on the N face at x 362.89. GRT-stage repair left -4.04;
  detailed route moved it to -10.10 at 0 uncertainty.
- Advisory only under the academic profile: slew 506 TT / 295 FF (worst u_lpl_5_r.g_ck[6].u_local/_152_/A 590.6 ps
  against 320), cap 1, pair skew 92.8 / 87.0, clock coverage NOT RUN (UNEXPANDED_CHILD_ETM).

### Structural fix
Keep (all measured to work): vF macro place dmem (43.2, 187.2) R0, dchn (220.32, 43.188) R0, cmem (518.4, 43.2) R0;
top layer M7; N-in / S-out faces; FACE_RET, RQ1 (DQREG), SPCYC; ck on N at x 362.89, which is 4.3 um from the dchn
clk pin column (x 358.6). No rotation and no pin-face change is needed. Do not go back to the vE single row (dmem at
x 21.6): its W channel is where the pads piled up.

Change one thing: time the core's ports against its measured insertion, not the 250 / 202.5 bound.
- RXB-M: spec insertion_ps 570 / insertion_ff_ps 450 (OT_VCLK_TT/FF, constraint.sdc, vclk_ff.sdc and sdc_lint follow;
  kit_modes checks they agree), HOLD_SLACK_MARGIN 0. This is what the kit's hard_core_latency contract already says
  ("parent tap subtracts the core insertion").
- Parent obligation: RXB ck must arrive 320 ps TT / 246 ps FF before the clock of its face partners (RXS face flops,
  parent registers). INFERENCE: this is cheap in the FIX-S81-SERDES-CLKPART island, because the serdes register trees
  are already 500-790 ps deep: RXB ck straight off the rck root, no delay chain. It is the same early tap that
  FABLE-SERDES-STRUCT fix 2 asks for u_chn, moved to the RXB boundary. RXS insertion is about 290 TT / 232 FF
  (vF routed clock path), so the RXS-to-RXB lead needed is about 280 TT.
- If the parent cannot give that lead, the as-built form is the fallback: it is a valid late core against a plain
  250 / 202.5 tap, paid for with 5,700 pads.

### One-build proofs (run both, they are independent)
- P-RXB-1 (fastest, no rebuild): one hold ECO on the surviving routed DB
  (epyc7 .../die-s81-85/rxb_vC/run/results/asap7/kl_ot_s81_rck_rxb_vC_cons/base/6_final.odb), then re-sign.
  14 endpoints at 0 uncertainty, 136 non-port at 25. Pass: FF hold non-port >= 0, DRC 0, TT >= -42 (now +36.46).
  Understood local near miss, so ECO is allowed. The parent must then treat RXB ck as a plain tap.
- P-RXB-2 (structural, about 2 h): RXB-M from the same 1_synth netlist, floorplan onward.
  Pass: pre-repair FF hold endpoints <= about 600 (register-to-register only, was 1,505), HB4 count < 1,500
  (was 5,700), GRT overflow 0, routed TT >= -42, FF hold non-port >= 0 after at most one ECO.
  INFERENCE: the cmem seam stays (about 12 endpoints) unless u_cmem/clk shares a leaf with the u_lpl_6_r writer flops.

### FACE_RET verdict
Right. It is the only fix for the 864 shared input bits that adds no external cycle, it passes RAW guard and LEC,
and it has been in every build since 11-08. One open item I could not close from the hub: the dedicated proof log
showed base 9,989 checks / 0 errors with the negative-bias mutant "still to collect" (CODEX-S81-RCK-0222); later full-RX
runs (30,040 / 0) cover the vE defines, which include FACE_RET. TL-SERDEST1: confirm the mutant result before sign-off.
dchn_kr (+1 rck, registered dchn pins) is not needed for this: form B missed TT -78 internal, form A stalled in DRT.

## 2. RXS (ot_s81_rck_rxs, 259.2 x 216, no macros, about 140k cells)

### History, each failure with its measured cause
| form | result | measured cause |
|---|---|---|
| vB | placed TT -75.51 | ld2[2][3] -> BM2 group 3 PE18 thq[2]: 24-load control buffers. Fixed by BM_PE_LOCAL (46 groups). |
| vD (216 x 259.2, M5) | routed TT -94.15/131, FF -8.85/13; LEC NOT EQ 33 | Probe on the routed DB: sp1 -94 (sc_q -> sp1 XNOR tree; fixed by SPCYC, +1 rck); BM load cone dz -64 / 86 endpoints (Sl[1][9], 19 fanout, 50 fF nets, slews 190-335 ps); kc -27, gm -25, thq -10. LEC: never-reset theta constant, fixed by THC. |
| vE_tail_sp_pinned | placed -45.48, not routed | Same ld2 -> dz load cone. |
| vF_prel (PREL, +0 cycles, M5) | ROUTED: TT -24.34/9, FF hold -6.59/47 (25 unc), DRC 0, LEC EQ 18733 | All 9 are BM dz. Worst u_syn.g_bm[1].u_bm.d[1][5] -> dz[41][0]: flop fanout 18 (175 ps slew), place5286 137 ps, final net 14 loads 41.9 fF, 114 ps wire, 360 ps slew at D. The 3 BM units are interleaved (register medians (159,73) (143,92) (158,77)), 46 dz copies per unit spread die-wide. Hold: 46 x0 from u_face_in + 1 u_rst. Kit lost with epyc6. |
| vG_region (register-only guide, M5) | GRT 37,711 (M3 18,459, M5 9,528, M4 5,696, M2 4,028), max 157 % | The guide pulled 7,228 BM registers into three 48 x 44 boxes at y 80 and left their logic north of them. |
| vC_m6 (vG + M6) | GRT 74,981, max 182 %, 3.15 m wire | Same. Cut census: 9,649-9,974 nets cross y 100-115. |
| vD whole-unit guide (DIE-S81-85, M6) | PLACED, not continued | See below. |

Note: vF_prel routed at TT -24.34 already meets the 11-13 academic setup gate (>= -42). Its hold is +18.4 at 0
uncertainty. It was dropped under the older 0 ps rule and then made worse by the register-only guide.

### rxs_vD, measured
- Guide (region_guide.tsv): syndrome engine band x 4.32-254.88, y 140-204 under the N input face; one column per
  RiBM unit, registers and cone together: bm1 x 4.32-87.84, bm2 87.84-171.36, bm0 171.36-254.88, all y 12-136.
- Nets crossing horizontal cuts, vC -> vD: y 100: 9,649 -> 2,528; y 115: 9,974 -> 2,569; y 130: 8,920 -> 2,718.
- GRT estimate, same recipe on both placed DBs (M2-M6, 30 iterations): vC 120,020 overflow, 3.05 m wire, 62.7 % use;
  vD 0 overflow after 4 extra iterations, 1.60 m wire, 34.6 % use (M2 48.1, M3 47.8, M4 26.5, M5 21.6, M6 17.9).
- Placed TT (my probe, 5 TT libs, placement RC, ideal clock): WNS +200.87, TNS 0. vF placed was +103.68.
- 36 % utilisation, LEC EQUIVALENT 18733/18733, defines REFORM RELAY4 AM_FACE3 SYN_LOCAL BM_PE_LOCAL RXS_THC
  RX_SPCYC BM_PREL.
- Pins: ck M5 on N at x 129.61 (midpoint); i_d on N x 54.4-162.7; x_q / k_lo on S x 20.0-184.6. The band order
  (inputs N -> syndrome band -> BM columns -> S outputs) is data order, so no pin-face change is needed.

### Structural fix
The whole-unit guide is the fix: each RiBM unit owns a column, the syndrome engine owns the band under the input face.
Keep outline, pins, M6, RTL. Set HOLD_SLACK_MARGIN 15 -> 0 (the kit still has 15).

### One-build proof
- P-RXS-1: resume the surviving kit from 3_place (epyc7 .../die-s81-85/rxs_vD, design kl_ot_s81_rck_rxs_vC_m6):
  CTS -> GRT -> route -> sign-off. Pass: GRT overflow 0, routed TT >= -42, FF hold >= 0, DRC 0.
  INFERENCE: routed TT about +70 (vF lost 128 ps from placed to routed; its loss was the dz broadcast that the columns
  now shorten). Hold: expect the same 46 u_face_in -> x0 pairs; one ECO pass if they stay negative.
- Fallback only if P-RXS-1 fails GRT: rebuild vF_prel unchanged from main (no guide). It is the one RXS form that
  routed; -24.34 passes today's gate.

## 3. Dead ends
- RXB: any form with hold margin 15; the vE single-row macro place; more GRT repair iterations; dchn_kr.
- RXS: register-only guides (vG, vC_m6); raising the layer cap alone; NBM=6 / +30 cycles; another pin cycle on the
  inner RiBM loop.

## 4. Not done
- No route was run. P-RXS-1 timing after CTS and the RXB-M pad count are predictions.
- I did not check which hold uncertainty the current R-MINIMAL sign-off applies (0 or 25); both counts are given.
- I did not verify the FACE_RET negative-bias mutant log.
- The parent lead for RXB (320 TT / 246 FF) is not checked against a serdes__t1 island plan; DIE-S81-92 owns that.
