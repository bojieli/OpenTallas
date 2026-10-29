# Joint QC clock-cell and power access construction

The existing power-first access blocked all460 unresolved clock M8 witnesses. This successor allocates explicit clock access before rebuilding the clock cells' supply connections, retaining actual native signals, obstructions, supply metal, track grids, technology via enclosures and minimum areas. Source geometry is actual119_h800 from`baseline26/mechanics119_h800/clock_grafted.odb` on intel2.

Measured candidate:484/484 previously impossible base pins receive island-contained M6 jogs/M7 risers/M8 landing witnesses; all89,178 native rail groups (89,180 clock-cell supply contacts) reconnect geometrically with713,424 vias and2,407,806 wire/enclosure rectangles. The rebuilt PG and all484 actual192x80nm M8 landing shapes pass the joint geometry check with0spacing/overlap findings. Small result receipts are in`receipts/joint484/`. No clock sites, topology, RTL or cycles change.

This is a geometry construction result. Physical whole-die connectivity, DRC, IR, actual whole-clock tree and final native START source remain open. The source119_h800 clock frame still has the diagnosed old-nearest START pin positions; it is a regional-clock/PG vehicle. Broader local clock-access construction for all89,180 pin bases is running separately and retains every unresolved pin. The separate native377macro PG joins belong to the QC macro-PG lane.

`plan_access.py` constructs physical supply paths from actual M1 rail groups to canonical M9 supply stripes. It requires the actual lower clock seed and accepts optional`--joint-clock-reserved` signal-like exclusion rectangles. Clock M8 reservations add280nm beyond the actual landing geometry; the ordinary40nm M8 PG clearance supplies the remaining spacing for the320nm clock shield requirement. M8 landings are192x80nm (15,360nm²) and supply landings192x40nm (7,680nm²), exceeding the actual7,520nm² minimum. All lower-layer rectangles use actual via enclosures/spacing. Only exact matches between canonical PG and BLOCK obstructions are classified as owned existing PG, with opposite supplies still blocking.

`jog_backbones.py --joint-clock` emits the clock construction and reservation. `--all-bases` extends it to every actual cell pin in the fixed-wires source. `recheck_joint.py` checks actual landing shapes against other clock accesses, canonical PG, and optional newly built supply geometry, emitting a fresh verdict and corrected reservation. Neither script materializes or routes the proposal.

Large artifacts on intel2:`/srv/opentallas-scratch2/claude/codex-qc-mesh5-1029/`:

- `census119_h800/geometry.json`: fresh actual source;3,741,625 signal rectangles,384,041 obstructions,137,306 native supply rectangles.
- `joint_seed/backbone_plan.json`:484/484 local clock access construction (unit2681909 EXIT0).
- `pg_joint484/{access_plan,reserved_access,summary}.json`:89,180 contacts,0unresolved (unit2704221 EXIT0).
- `pg_joint484_recheck192/summary.json`: actual192nm landing + all rebuilt PG check PASS0 (unit2851513 EXIT0).
- `joint_all.log`: full89,180-base continuation (unit2754762), unqualified until terminal result and failure diagnosis.

The first484planner used a160nm witness; its physical192nm landing was independently checked afterwards with0findings. Current source uses the192nm witness directly. Old failures and candidates remain preserved.

`apply_access.py` provides the additive physical importer`apply_access(block,plan_dir,grid_path,expected_contacts=89180)`. It requires all canonical M8/M9 grid rectangles to exist as actual supply metal, exact actual native clock-cell M1 rails matching every planned group, and the plan's actual technology-via enclosure contract. It adds supply rectangles and technology vias, connects the corresponding native PG ITerms, and asserts identical main`infra_replay.physical_snapshot` hashes for every non-PG net (regular wire opcodes, special-wire geometry, terminals and instance geometry). Existing exact PG shapes/vias are reused; no old geometry is deleted. Actual import remains NOT RUN until a source with its real canonical grid is available. The helper never infers physical connectivity from supply net names or global_connect. Whole-die DRC/IR remain separate gates.

The importer mechanism is now exercised on one actual instantiated CKINVDCx16 master, with both native supply contacts and actual canonical grid metal in an isolated source-derived vehicle. It adds48 unique wire rectangles and16 technology vias, retains the exact non-PG snapshot hash, and reapplication adds0geometry. A one-DBU native-rail mismatch is rejected before mutation (`Planned rail has uncovered gap`). Receipt`receipts/import_vehicle.json`, intel2unit3611037 EXIT0. This checks the importer mechanism only; the complete89,180-contact physical import and whole-grid connectivity/DRC/IR remain NOT RUN. `import_vehicle.py` never writes its source ODB.
