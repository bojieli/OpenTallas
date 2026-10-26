# Frame feedthrough corridor correction

The previous station allocator avoided placing cells inside cores but its path search connected those stations using distance alone. A wide bundle could cross a small core between legal stations, exhausting its M6/M7 tracks. The helper now rejects an edge unless at least one Manhattan L order avoids every halo-expanded core; the same visibility filter applies to the first and last pin-centroid legs. Both L orders remain available. No reach, track budget, core position, bus width or station count changes.

In-place helper trial on DEC12 plan: all four failing frame types PASS the original overcore audit (22 total failures ->18 remaining leaf failures). 21 slots retain their counts (ft0=6, others5), so lane latency delta is zero. Actual paired-bit hop maxima: col_h10 ft0 370.44um, col_h9 ft0 367.731um; all other slots <=358.259um. Station placement still uses the exact row-legal allocator with core halos.

Invocation: python3 tools/die_plan/ft_sites.py PLAN --out NEW --ledger LEDGER --types col_h10_r0_p1__t1,col_h9_r0_p1__t1,col_h9_r0_p2__t1,col_h9_r0_p3__t1. This refreshes only the listed types; it does not rerun core placement. Regenerate the latency digest after replacing a plan, even though these counts do not change.

Viewed frame_ft_corridors.png: the revised stations stay in the existing top corridor above the ROM row and escape around the small eastern network cores; no station lies inside a core. Dashed links connect station targets schematically (actual routing uses the legal Manhattan order). Verdict PASS-COND for this geometry repair: downstream physical kit review must inspect exact bit paths and channel capacity before any route. No P&R/STA was launched.
