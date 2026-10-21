Exact preflight at6ef6df0f039a6f7d2334a44261c268209b4c2e03

Both rendered specs were passed to the real published canonical closure_loop.validate (mainb5f983efec3f397e21d998efd23bfa55e40d0c3d), with zero errors; real behavioral stages and mutants remain unchanged. bench_evidence_problems has zero errors/warnings; committed exact REVIEW receipts pass. No manual-evidence exemption, no fake verifier, no bench removal.

Both submit_exact --dry-run preflights accept exact gate source binding and coordinator review. This is additional evidence, not a replacement for canonical validate. The inherited WARN about22 helper paths arises from check_kit's temporary kit-only materialization before its subsequent actual-commit check_sources; the actual immutable Git source and verified runtime archive contain the helpers (GRT completed). No tool/policy change, waiver or re-gate was made. Insertion/depth/fill risks remain in gate reports.

These files are outside the route's consumed source closure. The final artifact-only commit must still be rendered with its actual hex SHA and passed to canonical validate before ROOT-integration handoff. ROOT integration alone publishes/submits. No job was dropped or main merged here.
