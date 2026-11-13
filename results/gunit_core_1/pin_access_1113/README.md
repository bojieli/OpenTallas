GUNIT parent macro pin-access fix

The frozen gunit__t1 attempt14 failed DRT-0073 on bf sv_lo[175]. The pin is on the M5 track and its S boundary is clear of adjacent macros. The plan abstract blankets M6 above the small edge pin. An exact bloat-0 export from the same routed gf3 core ODB has no M6 conductor at that failed access site.

The candidate refines M6 obstructions in 1um windows above all1903 matching tiny M5 N/S boundary pins. It keeps the plan-contract LEF header, ports, PG pins, lower-layer obstructions and all geometry outside those windows byte-identical. It restores8973 rectangles of actual M6 metal inside the windows. The existing abstract_detail checker accepts the refinement; full signal-pin geometry also matches the exact core export. No real metal is removed.

Measured pilot: read the actual attempt14 CTS ODB and swap only the four bf masters to that candidate (all instance coordinates, interface types and nets mechanically equal). OpenROAD pin_access with M2-M7 completes:261184 instances scanned,24534 pins and57885 groups; standard-cell pins without access0 and macro pins without access0. This is pin-access evidence only: detailed route, TT/FF timing and signoff are NOT RUN on the refined parent. Do not count it as SIGNED.

Artifacts remain on epyc8 under /srv/opentallas-scratch2/claude/gunit-core-1/detail_gf3. The exact core export is gf3_detail_b0.lef, generated from die-s81-85/bfpad/kit_gf3ds60/run/results/asap7/kl_dsdv_gunit_l1f_bf_gf3/base/6_final.odb. make_m5_edge_windows.py replays from an original plan-contract --base and same-ODB --detail, producing --out and --receipt; it imports the repository abstract_detail APIs. The candidate is private, not adopted by the wave or a plan event.
