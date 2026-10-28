# LIB-VDROOP-CHECK (OWNER request 10-27): ASAP7 delay at 0.665 V vs the 12 droop model (+5.1 % late on data)

## 2026-10-27 10:34 PDT result (lane agent, continues the 08:09-dead lane)
Method: ngspice-42 + BSIM-CMG OSDI on the open ASAP7 extracted cell netlists + 7-nm model cards (TT 25 C, FF 0 C), per VT R/L/SL;
nominal vs drop: TT 0.700 -> 0.665 V (-35 mV), FF 0.770 -> 0.7315 V (-5 %). Files intel1:/srv/opentallas-scratch2/claude/nc-vdroop-1027/
{scripts/vdsim.py,vdan.py, res_cells/dff/chain.json, rvt3/*.log (RVT 10-stage chain, ideal-ramp drive, .ic/uic + gear: the BUFx-driven
deck did not converge)}. Ratio = t(drop)/t(nominal). Cells: 3 slews (10/20/40 ps) x 3 loads x rise/fall each.
Cross-check: SPICE nominal INVx1 RVT TT s20/5.76 fF = 28.0 / 32.2 ps vs Liberty asap7sc7p5t_INVBUF_RVT_TT 27.7 / 32.5 ps (<=1.2 %) -> deck CHECKED.
The flow is RVT (ORFS asap7 default; all OT_* cells _R), so RVT rows govern.

| class (TT, 0.665/0.700) | RVT med (min-max) | LVT med | SLVT med | FF RVT med (0.7315/0.77) |
|---|---|---|---|---|
| INVx1 / INVx4 | +6.7 % (5.8-9.7) | +5.2 % | +3.6 % | +5.9 % |
| NAND2x1 / NOR2x1 | +7.8 / +7.5 % (5.8-9.9) | +5.5 / +6.3 % | +3.7 / +4.5 % | +6.5 / +7.3 % |
| BUFx4 / BUFx12f / BUFx24 | +7.4 / +7.1 / +6.3 % | +5.3 / +5.1 / +4.2 % | +3.7 / +3.5 / +2.9 % | +6.0 / +5.7 / +4.5 % |
| all cells | +7.1 % (4.8-9.9) | +5.2 % | +3.6 % | +5.9 % (3.0-11.3) |
| DFFHQNx1 clk->QN | +8.9 % (7.9-9.7) | +6.5 % | +4.6 % | +7.4 % |
| DFF setup / hold (RVT) | +0.2..+1.35 ps / -0.7..+0.9 ps | | | +0..+1.1 ps / -0.7..+0.45 ps |
| 10-stage logic chain (INV/NAND/NOR, 300 ohm + 5 fF/node) | **+9.4 / +9.9 % (r/f)** 417.6 -> 456.7 ps | +6.8 / +7.2 % | +4.7 / +5.0 % | +7.7 / +8.2 % |
| 405-um M8 repeated stage, BUFx12f (wire-dominated) | +5.0 / +4.7 % | | | +3.7 / +3.5 % |
| 405-um M9 NDR stage, BUFx24 (C UNCHECKED) | +6.3 % | | | +5.0 % |

Verdict (CHECKED, SPICE): +5.1 % is NOT conservative for RVT logic. Measured TT RVT sensitivity is ~1.4-2.0 %/% Vdd: cells +7.1 % median
(up to +9.9 %), DFF clk->Q +8.9 %, a logic-dominated 10-stage chain +9.4..+9.9 %. +5.1 % only covers wire-dominated M8 repeater segments
(+4.7..+5.0 %) and LVT/SLVT cells (+5.2 / +3.6 % median). A logic-dominated 833-ps RVT reg-to-reg path at 35 mV needs ~+9-10 % late
(~+30-40 ps more than the model on a full-cycle path vs +5.1 %); FF-corner sensitivity is lower (+5.9 % cells, +7.7..8.2 % chain).
Setup/hold constraint change at drop is <=1.4 ps (negligible). Not a rule edit: reported to COORD for a ruling on the 12 data derate
(options: +10 % RVT logic / +5 % wire segments, or pass on a smaller droop budget, e.g. +5.1 % ~ 18-20 mV on RVT logic, UNCHECKED interpolation).

## CODEX notes 2026-10-27 13:58 PDT
Measured RVT sensitivity report collected. No new SPICE run or rule edit: the +5.1% versus measured~9-10% logic discrepancy remains an owner-controlled policy question, preserved for FLOW/root.
- 2026-10-27 19:00 PDT [DROOP-DERATE-1] 12.4a b2 data droop per class implemented in the shared model: claude/droop-derate-1027@a54186302 (die_ci_margins.json data_droop block + tools/die_plan/data_droop.py; die_sta_related --data-droop class|flat|none, default class; die_ci class-mode data lines; signoff run --droop-check = INFO-only 0.665 V). Setup only; hold never credited; clock keeps shared-droop rule. CHECKED control: KV hm_r26q5c39 mode none = byte-identical to KV-PLAN-DELTA-5 G39_ab; QC none summary = original sta_cv; FF hold unchanged in every mode. Before->after TT setup (none -> flat 5.1 % -> class), UNCHECKED: KV raw seam 467.12 -> 462.23 -> 457.55 (-9.56), intra 504.13 -> 494.56 (-9.56); KV HB4 after-TT abutted seam 175.10 -> 131.70 (-43.4), intra 233.45 -> 196.81 (-36.6), plan HB4 seam 163.33 -> 120.56 (-42.8) [FLAG: larger than a few ps, from +10 % on ~5 HB4 cells/path; still positive]; QC R24 seam 558.51 -> 553.04 -> 547.81 (-10.70), hold -96.47 unchanged. HEAD-R23 NOT RUN (STA blocked by clock-jog shorts, COORD 17:44). S81 0.665 V INFO (TT, 60 ps unc kept): VQ 2.48 -> -60.90, node_NNfd 8.23 -> -65.12 (INFO FAIL, full-cycle RVT paths, no wire-class cells; matches LIB-VDROOP +30-40 ps). The other 6 cores were NOT RUN because their routed DBs are deleted on every host (gunit_l4r, rxsb, LLd, NNfu, LLfd, LLfu). die_ci ILM flow passes no wire list (all data cells = logic, pessimistic).
