# S81 native successor and conditional POST transport

This is the Codex successor inventory and physical-cut request, built independently of the untouched Claude tree. It does not publish a v14 contract or authorize a die GRT. The source-matched file bundles, hashes, footprint checks and outstanding view gaps are in manifest.json. The builder is tools/s81/native_successor_manifest.py.

## Native coverage and fit

1683 reference instances have an available same-directory routed LEF plus native-named TT/FF/SS files; their exported footprints fit the existing reference slots. These are pinned artifact bundles, not qualified closure counts, and they have not yet been substituted into the die netlist. Ten indexed master classes lack a complete native bundle, including the assembled controller and endpoints that previously substituted SS for TT.

Four of eight HC half-region leaf types have complete bundles: CTPL, CTFX, CTFN and CTFS. They cover704 of1920 prospective leaf instances after flattening64 half regions. CTNL, CTRN, CTRA and CTRB account for1216 missing native leaf instances. New CTRN/CTNL growth requests remain unadopted. Most other field and slab placeholders still require actual tile inventories, exported views and source-pinned qualification receipts. No positive qualified-closed count is established.

The shipped S_RD2/S_RT4 split requires3056 forward and2164 return bits per column,15660 aggregate across three columns. The read-only writer snapshot still has a v13 contract and a v14 recipe, with1264/1090 generator crossings. The snapshot hashes and copied contract/recipe preserve those inputs; the new seam widths are a requirement, not a claim that the private generator already carries them.

## Conditional POST geometry

Use24 disjoint active branches: north10 half regions per column split[3,3,2,2]; south outer columns12 split[3,3,3,3], centre10 split[3,3,2,2]. Every branch owns8 or12 Y words and all256 words belong to exactly one branch. This preserves the NORM golden chain and arithmetic. Maximum packet is384 payload plus25 metadata bits; completion is23 bits. All24 memberships must complete for each of20 beats, with finite20-beat credits and a resident coefficient-generation gate. Source keeps a coefficient bank leased until every writeback completes.

The conditional midpoint is(18220.68,13327.2)um within the12571.2..14083.2um HC corridor. Longest branch-centre Manhattan distance is9155.16um, requiring at least19 global500um stages each way. A3-half region adds a1029.24um local pin envelope, requiring at least3 local stages. These are geometric lower bounds: relay footprint placement, legal channels, actual consumer pin locations, local clock/CDC stages and paired CTPL/PB/HPR latency have not been approved. A straight interpolated line through hard tiles is not a legal register-placement plan.

## Cut evidence and limits

The recorded c5 GRT permitsM4-M9. M3 is excluded from capacity; earlier M3-based corridor estimates were optimistic. On M5/M7/M9, the1816.56um corridor has88935 geometric tracks,71148 after an explicit20%reserve. Widened HC plus POST cuts are20076bits north and20588south (conditional0.282/0.289). Those are not actual overflow predictions: complete native OBS, existing background wires and clock/power allocation are missing.

More restrictive row cuts use exact rectangles from the available native LEFs, including pin/power rectangles conservatively. The CTPL row's M5/M7 estimate is0.784 with HC5220 plus worst POST1728bits per column. Thin input/output strips reach0.814. A die-global M9 scenario, reserving a guarded PG-stripe bound from the published9.092um pitch/0.48um width plus20%additionalreserve, reduces these to about0.49..0.502. M9 allocation and actual die power/clock/background coverage remain unverified. This result requires a die-global routing decision and complete actual cuts; it does not grant M9 to a leaf or raise any leaf layer cap.

At the0.60target, the worst column needs11580 usable tracks. All missing rows must pass that cut with actual views. The POST family remains unqualified: measured serial production latency286–287cycles versus immutable112.9 requires<=124.19. Geometry forecasts never replace the production bench, complete writeback retirement, exactness/mutant checks or physical closure.

## Next integration steps

Bind native bundles into a successor die netlist with exact functional/clock pin maps; flatten the actual HC/SU/VM/collective inventories; obtain the missing HC views and approved inner layouts. Implement real registered minimum-delay seams. Place and harden the minimum express queue/dispatch/completion tiles, then prove every physical hop<=500um and every actual cut<=0.60, with a recorded M9 global allocation if used. Only after full real coverage and legal fit/cut evidence may a new die GRT start. Existing c5 is preserved as prototype pathfinding and remains useful congestion evidence.
