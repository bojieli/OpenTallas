# PG-GRID-AUDIT lane (COORD 10-27 12:0x, ruling (A) follow-up): plan die.pg.grid == IR-checked grid == clock/GRT grid? S81/HEAD/KV/HBM (+QC ref)

## 2026-10-27 12:34 PDT RESULT (read-only audit; no plan edits)
Metal fraction = VDD+VSS metal / layer = 2*w/pitch (pg_regions.row_spec: pitch = VDD-to-VDD, nets alternate at pitch/2). tracks = infra_pg.tracks_of.
Grids: PL = M8 0.48@8.64 / M9 0.48@8.64 (11.1 % / 11.1 %, tracks 14.6/14.6 %); C3 = M8 0.48@4.32 / M9 6.48@34.56 (22.2 / 37.5 %, tr 29.4/48.3);
G12 (HEAD-5) = M8 0.48@4.32 / M9 12.96@34.56 (22.2 / 75.0 %, tr 29.4/85.7); QC-dense = M8 0.48@2.16 / M9 0.48@1.728 (44.4 / 55.6 %). PHY domains 1.92@8.64 (44.4 %) not compared.
Who reads what (main d9d8fce68 source): die GRT/dry build (gen_phys.die_pdn_tcl, die_trial.psm_pdn_tcl) = plan die.pg.grid only; die_clock_mesh = plan die.pg.grid unless --pg-json.

| die (adopted plan) | (a) plan die.pg.grid M8/M9 % | (b) grid of the IR headline | (c) clock planner / dry / die GRT | match | IR on the PLAN grid |
|---|---|---|---|---|---|
| S81 (main) | PL 11.1/11.1 | G12 22.2/75.0 (survey 2.1 mV) | plan (PATH-S81 12.8 build, no --pg-json); GRT plan | plan=clock=GRT, IR headline differs | survey PL p70 = 6.5 mV PASS (0.115 W/mm2 region model, not measured activity) -- no new run needed |
| S81-HEAD (main = R19 df038a2a = R20 c588bb01) | C3 22.2/37.5 | G12 22.2/75.0 (HEAD-5 delta 33029005, NUMBER-CHECKED 31.1 incl below-M7) -- 33029005 NOT on main/R20 | clock: R19/R20 straps from head_mesh_r3 --pg-lanes on 33029005 = G12; die GRT = plan C3 (GEOM-27 M9 probe substituted 12.96) | NO: plan C3 vs IR+clock G12 | HEAD-5 C3 pad75 42.6 FAIL (UNCHECKED); THIS LANE (bs_psm, uniform 1.258 W/mm2 CONFIRMED tile basis, 150/70-um pad): C3 38.8 above-M7 (VDD 25.0+VSS 21.4) +5.13 below = 43.9 FAIL; same deck G12 23.2 (+5.13 = 28.3 PASS) |
| QC (main; R28 branch adds VSS holes) | PL 11.1/11.1 (R28 VSS -5.55 pts) | QC-dense 44.4/55.6 (33.5 mV qc-pg-wc); survey G12 10.8 | plan PL | NO (ruled 12:0x (A)) | R28 111 mV (864-um window, 64 POINT bumps, no pad, 0.759) vs survey PL p70 32.9 (2972 window, 150/70-um pads, 0.582): two different decks, 3.4x apart on the same grid -> NUMBER-CHECK must pick one deck |
| KV hm_r26q4 b5aefbd6 | PL 11.1/11.1 | G12 (survey 37.6 @1.82 vectorless; PG-ACT kv_meas G12/H8 LIVE @1.05 measured); B75C3 22.6 (75-um pitch) | plan (CLOCK-KV R1.. 'PG basis plan die.pg rows, no --pg-json'); GRT plan | NO: plan=clock=GRT, IR on G12/C3 | THIS LANE: 67.4 mV FAIL (VDD 44.2 + VSS 43.1 co-located interior, 1.05 W/mm2 MEASURED-activity map kv_types_meas, 150 um/70-um pad), 1.9x of 35, before below-M7 |
| HBM c14 (claude/hbm-mu-quad-7-1027@e41772821, not on main) | PL 11.1/11.1 | G12 (survey 39.8 @2.18; Codex pad70 23.4/23.2 @1.27); B75C3 24.6 | H-tree planner not PG-aware; G0/G0C + die GRT plan PL; no PG-aware die mesh yet | NO: plan PL vs IR G12 | THIS LANE: 122.7 mV FAIL (VDD 80.6 + VSS 79.7) at the survey 2.18 W/mm2 B2r2 map (linear ~71 mV at 1.27, UNCHECKED estimate) |

Runs: epyc2 docker 40g cap, kits epyc2:/srv/opentallas-scratch2/claude/pg-grid-audit-1027/kits (gen copy on intel2)/{kv/PL_p70_int,hbm/PL_p70_int,head/{C3,G12}_p70_int}
(bump-survey bs_psm.py + HEAD-5 src, same windows/bases as BUMP-SURVEY / PG-ACT; summary epyc2 .../pg-grid-audit-1027/summ_{pl,head}.json). Numbers = own PDNSim, UNCHECKED (NUMBER-CHECK please).
Reading: only S81 has plan grid == clock grid == a passing IR grid. KV and HBM plan PL fails 2-3.5x; their passing IR numbers are on G12/75-um grids no clock/GRT tool sees.
HEAD: plan C3 vs IR/clock G12 -> adopt 33029005's M9 12.96 into the HEAD plan (one plan event), so plan == IR == clock.

## CODEX notes 2026-10-27 13:58 PDT
CODEX owns KV commensurate canonical-deck candidate with KV plan owner. M9 12.96@39.96 offset13.77 / M8 .48@4.32 puts fixed583.2+319.68k clock columns midgap (3.51um centre-to-PG-edge). Viewed local geometry image /srv/opentallas-scratch/claude/codex-sta-pg-1351/pg_clock_phase.png; straight-column PASS, full-tree dry review remains KV-owned. Native PG solve LIVE intel2:/srv/opentallas-scratch2/claude/codex-sta-pg-1351/kv_c39_w13 (unit oth-ubuntu-3599679-1793134614,96GB/8threads). Exact crop preserves global stripe/net phase,400bumps,70um pads,9.4088W measured type map, co-located VDD+VSS; inherited below-M7 allowance6.05mV. No IR verdict/adoption yet. HBM lead owns inherited QC light/wide jobs and HBM1788511 collection; no duplicate solve.
