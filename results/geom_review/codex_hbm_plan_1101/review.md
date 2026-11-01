# HBM station and hub face plan candidate, 2026-11-01

The L204/L204m station redistribution fixes the mandatory-face hops of 935.67/900.03 um to 293.76 um using the existing nine stations per lane. Added cycles: zero. Pin windows, bus widths, core outlines, clock/reset pins, macros and PDN are unchanged. S8 G0: PASS, zero errors. The source baseline is DIE-HBM-57 sweep S7; this candidate is not the production plan of record.

Reviewed and VIEWED `l204-review.png`: station points occupy legal streets outside hard-core footprints; the two-bit buses take short M6/M7 spans over M1-M5 core abstracts. E/W handoffs remain aligned. No macro wall, new channel crowding, or clock/PG change is introduced. Verdict: PASS for these station moves.

Reviewed and VIEWED `hub-repin-bestface-review.png`: ten unsigned VMS core instances need incompatible partner-facing bus placements. The generic shared-table optimizer could not reduce the fifteen failing port groups. A four-table grouping clears the numerical rule but leaves several buses on nearly perpendicular faces; that diagnostic candidate is not selected. The selected nine shared views put each changed bus on its best partner edge, preserve bit identity, and leave clock/reset pins byte-identical. A focused check of all 5,814 hub port groups (661,294 pins) reports zero failing groups. Pins use M4 on E/W and M5 on N/S with two-track spacing. No cycle or outline changes. Verdict: PASS for bus-face placement, conditional on the existing independent VMS register-affinity/clock issues being fixed before any new core route.

The selected candidate combines the L204 fix with the nine-view bus repair as one proposed HBM plan event. Full G0C/render is running. It remains unadopted; the thirty-nine-type station sweep still needs its own 50-iteration GRT results. Existing failed and historical results remain in their original directories.

Current die G4 is BLOCKED(clock-feed): the old abstract composite spliced T028 to the NW mesh root across an unmeasured 4.78-mm gap. Actual routed feeds 99/248 um from the mesh root are being measured. The historical abstract zero-contract receipt does not qualify current freeze.
