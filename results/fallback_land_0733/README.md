# Bottom-up landed-partition fallback analysis

Analysis only; no main rule, plan, RTL, calendar or physical build changes. Each source is identified in its JSON: QC40493490d current owned UNFROZEN candidate, S81 B2d3@12a0c04f0 reviewed/applied event, HEAD mainb7232fde4 held baseline (pendingHEAD8 not adopted), KV B44 logical cland_r6 candidate (physicalr9 separate), HBM B1interfaces7aaba4 candidate. None is a final adopted clock plan.

This census counts every explicit source-to-destination **plan partition port** once, with its declared width, including abutted/zero-road seams. All endpoints resolve. It is nominal seam capacity, not an assertion that every bit is occupied by native data, and not an enumeration of undeclared hard-core cuts within partition types. Clock/reset/PG networks are separate and are not landed. Gross +2/+3 stage scenarios allocate two/three FF bit-sites per eligible data/control bit crossing, using the canonical1.404x0.27um legal FF envelope. These are gross placement envelopes, not synthesized cell area or net added area; source-fanout sharing and existing bank reuse are not deducted.

| Die | Partitions | Explicit seam ports | Nominal bit crossings | +2 gross envelope mm² | +3 gross envelope mm² |
|---|---:|---:|---:|---:|---:|
| QC | 377 | 2993 | 1,277,486 | 0.9685 | 1.4528 |
| S81 | 398 | 2368 | 1,122,900 | 0.8513 | 1.2770 |
| HEAD | 326 | 428 | 212,622 | 0.1612 | 0.2418 |
| KV | 160 | 3915 | 599,111 | 0.4542 | 0.6813 |
| HBM | 88 | 865 | 585,088 | 0.4436 | 0.6654 |

KV demonstrates the domain distinction: actual B44 native bind reports2545 occupied crossing buses/430554 bits, n_errors0/unmapped0, versus3915 nominal plan ports/599111 bit slots. The binder packs actual leaf sources and forwarders into reserved ports; dead/unbound/overreserved capacity must not become token cost. The physicalr9 road-repair candidate is separate from this logical B44 census.

The minimum actual QC ledger joins all65 known landing cuts both to their current88-type collector local_sources and to76 nativev7 consumer rows. `qc_minimum_edge_ledger.json` records the actual identities. Its priced example is physicalcut `sl_E3_fe__l9_eo_l9_wi__3`, a514-bit landing at `sl_E2_fe/u_cland_l9_eo_l9_wi_i`; the ultimate native consumer is `dvs_E2.u_core.u_sub.u_fdn.l9_i[0:513]` from `dvs_E3.u_core.u_sub.u_fup.l9_o[0:513]`, as-built2/landed16 stages. One physical cut on this seven-port lane gains2 or3 stages; the lane is not multiplied by its bit width or total station count.

The existing prepared nativev7 composer (archive94cd97b7a plus exact1121cb654 overlay, canonicalrederive/compose63f4e17f63) prices that single edge: baseline296341cycles/token, +2→296413 (+72),4050.0tok/s; +3→296449 (+108),4049.5tok/s. This is conditional nativev7 semantic pricing with current88 unchanged bus/latency contracts; it is not all-seam fallback cost, release adoption or an implemented R8 phase plan. Raw edges/ages, exact changed member, composer results and source runner are retained. Fleet intel2 unitoth-ubuntu-185348-1793034663 completed.

Every other all-seam critical-token row remains UNPRICED until its native occupied source/consumer membership, actual traversed seams and programme DAG are joined. Work is no longer blocked on a global map: the minimum QC join and compiler exercise are concrete. Further QC expansion must run CB16 DAG/R8 phase propagation rather than replacing it with geometric region sums. KV must use actual B44 compiler depth_map/attention calendar; S81/HEAD need the current bound operation graph; HBM accepted B1 operation→record/lane mapping is absent and already logged OWNER?. Existing accepted-cost ledger unit/design5%/15% gates apply once actual scenarios are priced.

The +2/+3 gross stage envelopes above describe alternative simple pipeline storage only. They are **not** the actual `ot_dp_clk_landing` hardware area: DEPTH4+RDREG1 uses5 live FF/bit plus epoch/control/padding. `qc_actual_ring_inventory.json` separately sums the current known65-cut candidate’s actual-width flattened canonical ring FF inventory and conservative logical cell bounds, including monitor/reset/collector copies. Its mapped area remains UNMAPPED. No all-seam mesochronous-ring area is claimed from the2/3-stage table.
