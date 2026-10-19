# SC2 native track applicability model

HOLD: no geometry, Liberty, helper, gate, or routed result is released by this
packet. This is a bounded model of all 437 paths from access model
`564c39512720a00c2924f267b87e36c487b5bba76817142b2c5b54d346fbb988`
(planner `2b4f2a2a...`). Source prototype `19ccd29b9` and its terminal
protection audit `ec861194a` remain unchanged.

The exact native technology LEF `7694bf4f...` declares 1000 DBU/um,
1nm manufacturing grid, M4 horizontal/48nm pitch/3nm offset, M5
vertical/48nm pitch/0nm offset, and RIGHTWAYONGRIDONLY on both. Its M4/M5
blocks also contain RECTONLY, WIDTHTABLE, EOL, corner, keepout and PRL
properties. Neither block supplies MINSTEP. These declarations do not,
by themselves, specify how a native rule interpreter treats the local
union between a retained macro contact and a shifted wire. No native
interpreter verdict is claimed.

All original long M4 and M5 centers are 12mod48 in the macro coordinate
system. That is a conditional mismatch against default global tracks at
R0 origin (0,0), not evidence that a parent route failed. DEF TRACKS,
parent origin, orientation and macro/pin rule applicability are not bound
in this packet. The macro LEF has implicit ORIGIN(0,0), SYMMETRY X Y,
and outline 216840x43752nm.

The candidate moves long M4 centers -9nm and M5 columns -12nm. Both source
and terminal 24x24nm contacts remain exact. Each horizontal segment moves
its column end with the VIA45 enclosure, removing the old column stub;
it retains the source or terminal end. All 437 paths connect through
1307 long rectangles and 870 complete native vias; 874 preserved contact
pads overlap the shifted wire by 15nm. Minimum connected same-layer area
is 7104nm2 M4 / 3408nm2 M5, above 2000nm2. Candidate finite scalar minimum
cross-net gaps are 50nm M4 / 72nm M5, with 276nm minimum to inherited PG.
All 1740 via enclosures remain covered by existing OBS. The existing
24nm PIN/OBS halo also covers every shifted terminal neck.

These checks do not resolve the retained-pad/shifted-wire union: it has a
33nm local bounding height and a 9nm step. A 24nm primitive-width check
does not qualify RECTONLY/WIDTHTABLE/corner legality. Conversely, a 33nm
bounding box alone does not establish a native width-table violation.
Inherited 77 PG shapes, outline, original anchors and outer pins are
unchanged. Actual PG access/connectivity and external parent access remain
open. A same-net horizontal parent approach on the conditional default M4
track can overlap its retained pin by 15nm, but has the same union issue.

The transform table is conditional on default global offsets (M4=3,
M5=0) and defines origin as the lower-left of the oriented bounding box:

| Orientation | Required origin x,y modulo48nm |
| --- | --- |
| N | 0,0 |
| FN (mirror x coordinate) | 24,0 |
| FS (mirror y coordinate) | 0,30 |
| S | 24,30 |

43.2um is exactly 900 native pitches. Thus N at a lattice origin matches
these long centers, while the other three allowed orientations require
different phases under this convention. Bind actual DEF transforms and
TRACKS before applying the table; the LEF offset is not a substitute for
a parent TRACKS record. Original-center phases could instead align under
different origin/track choices, which likewise need source qualification.

Reproduce with `python3 tools/mem_compiler/check_s81_sc2_native_grid_1019.py
--root "$PWD"`. The finite audit finishes in about one second. The original
phase mutant fails the explicitly conditional phase predicate (1307
violations); a -33nm M4 shift loses contact overlap and fails connectivity.
These are causal model controls, not native DRC failure reports. Complete
witnesses and input/checker hashes are in `audit.json`; candidate path
rectangles are in `candidate_paths.json`. No new electrical/clock/energy
numbers are qualified: shifted union RC must be repriced if this geometry
is selected, and no earliest CQ bound is inferred from nominal CQ.

Next is a source-backed native union/rule applicability decision, then an
exact master transform/parent TRACKS/AP/PG model. ROOT selects any corrected
generation only after those prerequisites; no compiler rewrite is needed.
