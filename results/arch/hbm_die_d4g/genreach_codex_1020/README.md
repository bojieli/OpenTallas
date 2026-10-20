# GENREACH continuation: preserve every leftover relay branch

Pinned predecessor: 703497f98; cquick failed its complete-placement assertion. A diagnostic-only replay afb253de4 preserved the exact missing-instance packet instead of an opaque assertion. It reports 57,209 / 57,211 placed, missing hcx_NW_2 and rf0101_s000_l0.

The contract confirms both backward links are nonreciprocal: hcx_NW_2 has predecessor rf0472_k00_00_l0 whose selected successor is absent; rf0101_s000_l0 has predecessor hcx_NW_0 whose selected successor is rf0101_s000_l1. The old algorithm walked backward over those links then followed a different successor, losing the starting node after the outer iteration had already passed it.

189871044 groups only mutually reciprocal linear links. Every starting member must occur in its group; forks and fan-ins split into separate groups and cycles terminate. Five meaningful regression cases pass. This changes only placement grouping: contract instances, edges, registered stages, static schedule and RTL stay unchanged. There are zero new hardware cycles. Reach is still checked on all actual buses and any overreach remains FAIL.

An isolated full fprsv-input validation is live in /srv/opentallas-scratch/claude/codex-hbm-genreach-forkfix-1020 on epyc7 (log artifacts/codex-hbm-genreach-1020/forkfix.otrun). It is not a native closure or release STA result. Original fp86/fprsv/diag/quick jobs remain preserved.

Runtime evidence: py-spy of original replay PID2068138 showed Occ.ii -> Occ.find -> put_near rebuilding the full die occupancy image for each leftover relay. A neutral performance continuation keeps the exact spiral, region, halo and tie decisions but uses expanding local summed-area windows. Three oracle tests pass (48 random occupancy cases, far window expansion, no-space, and post-mark cache invalidation). No new full GEN duplicates the progressing189871044 validation.

Other physical blockers remain explicit: baseline4649 failed lane rows,1188 planned missing stations,16914 overreach buses; reset/data station grouping was already split by predecessor code and must be regenerated on actual new pin placements. No die STA trust until complete emitted-hop reach and actual native closure.
