# SYSFACE mapped/GRT native review — 10-20 takeover

Critical qfd_sys_face MU1/MU_HEAD1 gate remains historical PASS at source d9fcf82a47238ba1b949fb30deed2d4928adcd71, evidence branch77454180d. Actual floorplan/density inspected by coordinator: one lattice ROM, continuous rows, clock beside register mass, pin-bound24%fill, TT/FF39.5/40.4ps and GRT0. These geometric and clock passes do not qualify native fanout.

Read-only original 1_synth and5_1_grt ODB audits use actual pinned Liberty functions to follow transparent buffers/inverters and count data terminals; clock:true/nativeCLOCK trees are excluded from data. Both original ODBs remained mounted read-only.

Mapped FAIL:580 drivers above32 (includes constant tieHI2153); real cal_t.ptr[1] fanout2043, cal_l.ptr[1]1028, cal_t.ptr[0]1025. GRT FAIL:561 above32, max2043, no driver reach above405um (maximum318.618um). GRT18380 nativePG unbound terminals recorded as original intermediate state. All raw endpoints, role inventory, sourceODBsha and audit implementation retained. This is a structural RTL blocker; no REVIEW/route submission approved. No constant exclusion can hide actual calendar pointer failures.

Next: opt-in fanout-safe source successor, preserve old defaults and all failure evidence; actual mapped census<=32 and every storage allocation>2kb SRAM before new gate. Calendar lockstep must retain prefetch/seg1/config/start/halt, dt=1 and burst/event/fault semantics. Root owns tool merges.
