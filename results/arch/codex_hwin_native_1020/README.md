# HWIN terminal gate pickup / native census 2026-10-20

c21g gate2 WARN (23:35 Oct19), GRT overflow0 but grt rc2; TT placement reg->reg -107.4ps at event count_r. c21h WARN (00:30 Oct20), GRT overflow0 grt rc0; TT placement reg->reg -31.7ps at write_slot[5].copy[1].we_r. Pin-flop spreads g54.7/54.3, h52.6/51.7 ps. These are pathfinding gates, not closed views. No submit/bind.

Both actual h PNGs viewed:84 SRAMs on43.2 lattice, a single full-width central standard-cell band; measured band54.59%, outside approved area0; outline561.6x388.8 aspect1.44; fill19% ratified lattice/channel exception. Geometry cannot waive the new native census.

Binding23:45 pre-gate census applied to exact h mapped1_2_yosys.v using the current textbook parser/flatten/BUF+INV-transparent fanout semantics (tool/netlist hashes in JSON). 46,149 nonclock nonBUF/TIE/physical roots,58 roots above32, maximum126:39 FF and19 combinational drivers; no reset-labelled over32. Largest16 select cones119..126; shared event0 payload wdata31bits each33; lw bits up to84, gn34/33; due42/48. Every root is recorded; over32 entries include source inputs and sink examples. Unknown macro directions inferred by textbook algorithm; placed native pin/reach/PG audits remain separate obligations. No census PASS claimed.

Structural successor must preserve per8-bit current_hit logic (module keep in SYNTH_KEEP_MODULES), per-event kept wdata, split lw/gn consumer domains, and four due copies before synthesis/census. COUNT_STEP_SPLIT-only c21i was prepared before final h result and is insufficient to meet this audit. Preserve it as untested scratch, no layout gate.

Script invocation: python3 mapped_census.py --tool textbook_lint.py --netlist 1_2_yosys.v --top TOP [--dump fp_dump.json] --out census.json. This does not establish <=405um reach, registered pin placement, SRAM storage semantics, or functional tie intent. These require their own native/source evidence.

## Actual saved-GRT native endpoint check

Read-only OpenROAD Python extraction reuses extract.py from15729fb15 with paths/output changed only; input ODB mounted read-only. Exact ODB SHA d2e4d2ea7d5f5a0d4be43463409342c6d42ac66ce3655122d938e72f9ae9da87. Native54,591 root pins,58 over32 (agrees mapped);150 nonclock roots/549 individual endpoint pairs exceed405um, worst662.5um shared wdata. Config relay0 mw_r reaches556um, global limit_input payload549um; source geometry estimates in inherited README were insufficient. Boundary firstnonBUF/INV inventory: zero input bits with nonFF first sinks, zero outputs without FF root (clock excluded, reset included).84 real SRAMs. No functional tie intent, fullstage path reach or native PG qualification inferred. Compressed allroots and boundary/reach examples are lossless evidence.

Native-safe j R1 source fixes kept copies/fanout to10 over32, but physical placement constraints/landed distribution still required for remaining long controller wires even if R2 census clears. No gate or submit authorized by this packet alone.
