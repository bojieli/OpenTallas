# S81 count and operand-credit evidence

Source commits: 1b7ba9403 (count RTL/test), 1d8b76053 (19.44-um count kits), 2521e4ce6 (operand credit path).

The count gate compares ga/q2f cycle by cycle with the RWB core for NR15 and NR2 over 200,000 cycles, including sparse/dense/burst/tag-storm inputs and changing live bits. Exact PASS; MUT_GA deliberately drops the final region and FAILS with 133,371 mismatching cycles. The proof is a leaf proof. It does not prove the die's 12-leaf live chain is safe while tags are opened or retired; the composed phase program must retain tags until every root and leaf has drained.

Count kits fit 142.56 x 19.44 um. Pre-route CTS passes on provisional faces; die-assigned exact pins are still required before route submission. NR15 310 sinks, TT insertion max86.5 / spread9.7 ps, setup+270.8 / hold+26.4 ps; NR2 55 sinks, max71.0 / spread6.0 ps, +280.0 / +28.1 ps. These are pre-route measurements, not CLOSED views.

Operand credits are held in the engine adapter across CDC/engine stalls and consumed only at actual dispatch. The positive bench observes three commands with three credits, starvation after two, reset epoch clearing and over-credit fault. The no-decrement mutant fails. The seven existing adapter scenarios still pass their intended positive/negative expectations. This mechanism does not provide SU/HC VM read/write slot backpressure. Those ports still need whole-group atomic issue and paced write draining, plus response-order proof against the VM client adapter.

Native dsfd_sp_su_c/dsfd_sp_hc_c select INPUT_CREDITS=1; direct slab/hierarchy defaults retain level mode. The existing layer bench HC instance explicitly uses INPUT_CREDITS=0. Native whole-layer composition with engine12 pulse producer remains to be run. Changing endpoint control RTL requires re-hardening its actual control leaf after the wider adapter contract is final.

Assigned pin update: die commit3cbe13003 adopted in26f237a89, gate commit0e426e71c. Exact assigned-pin CTS NR15 TTmax109.1/spread12.5, setup+273.6/hold+26.7 ps; NR2max105.5/spread4.3, +283.5/+34.6. Both WARN0fail. No route submitted: actual PQ phase/tag-lifetime proof still absent (S-FUNC vehicle injects root words, not real field+PQ composition).

Count-controller fix d7f2edbd3: the native controller exposed 12 groups (RG11,192-bit ga_i) but read16 (hard-coded8-region NCA). NCA now equals NGR, eliminating out-of-range inputs with unchanged sum-pipeline depth. The verbatim extracted controller sum block passes5000cycles over actual15/2/15group capacities; dropping the lastgroup mutant produces11931errors. This targeted test does not replace production phase correctness, and the CLOSEDcontroller must be re-hardened when the multi-leaf latency/control re-plan is final.
