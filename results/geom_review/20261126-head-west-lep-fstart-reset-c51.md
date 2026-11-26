# HEAD West LEP FSTART reset review

The exact R2d3 East work is independent. West evidence comes from the retained E8 W9 rows2 kit and its E8 clock synthesis report. The exact successor is W10 plan 450e777c0e584a1f0be1173b0ce2bd6cc0e394f6587deaf7626bb1236d472973.

The old FSTART relay receives a reset leg across the upper pair macro. The CTS report gives −908.21 ps on u_rrl_271 to u_cland_rfan_coll_i0_1. The actual relay centers are 817.506 µm apart. The old west relay then drives two FSTART consumers at distances 68.796 µm and 701.514 µm.

I opened the exact revised overlay at epyc12:/srv/opentallas-scratch2/claude/codex-head-west/c51_1126/fstart_reset_plan_review.png. Both new reset copies fit west of the pair macros and clear the planned reserved sites. The upper proposed branch measures 234.495 µm to its copy and 132.597 µm to FSTART. The lower branch measures 34.533 µm and 60.885 µm. The two coordinates come from the candidate plan and the other points from the retained native CTS database. These are placement projections.

The stock generator emits two seven-edge reset histories from the same rst_root_n and preserves the old reset for the coll_i0 ring. Only the two FSTART loads and the displaced reset fanout copy change. The isolated emitted-relay lockstep passed 118 checked edges, and a one-edge mutant departed on cycle 26.

**PASS for the two revised plan branches.** Source PRE and export run in codex-head-west-c51-source-1126. Any changed kit requires normal admission and a fresh detailed-placement review. The independent C20b read-pointer path at −286.31 ps, internal reset removal, and related parent FF remain open. Route stays held.

## Source gates

E12 source units 2127552 and 2263560 completed successfully. PRE found zero issues. The full HEAD strict check bound 8,218 nested instances, the generated cohort matched 27 of 27 types, and all 334 measured lane ages matched the original. E8 unit 2402694 passed whole G0 with zero errors and zero pending views on the same plan. The isolated native SerDes release witness remains conditional for its 12 unchanged targets. The candidate is ready for plan integration and later changed-kit placement once normal host admission is available.

The retained older E8 placement still has separate FF hold issues. A read-only replay of its final CTS checkpoint reproduced −78.16 ps and 2,948 negative endpoints on the stock gate. The exact internal removal path launches from the clk_t40 local-reset copy into slice23 valid_r2 on clk_t54. The associated valid_r to valid_r2 data path crosses the same taps. The clk_t40 tap is at its 800-sink cap and clk_t54 has 126 sinks. These paths need separate clock-cohort work. They confer no route authority on either kit.
