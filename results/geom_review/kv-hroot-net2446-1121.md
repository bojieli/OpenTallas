# KV-D26 hroot failed route review

I viewed the exact guide and PG geometry from the retained pre-TT global-route ODB. The failed net is the buffer on input i_kvs_ctl_o_hroot_Q[576] entering four writer-ring gates. The driver and sinks are within 31 µm, and the worker box contains no hard macro. The M8 to M7/M6 transition guide at x 1870.170–1870.740 µm overlaps the VSS and VDD M7 stripes. Track centers in that guide have no legal M7 clearance after the stripe shadows. Nearby M8 OBS rows do not intersect this transition’s y window.

Verdict FAIL for the D26 routed geometry. A D27 or later revision needs to steer GRT to a legal guide transition and be reviewed before detail route.

Picture: hroot-net2446-1121.png.
