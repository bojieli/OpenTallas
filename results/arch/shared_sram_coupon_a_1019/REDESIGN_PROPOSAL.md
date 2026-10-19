# Concrete redesign proposal after original native RECTONLY failure

HOLD before B/C. This is a proposal, not repaired geometry or a released master.

The actual native checker reports two RECTONLY markers on each selected
Qwen5666/SC2e91 source-contact union. Each retained M4 contact is24nm high
and remains on its original row; its connected24nm lead was moved9nm.
Their15nm overlap creates a nonrectangular connected polygon. Source-join
markers land at the preserved contact, inside the scoring ROI and far from
the crop boundary. The original routed union is therefore a measured failure.
A true fixed pin hides the same defect; turning these shapes into fixed pins
is a visibility change and cannot be used as a repair or qualification.

Preferred next model: construct a NEW master with contact rows and their
entire connected M4 leads on one common native phase. Rebuild the actual
port-row/core-offset mapping from the logical bit layout. For each original
selected M4 pad center at12mod48nm, a candidate native row is center-9nm,
3mod48nm; move the actual source/terminal contact and its analytical internal
attachment together, rather than moving only a lead or changing an old
anchor label. Existing native-grid long leads/VIA45 columns are source
starting points, not a qualification of the new contact layout. Preserve
logical port/bit identities, memory semantics, and every physical PG contact
in an explicit old-to-new ledger. This changes physical anchors and must be
called a new master; it cannot claim unchanged original contacts or inherit
old timing receipts. No such geometry has been generated in this packet.

Before generation, the owner must accept that new-anchor master choice and
its complete model: every signal pad/lead/via, native discrete-width checks
including the non-ORTH table missed by this checker, connected-union polygons,
all cross-net neighbors/EOL/corners, transformed parent TRACKS, pin density,
outline/core fit, each PG contact, RC/clock load/energy and the actual parent
boundary. Price changed wire lengths/capacitance from complete shapes; added
logic cycles are not presumed necessary, and timing/CQ/reset/K/first-use are
still NULL until their own source/native contracts are proved. Both families
need independent all-pin inventories; they cannot inherit one another's
closure. Recheck representative new unions as visible REGULAR wires before
any Stage B signal AP/route or Stage C PG/PDN work is authorized.

Do not choose a33nm local patch: it remains nonrectangular at a24nm lead,
and33nm is absent from the declared discrete widths. Making an entire
connected strip120nm wide would also require a new complete pitch/neighbor
and area model; at96nm rows it overlaps its neighbors. Do not repair by
omitting contacts/neighbors, hiding leads behind OBS, changing only net names,
relaxing rules, suppressing markers, or executing B/C on the failed geometry.

The measured via-crop silence suggests those selected exact rectangular
cross-layer unions can be retained for further modeling. It qualifies no
whole master, PG access, external AP, or source phase. Native PRL/track/width
coverage gaps remain open despite zero markers in some controls.
