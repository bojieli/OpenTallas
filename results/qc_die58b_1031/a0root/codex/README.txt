CODEX A0 continuation 2026-11-01.
All physical sources are copied into /srv/opentallas-scratch2/claude/codex-qca0 (intel2); original lanes untouched.
Review images nk/auto_geom.png and nl/auto_geom.png viewed; CTS diagnostics allowed, DRT held for GRT50=0 (GEOM-99).
Root cause of inherited zl_test.tcl failure: a flattened cell name includes slash hierarchy; splitting at the FIRST slash returns an absent ancestor rather than the endpoint cell. Resolve the cell from the full D pin object instead.
The two diagnostic variants preserve RTL, period, all IO delays and uncertainties. Z0 pads only measured zero-logic shift-chain captures. Z1 additionally tries moving the existing gated delay chain before the ICG so ENA can be captured later without changing body sink latency.
No SIGNED claim. Probe runner memory16GB/cpu4; NL GRT50 runner24GB/cpu2. Logs live under own scratch only until results collected.
NL B3 inherited active route had congestion_iterations30; own GRT-only run uses exact4_cts, includes clock, congestion_iterations50, skips repair and never runs DRT.
