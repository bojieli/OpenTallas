Final CE source engine-local gate activity, same native workload and idle epochs:
59839 cycles; native=split21279 enabled edges; idle30814 cycles and154 enabled
edges;3387 events each/zero differences. Monitor reads actual u_tree.local_en.
Additional idle clock-pin estimate, NOT physical power: up to475 head station
bits clock each root edge instead of only native enabled edges, yielding
475*(30814-154)=14563500 extra rising edges. v1 CTS duplicate predictor has628
FF plus2 SRAM clocks, yielding19351192 extra FF and61628 SRAM clock-pin edges.
Combined estimated extra FF clock-pin edges33914692, excluding clock-buffer
capacitance and SRAM activity/leakage. Conservative synthesis cost+915FF and
2 extra program SRAMs26639um2. Actual physical total power remains unmeasured.
