# COLL native all-driver repair model

The v74w native checkpoint exposes 64-terminal counter reset, shared iteration/step multiplier captures up to64, and start capture33. Existing gate WARN does not qualify these roots.

Structural source successor: 31 independent8x8 products each capture their own16 operand bits in a kept module before the unchanged product register. This replaces280 shared captured operand bits with496 (delta216). Product registers, partial sums, truncations and all capture/output edges stay unchanged. Ten reset copies replace nine, and a second same-edge start capture partitions the two16-bit counter halves. Source state delta218 FF before native optimization. No indexed store is added. Input step/iteration bits drive at most7 capture D pins each; each captured operand drives only one8x8 multiplier. This is a native-mapping hypothesis to verify, not a fanout PASS.

Counter halves both use the same full32-bit cycles+1 combinational expression and reset synchronously to zero on their same-age start copies; carry/rollover unchanged. Low/high16 reset groups each expect32 native terminals when the gate splits the32 output FFs into face copies. Reset root drives10 same-age reset-copy cells plus the existing face infrastructure.

Thirty-one product units retain current total fixed compute throughput one full issue per clock. Added latency0 edges, bytes/edge and boundary bit counts unchanged, no new scheduling state/backpressure. Conservative raw FF area using0.0729um2/FF adds15.8922um2 before native characterization. Source area must be remeasured; no new physical gate until whole source all-role mapping and explicit single full-width band/region floorplan model are ready. Pinned prior failures remain immutable.
