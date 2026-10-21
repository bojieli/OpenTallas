# Preserved pslice lp13 active-gate CTS checkpoint

Consumed source1da987d16e17f072c92766446244fb870a70ae95, original localclients1118691/1118692 remain active; EP9 ref_gate lp13a-20261021-072655/lp13b-20261021-072658. Both64GiB originaljobs preserved; no relaunch, no newgate, no oldWT git/write. GRT congestion extraiterations still active atcollection15:33; no final gate_result exists yet.

Actual root_child_flops from consumed helper uses each hard child's consumed insertion.json boundary min/max plus measured pin arrival, compared with linked soft ALL-register range. The ck.json child_flop aggregates use mean references and alone understate parent boundary spread. Frozen3view insertion records and rawck.json retained. clock_model.json records both raw aggregates and actualchild/soft ranges. Source-bound pair reconstruction matches actual reported failure to0.1ps rounding: a ck_h87.8TT/83.5FF, c2~94.1TT/63.8FF,c3~88.3TT; b c2~177.0TT/133.5FF,c3~185.7TT/136.4FF. No new80rule or source/physicalalias.

Current geometry/clock candidate remains FAILED_CLOCK and GRT_PENDING. Any successor must model actual hard-boundary ranges+soft clusters with physical clock placement/landings, retain functional schedule and immutableexistingproof, and use newsource/geometry only after actualcause. No lp14 implementation/gate launched.
