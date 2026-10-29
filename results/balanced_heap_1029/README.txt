Deterministic balanced clock-cluster planner acceleration

core_infra_htree.balanced previously rescanned all overfull-group members
for each corrective transfer. Correction moves only from overfull into
deficit groups; a destination cannot become overfull. Eligible candidate
edges only disappear, so a static heap with lazy invalidation picks the
same (cost, point-index, destination-index) minimum as every old scan.

The300-round assignment loop also used Python min/key for every point.
Optional NumPy performs the same float64 additions and first-min choices;
missing NumPy or non-finite distances retain the scalar path. Python
weight updates and their order stay unchanged. No geometry/model/clock
policy changes, no timing margin changes, no changed plan assignment.

Ten focused tests PASS:24 legacy-assignment comparisons (integer and
fractional coordinates, ties), exact target loads/coverage, no-NumPy
fallback, existing tree naming/vpass regressions.

Measured on intel1 with8,192 actual bf_col census sink coordinates,
8groups/300iterations: legacy3.526s vsnew0.340s =10.37x faster.
Full group assignments compare equal (assertion plus committed hash).
This is one clustering operation, not a claimed end-to-end planner
speedup or a physical/timing gate. Existing progressing full plans use
their pinned original source and are not restarted.
