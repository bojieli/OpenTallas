Actual next-read-address bank selector, source candidate only

The immutable prior NORST map registers u_core.pr_n[0] as pr_odd. Its 2,048 contacts select the two 512-bit P words from the even/odd SRAM outputs. PMEM=1 reads the next address, and the unchanged registered select accompanies those outputs one edge later. MUT4 inverts that same select. PMEM=0 selects constant zero.

Construct 64 independent kept scalar select registers, one per eight-bit output chunk. Each captures the identical pr_a[0] expression on the original edge. It drives both word-swapping muxes for that chunk: a conservative four mapped contacts/bit gives32 contacts/copy. The input expression drives64 D pins, a separate real remaining control-distribution obligation if mapping exposes it; no claim that merely copying Q solves all fanout. Adds64 plain FF before pruning the unused original selector; no SRAM, clock, reset or data edge changes, and no new reset initialization assumption.

Paired mapping must measure both select outputs and upstream D cone. Bitwise lockstep must include zero/fullscale/random banks, back-to-back selects, PMEM0 and MUT4. The actual ATT fullgolden on reset source7a remains immutable; this later PSEL source cannot inherit its result. Whole-core native, physical, clock, G4 slot geometry and calendar remain OPEN.
