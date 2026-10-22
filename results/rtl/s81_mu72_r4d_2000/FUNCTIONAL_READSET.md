# Functional regional source readset

Use functional_sources.txt at exact source ref b361a14e6. functional_readset.json records all 32 file Git blobs and SHA256 hashes plus the static module graph. It contains the real regional/r3r/r4l LEP implementation, actual LEP core, reset and landing helpers, lane transport and six functional SRAM models. No assembly stand-ins, blackbox declarations or numerical stub definitions are imported. Conditional inactive branches are conservatively retained.

The sole external boundary is the existing real ot_s81sl_slice_c1x_k8_cap5r_lp instance u_sl. Keep that baseline wrapper and its complete existing functional engine dependency closure. This readset is the regional parent delta plus its functional dependencies; it is not a replacement for the whole numerical engine readset. The combined HBC top must come from the lead's separately named source revision and replace this list's original r4d top path when composing.

All ten W lane source blobs at b361a14e6 match the original CLOSED c8c2b1bfe source packet now published in main a19178766. Reuse that CLOSED child only at CORE_CRED=12. The regional endpoint remains a distinct unqualified child. Static source resolution does not establish numerical whole-top or physical closure.
