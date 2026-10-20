Exact original xl_dsA_6a event replay — FAIL, not release qualified

The candidate STREAM-side cache-busy/open-pending admission guard prevents the original illegal OPEN at cycle4569. Trace instead accepts the next OPEN at4570 with running=0, and cache fault remains0. Original raw ingress/xw/ids/full-memory events and the original95-descriptor fixed GO calendar were unchanged; manifest pins events, RTL, executable and exact argv.

The immutable schedule then misses readiness at absolute cycle4851 (issuer relative4445): the next64-row transfer starts4773, leaving78 cycles before GO, below the actual80-edge producer drain plus cache tail. The next edge4852 reports sticky issuer fault1/cache0/feed0. Only29/95 GOs and108 results precede failure. No numeric/whole-run/fixedGO/price/controller/physical PASS is claimed. All original fault paths remain enabled.

A schedule correction must derive and price service/cache tail per operation, preserve the fixed calendar admission checks, prove exact original golden operation outputs, and be replayed on current MC3c. Merely adding arbitrary slack until a pass or suppressing a fault is invalid. The stored legacy SAFE-controller direct-RTL replay is mechanism evidence only; no imported Yosys sequential-cell behavioral model is used. The minimum282-read positive and three causal fault witnesses remain separate cache-contract evidence.

run.log, result.json and manifest.json are verbatim remote products. golden_sources.sha256 pins the eight original fixture/weight sources used by the independent original-operation golden checker.
