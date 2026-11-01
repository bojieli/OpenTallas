CODEX A0 continuation 2026-11-01.
All physical sources are copied into /srv/opentallas-scratch2/claude/codex-qca0 (intel2); original lanes untouched.
Review images nk/auto_geom.png and nl/auto_geom.png viewed; CTS diagnostics allowed, DRT held for GRT50=0 (GEOM-99).
Root cause of inherited zl_test.tcl failure: a flattened cell name includes slash hierarchy; splitting at the FIRST slash returns an absent ancestor rather than the endpoint cell. Resolve the cell from the full D pin object instead.
The two diagnostic variants preserve RTL, period, all IO delays and uncertainties. Z0 pads only measured zero-logic shift-chain captures. Z1 additionally tries moving the existing gated delay chain before the ICG so ENA can be captured later without changing body sink latency.
No SIGNED claim. Probe runner memory16GB/cpu4; NL GRT50 runner24GB/cpu2. Logs live under own scratch only until results collected.
NL B3 inherited active route had congestion_iterations30; own GRT-only run uses exact4_cts, includes clock, congestion_iterations50, skips repair and never runs DRT.

Smallest exactness/mutant receipt: qualified_receipt.json, actual ot-run epyc2 unit oth-ubuntu-1316565-1793541871 exit0. 12k cycles; mut0 qualified errors0, mut12 errors4156, mut2 errors9837. Upstream bench compares valid/fault each cycle and data on valid; raw invalid data differs as allowed by existing contract. Initial harness wrongly required nonzero exit for the mutant even though upstream bench uses $finish on both outcomes; first harness failure retained. Corrected harness accepts only explicit FAIL + positive qualified_errors for each mutant.

Second structural trial preserves gating: existing ICG1 EREG1 option, gate/en_q balanced to (228.972,730.93)/(231,730.93). Raw clock152.05um; direct ENA face flops max389.022um. Initial y830 idea was rejected BEFORE launch because go leg exceeded405um; y740 refined analytically to730.93 to balance go and far-node legs with16um reach margin. Child LEF OBS endM5, narrow ENA can cross onM6/M7. Full postplace reach, CTS and GRT50 remain gates, no DRT/adoption yet.
