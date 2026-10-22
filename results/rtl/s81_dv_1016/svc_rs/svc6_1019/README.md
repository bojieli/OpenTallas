SVC6 terminal evidence pickup 2026-10-20

Corrected SOT/SO bench (95d63f254) passes all eight FG3 ST0 cases, including the SO checker and fault checks. These are FG3 evidence, not production-engine release qualification. KPV sweeps verify55/58 fail and62/70/85 pass on pin ST0 and landed-parent ST2 tail46, two seeds each: registered attention pins require +7 P.V drain edges (5dd12f995). Production-engine ST2 without SO passes eight cases. SO production, release-config SO+pin+lp, and lp/SO mutants are still live and not qualified by this record.
