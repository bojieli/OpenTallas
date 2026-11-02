# Finite source review of FC9 four-caller/root composition

Reviewed exact e155c5a1a selected_callers versus proposed five source bodies and proposed/event.json, including additive hfd_ep_static_fc9 and OBS136 snapshot. Source-only review; no compile, proof or CAD rerun. No packing/epoch/scalar must-fix found.

- New FC9 cause9 maps `{old10:5,old2:0}`. Nested RX cause stays its real seven-bit internal wire; only the two separately proven reserved fields are excluded at the true FC9 output. No constant hole is reintroduced at another physical cut.
- NE_io L125 new payload4:0 maps old cause6,5,2,1,0; other L48 cause new8:5 maps old10:7 exactly. L125 epoch shifts7→5 while L48 remains unchanged.
- q_spb0 and its selected physical_v1 source both L117 payload8:0 map old0:2,5:10 in ascending retained order; epoch11→9. The two variant definitions do not authorize double-counting one physical selection.
- vsN0 L118 new payload is scalar fault at bit0 and compact cause7:0 above it, mapping old packed0:3,6:10. Its separate L141 cause8 is old cause10. L118 epoch11→9; L141 fields/epoch unchanged.
- ROOT uses matching compact W9/W9/W9/W5 bin captures and matching incoming epoch bits9/9/9/5. Its actual L118_q[0] fault scalar relay expression is unchanged. Unrelated L125 input remains seven data bits.
- ROOT OBS compact concat preserves all other fields and removes exactly old global16/17,29/30,42/43,55/56. Proposed OBS136 snapshot SHA43538a84a89ecc2019ece9260d0486fb316fdf52596417ec3a26feb7426f6982 equals the reviewed15e4f8d2f master. It captures136-bit p1/p2 before reconstructing old logical144 positions, retaining existing host q/r debug indices, word selection, sticky/clear/reset/latency. No other vc2/host fields were removed.

Source-event cost must remain scoped: −2 declared child fault-output registers per selected child (four intended instances→−8), −16 total declared source/root boundary data registers, and −16 declared OBS p1/p2 bits. OBS SYNC0 can optimize p2 in both versions; this is not a mapped FF/area total. No new mission cycles are introduced by these field projections.

Event holds still contain an old FC9 SYNTH/LEC/face NOTRUN description. The owner should point to the separate actual component intake14054/KEEP160/face2284PASS while retaining caller/source-event, paired physical pin/relay plans, source/bind/reset/calendar/clock and physical adoption holds. This review supplies no new producer-zero lemma, component proof transfer, whole-parent proof, mapped costs, or release credit.
