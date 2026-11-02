# Corrected reset comparison using independent Plans

This supersedes the reset graph/count/proof claims in the original t18 c902 and cl911 af361 packets. The tap-coordinate fixes themselves remain unchanged, and FLOW's actual fresh-plan BIND is a separate native producer.

The original local comparison called reset_tree.for_type on one Plan, changed its clock coordinate, then called for_type again on that same Plan. Native RT caches `_reset_tree_cache` on the Plan, so the second result could be the old graph. The earlier cl911 miter therefore compared the old graph to itself; its mutant control did not establish equivalence of the actual proposed graph. Original inputs, logs and failed reasoning are retained, with superseding status links added to both READMEs.

compare_fresh.py constructs two independent Plan objects from separate deep-copied raw plans before either native RT call. Both are evaluated by the exact frozen SOURCE39 tool readset against the same complete current private plan; only the one selected coordinate differs.

Corrected results:

- slice_station__t18 stays153 relay FFs and43 named outputs, release8 clocks. Raw RTL differs in coordinate comments. Comment-stripped executable RTL is byte-identical, SHA2569b726dc2ad9d53b7d046d6f19d3225d3c31ab55a44cbe6e87a2ffcc94bf8fd8c. Its FF/clock/reset-data/cycle delta is zero.
- col_h10_r0_p1__t1__cl911743eb actually changes178→179 relay FFs,44 named outputs, release7 clocks. Executable RTL differs. Price +1 synchronous reset-control FF, +1 clock load and +1 reset-data input, no new asynchronous-reset load. The prior zero-FF/raw-identity claim is withdrawn.

The REAL cl911179-versus178 emitted native RTL now passed its own all44-output plus dedicated rst_o_0 lockstep and seven-edge oracle:212608 checks over4895 cycles, including cold/warm/short reset episodes and512 exhaustive nine-bit input words. The one-edge-short actual new tap28 mutant caused2312 mismatches. Normal Intel2-entry2GB/1T unit1406584-1793620790 rc0. USED testbench [43:0] and loop i<44 establish44 outputs; inherited cosmetic log text says all45_plus_dedicatedout and is preserved/disclosed. Boot and mission-cycle deltas remain zero because every observed output retains its exact release behavior.

Source-clock budget checks for this real current plan are independently covered by FLOW's complete ALL168 native census, not the earlier cached candidate model. FLOW owns the sole current BIND successor including its independently checked t49 fix60f4b5128. This correction changes no selected coordinates and starts no additional BIND/ELAB/P&R job. Canonical186 physical planning used a separate fresh Plan against saved185 input and is unaffected by this cache error; that disabled event remains distinct from source-only BIND.

Combined source-only price from original SOURCE39: cl574184→185 plus cl911178→179 adds two synchronous control FFs total; t18 and t49 add none. The separately disabled canonical cl574186 replan adds one more FF beyond that source-only set. Source adoption requires the corrected price/proof join; physical halo/cohort checks remain explicit.
