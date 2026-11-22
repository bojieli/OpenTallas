# NEARMISS-ECO-R1 handoff (Opus, started 2026-11-22 ~01:20 PST)
Goal: close routed near-misses (DRC 0; TT >= -80 or <= 20 ep; internal FF >= -40; unsigned, plan/any-plan, not HBM) with eco_loop run --lec (R-MINIMAL, <=3 passes) in private out roots; export on PASS+LEC EQ.

## State
- Scan: rtx-pro scratchpad nm_scan.py (read-only, signoff.json <4 d, all 7 hosts) -> scan/<host>.jsonl; match.py vs release cache + kit_wave_stages. Most near-miss records belong to types already signed (any plan).
- 02:2x RESUMED after limit. fe_v1 run1 ERROR (6_final seed fillers, DPL-0033) -> relaunched --from grt as ..._g. Waiter wait_eco.sh re-armed on fe_v1_g, stm_v2, serdes.
- ECOs (roots /srv/opentallas-scratch2/claude/nearmiss-eco-r1/<item>/{eco,ot-run.log,LAUNCH.txt}; kits read-only):
  - epyc8 slw_stm_v2__cl9beb65e6 unit oth-ubuntu-2124691-1795339457
  - epyc9 slw_fe_v1__clfe325744__cl08d14f0d unit oth-ubuntu-3818921-1795339456
  - epyc9 serdes__t13 (queued for 136 GB)
- Waiter: rtx-pro scratchpad wait_eco.sh (polls eco/eco_loop.json + ot-run RAN line every 10 min).
- On PASS + LEC EQUIVALENT: python3 -I <rt>/tools/autopilot/auto_export.py enqueue <best signoff.json> --die D --element ITEM --kind t on the DB host; the hub drain + rtx-pull do the rest. If rtx refuses for space: post, keep the record (no delete).
- COORD side item (epyc7 fam-kv-iopc-r2/kw44/fam-qc-cb unexported): done, 0 gained (all tree view copies; R-MIN ones already INDEX elements).

## AUTO-ECO gap (proposal, not pushed)
1. autopilot.py classify (~l.1300): NEAR-MISS needs TT and WHOLE FF (port-incl) >= NEAR_WNS_PS -30 and no clock/unconstrained FAIL; R-MINIMAL records with port-heavy FF or TT -30..-42 (still passing) go STRUCTURAL routed-not-signed and never become DONE-NEAR-MISS.
2. auto_resign.judge_eco re-applies the -30 ps / 100-endpoint window and the 'not an ECO class' refusal on advisory fails, which eco_loop dropped under R-MINIMAL (WF-1 minimal_eco_case).
Fix: under SP.is_minimal() use eco_loop.eligible(rec, path) for both (one source of truth).
