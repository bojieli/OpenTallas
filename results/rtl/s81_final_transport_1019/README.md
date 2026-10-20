# Final FFN transport architecture packet

The complete source-derived model covers all4480 local RD pairs and480 peer
allgather packets. It identifies a real missing RD tier/local mechanism and
recommends a default-off typed273-bit V row-pair stream plus explicit local
delivery. No RTL was edited and no production calendar is emitted.

Read OWNER_CHOICE.md for the complete alternatives, every resource cost,
source/hardware obligations and exact minimal source-only pricing cut. The
compressed model contains every original pair, proposed staging submove,
literal CTL/RDOUT word, real physical lane and current source hash. summary.json
contains per-port sustained demands and honest NULL peer/full-token ages.

Fleet8 tests PASS (logs/run_r4.log, receipt.json), including full actual graph
coverage,2560 exact273-bit encoding round trips and causal refusal guards.
run_r2.log preserves an intermediate model Python failure. These are software
architecture/encoding tests, not new transport RTL, native or token PASS.

The source base is codex/s81-final-fold-1019@9b2e70333. Preserve the existing
80-cut VS13/POST evidence and75/63 pin ages, pre1008/post1009, and all HOP jobs.
No arithmetic sweep or whole-die build was repeated. ROOT has not yet authorized
full implementation; per the coordinator, first obtain an exact bounded
source-only pricing-cut decision. No physical gate is ready.

Reproduce from the repository with PYTHONPATH=tools/s81_dv:
`python3 -m unittest layer_prog.test_final_ffn_transport -v`
`python3 tools/s81_dv/layer_prog/final_ffn_transport.py --out model.json`
Use unpinned ot-run for heavy work. Current source admission deliberately
refuses even caller-supplied positive flags or invented ages.
