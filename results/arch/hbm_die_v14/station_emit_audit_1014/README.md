Actual station emission audit, 2026-10-14

Source inputs are the completed production glue25f pin files and forwarded map on ot-epyc1tb, under /srv/opentallas-scratch/claude/hbmdie-v13/glue25f. The corrected full model has 63,400 instances and passed the previously terminal forwarded-layout consistency check. Full generation then failed at hfd_cdist_r45.t0[42].

The audit invokes both actual positive and mutant build paths for all 1,473 station masters. Before: 1,363 pass / 110 fail. After the multi-slice launch fix: 1,371 pass / 102 fail. Eight actual 571-bit IDX-query launch masters now generate. Seven additional multi-slice cases advance to subsequent contract failures; they are still failures. All failure details are preserved, including unsupported non-a/b endpoint masters, one-sided forwarded layouts, conflicting relay directions and stale SM control widths/directions.

The actual hfd_stn_699 pin contract is checked in as the focused regression fixture. Its two real ot_hbm_stn_launch instances preserve every one of the 571 data bits over 4,096 cycles at period 833.333 ps; the generated data-swap mutant fails. This is behavioral transport evidence only, not routed timing or native parent qualification.

No failed emission is replaced with a pin-only shell, tieoff or guessed ABI. General port binding and physical gate remain blocked until the remaining source contracts are repaired. No route was launched.
