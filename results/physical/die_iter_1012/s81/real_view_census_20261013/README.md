# S81 source-pinned real-view census

Counts below come from the actual floorplan_placed.def component list and a_real/die.v. Both match exactly with zero master/name mismatches and no missing index rows. Source commits and SHA256 hashes of DEF, netlist, manifests and all bound LEF files are in each census JSON. The source snapshots are c3 f13695e45 and c5 2fa1d3e09.

| Run | Placed instances | Generated physical placeholders | Source macro abstracts | Interim timing | Closed-tag timing | Assembled-tag timing | Partitioned timing | Macro timing |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| c3 |56802 |42966 |13836 |42632 |1612 |1 |1 |12556 |
| c5 |57015 |43179 |13836 |42765 |1692 |1 |1 |12556 |

The13836 source abstracts comprise1280 routed Q-element outlines (interim timing),12547 configuration ROM macro abstracts and9 external PHY/link abstracts. Source abstracts are not proof of complete closure or qualification. Every closed-tag ETM instance still uses a generated elements.lef abstract. Consequently this census establishes zero die-placed logic instances bound to both a routed LEF and a closed-tag ETM; it makes no positive count of qualified closed elements.

C5 generated placeholders:29184 relays,2854 stations,3456 nodes,2560 qbanks,1792 configuration sequencers,512 BF blocks and2821 others. Complete per-master counts and library source hashes are in c5_census.json. The replacements JSON lists routed LEF candidates adjacent to pinned ETMs for26 of27 closed/assembled timing masters, with current generated dimensions and candidate dimensions. These candidates are not adopted or qualified; compatibility has not been checked.

## Requirements for the active v14 writer

1. Bind each die-placed logic instance to its exact routed LEF plus same-source TT/FF ETMs and clock insertion; stop generating substitute outlines, pins or obstructions for supposedly closed masters. Existing closed-tag CFIFO/station/end-point libraries do not make generated geometry real.
2. Supply the1280 Q elements' matching ETMs for the exact routed outline. Keep the512 BF placeholders separate; they are not counted as Q-element real geometry.
3. Harden replicated glue once per actual width/orientation/interface, then place its real views. Relay/station reach and FF minimum delay must be measured from the physical implementation. Synthetic hold offsets do not satisfy this requirement.
4. Replace slab proxies with actual die-placed tile inventories and layouts: HC upper/tail split and cth strips, SU SM/SW stops, VM, collective, service, MTP and their clocked seams. Preserve exact pin mappings and measured local roots.
5. Check real outline fit, overlaps, actual OBS/cut supply, scalar clock naming, all functional pins, native TT/FF timing, child_lint, bit-exact/mutant and production throughput before treating any indexed view as qualified. Record external/memory abstracts separately with their modelling limitations.
6. Use a strict view gate for final evidence: no generated physical placeholder, interim/partitioned timing or unverified synthetic delay may qualify die closure. A prototype run may continue for congestion analysis, visibly labelled as such. Do not restart c5 or duplicate its GRT to change this label.

All current c3/c5 GRT, IR and STA are prototype pathfinding evidence. Physical minimum-delay seams remain owed even after the ETM reference correction.
