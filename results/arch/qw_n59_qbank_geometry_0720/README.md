# Actual qbank9 geometry: HARD HOLD

This is the immutable completed `3_5_place_dp.odb` of the original qbank9 gate, not a final-route claim. SHA256 `16cd242412a736c077e2b8baa141eceb8bd8580bd25fcfc1b9500a1f2a9ded26`. Original progressing jobs and all earlier failures remain untouched.

The actual eight 167.4 by 76.14 um macros have six vertical channels of 0.036 um, below the mandatory 20 um minimum. Six origins are not literal multiples of 43.2 um. `at_exact` does not waive either rule. The legacy macro has 775/774 E/W functional-and-clock pins, giving 10.1786/10.1655 pins per um, above 6. A native32 PASS cannot qualify this placement. No exact submission or parent adoption is authorized from these kits.

`geometry.py` reads actual OpenDB pins and shapes; `geometry.json` contains all macro/pin/port evidence, and the raw fleet execution log is retained. The gate may finish for diagnostic evidence, but CTS knob changes cannot cure these source physical constraints.

A separate proposal evaluates the existing canonical `64x512_m1_r2c2_p192_bs` analytical view, with address MSB zero and repair disabled per provider policy. This is MODEL ONLY, no view generation/adoption. Full 32 KiB physical capacity is charged against 16 KiB logical use. Full combinational stage reach, arbitrary-state source equivalence, pipeline ages, parent fit, clocks, PG, timing and detailed route remain open.
