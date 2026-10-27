HBM-CORE-LAT-R3 gate evidence (2026-10-27). gate_r3.tsv = per-type gate (survives unified plan / interface free of pending deltas).
Reproduce on epyc2: copy codex/hbm-2001@3c3dae6bb results/hbm_mu_2001/buddy/{NW,NE}/candidate_type.json to /tmp/cand_{NW,NE}.json,
 python3 scripts/gate2.py /srv/opentallas-scratch2/claude/path-hbm-r15-1026/planS2 /tmp <mod,mod,...>   -> pinmap_census.txt
 (OWNERS.tsv hbm NEEDS-KIT rows as /tmp/needskit.tsv) python3 scripts/loc.py <planS2>                   -> needskit_locations.tsv
pinmap counts = distinct per-instance pin tables (sha of sorted name/layer/x/y); 'same=True' = unified candidate reuses the B2o tables.
