# HBM plan event d44q (DIE-HBM-56/57, 2026-10-31): CANDIDATE, pending the g50 50-iteration verdict

STATUS: CANDIDATE. Do not merge until the g50 50-it table below is filled and every row beats its control (COORD ruling (b): judge each row against its own control at 50 iterations on the same current g2 probe; the old d44f 140,343 is not the reference).

d44q = d44p + one-class per-bit ft station siting fix (COORD ruling (a): one event, 12.28b by intent). Only `partition_types` changes, in 3 types [CHECKED: section diff against d44p]:
- q_b011 (NE_b011): L15x1 E-strip columns (DIE-HBM-55 B), last hop keeps 8% of dy; L42x4 gap box x150-230 y1031-1129; L183mx2 E strip x245-300. Changes: 26,307 bit sites, 12 regs.
- q_b011__physical_v1 (NW_b011): the same family fix. Changes: 24,741 bit sites, 6 regs.
- q_b110__physical_v1 (NE_b110): L6br0_2 stations spread rank-linear in the lane0/lane1 channel x100-300. Changes: bit_sites + 4 regs.
Station counts are unchanged and every per-bit hop is <= 394.9 um (asserted by site_box.py, branch claude/die-hbm-56-1031 results/die_hbm_1031/dhbm56). Clock, tap_window (q_hub W80), pins, cores and connections are all unchanged.

die_plan.json sha256 = f1d2075992c7 (full value in SHA256SUMS). Source plan: intel1 /srv/opentallas-scratch2/claude/die-hbm-56/plan/r3_0.08.

G0 / G0C (tools/die_plan/check.py, --completeness) against d44p: identical message sets (G0 966 = 2 ERROR / 964 WARN; G0C 1319; 0 new, 0 gone) [CHECKED]. Reports are in g0/.

G2, 0 iterations (current g2 @ main f1a8dcffa6e) [CHECKED]:
| type | d44p | d44q |
|---|---|---|
| q_b011 | 1,026,793 | 353,666 (-66%) |
| q_b011__physical_v1 | 1,027,141 | 605,084 (-41%) |
| q_b110__physical_v1 | 35,091 (d44q_B base) | 9,037 (-74%) |

G2, 50 iterations, the gate. TODO successor: fill this table from intel1 die-hbm-56/g2 and die-hbm-57/g2.
| type | control (same probe) | d44q |
|---|---|---|
| q_b011 | ctlP_b011_i50 = TBD | r3_0.08_b011_i50 = TBD |
| q_b011__physical_v1 | d44p_pv1_i50 = TBD | r3_0.08_pv1_i50 = TBD |
| q_b110__physical_v1 | d44f g50 9,166 (old g2) | r2_b110_i50 = TBD (q_b110pv1 and q_b011pv1 are byte-identical in r2 and r3_0.08 [CHECKED]) |

Kits: core kits do not read partition ft_slots, so every d44o/d44p core kit stays valid on d44q.
