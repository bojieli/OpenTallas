# stationfix_1111 (STATION-FIX-HBM, DIE-HBM-98, 11-11)

HBM plan event for the 12:00 combined HBM event (HBM-COMPOSE, tag hbm-cut-1111). COORD S7 class: station_lint
INVERTED on plan p11t 29333b2b, the same class as KV phyrev_1111.

- `event.py PLAN_IN PLAN_OUT [RECEIPT]`: on 13 entries keyed (type, bus, internal_stations index), swaps from_um and
  to_um and reverses regs_um. Same sites, same count, launch, capture and note: EQ by construction. Idempotent.
- Apply order: base 29333b2b, then VIS-TRIAGE-HBM NW_io form h (fb858a44), then this event.
- `tools/die_plan/native_istations.py` `face_first()` (same branch) is required with it. These 13 buses are native
  OUT buses (asbuilt `internal_stations_buses`). native_istations used to reverse every core-launched OUT entry; it
  now reverses only entries still written face first. The native source entries, the native_topology digest and the
  bound RTL stay byte-identical across the event, so no rebind is needed.
- NW_io L52_o (index 22 on 29333b2b) is not changed. It is the planner's face-first row form, which kit_istations
  reverses (KW-FIX-27) and merges into one chain, and the placed chain is monotone. Form h re-sites it, and lint shows 0 flags.
