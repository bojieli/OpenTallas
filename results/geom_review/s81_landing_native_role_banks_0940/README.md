# Default-off native landing role banks

The old landing FF placer packs the forwarded write storage and mission-clock read/control FFs together. The T51 source geometry model showed that moving all2677ring FFs toward the north input pins breaks68station0 target intersections. Separating the existing2077forwarded-write FFs from600mission-read/control FFs provides the existing zero-cycle bridge and makes the reviewed split representable by the helper.

`clock.landing_contract.bands[bus].native_role_banks` is an explicit opt-in. No production plan, source39capsule, live kit or GEN activates it in this change. Absent or null metadata emits the byte-identical old generated Tcl, including the old template; other group order and every legacy path remain selected. The new path reuses the existing FF packing/reserve/pinslot functions and exact mirrored `cland_ffkey`/START-control ordering, with full-ring chunk-width context preserved for both filtered banks. It does not change the0.4reservation policy or install the separate reviewed DATA-cone poses.

The v1 object contains:

- `schema`: `opentallas.landing_native_role_banks.v1`.
- `ff_pin_roles`: exact master names mapped to one `clock` pin and explicit `data` and `reset` pin lists. These are pinned semantic declarations; the native runtime verifies their complete input coverage and queries the actual Liberty clock-pin property. The fixture's declarations came from the actual used master/SEQ-Liberty census. This is not new body-EQ or library qualification.
- `expected_total_members` and `expected_captures_per_port`. The pinned T51 case is2679native FFs and4first-capture slots for every actual515input bus bit.
- `held_members`: exact native name/master/clock-port triples. The two existing status FFs must already be FIRM/LOCKED through the unchanged standard status placement. Their locations, status and master are held; their footprints are reserved.
- `banks`: unique `name`, exact native `clock_port`, `first_capture` filter (`any`, `present`, `absent`), `expected_members`, `expected_first_capture`, `rect_um`, and exact native `members` name/master pairs. T51 declares2077/2060 forwarded-write and600/0mission-read.

All bank membership is validated before any role bank moves. Each actual sequential instance must match the pinned identity/master and a single role filter, its live Liberty clock pin and complete native input inventory, and the exact declared INPUT BTerm net. Logical bus aliases and buffered/unknown clock sources are rejected, with no fallback. The data first-capture walk follows native nonPG drivers, stops at actual clocked cells, rejects unknown/multiple drivers/cycles/multiple bus bits, and counts every input bit's actual first-capture multiplicity. Unknown, missing, duplicate or resized FFs fail. All candidate banks are checked before dispatch; dispatch occurs at the original group's position in the existing placement order.

`test_native_role_banks.py` uses a reduced actual T51 nonPG connectivity fixture:11982native cells/12500native nets/517actual relevant ports, including the2679FFgroup. Unqueried foreign sinks and PG terms are omitted explicitly. It does not load an ODB, rerun a physical model or launch GEN. Nine focused checks passed: absent-option actual-T51 byte equality; invalid metadata; both mirror directions with exact legacy ordering/counts; missing/duplicate/native-unknownclock/resized FF and duplicated-bit first-capture negative controls failing before any bank placement.

Run: `python3 -m pytest -q results/geom_review/s81_landing_native_role_banks_0940/test_native_role_banks.py`.

The bank rectangles in the fixture exercise the inactive API; they are not a newly qualified physical plan. The earlier403.97um data model, q496explicit existing-tap planning correction and915remaining clock-radius/actual-phase/NW/PG/partial-face/fill holds remain separate. This change provides the guarded helper seam only. No new RTL, FF, clock/reset node, external pin or pipeline cycle; no source/clock/PG/physical qualification, canonical adoption or release.
