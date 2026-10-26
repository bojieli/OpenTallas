# B2m SerDes PHY supplies (OWNER decision 7) - IR check, 2026-10-24 (HBM lane)

Tool: `tools/die_trial/hbm_b2_ir.py generate --domain <die.pg.domains name>` (PDNSim, openroad/orfs:latest, run as
docker probes on epyc2 /srv/opentallas-scratch2/claude/hbm/ir_b2m). Each case solves ONE separate PHY supply alone:
its domain rect (window + 63.64 um guard), its own M8/M9 straps, bumps only in its dedicated rows over the window,
load = the SerDes macro only (TRIAL-HBM power map serdes class, 4.37 W per 600 x 600 um macro = 12.1 W/mm2, ASSUMED).
Budget 35 mV rail sum.

| case | straps per net | VDD mV | VSS mV | sum mV | verdict |
|---|---|---:|---:|---:|---|
| NW_io lk_N0, core grid 0.48/8.64 (baseline) | 5.6 % | 65.2 | 166.3 | 231.6 | FAIL |
| NW_spb0 lk_S0, core grid 0.48/8.64 (baseline) | 5.6 % | 67.0 | 127.7 | 194.7 | FAIL |
| NW_io lk_N0, PHY supply 1.92/8.64 | 22 % | 18.5 | 56.9 | 75.4 | FAIL |
| NW_spb0 lk_S0, PHY supply 1.92/8.64 | 22 % | 19.4 | 43.0 | 62.4 | FAIL |
| vsN0 lk_S1, PHY supply 1.92/8.64 | 22 % | 18.0 | 49.3 | 67.4 | FAIL |
| NE_io lk_N2, PHY supply 1.92/8.64 | 22 % | 18.5 | 53.5 | 72.0 | FAIL |

(1.92 um = the ASAP7 M8/M9 max width 2.0 rounded to the track grid; PDN-0107 refuses 2.16.)

Finding: the separate supply + dedicated rows cut the drop 3.1x (VDD 3.5x) but the assumed density still fails.
The density is the real problem: 6 x 112G PAM4 lanes in 0.36 mm2 is ~5-7x denser than published 7-nm 112G SerDes
(~0.35-0.5 mm2 per lane). PDNSim is linear in current: at a published-size macro (~2.4 mm2 for 6 lanes, ~1.8 W/mm2)
the same supply gives ~10-11 mV (PASS). Next (plan change, owner-visible): grow ot_pdie_serdes to a published-area
outline (or fewer lanes per macro) and re-run these cases; the NE_spb0 case is not solved (mirrored MY transform not
handled by the case generator; identical by symmetry to NW_spb0).
