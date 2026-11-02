# Actual selected macro access and compact cut census

Status: access UNPROVEN. Source-only census of the exact three LEFs selected by the completed GLUE placement kit, covering its six R0 macro instances. No layout, source, model or CAD change. Personally viewed the access drawing. The proposed compact frame is a sizing concept, with no packing credit.

| Actual macro | Instances | M4 west contacts | M4 east contacts | Peak contacts / 10 um |
|---|---:|---:|---:|---:|
| D2D SRAM | 4 | 229 | 229 | 53 per face |
| Code SRAM | 1 | 793 | 792 | 105 per face |
| Sys ROM | 1 | 43 | 43 | 43 per face |

Counts include signal and clock pins, not PG rectangles. All actual signal/clock pin rectangles are on M4 west/east faces. Thus the three 11.208 um D2D body gaps (2.568 um after two 4.32 um placement halos) and the 10.152 um code/sys body gap (1.512 um after halos) are real escape zones. They cannot be dismissed as unused macro faces. Code SRAM peak density is 10.5 pins/um on M4, above the existing 6 pins/um/layer/face planning budget; preserve the WARN rather than granting an exception. D2D is 5.3 and sys ROM 4.3.

Each selected LEF blocks M1–M3 over the full body. Its M4 interior obstruction leaves 0.072 um west/east edge strips. Every actual M4 rectangle therefore needs a legal access/via or direct local connection. M5+ has no macro body obstruction in these LEFs, which permits an upper-layer escape concept but establishes neither legal vias nor PG/neighbor ownership. The JSON retains all actual PG rectangles and obstructions as well as signal rectangles.

Necessary face cuts have code density 10.5 contacts/um against a gross M4 preferred-track budget of 0.55 / 0.048 = 11.458 contacts/um before PG/clock/via reservations. This narrow gross allowance is not a routed-cut PASS. Opposing-face contacts cannot be added into an asserted mandatory full-gap M4 mincut: each may turn through a via before reaching the gap midline. Conversely, assuming every contact freely escapes over the macro is equally unsupported. An actual access assignment must choose each local termination, track and layer transition.

Actual baseline signal nets demonstrate why all pins must not be priced as long-distance demand. Each D2D macro has 170 direct tie-driven incoming unique signal nets and 150 other incoming signal nets; code SRAM has 546 tie-driven and 526 other incoming signal nets. Sys ROM has 13 other incoming signal nets. Separate clock nets are excluded from these figures. The geometry dump lacks per-port net names, so these are unique-net counts, not a per-pin correspondence. Constant access still consumes real cells, vias and clearance.

## Boundary contacts, CA banks and native area

The completed kit has 4,545 actual boundary contacts: north 1,633 M5 + 1,659 M7; south 588 M5 + 588 M7; east 38 M4 + 39 M6; west zero. There are 33 declared hold-mux buses, of which 31 have 1,747 external data contacts (north 828 M5 + 842 M7, east 38 M4 + 39 M6). The two remaining declarations are internal cland ready/fault paths without external data boundary contacts. Ring START and other controls are separate from this data count.

The compact north/west/east bays reserve 18,197.706 / 11,421.389 / 9,853.747 um², respectively. Those are unassigned areas. In particular, no current bus owns the west bay. Each contacted CA bus still needs explicit bank/bit placement, parent-face correspondence and access cuts; multiplying bay area by a density does not make that assignment.

Actual standard-cell FF inventory is 47,739 FFs occupying 14,317.473 um², plus six macro clock consumers. Within it, the current cland rings contain 11,109 FFs / 3,239.501 um². Their entire logic occupies 6,718.974 um², and native bin/bout logic another 2,909.337 um². The summary records the full actual cell/FF area groups. These areas are already included in the 28,564.946 um² actual standard-cell footprint used for compact sizing; do not add them again or claim a placement from this area census.

Gross boundary cut arithmetic is recorded per real layer and face using the proposed core spans and actual preferred pitches. It does not allocate CA contacts, clock/PG tracks or parent seams. The 402.76 um control bound remains unobstructed point geometry only. Access, actual registered bank packing, parent interface ownership, channels, PG, local clocks and real timing remain unresolved.

The next source-level obligation is one explicit per-bus bank/face and macro access assignment for this same compact option, including local tie terminations and M4-to-upper-layer cuts. No alternative frame, CAD, old proof carry, default adoption or global exception is proposed here.

Inputs copied read-only from intel2 /srv/opentallas-scratch2/claude/codex-qc-glue/place_spill/kit/{macros/*.lef,macro_place.tcl,pins.json,land_slots.json}; exact selected LEF hashes and rectangles are in the compressed artifact. Actual cell/net census comes from the completed baseline geom_dump retained with the B diagnostic. No active proof or frozen event was edited.
