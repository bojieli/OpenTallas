# G2 descriptor-driven input transport

Status: implementation plan, 2026-09-22. This document does not claim the input
transport is implemented. It defines the next integration change following the
bounded output writer.

## Observed boundary

`ot_a3_g2_array_issue_adapter` reads three beats each for A/B: dtype, scale
binding and shape, but not their strides or object capacities. It uses resolved
element offsets as service-word bases. `ot_a3_lq8_runtime_operands` requests
128-bit packed weight words in the array's issue order. The loaded campaign
constructs those words in Python, repeating the stream for each output row.
Activation byte mapping and auxiliary SRAM windows are instantiated by the test
bench; their object identity, bounds and layout are fixture inputs.

Consequently, the current loaded test verifies arithmetic, queueing and output
transport, but does not establish arbitrary descriptor-driven input transport.

## Required architecture

1. Capture A/B rank-two element strides and object identities alongside their
   dtype and resolved offsets. Resolve their MEMORY_OBJECT descriptors and
   permissions before launch. Read four descriptor beats for each tensor view;
   the existing short/long descriptor-store protocol can support this. Resolve
   scale and numeric bindings explicitly; host scale geometry cannot be treated
   as descriptor-derived coverage. Keep the full admission record immutable
   until cancellation/drain completes.
2. Separate the monotonically increasing service-word identifier from logical
   tensor coordinates and object byte addresses. Preserve existing bank and
   operand-join tags. A layout cursor generates physical gather work; transport
   responses assemble the packed word expected by the arithmetic lanes.
3. Walk the actual weight order: output row, groups of up to INTERLEAVE local
   columns, K word, local column, lane. For BF16, lane `l` of local column `c`
   reads element `B_offset + (LANES*c+l)*B_stride0 + k*B_stride1`. Mask columns
   beyond logical N and supply zero without a memory request. Activation reads
   `A_offset + row*A_stride0 + k*A_stride1`. These formulas define a reference
   oracle; per-word hardware uses registered increments and wrap/reset state,
   not a variable divider/multiplier chain.
4. Coalesce gathers into bounded memory-line requests and retain fetched lines.
   ABI N-major weights place adjacent K values together, while the array consumes
   adjacent output columns together. Eight independent scalar reads per issue
   word would close the functional gap but waste bandwidth and is not the
   performance target. Banked line storage and an explicit transpose/assembly
   stage must expose useful bytes, transferred bytes and bank-conflict counters.
5. Reserve assembly capacity before issuing reads. Track operation generation,
   response identity and destination slots until all accepted reads retire.
   Cancellation stops new reads, drains accepted responses and revokes partial
   words. Do not release a bank or reuse a generation while responses can still
   target it. Backpressure must retain every published request unchanged.
6. Preserve resident-row replay: retained packed words need no repeated object
   reads. For rows beyond 1,024 words, tile reuse across output rows requires a
   separate accumulator-capacity design. Changing the memory layout alone must
   not silently reorder sequential FP32 accumulation.

Sub-byte formats require bit offsets, boundary-spanning extraction and their
actual group/scale semantics; extending the byte mapper's shift field alone is
insufficient. Unsupported layouts must be refused before reads, with explicit
coverage gaps until those formats are implemented.

## Integration and acceptance order

First implement immutable descriptor records and the logical layout cursor,
including overflow and tail handling. Next integrate bounded line fetch,
transpose/assembly and response ownership into the synthesizable cluster.
Replace the fixture's packed `weight.hex` input with actual deployment object
bytes; the fixture should model external memory timing and errors only. Then
extend formats and scale transport, followed by reuse beyond resident rows.

Functional acceptance includes nonzero input offsets, independent row/column
strides, logical tails, K boundaries, objects ending inside a final element,
read-permission failure, response stalls, cancellation and late responses.
Compare against the independent Device model and protect output gap bytes.
Replay-enabled and streaming runs must produce identical numerical results.

Performance acceptance records memory bytes per useful output, line reuse,
assembly occupancy, bank conflicts, operand starvation, compute utilization and
whole-operation latency. Compare with the existing packed-stream baseline under
the same external bandwidth/latency assumptions. Report packing costs explicitly.
Physical acceptance requires current-source containing-block synthesis with the
actual SRAM macros, followed by setup/hold and physical-rule closure. A standalone
cursor frequency cannot qualify the integrated transport.
