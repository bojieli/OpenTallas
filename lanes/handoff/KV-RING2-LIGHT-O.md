# KV-RING2-LIGHT-O handoff (2026-11-18)

Successor of KV-RING2-LIGHT (Fable, weekly limit). Owner KV-HG-OPUS. DONE.

- Code: RING-LITE-1 on main via merge 8d32316ad46 (claude/ring-light-narrow-1118 @d22b3cd0d31). Type key
  clock.landing_ring_lite = {"max_width": 4, "monitors": 1}; absent = byte-identical RTL. Existing key
  clock.landing_ring_narrow (R1-NARROW) unchanged.
- Re-verified on the rebased code (main e1ce3e0b234 + branch): formal A 9/9 LITE0 == main, B 9/9 LITE1 q == LITE0 q,
  9/9 mutants caught; lock-step 11/11 phases x 196 forms 0 mismatches, both negative controls caught; pytest of the
  landing-ring, schema and adopted-plan tests pass; schema JSON regenerates identical. Bench: epyc7
  /srv/opentallas-scratch2/claude/kv-ring2-light/bench/{eq,run}.out.
- D22 mirror strict binds (gate_a lite on hub_C, gate_b hub_C lite+narrow, gate_c all 5 hubs lite+narrow): all RC 0,
  160 / 56 / 2545 / 429530 bits, 0 errors, LATCHECK 2404/2404, R8 recheck 0 changed and same findings as reference;
  bus_groups / bind_latency / lane_asbuilt / strap audits byte-identical to D22. Only the keyed parts' RTL differs.
- hub_C ring cells (flat ASAP7 map): D22 357,873 -> lite 246,518 -> lite+narrow 238,112 (-119,761, -33%).
  Other hubs lite+narrow: Ei 228,924->203,099, Eo 180,150->165,913, Wi 217,271->214,025, Wo 180,150->166,270.
- Keys for D24: ~/coord/lanes/handoff/KV-RING2-LIGHT-keys-d24.json (hub_C first; other hubs optional, proven in gate_c).
- Not done here: pv types (lite candidates per census: pv_v12 58, v7 57, v6 52 ...) were not bound with the key.
