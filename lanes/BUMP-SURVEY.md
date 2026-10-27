# BUMP-SURVEY (OWNER request 10-27): bump pitch + pad model per die

Scope: S81, S81-HEAD, QC (qwen_compute), KV (qwen_kvsys), HBM. Open pad data only (COORD 07:33 basis: GF180MCU open PDK 9.4.3
pitch >= 70 + 1.3*UBM -> pad >= 73.5 um at 150 um; CERN hep-ex/0101011 150-um pitch = 70-80 um footprint; TOPLINE daisy-chain
150-um parts). HEAD-5 basis = 150-um C4 pitch, 70-75-um square pad plate tied to every same-net M9 strap it overlaps.

## 2026-10-27 10:45 PDT result (lane agent, continues the 08:09-dead lane)
Files: intel2+epyc2:/srv/opentallas-scratch2/claude/bump-survey-1027/{bs_psm.py,summ.py,kits/<die>/<cand>_p<pad>_<win>/}
(tool = INFRA-FIRST-HEAD-5 window_kit pad model, src = claude/infra-head5-1027 tools; plan = origin/main die_plan.json, pg.domains dropped;
PDNSim VDD+VSS, co-located VDD drop + VSS bounce per load block, interior >= 450 um from open window edges; 2972-um window).
Grids: PL = plan grid (M8+M9 0.48@8.64); G12 = HEAD-5 (M8 0.48@4.32, M9 12.96@34.56); C3 = M9 6.48@34.56; B75C3 = 75-um pitch, 37.5 pad, C3.
Window values are ABOVE-M7 only; HEAD-5 adds the below-M7 tile slice (5.13 mV at 1.542 W/mm2) -- not solved for the other dies.

What each die's PG plan / IR assumes today (origin/main 60b5ddf52 + lane records):
- No die_plan.json on main has a bump pitch, pad size or bump map. Pitch is a tool default 150 um (die_trial.bump_grid, infra_pg pg_bumps);
  contact model on main = 4x4-um point source on the nearest same-net M9 strap (die_trial.bumps_tcl size=4.0). Pad plate exists only on
  unmerged claude/infra-head5-1027@e5f4fb2cd. PHY windows: own 45-um micro-bump PG lattice (45/sqrt(share)).
- S81: plan grid 0.48@8.64 both layers + 14 phy domains. Last IR 10-26 codex/aux-pg-1026 analytic VDD-only 71.2 mV FAIL (preparatory, 130 um,
  assumed power); native PDNSim lost with epyc1. No pad model.
- S81-HEAD: 150 um + pad 70/75, G12 grid; NUMBER-CHECKED 29.9 mV (75) / 31.1 mV (70, overlap contact) incl 5.13 below-M7; 35.45 centre-only bound.
- QC: plan 0.48@8.64; last IR claude/qc-pg-wc-1026 VDD-only 33.5 mV PASS at 100-um C4 pitch, point contact, flat 0.759 W/mm2, UNCHECKED, not adoptable.
- KV: plan 0.48@8.64; KV-INFRA-R2 analytic VDD-only, point contact, measured (vectorless report_power) 1.29 avg / hg 2.05 W/mm2:
  bp150 194 / bp75 41.8 FAIL, bp60 32.8 PASS. Codex PDNSim codex-kv-pg-1027 (flat 0.15 W/mm2) worst 3.51 V = invalid (VDDPHY window loads, no bump).
- HBM: main plan is the stale d4g v2; current plan not on main. Last IR 10-24 B2r2 PDNSim with a 45-um 20-um-contact array (not 150): SM 31.7 int / 47.0 edge.

Survey under the HEAD-5 basis (150 um, pad 70/75), this lane's PDNSim, CHECKED (run outputs; window power from each die's model):
| die | window W/mm2 (basis) | PL p70 | G12 p70 | G12 p75 | C3 p70 | edge band G12 p70/p75 | B75C3 (75 um/37.5) |
|---|---|---|---|---|---|---|---|
| S81 | 0.115 (infra_pg region model) | 6.5 | 2.1 | 2.0 | 3.7 | 3.8 / 3.7 | - |
| QC | 0.582 (region model, owner cap) | 32.9 | 10.8 | 10.0 | 17.9 | 12.4 / 11.8 | - |
| KV | 1.82 (hg window, KV-INFRA-R2 vectorless measured) | - | 37.6 | 35.2 | - | not run | 22.6 |
| HBM | 2.18 (B2r2 power_map, SM r25gp) | - | 39.8 | 37.6 | - | 112.3 / 87.7 | 24.6 |
| S81-HEAD (NUMBER-CHECK) | 1.542 hot block | - | 26.0 (+5.13 = 31.1) | 24.8 (+5.13 = 29.9) | - | 19.9/23.7 (75) | - |
H8 (M8 0.96@4.32) kits for KV/HBM OOM-killed (exit 137); not rerun.
Reading: at the HEAD-5 basis S81 and QC PASS with wide margin (and QC even on the plan grid at 32.9 above-M7, marginal once below-M7 is added).
KV and HBM FAIL 35 already above M7 at 150 um / 70-75 um pads (KV 35.2-37.6, HBM 37.6-39.8, + an estimated ~6-7 mV below-M7 UNCHECKED);
both PASS at 75-um pitch (22.6 / 24.6 above M7). HBM edge band 88-112 mV: first bump column sits 147 um from the die edge (grid centred),
so the strip x<147 is fed one-sided -- an edge-row placement fix, UNCHECKED. KV/HBM power maps are not activity-measured (owner 10-27:
PG on measured toggle rates) -- a lower measured density may move them under 35.
Next: KV/HBM measured-activity power maps; edge-aligned bump row on HBM; below-M7 slice per die; adopt pad_um into main (HEAD-5 merge).
