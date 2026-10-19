# Dual-clock access terminal review: analytical HOLD

The exact `693ac5af4` candidate passes the bounded terminal/OBS protection
review, but native grid access and PG access remain **HOLD**. This packet
changes no geometry, macro views, RTL, timing libraries or bindings. It starts
no synthesis, route, gate or OpenROAD job.

`audit.py` applies the rectangle-union and spacing-halo algorithm from S81
`ec861194a` to this master's actual 206 paths, outline and obstruction list.
The reference checker is preserved verbatim, with its hash in `audit.json`.
The original planner is replayed from per-master inputs; exact path, PG,
obstruction and scalar-proof records must match, rather than trusting the
previous PASS field. The actual technology and platform snapshots are
preserved from S81 `ef4aaca9226b64688d8613f5e106522c4276c90d`; their hashes
match the geometry input's pinned `7694bf4f...` and `b7103a10...` identities.

| Exact bounded check | Result |
|---|---:|
| Terminal necks and constructive horizontal approaches | 206 PASS |
| Wholly obstructed internal metal patches | 408 |
| Internal VIA45 instances / protected metal enclosures | 408 / 816 |
| Original PG rectangles translated unchanged | 44 |
| Causal mutants: enlarged neck, missing M5 OBS, blocked PIN, exposed via | 4 FAIL |
| Shapes with nominal native centerline grid mismatch | 614 HOLD |

The 24 nm PIN and M4 OBS separated by 48 nm have touching native 24 nm
spacing halos; no positive-width foreign conductor can enter the internal
neck while satisfying both clearances. A 108 x 24 nm same-net approach is
2,592 nm², above the native 2,000 nm² minimum. It is a constructive abstract
approach, not an actual parent access-point result. M4/M5 native minimum
width, minimum area and width-dependent PRL spacing are checked against the
preserved deck. The source-input replay also checks connected metal patches,
signal-to-PG clearance, native via containment and cross-net cut spacing.
Full native LEF58 EOL, corner, density and grid qualification remains open.

The native M4 deck states pitch 48 nm, offset 3 nm; M5 states pitch 48 nm,
offset 0 nm. Both declare `RIGHTWAYONGRIDONLY`. Candidate horizontal M4
centerlines have phase 12 nm and M5 columns have phase 12 nm. All 614 signal
rectangles therefore disagree with the nominal technology centerline phase
at the modeled origin. This is an exact coordinate discrepancy and a
native-access HOLD, **not a routed DRC verdict**: actual master orientation,
parent tracks and the tool's native rule interpretation have not been
validated. The 43.2 um lattice step is divisible by 48 nm and does not itself
remove the discrepancy. No shift, rescale or altered anchor is silently
introduced. Any repair must preserve electrical anchor ownership and reprice
changed access geometry, RC and PG before generation.

All 44 original PG rectangles remain M4 PIN rectangles overlapping the M4
OBS, as in the original abstract. For each, a hypothetical native VIA45 M4
enclosure fits inside the actual rectangle, and a 24 x 84 nm M5 landing
patch (2,016 nm²) clears the declared M5 OBS. These candidate landing
rectangles are only analytical witnesses; they are not added vias or proof
of connectivity. Exact native same-pin OBS access semantics, actual PG
straps, all terminal binding, cross-net PG routing and bank escapes remain
HOLD. The original 21 Qwen final ODBs separately have PG_HOLD receipts;
their timing/CLOSED histories establish no PG proof for this new model.

The original price remains 52.440 x 21.144 um per macro, 26 banks totaling
28,828.575 um² (+100.29%), 52 clocks at 581.910 fF TT, and 11.452 pJ TT
full-activity R+W. The 259.2 x 388.8 um reservation is not parent fit.
Required repair cost is **NULL pending an explicit mechanism**; no free
repair or positive qualification is assumed. No minimum CQ bound, native
clock phase, first-use/reset/K contract, R-versus-R+1 qualification or token
latency claim is established.

Reproduce only the bounded analytical check with `python3
results/arch/qwen_dualclk_terminal_1019/audit.py`. `audit.json` preserves exact
source hashes, all mismatch rectangles, all PG witnesses and mutant errors.
