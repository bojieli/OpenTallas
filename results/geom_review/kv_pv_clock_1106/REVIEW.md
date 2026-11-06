# PV clock diagnosis review
Actual retained 4_cts geometry rendered/viewed in clock_geometry.png (2026-11-06).
Twenty hard cores leave wide physical channels; the problem is clock ownership.
clk_t98 clocks one large PV macro and1199 soft FFs while adjacent clk_t94 clocks1200 FFs without a macro.
The worst shift-chain consecutive FFs are only2um apart yet use different roots.
The full67-stage bit452 chain fits97x63um; existing density assignment splits it over6roots.
Verdict FAIL for closure; PASS-COND for read-only diagnosis of this retained failed subject.
No new placement/CTS/route is authorized by this record.
Candidate must separate hard-core branches and enforce bounded per-bit chain affinity, preserving140ps window and signed TT/FF means.

Candidate geometry clock_split_candidate.png viewed: PASS-COND for source preparation only.
Twenty added entries are outside actual macro outlines plus4.32um halo and outside declared reserved rectangles, using8.64um edge margin. All data/macros stay fixed.
Local branches are95.0–103.68um estimates; actual child M5 access through detailed M6/M7 and clock RC still require ordinary qualification.
The worst scalar D23 chain physically spans~680x192um and has593um whole-chain nearest-tap reach: it CANNOT be collapsed. Only contiguous subgroups passing200um/capacity rules are proposed.
The representative D68 per-bit chain includes67 r stages plus terminal q (68FF), fits97x63um and has80.643um nearest-tap maximum reach.
