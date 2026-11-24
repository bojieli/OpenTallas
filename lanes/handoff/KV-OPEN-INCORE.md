# KV-OPEN-INCORE handoff (Opus 5.5, started 11-23 19:30 PST). FAMILY lane under KV-ALLFIX; census item (e) (FABLE-RC-KV 331a59eb).
Job: move every in-core station onto streets (re-site / re-route slot), hops <= 405, cycles priced; PRE + G0 (GEOM-STATION-IN-CORE 0); ROW-REBASED to KV-ALLFIX. Due 22:30.
## Dirs (epyc8 /srv/opentallas-scratch2/claude/kv-open-incore = I)
- I/rows/ROWS_KV-OPEN-INCORE.py: pass1 re-route in-box runs (hard cores + clock keepouts, +2.16 um) round cores, target 395 routed;
  pass2 SEAM re-seat (last station -> out pin -> next first station <= 395); pass3 latency.lanes rows re-derived (gen.latency_table delta).
- I/census.py PLAN [OUT]: die G0 lane stations in keepouts (check.lane_geometry model), strict type GEOM, lane pin hops > 405.
- I/compose_i.sh = KV-ALLFIX compose.sh with O=I/TAG; I/g_i.sh TAG LIST = compose + precheck + census + G0 (check.py --r8-strap-pads --band-base D28).
## Findings
- A2f 2d63fe8dbefe: strict GEOM 18 (hgi_v3 13, hgi_v4 2, hgi_v6 2, hg_v3 1); die streets in-keepout 40; lane pin hops > 405: 5 (L346 523.5, L536/543/550/557 562.7 = seam hops, last station at y 997.92).
- Dry run on A2f: GEOM 0, die in-core 0, over-405 0. +1 station on hgi_v3 ft8/16/17/18/20 and hgi_v4 ft16 (L346 +7, L341/342/343/1431 +1).
- Left: hgi_v3 ft28 face station at (1237.463, 0) in clock keepout [1156,0,1500,130] (not a hard core; die G0 does not count it).
## Log
- 19:30 TAKING. 19:5x I1 = A2g 3857747ea992 + row 2da978d59b97 (no LAT pass). I2 = A2g + row 62c2c39b7a5a (with LAT pass) running.
