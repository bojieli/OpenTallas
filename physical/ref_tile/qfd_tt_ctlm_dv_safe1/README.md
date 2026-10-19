# qfd_tt_ctlm_dv_safe1 — structural successor draft

The failed clk2 gate (9b51e7034) fenced only flops into two full-width halves. OpenROAD reserved the entire die for those regions but left 81,456 combinational cells at top level, calculated negative top-level free area, and diverged. This successor groups complete combinational cones with their sequential clock root after fixing pin anchors. Mixed and rootless cones occupy a real 43.2um channel; no density override or timing exception is added.

The independent forward-source / reverse-destination ownership passes stop at every flop and hard macro. Ambiguous sequential clocks fail with a request to harden separate leaves. Fixed face registers retain their granted locations. Mixed-cone area must fit at <=55% of the physical channel. Topology-only OpenROAD analysis on the exact clk2 pre-placement ODB accounts for all 12,246um2 of synthesized standard cells: core9,620, hr1,867, shared759; all cone cells are owned. This establishes the method, not successor placement/clock closure. Witness: bench_witness/cone_partition_clk2_topology.log.

The draft outline is777.6x432um (aspect1.8), retains the h16c R0 child at475.2,43.2 and the external width contract. Six SRAMs are arranged on the43.2um lattice in two columns and three rows; column gap44.712um, row gap51.84um. The ROM sits at475.2,302.4 above h16c, leaving36.72um clearance. N/S face bands are51.84/43.2um; the standard-cell space remains connected around the macro columns and above h16c. The old measured std area12,246 plus six SRAMs and h16c yields about46% total fill; actual successor synthesis must replace the old estimate before gating.

## Safe-design checklist — gate is blocked until every pending item closes

1. Pins: inherited pin registers; fixed before ownership assignment. New ctx_x/fault pins and reset landing must be reviewed after unified RTL regeneration. Pending.
2. Reach: complete local cones and real landing channel; maximum measured single-cycle data reach and raw ROM clock relation must be checked on the unified netlist. Pending.
3. Fanout: CALPIPE author is adding preserved <=32-bit select copies; parent reset/select copies and Yosys inventory still need review. Pending.
4. Depth: SRAM ring / registered head CALPIPE behavior is proved, but physical <=600ps stages await synthesis/timing. Pending.
5. Storage: four per-user 64x512 SRAM rings replace runtime-indexed flop FIFOs; programme has two SRAMs. Other wrapper delay/storage inventory awaits unified RTL. Pending.
6. Geometry: aspect1.8; macro origins on43.2 lattice and real >=36.72um channels in draft. Raw SRAM abstract itself has793/792 W/E pins over77.76um (~10.2/um): macro pin-face escape or successor abstract must be resolved before claiming <=6/um. Utilisation must use final synthesis area. Pending.
7. Clock: two regional roots with landed crossings and h16c insertion reference; inherited hold margin30ps. TT/FF pin-flop spread<=80ps and raw SRAM phase require actual successor CTS. Pending.
8. Schedule: CALPIPE adds zero external issue edges by lockstep witnesses. ctx_x/FCTX/fault integration and die/compiler first-context result-write rule are owned by coordinator; no successor schedule claim until integration proof. Pending.

No REVIEW.json, submission, or gate has been performed for safe1. Spec is a reviewable physical draft; inherited benchmark paths are not evidence for the changed unified RTL. Coordinator owns controller/parts/LP specification edits; this branch owns physical kit geometry, cone partition Tcl, and the opt-in post-pin hook generator.
