GEOM-REVIEW xfin actual placement — 2026-11-01 07:48 PST

Reviewer: Codex xfin. Both PNGs opened and visually reviewed. Verdict: HOLD for route; B preferred; full signal GRT pending. Neither variant is SIGNED.

Actual rendered geometry is balanced and near square with distributed arithmetic placement, no macro slivers or blocked crossing. N-face signal banks remain fixed near pins. B155.52x164.16 measures54.54% fill,10.03% near-empty bins, pin-register p90=7.97um,max138.59um(reset), no unregistered data pins,0 paths>405um and worstR2R287.87um. Pin density4.2/um is below budget6. The estimated vertical-demand hotspot at(100,107.5) is.809 vs default.6 and hard1.0. This is a localized estimate; existing rule accepts .6..1.0 only after actual GRT0. No route approval while that result is pending. Clock root N-midpoint has237.57um maximum pre-CTS reach, informational before CTS;17540 sinks are rooted.

A151.2x164.16 has56.07% fill,10.17% near-empty, p90=8.04um,worstR2R275.94um, but reset-to-register150.71um exceeds150um backstop; same col_v hotspot.807. Prefer B instead of waiving that A reach violation.

Next: let progressing immutable3_place signal-GRT finish; use its congestion result to judge B, then CTS with current standard G5 class and actual fresh-face guard. Detailed route remains held until GRT and timing support it. No latency changes or relaxation of833ps,TT0/FF25ps.
