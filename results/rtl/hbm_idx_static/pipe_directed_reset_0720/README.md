# PIPE directed asynchronous reset proof

Nominal source exactly8646e261d854b12a432da4413c7fe80c8b014482ce7a9268e0b0fcc62fd0aa10 (bae9e6f10/aedbb4076 source). Reference is exact same FAN32 source PIPE_HAZARD0; candidate PIPE_HAZARD1. Every public edge compared including reset/quiet; paired arbitrary201240physical SRAM+768read-output bits, OT_MEM_NO_INIT.

Prior quiet-mutant proof55fbc4c56 was explicitly noncausal. This fixture waits for new pipeline v_p NONZERO, stops actual clock, verifies nonzero again, then asserts raw reset BETWEEN clock edges. New v_p/other_p/id_p controls must asynchronously clear. Clock restarts only after successful assertion observation; every-edge public comparisons continue.

Nominal session92450/unit245452-1792506192 PASS3x200000,31 asynchronous checks each seed, nonzero/precondition+stopped-clock observation PASS. Actual mutant disconnects ONLY the rr15 new-control bank (v_p/other_p) from reset; session63328/unit245442-1792506192 causal FAIL44ns with v_p6. The prior vacuous reset-mutant PASS remains preserved separately. This resolves source-simulation reset causality for these new controls; no production parent/calendar/mapped-state or physical qualification follows.

PIPE physical gate aedbb4076/hidx_sel_s3p_a-20261020-050446 FAIL DPL0033 beforeCTS: hold10961 overlaps clkbuf_5_13_0_clk_regs and fails padding; max30native/pin geometry1257PASS/depth566.8ps. Requires real placement correction and fresh gate. No submit.
