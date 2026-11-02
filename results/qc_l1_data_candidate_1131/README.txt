PREPARED, UNEXECUTED L1 three-DATA-edit candidate.

Exact source: retained actual5_1_grt.odb SHA f2ea233f4efaf564046b47fd1beb15b16363f52e4a5455e645564a94fce10d66. No original runtime/source file is edited. candidate_manifest.json lists complete actual predecessor/fanout ITerms and only two resize+one sink-local buffer edits. All original clock-connected instance master/location/orientation/flags and cell census except those declared edits must remain exact. Lib/LEF master contract uses A input/Y output/functionA at both selected TT/FF SHA identities. Platform excludes *x1p*,*xp*,SDF*,ICG*; selected master names do not match, and BUFx2 is platform MIN/HOLD buffer.

Structural extraction: sole normal4GB/1T actual snapshot import completed full cell/clock/BTerm and EXP/HEAD/INV cones. Its last unescaped sink lookup errored (OpenROAD outerrc0 was misleading); exact escaped native sink was resolved from already complete INV output adjacency/cell census, no second session. cones.tsv is new DATA-only filtering of retained raw rows; no timing/RC/placement/route ran. master_pins.tsv comes from exact selected ASAP7 LEF static extract, not a claimed completed DB master query. Full immutable structural outputs stay in intel2 codex-qc-su/l1_candidate_struct1131; this packet retains their digests and complete needed DATA incidence.

Preparation (copy only, no CAD):
python3 prepare_candidate.py --source-kit /srv/opentallas-scratch2/claude/codex-qc-su/l1 --tools APPROVED_TOOLS/die_plan --out FRESH_OWNED_COUPON
The current published helper bundle is snapshotted and hashed; original RTL/config/SDC/source clocks/Libs remain byte exact. No generic make target is invoked. The route-stage4_cts.sdc filename is explicitly a byte-identical alias of final5_1_grt.sdc for current MM session semantics, not an old CTS constraint substitution.

After source/manifest review ONLY, invoke through normal ot-run16GB/2T (same-family actual GRT peak6.786GB):
bash run_candidate.sh place REVIEWED_MANIFEST_SHA256
This stops after the three edits plus native DPL, writes candidate_place.odb/candidate_place_geom.tsv/candidate_placement.tsv. Actual LOOK is required. No route, proof or DRT in this phase.

Only after actual candidate placement LOOK, write placement_review.json {"scope":"L1_THREE_DATA_EDITS_ROUTE","placement_sha256":"EXACT_REVIEWED_candidate_placement.tsv_DIGEST"}. A distinct fresh owned coupon with that review replays the same exact edits/DPL from original snapshot, requires identical semantic full-placement digest before any route, then:
bash run_candidate.sh route REVIEWED_MANIFEST_SHA256
It uses native incremental DATA routing/actual GRT RC, late native write_guides, both-class DB/native coverage with exact original CLOCK guide geometry, and current legacy_gate.py grt read-only TT/FF+source/pair policy. It never calls broad core_final_repair (which could add mutations). This incremental coupon is not a new full GRT50 qualification, DRT authorization, postrouteEQ, source/profile adoption or SIGNED result.

Rollback is discard the OWN coupon and restore the immutable original5_1 ODB/SDC by recorded SHA; reverse connection/master operations are also listed in manifest. Full physical lifecycle/helper capability remains subject to review; scripts have only syntax/static checks, no candidate CAD execution or timing-improvement claim.
