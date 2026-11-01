# ROOT station reach repair, 2026-11-01

VIEWED root_forward.png and root_mirror.png. Eight ROOT slots (L4/L4m, L9/L9m, L63/L63m, L114/L114m) now have explicit per-bit legal-street station sites, with all original stage counts and data/valid bit indices preserved. Added cycles: zero. The worst actual bit hop falls from1400.007um to396.1um; every selected hop is below403um (405um policy plus geometric reserve). No arithmetic, pin window, core outline/origin, or clock/reset interface changes.

Geometry findings: wide bundles use explicit 0.0458um/bit corridor lanes, stages follow short neighbour hops, and legal rows avoid all hard-core footprints plus1.08um keepoff. Existing macro streets stay open. L9/L63 long north-going routes use the large macro-free upper corridor; dense lower L4 stages remain in existing streets. No new macro walls or pin-face changes.

Verdict: PASS for these station locations; COMPOSE READY, not a routed sign-off. Parent must rebuild/check clock-tap load assignment (some stages exceed1500bits) on the joint event before route, and obtain actual GRT0/STA. No route or SIGNED claim is made. The earlier generic turn-diamond geometry is diagnostic reach-only and is not selected.
