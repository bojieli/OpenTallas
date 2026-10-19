# INT8 native census: both geometry variants HOLD

Source is claude/smh-int8-tile-1019 at 3aa5bb9be. This packet reuses the original
completed gate GRT databases; it does not synthesize, route, submit, or approve.
Exact original remote run identities, source/archive/tool bindings, kit hashes,
and clock measurements are in t1_gate_context.json and t2_gate_context.json.
The full original gate_result files remain in the source kits at their recorded
SHA256 values. These records are historical tool bindings, not permission to
submit against whatever helpers main subsequently contains.

The audit reads actual OpenDB instance/master/ITerm direction, traces through
every BUF/INV (including both polarities), counts final logical pins without
truncation, and retains all roots/endpoints in compressed JSON. Clock is excluded
explicitly; reset, inputs, FFs, comb outputs and ties have no exemption.

Both t1 and t2 contain 11,506 nonclock roots: 2,531 FF, 7,939 combinational,
1,036 input. There are no unknown driver nets. Exactly 17 roots exceed 32:
the final reset-landing FF drives 87 RESETN pins and all 16 pend FFs drive
85–110 logical pins. t1/t2 have the same unsafe fanout structure. The mapped
root/pin/master role counts and full endpoint lists are committed. The source
claim that 32 selected code bits imply 32 physical loads is false: mapping
distributes selection through classifier logic, including AND/AO/AOI/OA gates.
No broad gate high-fanout PASS can override this census.

All 1,036 input roots terminate first at FF pins, including i_v's 22 kept D
copies; every one of the 1,070 output bits has a FF driver after transparent
inversion. No combinational data input/output exception was found. Placement
straight Manhattan reaches are at most 270.378 um t1 and 240.084 um t2. These
are endpoint displacement bounds, not routed wirelength or a substitute for
complete stage-composition timing. TT/FF pin spread is 23.1/21.8 ps t1 and
29.9/29.6 ps t2. Parent placement, neighbour-matched clock references and
parent output-select load budgets remain unqualified.

## Concrete structural successor model (not implemented)

Replace sixteen 32-code-bit select groups with 128 kept same-edge pend FFs:
two useful copies per converter lane, one selecting bits [3:0], the other
bits [7:4]. For lane l and nibble h, the original next-state equation remains
pend[l,h](t+1)=p_v[floor(l/4)](t), or zero under the same landed reset.
The copy feeds only its actual nibble's low/high code select before to_bf16;
there is no buffer/inverter exemption, extra pipeline stage, or output-age change.
The existing input p_v group consequently drives eight pend D pins, rather than
one. Two copies per lane give margin against the observed 85–110 loads per
four lanes; the target is <=24 *mapped logical pins* per copy. This target is
an estimate requiring synthesis/census, never a construction PASS. Mapping
that propagates selection into excess gates must be stopped structurally at
the actual nibble cone or split further, then recounted.

Preserve the exact inherited reset contract: the generated current wrapper
contains TWO ordinary posedge FF stages (raw -> rl0 -> rl1). Assertion AND
deassertion are sampled at those two edges; this is not an asynchronous-assert
landing wrapper. Core resettable flops have asynchronous RESETN sensitivity
to rl1. A successor must use one kept first stage and nine distinct kept
second-stage copies, each with <=24 assigned actual RESETN sinks. All second
stages sample the same first stage at the same edge. Do not append another
stage, remove either inherited stage, change stopped-clock behavior, or drive
all core resets from one alias. Exact assertion/release/short-pulse/stopped-clock
lockstep and native role counts are required.

Replacing 16 pend FFs by 128 adds 112 ASR FFs. Existing 87 reset sinks become
199; nine final reset copies replace one, adding eight ordinary FFs. Minimum
delta is +120 FF / +120 clock contacts, 44.78976 um2 cell area and 55.642576 fF
TT clock pin capacitance, before actual mapping, inverter polarity and reset
distribution logic costs. Reserve a further 120 minimum inverters (5.2488 um2)
until their actual polarity need is mapped; do not count this reserve as a
measured result. The table is sourced from the exact image's RVT TT SEQ library
with SHA in library_cost.json. Latency delta is zero; low/high output ages stay
+2/+3 and reset landing remains exactly two sampled edges. Recompute area,
all roots, port registration, complete stage depth, PG and clock costs before
any fresh gate. Floorplan geometry/pin-bound low-fill approval alone does not
qualify either failed source.

Execution: unpinned ot-run, memory 4 GB, one thread, original run data locality.
t1 unit oth-ubuntu-1920448-1792438842; t2 oth-ubuntu-1921214-1792438852;
both RAN exit 0. OpenROAD 26Q3-1510-g6cb3f2b704 in openroad/orfs:asap7lock.
No new REVIEW.json and no route submission were written.
