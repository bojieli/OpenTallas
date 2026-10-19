# S81-CAPC-NATIVEP1 (candidate, not adopted)

Native audit on the actual CLOSED source c6ad2f676/record8e81f222e fails six cw_s_v launches and data captures cfg_d/rt_e, as well as reset. Global clock compensation cannot fix both. This candidate registers every input bundle and every output bundle around the immutable core. PINPIPE defaults0; the p1 kit enables it. Latency +1input/+1output; reset boot +2. Throughput accepts/emits each edge. The production-shape golden vehicle expects every A arrival at+1 and every W write at+2, preserving values/order; output-valid and cfg-valid bypass mutants must fail.

Model: results/uarch/s81_capc_nativep1_1019/model.json (1174newFF, actual child LEFs, no parent outline/slot change). Clock spine keeps the children's measured boundary references and balances parent flop arrivals to their internal flops. All native timing and CTS results remain pending; no masks/waivers for data.

SAFE checklist before gate:
1 FIXED: explicit coherent input/output flops; reset reaches only rst_l0/rst_l1; local reset14sinks.
2 PASS model:345.6square parent; local parent/child boundary legs planned below405um; gate must measure wire reach.
3 PASS RTL: pipeline point-to-point; local reset14loads; clock is a clock tree.
4 PASS RTL: one flop per stage, no wide mux/arbitration; hard-child logic unchanged.
5 PASS: extra storage is one-edge boundary transport, not deep delay storage; existing cap_rt SRAM remains unchanged.
6 PASS model: actual child sizes/origins preserved on43.2lattice; full-width43.2southstd band; estimate600stdum2 vs73529free;39%combinedfill. Gate must replace estimate with synthesis area.
7 FIXED: south clock centered172.8um, child_clock_ref=boundary, hold margin.03; CTS spread/native budgets pending.
8 FIXED: PINPIPE0default, PINPIPE1 adds2dataedges and2resetboot; MU-DIE-S81/compiler notified. No rate credit until priced.

Gate PNG/checklist review required before submit; this is a successor after failed physical/native evidence. No REVIEW.json or submission has been written.
