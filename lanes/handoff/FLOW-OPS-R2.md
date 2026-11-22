# FLOW-OPS-R2 handoff (Opus 5.5; successor of FLOW-OPS-1300) -- live memory
Lane clone: epyc10 /srv/opentallas-scratch2/claude/FLOW-OPS-R2/repo (sparse tools+rtl+physical/common_flow); tmp .../FLOW-OPS-R2/tmp
## P1 NOMCAP-MAP (re-sign clock gate NOT RUN)
- Cause: signoff.consumed_clock_model_coverage mapped only /work/ receipts; r708 /nomcap/<lib> -> UNAVAILABLE -> checks.clock NOT RUN -> resign.py run --auto refuses (gates not PASS: clock).
- Fix b5ea2f4739d (lane clone): /nomcap/<f> -> nomcap_dir()/<f>, sha-bound; new `signoff.py refresh-coverage RECORD --flow-tag T [--write]` (no STA rerun, keeps signoff.json.pre_cov_refresh). Test tools/die_plan/test_nomcap_coverage_map.py. Push: epyc10 tmp/push1.log.
- qkd_ahub: epyc7 /srv/opentallas-scratch2/claude/fable-fix-kv-hub/r4/ahub/eco2/resign_je, tag flow-20261117-je-kv; probe with fix = SIGNED_CHILD_ETM PASS both corners. TODO after push: refresh-coverage --write, resign.py provenance --kit .../eco2/k --tag flow-20261117-je-kv --dir resign_je, tell FABLE-FIX-KV-HUB-R5.
- Sweep: auto_resign_jobs on intel2: only ar-eaedf7da0b75-a1 (sle_st_b_v1 qc, 11-19, gates not PASS: clock) candidate. Host scan of signoff.json (>=11-18) with the nomcap reason: scratchpad scan/*.out (7 hosts).
## P2 push17 PUSHED 3504af932d (COORD: done). Left: flaky ot-run tests under load.
## P3 canary bisect s81_head_cl (baseline .. cd2cd11c4e), start 8a2a7b31a9 (OT_CLASS_KEEP=0 A/B). s81_cl needs FLOW-CANARY-R2 fixture. HBM canaries dropped.
## P4 watchdog (container gone or 0% CPU 30 min -> HUNG + cancel), io_guard, lever 9, items 8/11/12, tools_lag parser false positive.
