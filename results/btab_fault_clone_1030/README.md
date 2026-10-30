# Default-off BTAB dedicated fault face proposal

`FAULT_OUTPUT_CLONE=0` is appended after MIF; no public port or production latency change. The opt-in has two kept distinct-ID modules with identical D, asynchronous rl1 reset and ck: private sticky feedback and a dedicated output. One extra source FF/clock load compared with the original synthesized source. The current C final physical DB already has late clone `ot_prs_00000_ff`; final integration must replace/account for that late clone, not add a second blindly.

Actual original C BTAB module body is the gold in the miter (only module name changed), both MIF0 and MIF1 with actual compiled SRAM behavior. 833ps clock, full outputs compared for934 cycles, cold and3warm reset episodes. Wrong-D and wrong-reset mutants are caught. Generic synthesis retains both distinct helper instances, one FF each, identical D/reset/clock, separate Q; this is NOT native mapped LEC/FACE or physical qualification.

Candidate output home proposal is the current physical face clone home center256.770,5.265, near frozen fault pin253.788,0.042 (L1=8.205um). Private state may retain current center256.446,6.075. Existing core293.76x155.52 and pin coordinates remain. ClockRC/reach/load must be requalified for native helper naming and actual adopted clockgraph; old clock-only SPEF/identity cannot be reused. Reset/startup/steady source proof passed; no new cold or production cycles.

HOLD: root/shared-source review, canonical native GEN+LEC+FACE/retention and new clockload qualification before activation. No P&R or route approval is implied. Old current C NOTSIGNED/DRC3/FFhold/DRV/face evidence remains immutable. Hold/DRV/local DRC repair proposals are separate measured work.
