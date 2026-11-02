# QC L1 final data-stage load isolation — pre-placement review

Verdict: PASS-COND for PLACE-only diagnostic. No GRT or timing release yet.

Personally viewed `/home/ubuntu/.claude/jobs/b7f906df/tmp/geom107/l1c/auto_geom.png` and read the actual `postcts_gate_TT.log` lines 130–192 at intel2 `/srv/opentallas-scratch2/claude/codex-qc-su/l1_data_coupon_place1131`. Baseline TT setup fails −11.76 ps. The final XNOR2x2 `_279616_` drives 10.48 fF with 47.72 ps output slew and 52.95 ps cell delay; the last net adds 10.27 ps to `u_u_exp1.u_exp.nint[6]`.

Proposed one BUFx6f data buffer near (106.704,190) isolates the XNOR at (106.704,199.800) from the approximately 99 um final leg to capture FF (106.272,100.980). Both new legs are under 405 um, the x106 column is clear of the two central SRAM footprints, and no clock/FF/port or latency change is proposed. This directly addresses the final-stage load rather than changing a clock budget.

Conditions: actual candidate must legalize on rows with no overlaps, preserve all clock and sequential/pin geometry, show acceptable pin/r2r metrics and receive a personally viewed actual-candidate review before incremental GRT. Buffer delay versus XNOR load savings must be measured; this pre-placement review claims no timing gain.
