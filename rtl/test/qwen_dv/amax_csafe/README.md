Isolated running-argmax successor, generated from the original
`qfd_dv_amax_mu` before technology mapping. Public wrapper parameters are
`NU`, `MUT`, `SAFE`; SAFE=0 instantiates the original. SAFE=1 supports NU=1
and NU=4, preserving MUT=0..5 semantics (MUT has no effect for NU=1).

There are zero additional arithmetic or command pipeline edges. Reset is
different: rst feeds two synchronous tree edges before every original state
reset pin, for assertion and release. The owner must hold reset through two
clock edges and align all sibling control state to the same two-edge reset
tree. The final generated NU1/NU4 variants each put exactly five D-pin loads
on rst. Clocks are the only excluded signal in the generic fanout bound.

The existing generic constructor recursively duplicates FFs and overloaded
combinational drivers in distinct kept helper hierarchies. This is real
source construction, not a constraint waiver, timing exception, or added
data pipeline. Native mapping must independently confirm the <=32 bound.

Fleet generation: `python3 tools/qwen_dv/gen_amax_csafe.py generated`.
Fleet simulation: `bash rtl/test/qwen_dv/amax_csafe/run.sh sim`.
Fleet synthesis: invoke `synth.sh native` inside openroad/orfs:asap7lock,
with the repository root mounted as the current working directory.
Then `python3 rtl/test/qwen_dv/amax_csafe/census.py native/n1.json native/n4.json`.

The bench compares all outputs against the same-MUT original with the
matched two-edge reset, on 12,000 randomized edges, including 13 reset bursts
and recurring equal-value ties. This verifies MUT behavior preservation;
it is not a claim that each mutant is rejected by a causal witness.

No layout gate or submission is authorized by these construction receipts.
