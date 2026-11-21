# COL h10 relay placement

The two private lever-1 pilots used the same fixed endpoints for the 15 station groups that failed relay midpoint coverage. The baseline touched 106 of 121 groups. The RDX variant touched 127 of 142. At a 405 µm hop budget, exact fixed endpoint centroids require the following additional stages before allowance for pin spread or macro detours.

| Chain | Current stages | Span (µm) | Added stages by centroid |
| --- | ---: | ---: | ---: |
| lpl_11_r.u_y_q | 1 | 1446.880 | 2 |
| lpl_12_r.u_y_q | 1 | 1160.309 | 1 |
| es_p0 | 2 | 1219.060 | 1 |
| rr_1 | 1 | 1062.636 | 1 |
| so_1 | 1 | 861.787 | 1 |
| so_3 | 1 | 919.963 | 1 |
| xo0 | 2 | 1529.364 | 1 |
| xo1 | 2 | 1597.821 | 1 |
| xo2 | 2 | 1666.181 | 2 |
| xo3 | 2 | 1734.551 | 2 |

For xo1, the compact group shares stages across a 1649.970 µm endpoint envelope. Four 405 µm legs provide only 1620 µm. Allow for an additional stage or a split bank before claiming 405 µm for the whole group. The measured endpoint envelopes for xo2 and xo3 are 1718.550 and 1786.860 µm.

The es_p0 chain connects two u_bn0.d_st pins to u_t0.e0. The maximum pin envelope is 1219.350 µm at the frozen placements. A diagnostic candidate shifts u_t0 left 17.28 µm to (1270.188, 293.580) and seats the two existing stages at (598.968, 456.300) and (1002.888, 456.300), with 10 µm margin outside the standard macro halo. Predicted centroid hops are 395.694, 403.920 and 402.167 µm. The t0 move is specific to es_p0 and needs review of t0's other incident paths and actual physical integration.

## Adjacent fitted stations

The FIT branch tests a candidate center against its nominal neighboring stage centers. The actual adjacent stages can choose different off-line points. On exact 3_2 replay, 7 of 59 chains with every stage reported fitted have actual center-to-center hops above 405 µm, up to 522.725 µm. A joint search on the fixed macro and endpoint geometry found candidates for all seven chains with the original depth and 20 µm channel margin. Worst predicted centroid hop is 403.812 µm. The plot shows these seats against the actual macro rectangles and was visually inspected. Stage choices remain a geometry diagnostic until prepared in a new kit and reviewed with its actual placed, routed, and timed results.

| Chain head | Original maximum hop (µm) | Candidate maximum (µm) |
| --- | ---: | ---: |
| u_y_xb_1_bs0_0 | 522.725 | 397.440 |
| u_y_xa_1_bs0_0 | 521.185 | 397.440 |
| u_y_cc_1_s0_0 | 496.156 | 397.440 |
| u_y_rt_2a_0 | 464.993 | 403.189 |
| u_y_rt_8b_0 | 457.399 | 403.812 |
| u_y_rt_6b_0 | 426.877 | 403.002 |
| u_y_rt_6a_0 | 417.594 | 397.440 |

Artifacts on intel1 are under /srv/opentallas-scratch2/claude/fam-s81-col/relay-mid-diagnosis-indexed-1121. The endpoint rows are produced by endpoints.py from probe.log. The adjacent-leg audit is station_leg_audit.py. joint.log contains the full trial site table and relay-joint-fit.png is the reviewed overlay. The exact shifted and joint placement replays use sibling directories relay-mid-es-p0-1121 and relay-mid-joint-actual-1121. The inherited kits and candidates remain independent.
