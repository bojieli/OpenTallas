# Native versus KIT topology ownership

Native freshness now uses the actual asbuilt opt-ins. `native_contract(raw, asbuilt=None, plan_path=None)` includes OUT station rows only when internal_stations_types (including existing collector lineage rules) selects that type, reusing native_istations.source_entries. IN/core stations and other OUT rows remain fully represented by contract(raw) for KIT application/census, without falsely claiming native emission.

The native contract also seals count_straps/id_straps ABI, actual clock_landing_table content, reset/clock context, and transport pricing. A PADW or clock-table-content change therefore cannot reuse an old native origin. Successful binding snapshots this native contract before working-data mutation. Fresh-driver comparison uses native ownership; posthook preparation/census remains complete.

The small probe exercises KIT-only changes, selected native OUT changes, IN ownership, count-strap width, transport-price and actual sidecar content mutations. All controls behave as expected. No RTL or physical jobs changed.

This does not invent a receipt for an unrecorded or globally failing bind. HBM owns the separately approved LOCAL component-proof API, retaining its unrelated global failure. That proof must use this helper and be verified explicitly by its consumers.
