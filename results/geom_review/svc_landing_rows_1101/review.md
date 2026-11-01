# SVC row-shift prototype — HOLD

Candidate moves the first32 hcpost cores in four rows by34.56/25.92/17.28/8.64um Y. It creates a16420.624um² landing reserve at[751.6465,34.56,1386.6865,60.48] within the original378um pin hop. Reset/clock planner reserves the actual landing corridor before rebuilding the reset tree: depth stays11, relays499→466. Original data buses, lane stages, clock means and core views stay unchanged.

LOOK: the actual candidate reserve is macro-free; rebuilt relay sites avoid the reserve. Blue lines in the render show graph connectivity, not routed wire paths. No P&R was launched.

HOLD: automatic R4 legalization moves8 of28 grid-clock port coordinates. Original clk_t9/clk_t10 are no longer legal: shifted core tops1131.84 leave only1.5429um to old y1133.3829 versus existing8.64um halo. A source freeze cannot waive that failure. Need another floorplan/multiple-rectangle band candidate or an explicitly reviewed clock-pin event. Boot sidecar recomposition is running separately; no boot budget equality is asserted here.

The preceding no-core-shift layout had17 null bands across11 types. Exact ring_ff search failed all17; aggregate within-reach free area is insufficient for11, including both cut-affected SVC types. Previous raw failures and successful candidate are retained under intel1:/srv/opentallas-scratch2/claude/codex-s81-svcprep-1101/attempt_2 and attempt_3.
