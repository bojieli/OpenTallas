# S81 r9m215 + --vch-interleave (v4 die cases, 07d041319), recorded 2026-10-06 18:20 PT

Cases on EPYC3 /srv/opentallas-scratch2/claude/s81-rerun/cases/v4 (record mode of tools/dsrom_s81_fulldie.py).

| die | legality (outside/overlaps) | GRT i50 overflow v3 (no interleave) | v4 (interleave) |
|---|---|---|---|
| scan (sa/sb) | 0 / 0 | 2,466 | **1,212** (-51%) |
| layer1 (l1a/l1b) | 0 / 0 | 256 | **148** (-42%) |
| head (ha/hb) | 0 / 0 | 1,256 | **808** (-36%) |

Empty baselines (i5_base) 0 on all three.  Decision: adopt --vch-interleave (scan die round trip 151 -> 152, recompose
at rt 152).  Overflow is not zero: the remaining hotspot is M6/M8 (scan 429/248); next generator lever is VCH lane
pitch / an extra VCH column, not a setting sweep.
