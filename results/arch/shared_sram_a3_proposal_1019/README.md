# A3 complete-master native-visible inventory: proposal only

No native engine was launched. No geometry was repaired. No production views,
B/C, access-point generation, PDN, route, timing or RC study is authorized by
this packet. Exact c634d1540 model SHA256
`033b2a0e1522a9bd28b3ab9a35df88d394175fa06fbf6dca0e6f48b12e97146a`
is retained unchanged. A2 cf63992e4 input, actual raw control verdicts, loaded
rule objects and measured receipts remain separate immutable evidence.

| Entire master | Signal nets | Signal rectangles | Complete VIA45 | PG rectangles | OBS reservations | Metal + cut boxes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen 52.440 × 21.192 µm | 206 | 820 | 408 | 44 | 6 | 2088 |
| SC2 216.840 × 43.800 µm | 437 | 2181 | 870 | 77 | 6 | 4868 |

Each via has two independently retained enclosure rectangles and one actual
24 nm V4 cut. Exact 46×24 nm M4 and 24×46 nm M5 enclosures are asserted.
All 643 signal networks have exactly one independent geometry component.
Layer equality plus positive-area rectangle overlap establishes planar edges;
only a complete same-via cut enclosed by both routing-layer boxes establishes
cross-layer edges. Net-name equality by itself establishes no edge. Every box
is outline-contained. Native shapes must later be re-extracted from ODB and
compared by source identity and exact bounds before checking. No crop or
sampling is proposed, so full contact, lead and terminal min-area/EOL context
remains present, including first and last source/end/via/PG entries.

Supply contacts are retained as actual conditional visible supply metal,
without adding a supply strap. Qwen VDD/VSS geometry has 22/22 disconnected
rail components; SC2 has 39/38. This is NOT an electrically fed supply network.
Core/contact/internal PG attachment remains conditional. The inventory has
zero positive-area same-layer cross-net metal overlaps; this is a finite
geometry result and does not establish spacing, EOL or cut legality.

`inventory.json.gz` contains every original identity, every signal/PG/via box,
every complete via, 69,036 neighboring box pairs (21,521 Qwen / 47,515 SC2),
and each per-net component membership. Neighbor pairs include all layers within
200 nm box distance and record layer relationship. This 200 nm diagnostic
adjacency list is NOT a checker-context cutoff: every full master is always
instantiated, and the native checker receives the entire unchanged geometry.
Every same-layer OBS intersection is listed by identity (1680 / 3561).
The 12 complete OBS objects stay conditional reservations and are NOT modeled
as real metal, NOT deleted and NOT silently converted into hidden fixed pins.
All 121 PG contacts still intersect their own M4 OBS reservations: HOLD.
Parallel PG/OBS owner supplies the independent access model keyed to
`qwen:PG:{0..43}`, `sc2:PG:{0..76}` and `{family}:OBS:{0..5}`.

## Concrete proposed execution, requiring ROOT grant

Use three sequential, separate native databases: full Qwen, full SC2, and the
four unchanged A2 controls. Each signal and each supply shape is a regular
ROUTED dbWire segment/patch; each complete VIA45 is a native tech via. PG stays
ordinary visible wire with original supply net identities (SIGNAL type in the
diagnostic GC representation, explicitly not a fed/PDN object). No dbBPin,
fixed geometry, special-wire suppression, routing, repair or fake macro view.
The native ledger must prove GC-visible status and match all actual box bounds.
Translate nothing: each master is checked independently at local R0 origin0.
M4 Y3 / M5 X0, pitch48 nm, and exact 1 nm DBU remain unchanged.

Plan exactly three engine processes and nine native calls: global + full
outline ROI for each of the two masters; global + four control ROIs in the
control database. Qwen ROI [0,0,52440,21192], SC2 [0,0,216840,43800], integer
DBU. Use actual `drt::check_drc`; check Tcl errors plus report existence and
retain every raw marker, ODB, DEF and loaded-rule receipt. Full global reports
are the verdict; ROI reports are corroboration, never a way to hide outside
markers. No crop-edge classification is needed for either complete master.
Controls are the exact A2 aligned rectangle, original 9 nm step,23 nm gap and
disconnected contact, retaining original raw failure witnesses. Required
native controls: aligned zero; step 2 RECTONLY; gap causal spacing/EOL;
disconnected independent component count 2 plus original native failures.
Any changed control behavior fails closed. Full-master native failures stop
adoption and retain original geometry for structural review, without repair.

Source 6cb3f2b704 checker snapshots are under checker_source. DRT rectangular
union checking suppresses genuinely fixed-only corners, so dbWire FIXED or a
true fixed BPin is not an acceptable replacement for routed visibility.
Native DRT does not bind the non-ORTH WIDTHTABLE rule; absence of a width marker
cannot qualify width-table legality. Track-center legality is also a documented
native-coverage gap. The c634 scalar width/phase checks remain conditional
model evidence; actual technology applicability, complete PRL/EOL/cut/density,
internal transistor grid, source-clock phase/reset/K/first-use, AP/OBS/PG
continuity, native RC and all timing remain open. A3 can establish only the
actual native covered-rule verdict on complete visible modeled metal.

## Resource admission and provenance

A2 actually measured 0.79 s, 249580 KiB peak RSS, 6988074 B staged disk for 477
rectangles +130 native vias = 607 encoder objects and 33 native calls. A3 has
4400 whole-master encoder objects + 7 exact control rectangles = 4407 objects,
7.2603× A2. Linear total-object scaling gives 1812025 KiB RSS and 50735490 B
disk; these are conservative planning estimates, not measured A3 performance.
Propose 1 CPU / 4 GiB RAM / 2 GiB disk for sequential processes, unpinned ot-run,
only after ROOT grant and actual host memory/disk headroom admission. Full
uncompressed inventory27.66 MB plus model5.59 MB; native input only needs exact
boxes, not the expanded neighbor ledger. No guessed wall-time deadline or
per-process address-space cap is proposed. Record actual peak/disk afterward.

Current three-host validation receipts (ot-epyc6/7/8 at21:32 UTC) are retained
under current_image_receipts, separately from A2 contemporaneous ep7 receipts
at21:54 UTC. Actual image.Id /RepoDigest16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29,
OpenROAD binary21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846,
version26Q3-1510-g6cb3f2b704. af971398 is frozen analytical calibration only.
These existing receipts do not retroactively qualify any unobserved A3 host:
future execution must collect its own actual host, current .Id/RepoDigests,
binary SHA, version, tech SHA, headroom, resource and timestamps before engine.

Run `python3 inventory.py` for the finite extraction (about 6 seconds locally).
It reproduces summary.json and deterministic inventory.json.gz. No simulator,
synthesis, OpenROAD or production geometry generator is involved.
