# Incremental bounded graph worklist

Opt-in --incremental keeps per-net sink sets and a versioned maximum-load heap instead of rescanning every cell after each cloned driver. It retains the reference implementation by default, the canonical SCC feedback frontier, port/multi-output frontiers, and the same source-function/clock/reset ledger. It changes model/generation cost only.

Fleet unit2175220 passed14 tests in0.249s: the six canonical cases through both paths,150 random acyclic graph comparisons against the reference, and direct feedback rejection without clone growth. Random cases check every final nonclock root bound and clone accounting. This does not prove independent unreset initialization or authorize RTL adoption.

A new direct-feedback negative exposed unbounded growth in the initial4347 reference; the own test process2008540 was terminated after that structural diagnosis. The canonical cf32860cf SCC fix supersedes that version. The original large VE budget process1614102 was also stopped after the same demonstrated feedback frontier, preserving its log. No fleet simulation or layout job was stopped.

The large VE canonical core,310622 original cells, runs through the worklist in seconds and refuses a held operand-ring feedback driver after2901 primitive copies atlimit24. Its graph has25363 cyclic cells; the frontier requires explicit state/initialization reasoning. A limit32 model run is separate because the demonstrated limit24 root itself has32 loads, already inside the binding maximum. Neither model emits RTL.
