The native IDX parent requires four stack scorers. Each scorer has four engines,
each engine scores four keys over four eight-head chunks, and each chunk contains
four columns of eight head-key hslice leaves with a distinct registered reset-ready acknowledgment successor. The required count is
512 leaves per scorer and 2,048 per die. The historical 32-child grid cannot be
used as this parent or as its placement footprint.

The new source `rtl/hdc/v41x/ot_hbm_idx_owned_native.sv` assigns separate clock
inputs to engine queue/control, per-engine metadata, tail arithmetic, chunk
control, and every hslice. The engine parent contains only wires and child
instances. The metadata queue retains last, first global index, and refusal
mask; output scores remain finite-credit and ordered. The hierarchical latency
adds the previous measured hslice substitution's 23 edges. At native FPL7/FML5/
QL5, both engine and metadata capacity are 128 beats. No queue is replaced with
an unbounded host array or precomputed output.

A full-width arithmetic vehicle instantiates NS16/NK4 (all 2,048 real RTL hslice
state objects) and compares actual output scores, flags, masks, global IDs and
last tags against the canonical NumPy golden. Hierarchical compilation preserves
the real hslice arithmetic and compiles its implementation once; the distinct successor adds one actual rs/rn_p-qualified acknowledgment FF and pin. Source contains
2,160 owned clock roots (16 state + 16 metadata + 16 tail + 64 chunk + 2,048 leaf).
The functional vehicle ties those clocks to one common phase. It does not prove
independent-clock delivery or four independently timed stack-service streams.

The native full-parent continuation must then bind four NS4 scorers to actual
line landing, query distribution, selector and ordered candidate collector.
Existing hfd score line FIFO64x1098 state, selector landing/control/memories,
query quantizer, and ordered collector state cannot disappear from that graph.
The current scorer-array vehicle is not full service/selector/parent closure.

Measured hslice outline is172.8x103.68um, area17,915.904um2; replicated outline
lower bound is9,172,942.848um2/scorer and36,691,771.392um2/die. Liberty cell area
and utilization are different quantities and must not substitute for outline.
An arrangement of four engines, each four chunks, with eight-head columns can
have a leaf-only 2,764.8x3,317.76um bounding rectangle/scorer. This is a lower
bound geometry request, not an assigned slot. Glue, memory, clock/reset delivery,
routing gutters and registered relays must increase that request. Existing
2,000.16x2,646um grid has only5,292,423.36um2, giving a leaf-only ratio1.73322.
Actual die windows must come from the die owner; no fabricated slots or legacy
32-child macro aliases are accepted.

The fresh source-bound glue census is 566,992 generic FF bits across112 roots: engine9,905, tail8,104, chunk3,551 and metadata3,224. An additional2,048 independently clocked ready-leaf instances produce2,160 total roots. The related old measured leaf has15,334 sinks; the new acknowledgment leaf requires a fresh physical view.

Physical intake remains blocked on fixed
named hard leaves, actual clock-root acceptance, registered pin/seam timing,
source-derived die pin files, and an admitted placement/window from the die
owner. The closed hslice, q-end pack and T4 join remain constituent evidence;
they do not close this native parent. Current functional clocks, geometry,
complete-service bandwidth, native rate and parent physical timing are all
unqualified. Fullgold and mutation receipts will be published separately.

Complete native functional parent evidence is now published in
`full_parent_d850fd545` and `parent_mutants_d850fd545`. Four independent stack
scorers use all2,048 actual ready-leaf arithmetic objects, hardware FP32 query
quantization, real SRAM topK, and the ordered max8/newest candidate collector.
Canonical retained1M rank0 L20/L24 operands, rank37 partial4,100 keys with two
empty quarters, and a refused-key fault pass without resetting between frames.
Lane/GID/keep/value/order source mutations are actually detected. These are
common-phase functional fixtures, direct endpoint nets; actual HBM PHY/service
and downstream VM commit/drain barriers remain outside this proof.

The separate clock/state cut successor is source-bound by `cut_edab82fb5`.
Its actual census retains681,099 FF bits plus246,284 inferred buffer bits,
185 glue clock names,2,048 new-ready leaf clocks and120 distinct SRAM clocks:
2,353 unique source entries. Every glue root, counting inferred buffers, is
at most13,860 bits. Source contains96 real64x512 line macros and28 real256x256
score/topK/ordered macros. Exact caller line capacity64 and score capacity128
include buffered/prefetched records; extra physical SRAM rows grant no credits.
The actual SRAM catalog outline sum is1.477370mm2, in addition to the related
leaf-only36.691771mm2, before glue/channels/clock/reset. `request_graph.json`
contains actual module logical ports, source hashes, instance/clock/macro lists,
and requested geometry; it contains no assigned slots or physical driver ABI.
The related old scorer slots overlap107 real current-v13 children and are not
available grants. This candidate's numerical proof is separately admitted;
the uncut baseline verdict is never copied to it.

New-ready nominal leaf sink demand15,335 requires fresh physical measurement,
partition or the actual allowed300/80 clock rule; old15,334-sink CLOSED evidence
cannot grandfather it. New macro/control seams, coherent clock delivery,
active-clock-stop reset/drain leases, actual driver slots, source-bound die
placement/STA/GRT and all physical rate/bandwidth claims remain unqualified.
The original cancelled score_slice_reg/f0ba521d3 and ksub_el/9e9a8a8a7 are not
silently aliased or retired by this distinct full-native successor.
