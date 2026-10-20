# CB16 fullk terminal failure

Source4ccb8574e, README06a83f0d5; remoteep9 qfd_c_b16_fullk-20261020-030948. Actual cts.log fails ODB-0359 changing FIRM soft-ring leaf origin in global placement. This is explicit hook incompatibility, not a timing result. GPL must own soft masses inside legal fenced bays; fixed macro masters remain fixed. No measured CTS/FF/GRT qualifier. Original floorplan PNG viewed:4columnsx4rows of A0 parents, stations in corridors, original outline3067.2x5486.4/lattice retained. Safe checklist inherited source declarations; item3 census max31 PASS, item6 placement FAIL, item7 unavailable, other items require exact successor review. No REVIEW/submission.

fill: parent kit without std_area_um2: fill not computed at gen (the gate measures it)
native_census: mapped dynamic load limit32 PASS; max=31
floorplan.pin_geometry: actual pin geometry PASS: {'signal_clock_pins': 5717, 'pin_rectangles': 5717, 'pin_track_checked': 5717, 'pin_track_inaccessible': 0, 'pin_rectangles_outside': 0, 'missing_geometry': 0}; dump SHA256 d23b2d9fd73874478749437dcd0dbef5fc1a151b3cce775cc0d3e55d4d54c406
util: synthesized std area 110206 um2 + macros 9099488 in core 16790953: util 2% (std-cell density 1.5% of placeable 7200831 um2; total fill 54.8%)
textbook: WARN qfd_c_b16_fullk cells 747,212 flops 206,324 depth 158.4 ps util 0.5485 reach 0.0 um (80.7 s)
cts_run: placement / CTS of the kit failed: [ERROR ODB-0359] Attempt to change the origin of FIRM instance u_fab.u_land_pad_2_1b_0_w.g_grp\[0\].g_sub\[0\].g_s\[0\].b\[0\]$_DFFE_PP_
clock_rule: root port:ck_c2r2: 20,966 sinks on the largest root; no measured clock tree (no --cts gate evidence); WARN: 20,966 sinks on one clock root > 15,000 (guidance); no measured spread: run the --cts gate
fill: fill 55% = (hard macros 9099487.6 + synthesized std cells 109524.2) / outline 16827886.1 um2; pin demand per face: S 3469 pins over 2868.1/3067.2 um (94%), N 2941 pins over 2868.1/3067.2 um (94%), W 288 pins over 2410.6/5486.4 um (44%), E 288 pins over 2410.6/5486.4 um (44%)
