# CTL dispatch structural replacement

The failed c32g attempt boxed an output-pin strip during GRT. Its target decode, accept checks and held payload mux formed the setup path. This opt-in version adds a register between the accepted word and held payload selection. MU GAP order validation retains its original edge; the complete layer write interface stages after its GAP mux. The compiler-visible boot write interface costs one additional edge, with zero production programme edges. Existing variants remain DSTG=0.

Safe design review before the gate:
1. Pins: input/output flow pin registers retained; W/E outline capacity is <=3.1 pins/um if fully spread; i/j automatic placement remains unverified. Explicit full-face k/l successors are separate kits. Native tied-port check is a prerequisite of the gate.
2. Reach: outline enlarged; flow pin-register relocation and relay stages retained. Actual reach verdict pending; no reach waiver.
3. Fanout: kept accepted-target stage; native census max32 prerequisite of the gate. Any violation gets RTL kept copies before layout.
4. Depth: accept and held mux are separate stages. Actual mapped depth/setup pending.
5. Storage: existing six SRAMs retained; new fixed pipeline holds at most255 bits, no indexed flop memory.
6. Floorplan: separated SRAMs on43.2um lattice, full-width standard-cell rows, >=20um macro channels; main/fallback spend area to unbox pin strips. Aspect below2:1. Pin-bound low fill disclosed; no shrink.
7. Clock: same local spine and16 kept leaves. Gate measures TT/FF spread; no clock waiver. Hold margin0.03ns retained.
8. Schedule/reset: +1 boot-write edge, zero production edges; controls/valid reset, new payload pipeline unreset. Fault/sequence checks retain original edge. Independent reference delays full original write interface; real compiler boot and causal mutant run in parallel.

See results/arch/codex_k_ctl_dstg_1021/model.json. Native/gate results remain pending.

Functional results: independent legacy-interface +1-edge reference PASS199930 compared edges; real471-word MU image PASS2660 compiled event edges/10 tokens; layer slice mutant caught at cycle1895. Verilator5.050; receipt in results/arch/codex_k_ctl_dstg_1021/receipt.json. Physical/native pending.
