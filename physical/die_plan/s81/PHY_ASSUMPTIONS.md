# S81 PHY, PHY power and bump contract: published-figure assumptions (S81.XDIE)

2026-10-26, lane S81-PHY-ASSUME. OWNER 2026-10-26: "I do not have those numbers. Use published figures and record
them as assumptions."

Every value below is **ASSUMPTION (published)**. None of it is measured on an OpenTallas PHY view. The machine-readable
form is `phy_assumptions.json`, and `phy_assume_check.py` checks the plan against it (output `phy_assume_check.json`).
ASAP7 counts as N7-class here, the same node as the A100 comparator. Published N5 silicon is scaled to N7 by area
x1.5 (range 1.29 = SRAM-cell ratio to 1.84 = logic-density ratio, TSMC IEDM 2019). Bump pitches and module widths are
package technology and are not node-scaled.

**What the plan assumes now** (`die_plan.json` die.io + die.pg.domains, plan rev on main):
- 14 SerDes windows per die (WS0-3, WN0-3, ES0-1, EN0-3). Rank dies use 10 of them and copy-A/B dies use 12.
- Each window is one `ot_pdie_serdes` macro: 6 lanes x 112G PAM4, 614 Gb/s at the core.
- 26 signal sites per macro at 150-um "C4" pitch.
- A dedicated VDDPHY/VSS domain with 45-um PG rows over the macro.
- PHY area target 2.4 mm2 per macro (0.40 mm2/lane). The placed macros are 0.81-2.41 mm2.
- One HBM3E PHY: 8657 x 1227 um, about 1,900 signals, 55-um micro-bumps.
- The S81 die has **no UCIe** link (one die plus one HBM3E stack per package). The links are board SerDes over DAC/AEC.

## Assumptions table

| ID | Value | Unit | Source | Scaling to ASAP7/N7 | Conf. |
|---|---|---|---|---|---|
| SER.RATE | 112 | Gb/s/lane, PAM4 | OIF CEI-112G; IEEE 802.3ck | none (112G LR shown at 7 nm: ISSCC 2020 6.2, ISSCC 2021 8.7) | high |
| SER.EFF_NET | 0.941 | payload/raw | RS(544,514) KP4 x 256b/257b (IEEE 802.3) | none | high |
| SER.LANE_AREA_N5 | 0.373 | mm2/lane | VLSI 2022, doi:10.1109/VLSITechnologyandCir46769.2022.9830304: "quad transceiver occupies 1806x825um2" (5 nm) | measured at N5 | high |
| SER.LANE_AREA_N7 | **0.56** (0.48-0.69) | mm2/lane | from N5 above | x1.5 (1.29-1.84) | med |
| SER.MACRO6_AREA | **3.36** (2.89-4.12) | mm2 / 6-lane macro | 6 x the above | N7 | med |
| SER.SHORE_PER_LANE | 553 (513-612) | um/lane, one row | VLSI 2022: 1806 um / 4 lanes | x sqrt(1.5) | med |
| SER.DEPTH | 1011 (937-1119) | um | VLSI 2022: 825 um | x sqrt(1.5) | med |
| SER.MACRO6_SHORE | **3318** (3078-3672) | um, 6 lanes in 1 row (a 2x3 fold: ~1.66 mm shore at ~2 mm depth) | derived | N7 | med |
| SER.ENERGY | **6.5** (4.1-7.5) | pJ/b/lane incl. DSP, excl. FEC | 5.6 pJ/b 5 nm incl. DSP (VLSI 2022); 602 mW/ch 7 nm analog only (JSSC 2021, doi:10.1109/JSSC.2020.3024261); 460 mW at 112G at 7 nm = 4.1 (ISSCC 2020, doi:10.1109/ISSCC19947.2020.9062925). Same as technology.json `board_serdes_112g` | N7 LR with DSP | med |
| SER.FEC_ENERGY | <=0.9 | pJ/b | RS(528,514) 90 mW at 40 nm (IEEE P802.3bj gustlin_01_0312) | upper bound, not scaled | low |
| SER.MACRO6_POWER | **4.37** (2.76-5.04) | W per macro, active | 6 x 112 x SER.ENERGY | N7 | med |
| SER.IDLE | 0.73 | W/lane ungated | technology.json (static links: ungated = active) | N7 | med |
| PHY power density | 1.30 (0.67-1.74) | W/mm2 | MACRO6_POWER / MACRO6_AREA | N7 | med |
| SER.SIGNALS | 26 | bumps/macro | 4/lane (TX+/-, RX+/-) + 2 refclk | none | high |
| SER.SIG_GND | >=1 | GND bump per HS signal bump | industry practice. No primary 112G bump map found. The nearest is the UCIe-S map (Das Sharma et al., IEEE TCPMT 12(9) 2022, doi:10.1109/TCPMT.2022.3207195, Fig. 7) | package | low |
| BUMP.C4 | 130 (100-150) | um | UCIe-S 100-130 um (Hot Chips 2023 UCIe tutorial); TCPMT 2022: "minimal pitch of C4 bumps has reduced to about 100 um" | package | high |
| BUMP.UBUMP | 45 (25-55) | um | UCIe-A 25-55 um (HC 2023; UCIe SNIA SDC 2024 KPI table); HBM-PHY micro-bump 48x55 um (Alphawave Semi, DesignCon 2025) | package | high |
| HBM.SHORE | 378 | um per 96 I/O (HBM3, Si interposer) | Alphawave Semi, DesignCon 2025, "Innovative Interposer Solutions for HBM3/4" | package | med |
| UCIE.A.MODULE | 388.8 x 1043 | um (x64, 45-um pitch) | UCIe HC 2023 Electrical Summary; TCPMT 2022 "module width is fixed at 388.8 um ... depth is about 1 mm" | package; not used by S81 | high |
| UCIE.S.MODULE | 571.5 x 1320 (1540 at 24/32G) | um (x16) | UCIe HC 2023; TCPMT 2022 | package; not used by S81 | high |
| UCIE.RATE | 4-32 (48/64 in 3.0) | GT/s | UCIe SNIA SDC 2024; HC 2023 | none | high |
| UCIE.SHORE_BW | A 165-1317 / S 28-224 | GB/s/mm | UCIe SNIA SDC 2024; HC 2023 | none | high |
| UCIE.ENERGY | A 0.25-0.6 / S 0.25-1.25; idle 15% of peak | pJ/b | UCIe HC 2023 Electrical Summary | spec target | high |
| UCIE.A.PG_SHARE | ~0.30 | of bump field | derived: TCPMT 2022 "~400 IO/mm2" vs a 570/mm2 hexagonal 45-um field | package | low |
| UCIE.S.PG_SHARE | ~0.45 | of bump field | derived: ~72 bumps at 110 um in 571.5x1320 vs 40 signals | package | low |
| A100.NVLINK3 | 50 Gb/s/pair, 12 links, 600 GB/s | N7 anchor | NVIDIA "Ampere Architecture In-Depth" blog; Hot Chips 2020 | the node anchor ran 50G NRZ; 112G at N7 is the ISSCC class above | high |

Source URLs: UCIe HC 2023 tutorial
<https://hc2023.hotchips.org/assets/program/tutorials/ucie/Electrical%20Form%20Factor%20and%20Compliance.pdf>;
UCIe SNIA SDC 2024 <https://snia.org/sites/default/files/2025-05/SNIA-SDC2024-DasSharma-Updates-on-UCIe-Technology.pdf>;
Alphawave DesignCon 2025
<https://www.signalintegrityjournal.com/ext/resources/PDFs/DC25_PAPER_Track05_InnovativeInterposerSolutionsforHBM_Ilamparidhi_V6.pdf>;
NVIDIA <https://developer.nvidia.com/blog/nvidia-ampere-architecture-in-depth>.

## Check of the S81 plan (phy_assume_check.py, 2026-10-26)

All 14 SerDes windows MISMATCH. The plan is FROZEN-path material, so nothing is changed here. The findings go to
PATH-S81 as a PENDING-DELTA (lanes/COORD-REVIEW-QUEUE.md).

| Class | Windows | Macro (shore x depth, area) | Finding |
|---|---|---|---|
| A gross | WS3 | 363 x 2240 um, 0.81 mm2, 28 sites, no phy_macro_um | The shoreline is 1/9 of the published figure. There are 28 sites for 26 signals, so no ground per pair. |
| A gross | ES0 | 2886 x 1227 slot, PHY zone 396 um off-shore, no phy_macro_um | The PHY is not on the die edge (orient fix owed, already noted in die_io). |
| A gross | WS0, WS1, EN0, EN1 | 2758 x 482 um, 1.33 mm2 | Depth is half of the published 937-1119 um. Area is 46% of the low end. |
| B short | WN0, WN3, EN2 | 2608 x 711 / 1854 x 1163 / 1668 x 1163; 1.85 / 2.16 / 1.94 mm2 | The area is 64-75% of the low end. WN3/EN2 are too narrow for one row and too shallow for a 2x3 fold. |
| C marginal | WN1, WN2, ES1, WS2, EN3 | 2608 x 924 um, 2.41 mm2 | These fit the N5 measurement (2.24 mm2, 2709 um) but fall 17% short of the N7-scaled low end (2.89 mm2, 3078 um). |
| all | 14 | 150-um signal sites inside 45-um PG rows | PITCH_MIX: two bump technologies in one rect (see the bump contract below). |

The plan's 0.40 mm2/lane ("published 7-nm") is in effect the 5-nm measurement (0.373). The N7 value is 0.56
(0.48-0.69).

**PHY power.** The published figure is 4.37 W per active 6-lane macro: 43.7 W on a 10-macro rank die and 52.4 W on a
12-macro copy-A/B die. The VDDPHY IR trial (`results/die_trial_1024/codex_phy_1025`) ran at 0.15 W/mm2, which is
0.21-0.24 W per window, about 18x below that figure. Scaled linearly, its 2.55 / 2.74 mV worst drops become about
47 / 58 mV (6.7% / 8.3% of 0.7 V). A PDNSim re-run at the published density (1.30 W/mm2, or 4.37 W over the actual
macro) is owed. `docs/RELEASE_RACK.md` 2.4 already charges 4.37 W per macro on top of the 84.1 W die figure from the
old 10-04 report. Whether that 84.1 W includes the PHY is still unknown, and there is no 72-frame die power report.

**HBM PHY.** OK. The shoreline is 8657 um against the 7.48 mm needed (1,900 / 96 x 378 um). The pitch is 55 um. The
bump field is 45% PG, which is consistent with the UCIe-A/S derived PG shares.

## Bump contract (assumed, for the S81.XDIE decision)

1. The die face has **one bump technology**. The S81 package is 2.5D (an HBM3E stack on an interposer), so every die
   bump, signal and PG, is a micro-bump at 45 um (HBM field 55 um). C4 at 130 um (100-150) is the interposer-to-substrate
   layer. The plan's 150-um SerDes "sites" and the 150-um core lattice are a conservative stand-in for that escape
   pitch. Rename them as C4-escape sites, or re-derive the sites at 45 um.
2. Each SerDes macro gets 26 HS signal bumps, at least 1 GND per HS signal (low confidence), and the rest VDDPHY/VSS.
   That gives at least 52 escape sites at 150 um per macro. WS3 (28) fails this.
3. VDDPHY is separate per window (OWNER decision 7). It is sized for 4.37 W at 0.7 V, which is 6.2 A per macro.
4. The HBM PHY keeps 55-um micro-bumps with about 45% of its field as PG.
