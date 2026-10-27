Host delivered-reset source candidate, default off.

Exact selected observation ingress source is restored from the pinned r18h5 bundle at its main RTL path. Only reset selection changes: ingress retains TWO release edges; leaf2 and status join retain THREE. Assertion is now ordinary timed two/three edges in opt-in mode. DELIVERED_RESET0 preserves existing legacy/PHY CDC behavior. Join delivered mode requires existing RRELAY1 and rejects RRELAY0 instead of silently altering its latency. Data payload, control calendars, and host protocol are unchanged.

Small actual-module reset/control miter: ingress_obs + leaf2 NT20/NF32 + status_join_fa NT44/NF76/NH6/NA2/RRELAY1, random inputs and six reset/release rounds. All reset-region pins checked every settled model edge; every output compared outside the explicit assertion transient. PASS1165 checks/0. Independent early-release controls: ingress2→1 caught419 errors, region3→2 caught53 errors. No whole die/program simulation, P&R or timing run.

Source/profile closure lists both delivered helpers. Full-top wavefront and boot bindings remain MISSING; no emitter adoption or raw POR rewiring is included.
