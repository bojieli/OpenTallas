# Collector status face capture mutant

Source 9b39beae2fab5711f9e68d03dd6f97b2e3022ed0. Exact existing rtl/test/meso/tb_landing_collect.{sv,cpp}; own copy of rtl/common/ot_dp_clk_landing.sv changed ONLY `always @(posedge clk) q <= d;` in ot_dp_landing_face to `always_comb q = d;`.

Existing real-source baseline intel2:/srv/opentallas-scratch2/claude/die-s81-29/cst_sim/sim.log: 576 cycle checks, 0 errors. Own mutant: 576 checks, 255 errors, executable exit1. Same-region face ready, fault, ready-drop each arrives on edge2 instead of required3. Direct branch remains edge2. This detects the status-cycle omission rather than merely different source text.

Actual ot-run 8GB/2threads unit oth-ubuntu-359032-1793307617 on intel2 (fleet alias localhost) exited0 because runner asserts mutant nonzero. Artifacts /srv/opentallas-scratch2/claude/codex-support-1355/{landing_mut.sv,tb_landing_collect.sv,tb_landing_collect.cpp,build.log,mutant.log,run.sh}. Reproduction: copy the three pinned inputs to a scratch run directory; make the single substitution above; invoke run.sh with ot-run from that directory. Uses Verilator5.050. No design change, added cycles, physical run or signoff claim.

Initial launcher infra NOT RUN attempts (missing local-host dir; non-login ot-run PATH) did not execute any simulation. Corrected actual wrapper run above is terminal.
