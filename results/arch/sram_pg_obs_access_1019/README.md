# Conditional central-M5 supply access model; all internal M4 OBS obligations remain HOLD

This finite model retains every c634d1540 source contact, rail and OBS reservation.
It provides a concrete external approach mechanism for all 121 actual contacts,
with an explicit per-contact obstruction rather than declaring them qualified.
No native engine, AP/PDN stage, production view, route repair or geometry adoption
ran. A2 cf639 representative visible joins and A3 a58138 inventory are separate
evidence and confer no PG qualification on this proposal.

The exact source is `input/c634_model.json`, with core/source contacts +39 nm,
leads/vias +48 nm, 120 nm M4 rails at center +51 nm and the conditional internal
PG attachment +12 nm relative to the moved core. No original rectangle changes.
The new source/contact/core ledger is `model.json` under each family’s
`contact_ledger`: original rail, translated original core contact, unchanged
c634 widened rail, proposed internal V4, shared M5 trunk, original OBS identity,
and north/south external approach are linked for every original ID. Qwen has
44 unique actual rails, SC2 77; no W/E duplicate geometries or duplicate via
counts were silently assumed. VDD/VSS remain distinct nets.

## Concrete proposed geometry and finite checks

Add two *internal conditional* 24 nm M5 supply trunks, one VDD and one VSS.
Qwen trunk centers are X=26208/26304 nm; SC2 centers are 108432/108528 nm.
Each runs Y=0 through the unchanged outline height (21192/43800 nm). All are
on X=0 mod48 tracks inside the true central gap between the two M5 OBS
reservations. R0 only, origin X/Y=0 mod48, is inherited; mirrors are refused.

One proposed V4 connects each actual M4 rail to its corresponding trunk at
that rail's native Y=3 mod48 center. Its cut is exactly 24 by24 nm; M4 metal
46 by24 nm; M5 metal24 by46 nm. Bottom metal lies wholly inside the unchanged
120 nm M4 rail, top metal wholly inside its M5 trunk. Consequently the added
M4 union area is zero and via enclosure area is not counted twice. The
translated original96 nm contact band overlaps the retained120 nm rail;
this geometry is not proof that its conditional transistor/contact/strap
implementation exists or meets electrical limits.

Each trunk has two84 nm long M5 port subsets, at the north and south faces,
2016 nm² each. These are four proposed PG port rectangles on the existing
VDD/VSS nets, not four additional supply nets or additional clock/signal pins.
No pin is moved or relabeled and no existing M4 contact is omitted. Parent
M5 supply wires can approach from beyond the north/south outline, directly
collinear with these subsets. This requires real parent supply geometry,
continuity and access qualification; no external route is generated here.
The two trunks have a genuine72 nm inter-net gap. All added conductor/via
metal is checked against every original signal shape, via metal and PG rail;
all new cuts against every original and new cut. Exact positive-overlap
containment, 24 nm box spacing, conservative72 nm projected parallel spacing
and34 nm cut spacing have zero finite violations. Both full trunks and ports
have no M5 reservation intersections. Every conductor remains inside the
unchanged outline, and first/last rails and complete via enclosures participate.
These coordinate checks do not certify EOL, PRL, convex corner, density/fill,
non-ORTH width-table binding or actual native pin access.

| Additional conditional internal cost | Qwen | SC2 |
| --- | ---: | ---: |
| V4 count (one per original contact) |44|77|
| M5 union area µm² |1.017216|2.102400|
| Cut union area µm² |0.025344|0.044352|
| M5 wire C fF, pinned analytical coefficient |6.962165376|14.389526400|
| Each full-height M5 wire R kΩ |0.402510252|0.831915300|

The finite access-only costs use the c634 pinned M5 coefficients
0.164264 fF/µm and0.0189935 kΩ/µm; each V4 adds the conditional0.0118 kΩ
contact-path contribution. They do not establish a supply-drop bound.
The two trunks and all contacts create two geometrically connected candidate
supply components rather than claiming that the original22/22 and39/38 isolated
rail components were fed. Internal contact resistance, coupling, IR/EM,
transistor placement and supply return remain NULL. PG metal is not charged
as toggling signal energy. Outline, lattice reservation, core placement,
clock pin count and proposed cycle delta do not change; native timing,
minimum/maximum CQ and first-use/source phase remain unmeasured.

## Why the OBS intersections cannot be waived

The pinned actual native source is preserved under `source/` from6cb3f2b704.
`io.cpp` lines2947–3056 imports every routing OBS as a blockage. Its special
exception at2972–3001 transfers *cut-layer* OBS into an enclosing pin;
these reservations are routing M4 and that exception does not apply.
`FlexGC_init.cpp` lines44–101 maps actual terminals/routes to their electrical
net, but maps an instance blockage to the instance (or blockage for explicit
spacing/width); it does not assign a routing OBS to the VDD/VSS net.
Thus same supply-name does not make a blanket M4 obstruction same-net metal.
No general electrical same-net access exception has been demonstrated by this
actual checker path. The source-only conclusion is a coverage/applicability
finding, not a new native DRC run.

Every proposed internal V4 bottom enclosure still intersects the original
M4 OBS identity3. All121 rows retain that fact as HOLD. The clear external
M5 port addresses the external geometric approach only. It cannot prove an
internal V4 legal by hiding it, by erasing the reservation, or by assuming
that an internal strap crosses unknown real cut/metal obstacles. Source
inventories contain no V4/cut OBS, but unavailable internal physical cuts
cannot be assumed absent merely because the analytical abstract omits them.
If all internal V4 metal and the unchanged routing OBS were exposed together
as ordinary parent routing to this checker, no same-net waiver is justified.
A future source-owned macro implementation must explicitly own and validate
these internal straps and distinguish the external routing reservation from
its actual internal metal. This finite model has not supplied that proof.

The next concrete access mechanism is therefore central M5 landing with
explicit conditional internal V4/rail ownership. The per-contact blocker is
unchanged M4 routing OBS plus unimplemented internal attachment, for all121
contacts. Native AP/PG qualification would require ROOT's next scope decision;
this packet does not request or exercise an implicit B/C or PDN grant.

Reproduce with `python3 model.py`; no simulator, synthesis or EDA is invoked.
`SHA256.json` binds source, inputs, script and outputs. The finite geometry controls check all121 direct M4/OBS intersections,
coincident VDD/VSS candidate overlap, adjacent-track conservative spacing
failure and positive port area. Separate policy refusals prohibit an
unsupported same-net waiver, reservation erasure, inferring internal legality
from clear external ports, enclosure area double counting and unsupported
mirrored placement. These are model checks and scope rules, never native
causal DRC controls.

An initial full worktree checkout was stopped before work and removed; this
artifact was built in a fresh sparse checkout of the same branch. No external
worktree, source or progressing job was changed.
