# SAFE-QW-CB16 narrow v6 critical diagnostic packet

Exact production source b25f19be20174b6f98218ed6fa9ca6641e99b166, content-snapshot gate manifests preserved under each child. Candidate remains UNBOUND; no REVIEW.json or submit. Both floorplan+density PNGs visually inspected.

|258 child|FF|GRT violations|TT setup, routed RC|FF hold, routed RC|TT/FF clock spread|
|---|---:|---:|---:|---:|---:|
|write|1132|0|+306.779ps|+28.409ps|23.2/23.4ps|
|read|347|0|+298.386ps|+31.258ps|15.7/15.7ps|

Corner replay uses immutable5_1_grt.odb, saved5_1_grt.sdc, unchanged generated signoff.sdc, native TT/FF libraries, propagated clocks, estimate_parasitics -global_routing. Read-only, no repair/constraint edits. Input hashes in corner_sources.json; full expanded hold paths in corner_*_FF.log. This is global-route RC, not detailed-route signoff. Original gate path_classes numbers TT setup326.66/305.82ps and TT diagnostic hold49.625/53.758ps are placementRC diagnostics and are NOT the FF hold column.

1. Register boundaries: direct register Q write banks and registered read outputs; two face-reset stages. Reset input one firststage sink. Data bank crossing still requires linked exact age/overwrite constraint proof.
2. Reach: child64.8x129.6, internal reported96.5um (geometric maximum194.4um). Parent reach/layout is independently UNRESOLVED.
3. Fanout: native flattened mapped JSON audit checks exact1132/347FF before counting. W/R max register nonclock loads5/4;44receiver flags max9loads, limit32. Write output flag pin loads require linked receiver (explicit in audit scope). No text/hierarchy parser accepted.
4. Registered per24bit onehot write/read selection,4-way masked OR, no wide binary mux. Kept source flag copies prevent reset-stale words.
5. Each write storage1132bits INCLUDING control (<2048); read347bits. Full-width alternative remains MODEL ONLY and needs policy waiver.
6. No macros/islands. Pin-bound continuous standardcell floorplan, aspect2. Low util explicit waiver: W8.7%,R3.3%, gate2warnings each. Bank faces4.02pins/um, data4.05/um. Parent43.2origin lattice and20um channels remain prerequisite.
7. Native local clock spread below80ps both TT/FF; io_hold_margin_ns0.03. Parent roots only hardchild clocks/reset legalization not yet complete.
8. Continuous static D4K2 throughput unchanged. Both reset epochs+1 vs historical halves; compiler/fullfabric reset warmup replay required before binding. Original fullfabric/lockstep historical witnesses are not new parent qualification.

Blockers: parent CP legal placement+routed405um endpoints; calendar/forwarding alignment; exact age/overwrite constraints replacing legacy blanket setup2/hold3; reset relay/epoch/MUT8 binding; parent native-clock/TTsetup+FFhold. No component/parent CLOSED claim.
