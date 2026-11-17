# S81-TYPES-R3 handoff 2026-11-17 05:35 PST
Takeover from Codex handback. Nothing signed yet this lane.
- col pg3 hold+M5 repair: E8 unit3114257 live (pg3_hold_m5_mm2_1117_r2.log, prd_run in docker, ~50 min). Collect; trigger = DRC0, TT>=-42, internal FF>=0. Then release col_h10_r2(12)/col_h9_r2(60) via hold_split_wave1_proposed_1117.json. ir1/h10a still DRT/pending.
- serdes H9: E2 unit2767880 in GRT (H9/serdes__t13 5_1_grt), collect. H10b report-only exit0: TT target -58.81 (exact +17.2) FAIL vs -42, FF ok. H11 synth exit0, log h11-synth-1117.out, no place yet. xface bc62574bc34 not gated yet.
- svc lo7: E2 original floorplan repair still live (invalid); copy-sibling not launched. hi3 not checked.
