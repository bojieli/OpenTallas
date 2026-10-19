# P3 matched pad-return geometry checkpoint

Fleet-only geometry prototype PASS, not a safe-parent or gate qualification. Seven 32x128 SRAM pad macros plus an optional input register preserve the existing three-edge pad latency (native SRAM ring two edges). Input and output capture alternatives each pass 984 checks and both negative controls. Defaults remain unchanged.

Matched physical pin distances: source to pad capture 337.770um; capture to SRAM write 176.688um; SRAM read to proposed XS3 native-N rl1 pins 389.622um; parent RIN pin to capture 396.750um; capture to hard row input 403.070um. All are <=405um. The 45 hard rectangles fit the original 630.72x2203.2 outline at 54.36% hard fill with 10.8um halos and 43.2um lattice.

The XS3 native-N allocation has 2,994 unique signal pins, nominal N density 5.331/um. Existing S/W active-span spreading remains unresolved. Proposed capture regions overlap one another: they are placement bounds for distinct cell sets, not legal disjoint islands. Actual placement capacity, stdcell area, all row/strap/reset/control/clock endpoints, native clock audit and fresh child/parent gates remain mandatory. No routing, submission or REVIEW.json is authorized by this proof.

The existing hnx_rp4lp4_lfx rq register already captures rl1 before XS3. A successor may investigate using that physical relay instead of the prototype extra input capture; no such change is implemented or credited here.

Related completed XS3 baseline gate is committed under physical/ref_tile/hnx_rp3lp3_xs3: WARN, zero FAIL and five WARN, GRT0. Pin-flop clock spreads TT58.6/FF57.1ps pass the clock guidance, but auto-IO uses partial S/W spans and needs physical correction/review. It is evidence only and is not the proposed N-face gate.
