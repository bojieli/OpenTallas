G96 GROUP_REDUCE_MCAST candidate calendar
=========================================

Normative shape: 96 ranks, subgroup eight, n1024 FP32/rank; exact balanced rank-order pairwise FP32 tree, BF16 RNE once at each group root; concatenated n12288 BF16/rank. Four quarter reducers each hold sixteen 16-lane tags. Native V2 source cc6d946ad/original a84885466 and actual TX5 successor cc12ab88a; actual 613/487 transport359252cc2. No native SU composition is claimed.

Candidate graph: four parallel bidirectional 96-rank rings, contiguous four-rank packages. Eight of nine actual SerDes macros are allocated; host UCIe is separate. Every edge remains an unqualified physical binding, full FEC required. Candidate word-flight three is a component assumption, not measured full-FEC/board latency. Immutable price1325.9 cycles and 110% gate1458.49 remain unchanged.

Measured schedules: unidirectional4500 cycles (3.39392x), bidirectional3436 (2.59145x), chronological-hole insertion3232 (2.43759x). All FAIL the immutable price gate. Insertion preserves actual sequential write/read ordering and postassigns full16-bit sequence values; independent replay64 and emitted-word audits pass. Native route/load/add/publication instruction fields and registered sequence metadata one edge ahead of link reservations are checked independently.

Actual lower_expanded emits sparse1536-bit V2 words for384 native owners. This is expanded machine-word lowering, not an executable64-row program proof. Direct words exceed64rows; affine/count-loop compression remains UNVERIFIED. A distinct-word count is not a lower bound on counted-program storage. Numerical RTL, actual FEC/clock/board, SU producer and physical qualification are also open.

Runs: bidirectional ot-agidock128 unit oth-ubuntu-3725622-1792052067; audit oth-ubuntu-3725715-1792052089. Chronological holes ot-epyc4 unit oth-ubuntu-1307078-1792052519, audit oth-ubuntu-1310755-1792052596. Full calendar and expanded words retained at /tmp/hcoll-g96-bidir-1015 and /tmp/hcoll-g96-holes-r2-1015 on the respective hosts. Lightweight committed model and independent audit receipts identify both results.

Earlier insertion attempt rejected a real local-delivery sink collision; local delivery now participates in the same transactional resource plan. A separate audit attempted on a host without the output directory correctly returned nonzero; the source-bound audit was rerun through ot-run --hosts ot-epyc4. No failed run was treated as PASS.
