# DIE-QC-6 (2026-10-28): real-view FF hold on QC K2, freeze gate re-run with MESO-START-2

Runs: epyc2:/srv/opentallas-scratch2/claude/die-qc6-1028. K2 data is DIE-QC-4 (die-qc4-1028/K2/CA_2w2s). The plan is the event plan 40b05f16d753.
Tools:
- wt/die-qc5-1028 (4edf8acf6c: fixed scale_clock + --count-align-key region) for the real-view runs.
- wt/meso-start-2 (fbb34b6aac, which carries the same fixes) for the gate re-run.

Gate flags on every run: --cppr-lca --clock-cal spice --count-align-key region --clock-ocv table --clock-droop shared.
All numbers are OWN (my reruns / reads) and UNCHECKED-independent unless marked.

## 1. Binding the signed SU views: the K2 plan slots are not the signed cores
Five signed ETMs were staged in views/<module>/ with pins.json and provenance.json (scripts/mkprov.py):
- vmr f4kfinal
- crh_rp1 f4g
- prog s8b
- rst3 K0: the ETM is pre hold-ECO. This is conservative for hold, because the ECO only adds data delay.
- s8x_crh

The gate run with --core-view-match-pins (default ON) bound **0 of 84** SU placements. Every one failed with "pins differ" (CHECKED). Causes:
- The K2 plan pin tables are the provisional "QC-P6-G0C ... one 'io' group facing the glue band; the leaf LEF port table replaces it when the su_c leaves are bound" (CHECKED).
- The slot outlines differ from the signed LEFs:

| core | plan slot | signed LEF |
|---|---|---|
| vmr / crh_rp1 | 259.2 x 276.48 | 250.56 x 216 |
| prog | 354.24 x 259.2 | 259.2 x 354.24 (rotated) |

So step 1 is a plan delta, not a flag. The plan event must:
- take the signed LEF outlines and port tables for the 5 SU types;
- apply the CORELAT-SQ-1 taps (vmr/rp1 DROP, prog 472.7, s8x_crh 292.5);
- then pass G0C -> GRT -> CA -> STA.

## 2. Real-view FF hold (INFO: --no-core-view-match-pins, because the plan pins are placeholders)
Main die STA output (rvI_none):
- 84/960 placements real; 3,360 intra pairs have a real endpoint; 504 are both real.
- Real-endpoint worst: FF -133.57, TT -160.07.
- Both-real worst: FF -109.99 (84 neg), TT -125.45.
- Gate intra FF -162.18 and TT setup +127.34 (real prog -> crh paths), both unchanged.

The main tool keeps the budget register on every tap next to the core model. scripts/rv_phys.py therefore times ONE physical model per tap (core tap -> its ETM only, other taps -> budget). Results (rvphys_*.txt):

| sl_*_su_c FF | pairs | no early taps: worst / neg | CORELAT early taps: worst / neg |
|---|---|---|---|
| core-core | 504 | -114.5 / 89 | **-28.1 / 24** |
| core-glue | 2,856 | -131.9 / 1,277 | -114.4 / 1,143 |

The early taps fix most core-core SU paths. The cause without them is the core insertion against the 202.5 FF budget: prog FF clock-tree 345-411, so in_hold is 297.7.

c_* (A0, 145,152 pairs) is unchanged at **-160.6 FF**. There is no A0 view to bind: no routed NK/NL view exists on the fleet (CHECKED by search).

## 3. Structural cause of the c_* hold
- c_* partitions have 28 taps: 5 glue + about 6 die taps per A0 core x 4 cores. This is the old a0cv8 multi-pin entry (u_t00.ck, ck_t1, ...).
- Breakdown of the c_* pairs (scripts/c_pairs.py):

| pair class | pairs | share | worst FF hold | neg |
|---|---|---|---|---|
| same-core (two die taps of ONE A0 core = an in-core path timed at die level with zero logic) | 97,152 | 66.9 % | -162.2 (= the gate worst) | 89,004 |
| core-glue | 44,160 | 30.4 % | -159.6 | 41,046 |
| glue-glue | 3,840 | 2.6 % | -121.3 | — |

- The A0 centre entry that COORD adopted 03:35 (one tap per core, own in-core tree) moves the same-core pairs into the core's own CTS/hold sign-off, like the SU cores (signed in-core spread 26-60).
- The HB4 BOUND only falls 7.91M -> 7.40M without them (scripts/hb_nosame.py). The bound is (all core data pins) x (the partition's worst k = 4). The core-glue pairs keep k = 4, so the bound is not a per-path count.
- Clock OCV on c_* pairs (scripts/ocv_split.py, main clock_ocv_fn): median 45.4 = 34.8 die tree below the LCA + 10.6 declared in-core class B.
  - The capture branch below the LCA is a median 558 ps / 13 stages (p99 754). sl_* is 250 ps / 7 stages, with 17.8 ps OCV.
  - Two taps in one c_* region share only the region root, so the region tree is deep.
  - Shortening it to the sl_* depth saves about 17 ps of OCV. It cannot close hold by itself: the median c_* pair already needs 56 ps of data delay.

## 4. Freeze gate re-run on K2 + MESO-START-2 --tree-parent x3 (G_tp, COORD 03:36 default)
| item | number | verdict |
|---|---|---|
| GRT0 incl clock | DIE-QC-5 logs, unchanged input | PASS (CHECKED by QC-5) |
| in-region skew TT/FF | 135.39 / 117.43 | PASS |
| TT setup intra / seam | +475.43 / +545.94 | PASS |
| FF hold intra / seam | -162.18 / -97.89 | FAIL |
| CA plan | 0 fail, worst lo 106.8 | PASS |
| CA bind | 2537 crossings, 0 no-taps, 0 unbound | PASS |
| CA lag lo/hi TT | 121.7 / 288.4 | PASS |
| CA lag lo/hi FF | 116.8 / 241.0 | PASS |
| start-skew | 37/312 TT, 24/312 FF | FAIL (MESO-START-3) |

These match MESO-START-2's own numbers (on die_plan_sliceclk) on the event plan.
