# KV/system v1.2 candidate timing collection

Both source-027ac5870 cases passed placement legality and VDD/VSS PDN checks, then reached zero GRT overflow. STA applied phi-R files at every corner (OT_COMPENSATED_CLOCK TT/FF/SS, 8,947 sinks in kvs3); the old STATUS label “ideal (no clock plan)” was inaccurate because the external OT_STA_CLOCKS path overrides that fallback. The status-report fix is on main.

| Case | TT setup ps | FF hold ps | SS setup ps (sensitivity) | TT relay-to-relay violations | TT real-to-real / FF real-to-real ps |
|---|---:|---:|---:|---:|---:|
| kvs3 | -258.70 | -56.74 | -517.78 | 372 | +170.53 / +125.68 |
| kvs3L | -269.27 | -56.74 | -527.72 | 1 | +170.53 / +125.67 |

The worst setup is the closed CDC write-leaf co pin launching into a landing frame: 26,975 / 26,036 violators, worst -258.70 / -269.27 ps. The ongoing native pin-register repair remains rank 1. Real-to-relay write-leaf launch paths have 72 / 74 violations at -105.74 ps. Real-to-real paths have no TT/FF violations.

The N-half lane option reduces relay-to-relay TT violations from 372 to one: KV posted-write worst -155.93 -> -14.59 ps; read-response worst -89.69 -> +0.32 ps; embedding word worst -69.05 -> +49.03 ps. It remains a timing candidate, not an accepted-cost variant: 22 bus depths change, with up to +18 request stages and +16 response stages (relay_depth_changes.json). A source-bound protocol and end-to-end cost measurement must assess these changes before adoption; default remains unchanged.

All FF failures are on assumed frame/relay/PHY paths. The worst -56.74 ps is frame-to-frame/PHY; frame-to-relay and relay-to-frame also fail, and relay-to-relay fails at -33.94 / -34.96 ps. These are explicit negative diagnostic results, not signoff: only three real master views are bound, and the die still has placeholder frames. The seven direction-model defects found by the real relay-end check also need fresh generated relay RTL. No physical route DB or SPEF is archived in this collection; source notes, clock/view provenance, endpoint cause tables and depth comparisons are retained.
