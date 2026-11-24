# KV-PV-EDGESTRIP handoff (2026-11-24 02:38 PST)
JOB: pv face-strip taps over the cap (kv3_pv_v12e/v7e/v2ne/v6n/v5ne/v1n). ROW-REBASED on A5t posted 02:33. Job DONE.
ROW: epyc10 /srv/opentallas-scratch2/claude/kv-pv-edgestrip/row/ROWS_KV-PV-EDGESTRIP.py aff53806cf56 with ES_RESETS=anchor (NOT resel).
  On A5t2 a160bc6c5c2c -> epyc10 kv-pv-edgestrip/a5t/anchor/final.json 448aa1bcb33a (rt 445647cc300c).
  resel is void: it rebuilds the v12e/v7e collector trees, which drops other rows' relays, and the bind then fails with EMIT "reset tap absent" (27 sources).
GATES on A5t2: reprice 0 lanes, TAPOFF PASS, PRE 23 RSTREACH = base (diff 0), G0 PASS, collector trees identical to base.
  Scoped strict bind on the 6 pv types: 0 errors on pv types; 30 R8_STALE (astk read_addr <- vport out_t) = the same set as the A5t2 base -> KV-ALLFIX gate R8 refresh.
TAPS: v12e 1789->839, v7e 1859->917, v2ne 1376->1165, v5ne 1145->966. v6n stays at 1136 over its bank_sinks cap of 1000 (row untouched) -> KV-TAPSPLIT-HGPV, with the placed-sink class (pv at 1.3-3x planned flops).
CLEANUP: epyc10 tree (50 GB) and the epyc11 tree.forking-273274 deleted via ot-delete. ~5 GB of row/a5t/gate outputs remain on epyc10 kv-pv-edgestrip (plans KV-ALLFIX needs).
