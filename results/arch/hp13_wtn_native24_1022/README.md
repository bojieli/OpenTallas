# HP13 F16 witness native structural fanout repair

The complete composed HP13 parent failed the native census before placement: MAIN 12 violating roots, ALT 10, maximum118 dynamic loads. The source witness arbitration, pending selectors and state logic were previously soft inside an otherwise native bounded parent. Pending-user copies alone do not repair the other overloaded roots.

This candidate expands the exact frozen F16 wrapper/controller using the existing source constructor with cap24, kept combinational cones and same-edge FF copies. Original24978 cells become25313 in two passes, adding335 cells and no stages. All28 source lockstep stimuli and authentication BEGIN withdrawal pass on Verilator5.050. F16 protection and INIT_U0 remain enabled. Generated helper names have the mechanical prefix qfd_wtnmath_ to avoid collisions.

The parent reset witness input moves from leaf n96145 (native33) to spare n96154. Both leaf Q signals have exactly the same clock and same-age D; their two upstream D producers have identical C,D. SOURCE.json records that proof. No reset stage is added or removed.

Two new kits qfd_hp13_cpub39_wtn24_main/alt retain the original outlines,19 genuine memory macros, source interfaces, clocks and uncertainties. Actual mapped-native and layout results are pending. These candidates are not qualified or adopted by a die yet. Originals remain unchanged.

Safe-design checklist: pins/source ages preserved; reach/clock/area require actual gate; no new storage; kept native copies target fanout<=32 with internal cap24; SRAM/ROM unchanged; no schedule latency change. Source provenance and exact lockstep evidence are attached. Full native/layout closure remains required.

Reproduction: run the frozen witness/wrapper through wtn.ys using Yosys0.68, then construct.py with the pinned constructor. Mechanical helper prefix change is recorded in SOURCE.json. bench.sh compares the resulting native face against the exact source SAFE_PHYS controller over the committed28 stimuli and BEGIN. All heavy work was admitted through ot-run.
