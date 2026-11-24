# QC-OPEN-SU handoff (11-23 19:3x PST)
Parent QC-ALLFIX / QC-ALLFIX-SU. Job: per-row state for rc105 su_c, RED +2, rc103 su_l1, SUC-Q0, rc99, rc101.
DONE 19:32: all 6 IN-COMPOSE C1b 62ce8aba0292 (epyc7 /srv/opentallas-scratch2/claude/QC-ALLFIX/rows_c/plan_c1_fix1.json),
evidence = plan diff vs C4 81fd3e6370c0 (kw45/snap_qwen_compute/qwen_compute_v4c4 plan_of_record); ALLFIX-QC.tsv rows updated; post 7ffe38a1.
Scripts: localhost scratchpad qcopensu/verify.py, verify2.py.
Open risk (told QC-ALLFIX): RED2 is a tree-file row (zz_extra_red_plus2_c4.json 3daaf93866cb + asbuilt land_r8_extra);
the epyc11 cD fork comes from the C4 snap, so ov_red2 (+ov_r8) must be overlaid before the C1b strict. cD fork waits on tree-copy slots.
No units launched or adopted. Next if asked: su_c/stm/sc probes on C1b after its strict (~21:45).

## Job 2 (COORD 19:4x): C1x probes, probe-only (FIX3 = QC-ALLFIX-SU)
- 21:50 launched 6 stm/sc reps on C1-noSU 12b66c0e4829 (strict 0, LAT 1922): epyc7 QC-ALLFIX/cC/{tree,bind}, rt 70b6f0430ea9 + OT_TOOLSTALE_RT (9b19260 refused: reset gen differs from bind), gen epyc7 (epyc11 lacks plan). Units intel2 systemd runitem-<item>; specs ~/coord/autopilot/private_specs/QC-OPEN-SU/. Script intel2 /srv/opentallas-scratch2/claude/QC-OPEN-SU/probe.sh (env RT, PROBE_HOST).
- Pre-SU2R stm/sc form. TODO: su_c x3 + stm/sc rerun on C1c+FIX3 bind (cE) when QC-ALLFIX posts strict PASS.
- Reads: place, CTS post-hook, final 5_1_grt.odb, full-cause census -> post to QC-ALLFIX + FABLE-RC-QC.
