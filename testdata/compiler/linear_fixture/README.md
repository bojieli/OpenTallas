# Exact-integer executable fixture

This redistributable fixture exists only to prove the first compiler/runtime
artifact path. It contains a `1 x 4` signed-int8 input, a `3 x 4` signed-int8 ROM
matrix, and a `1 x 3` signed-int32 ROM bias. The program performs one
`ROM_MATMUL`, one exact-shape `VECTOR_ADD`, and one terminal `COMPLETE`.

The service engine must produce `[-1, 10, 4]`, reconcile all functional
counters, and do so without reading `known_answers.json`. This fixture is not a
transformer block or target numeric implementation and cannot close a real-model
milestone.
