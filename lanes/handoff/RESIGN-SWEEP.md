# RESIGN-SWEEP 11-14 06:2x
Scan: every signoff.json under /srv/opentallas-scratch{,2,3}, scratch-root, closed_archive, /archive on epyc2/7/8/9/10, intel1/2, localhost (rtx-pro) and AGIdock /archive: 227k passing-R-MINIMAL-or-SIGNED records, matched by name/top (dp_/kr_/ot_ prefix stripped) to the 594 unsigned non-HBM elements of /api/elements.
Only 8 elements have any passing record: coll_ftm, kv3_phy, kv3_sys_SD_v1, qkd_astk_ex_s, slice_station__t41, s81p_..t51_native_w, ot_s81hd_he_epc (already direct rows), kv3_phy_v1 (NOT passing: FF -17).
COUNT-DIRECT +6 rows (kv3_sys_SD_v1, kv3_phy, qkd_astk_ex_s, coll_ftm, slice_station__t41 x2). Forced count 06:10: all 6 read as signed_records; per-die signed_types/cores unchanged vs 05:35 (S81 36t/62c, HEAD 19t/5c, QC 3t/53c, KV 4t/33c; the plan-level 05:35 line already carried these), so the wave-view (/api/elements) was the stale side, not the tree.
No other unsigned type/core has a passing record anywhere: the remaining ~580 are genuinely unbuilt/failing.
Scan data: /tmp/claude-1000/rs on localhost.
