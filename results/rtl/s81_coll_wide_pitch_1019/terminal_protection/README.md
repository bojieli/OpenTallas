# SC2 terminal and internal-route obstruction audit

The source/geometry prototype at `19ccd29b9` protects every added internal
lead and via with its exported LEF obstructions or a declared terminal-access
region. This audit changes no geometry, views, timing tables or bindings.

`audit.json` records hashes of the exact analytical model, prototype JSON and
exported LEF. The checker independently compares every exported terminal and
OBS rectangle with those source records, then enumerates all 437 paths.
There are 870 wholly obstructed internal metal patches and 1,740 wholly
obstructed VIA45 metal enclosures. All 870 internal vias are protected.

Each of the 437 remaining M4 shapes meets its own face terminal. The visible
PIN occupies 0..24 nm and the M4 OBS begins at 72 nm on the west face; the
east face is mirrored. The only uncovered metal is that terminal's 72x24 nm
access strip. At the actual native 24 nm thin-wire spacing, the PIN's
foreign-net keepout reaches x=48 nm and the OBS keepout begins at x=48 nm.
Their union covers the entire internal neck. Consequently no positive-width
foreign conductor or via enclosure can cross it while satisfying spacing.
This is stronger than merely checking that an internal polygon appears in
the analytical JSON.

A constructive same-net horizontal M4 approach ends at the visible PIN and
stays outside OBS. Its 108x24 nm connected patch exceeds the native 2,000 nm²
minimum. Adjacent approaches have 168 nm clear separation on the 192 nm
terminal pitch, exceeding the native 24 nm thin-wire requirement. This
constructive abstract approach is not a claim about a selected parent's
routing grid, actual access points, PG vias or banked-array routing.

Three causal geometry mutants reject: widening the boundary gap to120 nm
exposes a neck; removing the west M5 obstruction exposes vertical leads and
via enclosures; extending M4 OBS to the face obstructs actual terminals.
All positive and mutant records are retained in `audit.json`.

Timing remains blocked. In particular, the earlier positive nominal
Elmore/FO4 CQ values (including FF346.044 ps) are **not qualified earliest-CQ
bounds**. This geometric audit provides no CQ, setup/hold or Liberty approval.
Actual native external pin access, clock/PG escape, client arrays and parent
integration remain unqualified.
