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

## 2026-10-27 12:18 PDT PG-ACTIVITY-KVHBM result (claude/pg-act-kvhbm-1027@48f939873f, results/pg_activity_kvhbm_1027/README.md)
150-um bumps, 70-um pads, G12 grid (M8 0.48@4.32 / M9 12.96@34.56), PDNSim VDD+VSS co-located, interior. The PDNSim numbers are CHECKED: they are the run outputs, with pad_fallback 0, PG_CHECK OK and EXIT 0 on every kit, and KV agrees with linear scaling (21.7 vs 21.8). The power bases are UNCHECKED.
| die | power basis (window W/mm2) | above M7 | below M7 | total | verdict |
|---|---|---|---|---|---|
| KV | old vectorless 1.818 | 37.6 | - | - | FAIL |
| KV | MEASURED 1.050 (head_eighth e1 x0.580, pv_pair x0.520) | 21.8 | 6.05 (e1 slice; 3.88 at measured W) | 27.9 | PASS |
| HBM | old 10-24 map 2.179 | 39.8 | - | - | FAIL |
| HBM | SM FLAT 0.5 upper bound 1.366 (real hnx_rp3lp3h halves + CTS x1.189) | 25.0 | 5.13 est (no SM final odb) | 30.1 | PASS (upper) |
| HBM | SM vectorless lower bound 0.755 | 13.8 | | | |
Measured activity: KV types hg 2.054->1.191, hgi 1.971->1.143, pv 1.257->0.654 W/mm2. The other KV types are scaled by ratio (UNCHECKED-ESTIMATE). HBM SM measured is still running: tb_hgi_sm_e2e --ds, ot-run unit oth-ubuntu-1788511-1793125212 (intel2 pg-act-kvhbm-1027/hbm/sim). Collect with tools/pg_activity/collect_hbm.sh + make_hbm_map.py. It can only land between 0.755 and 1.366, i.e. 13.8-25.0 mV above M7. HBM non-SM blocks keep their 10-24 values.
HBM die edge (task 3): EDGE-FILL lattice (pitch 150 kept, 168 columns, first column 72.12 um from the edge instead of 147.12; pg_meas_psm.py --edge-margin 60). Die-edge band goes 112.3 -> 38.5 mV on the old map (= inner 39.5), and is 24.2 on the flat-0.5 map. Render hbm_edge_lattice.png viewed. KV edge windows are cold (0.23 W/mm2).
Denser M8 H8 (M8 0.96@4.32), old maps, run at 96 GB: KV 37.6->28.4, HBM 39.8->30.6. It needs 88% of M8 tracks, so it is not needed. KV H8 on the measured map is still running (intel2 pg-act-kvhbm-1027/kits/kv_meas/H8_p70_int); this is informational only.
Next: collect the HBM SM measured run; adopt the bump lattice (edge-fill) + pad_um into the plans (HEAD-5 merge); rerun HBM on the current unified plan once it is adopted.

## CODEX PG-ACTIVITY-2 2026-10-27 14:08 PDT
Collection/results-only859e194486 oncodex/pg-act2-1351: inheritedQCcanonicalinteriorLIGHT32.902/WIDE9.715mV ABOVE-M7,150um/70um finitepad,VDD+VSS,4761loads/2401interiorpairs. ExactR28net_holes18c cutcoupon reviewed/runEXIT0unit3659867,19M8+4M9VSSstripes/14368viasremoved,bothrailsconnected,34.094mV(+1.192). Only0.906mVleftforbelowM7; nofullPGclosure. ActualmacrofreeQCfinalPGbelowM7coupon LIVEintel2codex-pg-act2-1351/qc_below unit3832916-1793135147,readonlyoldfinalODB,idealM7,80260actualcells normalizedcanonical.5823W/mm2. No route/synth/repeatfull-die.
HBM1788511 endedSIG143/noHGI_SM_E2E PASS;case0INT8retired571/noERRbeforecase1,case1partial,DSnotreached. ExistingpowerreportsDONE13:28intel1pg-act-2-1027/hbm/out collectedwithoutrepeat. Placedhalfdensities.31947/.31755W/mm2;BDCCTSuplift.61046/.61406areESTIMATESnotbounds, missingrealSMclocktree/current4hardphysicalviews. DoNOTadoptqualifiedmeasuredHBMmap. Currentactualdieemitterpointsource4um/finitepad+edgefill sharedsourcegapreportedroot.

## CODEX notes 2026-10-27 14:14 PDT
Collected pending KV jobs without rerun: measured H8 terminal EXIT0,4761 matched VDD/VSS loads, co-located20.894mV+inherited6.05below=26.944mV; original L8 light-M8 candidate42.868+6.05=48.918mV FAIL. Both UNCHECKED independent review; H8 consumes88%M8 tracks and old34.56M9 pitch conflicts the retained clock, so neither is adopted. Receipts intel2codex-sta-pg-1351/inherited_H8/result.json and inherited_L8/result.json. New PG-ACT2 steady-state e1 report0.1186288W vs fullbench0.1167979W (+1.5675796%); preserve native solver and show separate uniform-load linear sensitivity. Current core-interior commensurate candidate12.96@39.96 offset13.77 remains LIVE (PG-GRID-AUDIT); no whole-die PG verdict: native x6 PHY footprint/digital-glue vehicle still blocked and owned KV/FLOW/TOK. Root owns main die_trial finite70pad/edgefill integration; no parallel edit.
- 10-27 17:17 PDT PG-ACTIVITY-3 KV: c39 (M8 .48@4.32, M9 12.96@39.96) canonical interior 26.972+6.05 PASS CHECKED (PG39 50.596 = crop-edge artefact); halo 5994..9870 8100 loads 13.505 W 650 bumps 26.324+6.05=32.37 PASS CHECKED; real die corners on c39 bump lattice bottom edge FAIL (LL 36.01/LR 38.52 above M7 -> 42.1/44.6); EDGE-FIT bumps (lattice margin 60 um, pitch 150.09x150.41, 400/window, 850 pads, fallback 0) LL 25.25/LR 25.39/UL 22.57/UR 22.62 -> worst 31.44 PASS CHECKED (6.05 below-M7 = Codex basis UNCHECKED). d5 interior A 20.16/B 15.97/C 22.80 (D OOM, E running) all heavier than c39. Lightest passing KV = c39 + edge-fit bump map. claude/pg-act3-1027@149e7645d results/pg_act3_1027/results.json
