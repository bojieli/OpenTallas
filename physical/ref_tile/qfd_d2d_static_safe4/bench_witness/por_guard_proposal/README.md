Review-only source POR guard: concrete state/area price; no production integration

This standalone module and test are bench witnesses only. It is NOT instantiated in any D2D kit, parent GEN, controller or clock/reset source. No gate/adoption; production Kflush remains unbound. FLUSH31 is a diagnostic mapping point, not a selected source delay. Its defaults do not establish a native reset-tree bound.

Mechanism: a qualified real asynchronous POR clears all counter and armed FFs even while the clock is stopped. After POR release the guard counts FLUSH actual source-clock edges, then asserts armed once and holds it. guarded_rst_n=por_n & armed asserts immediately on POR and releases at exactly the qualified edge. It adds FLUSH cold-start source edges; it inserts no FF edge into normal transport/data paths once armed. POR pulse/minimum asynchronous requirements and legal source clock remain real physical preconditions; the guard cannot manufacture a qualified POR from arbitrary uninitialized signals.

Focused fleet behavioral check PASS: all64 two-state6bit prior states plus all-X prior state, source clock stopped during asynchronous POR assertion, exact releases forFLUSH3/17/31, held armed normal execution, reassertion and restart before the guard arms. No zero-init/equal-state premise. An early-release mutant fires edge30 instead of31 and FAILs deterministically. This proves only the standalone guard's digital behavior under a qualified assertion; it is not the full D2D first-defined-write/first-valid observability proof.

Actual mapping using pinned OpenROAD/orfs ASAP7 nonfake RVT TT Liberty and real standard-cell LEF:

- DiagnosticFLUSH31:6 DFFASRHQNx1 FFs,14 combinational cells,20total, actualLEFarea3.572100um2 (FF2.274480, logic1.297620).
- Actual mapped count:2INVx1,1OR3x1,1OAI31xp33,1NOR3xp33,1NOR4xp25,1NOR5xp2,4XNOR2xp5,1OA21x2,1NOR2xp33,1AND2x2,6DFFASRHQNx1, allASAP7_75t_R.
- Every FF CLK maps to the actual source ck port; every RESETN maps to por_n; every SETN is tied inactive1. Added physical source-clock sinks6; POR sinks7 including the AND gate. Maximum actual mapped signal driver fanout7 (constants excluded),0drivers>16, including both exported output observations.
- This is mapped cell/LEF inventory only. There is no placement/RC/slew/hold/nativephase/route proof, clock-buffer area, integrated recursive load accounting or reset-slew qualification. Liberty source hashes, actualLEFhash, netlist and machine-readable inventory are committed. The full actualLEF is compressed for reproducible area checking.

Required source integration before a guard could discharge initialization:

1. Bind FLUSH to the actual source-pinned native reset-tree propagation bound plus regional assertion and3copy-capture bound; select width ceil(log2(FLUSH)) for this implementation. No simulation time or convenient K is a guarantee.
2. Hold/reset the real producer so its66configuration writes are not dropped; join each calendar/slot/program defined-bit lifetime to its first read/use. A counter alone does not sanitize storage corrupted before arm.
3. Fence actual external valid observations and PHY startup until the downstream reset/capture/defined-write contract is met. A late guard only at the delayed D2D input does not prove earlier output validity. Price and constrain every real producer/observer fence route/landing and diagnostic status bit.
4. Prove reset/abort/restart and all legal phase histories. New global reset/clock loads need recursive native all-driver/fanout/slew/hold and source initialization correspondence checks in the actual integrated graph.
5. ROOT/GEN owns any changed cold-prefix ABI. Additional diagnostic/observer pins and route/landing ages are unpriced here;6FF/3.5721um2 is the root guard module's concrete price, not a total system cost.

Reproduce with run_guard_proposal.sh on the admitted fleet host/image paths (source files mounted under/data). prepare_guard_lib.py keeps the actual nonfake cell definitions/templates, changes only the container library name for mapping, and records original Liberty hashes. check_guard_mapped_inventory.py independently uses actualLEFareas, counts true mapped terminal loads and asserts all6FF clock/reset/preset connections. The source guard remains a proposal, not a source workaround for the still-unbound physical reset/observer contract.
