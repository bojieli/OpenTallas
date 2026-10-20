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

PICKUP SEALED 2026-10-20: the stable cap32 source is NOT native qualified.
NU1 actual ASAP7 mapping fails with 55 internal drivers above32, maximum64.
Including the module input boundary gives60 violations; r_addr[18] drives36
native pins. The exact mapped JSON/Verilog and census are in evidence/native.
All7 functional configurations passed84,000 total edges before this mapping.

The original NU4 mapping remains live on ot-epyc7. Preserve client2917450,
tool session83703, fleet unit oth-ubuntu-1939911-1792482414, Docker container
codex_amax_csafe_native_1020. Root remote directory:
`/srv/opentallas-scratch/claude/codex-amax-csafe-1020`.
Collect native/n4.json, native/n4.v, native/n4.log when terminal, then run
this directory's census.py on the copied JSON. The Docker-created native
directory is root-owned; run the census on a local writable copy.

An UNVALIDATED cap16 construction is archived as evidence/private_cap16.sv.gz
and its construction receipt. Regenerate with `--internal-cap16`; this private
adapter limits internally driven generic nets to16 and retains a32 input
ceiling. It has neither functional nor mapped qualification. The cap32 source
above remains the public source. ABC's two input loads for a generic MUX
select explain why the generic32 bound alone did not protect native32.

Further address-retiming exploration exists only in remote generated16r;
it is UNVALIDATED and must not be adopted. It moves leaf index offsets from
the al0 input to the al1 combinational operands, which needs an additional
reset-origin marker to preserve invalid-data output bits during reset drain.
No layout gates or additional native mappings were launched for these trials.
