HEAD LEP pair trial7: FAIL before route.

Image viewed: results/head_lep_next_1029/placed_v7.png (actual 3_place.odb).
The 55 SRAMs remain in regular rows, with aligned W/S boundary banks and
continuous empty central clock/reset access. Including locked TAPCELL and
PHY_EDGE occupied sites fixed the previous 475-overlap DPL failure: actual
DPL reports no violations. Registered reach is 390.69 um, zero captures over
405 um, zero collapsed relays and zero cells on macros.

The W channel is crowded around x30–34/y282.5: vertical demand 1.595,
column demand 1.102. Horizontal demand 1.022 near the top row also exceeds
capacity. The next proposal widens the W margin using the same macro masters
and outline; no route is admitted on trial7. Empty area 50.19% reflects the
large fixed macro footprint and deliberately localized register banks. No
preplaced local clock tree exists yet (400.61 um nearest entry), so clock
planning remains required. The 556 unregistered input reports are the known
four-slot D4 writer declaration class; original face_guard proves 2140/2140.
These classifications do not waive the real channel failures.
