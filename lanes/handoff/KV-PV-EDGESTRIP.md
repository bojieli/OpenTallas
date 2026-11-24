# KV-PV-EDGESTRIP handoff (2026-11-24 00:15 PST)
JOB: pv face-strip taps over the 1200-sink cap (kv3_pv_v12e/v7e/v2ne/v6n/v5ne/v1n), row on A5r 41044638cda3 for A6.
FINDINGS: v12e/v7e = reach_fix_sinks duplicated 7x (no geometry problem). v2ne/v5ne = stale clock keepouts (copy of moved landing bands). v6n 1136 and v1n 1145 (planned) already <= 1200; v1n placed-model 1483 -> 1198 in KV-TAPSPLIT-HGPV r2.
ROW: epyc11 /srv/opentallas-scratch2/claude/kv-pv-edgestrip/row/ROWS_KV-PV-EDGESTRIP.py (anchor and resel variants, dirs anchor/ resel/). Loads after: v12e 839, v7e 917, v2ne 1165, v5ne 966; 0 over 1200. v12e/v7e lose taps (250->245, 207->180) because the duplicate weight is gone.
OPEN: PRE (row/pre.sh, queued behind epyc11 load cap), tree fork (fork.otrun -> tree/), then row/sb.sh PLAN TAG = scoped strict bind + G0. Then ROW-REBASED to KV-ALLFIX + FABLE-RC-KV.
CAVEATS: plan sink bins are old placements (K2 v6n measured 139670 tap sinks vs 50235 in bins; 87424 of those were pad-delay flops that PADRAM/WIDERAM may remove). Re-read loads on the first A5/A6 place. Generator fix still owed: reach_fix.py density loop must not re-append rows already in reach_fix_sinks (FLOW owner).
