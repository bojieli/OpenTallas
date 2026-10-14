This distinct default-off frontend carries full whole-token TAG59 on accepted
Q VM reads, their responses, addressed attention VM writes, and actual write
acknowledgements. The epoch is retained across all decoder layers; stage is
layer + 1. The token, full thirteen-bit position, and segment zero are captured
with the reservation. Responses and acknowledgements retain the identity of
their originating accepted transaction. An old response is never relabelled
with the current layer. A mismatched acknowledgement faults before the actual
commit bridge advances its 32-word barrier.

`library_receipt.json` is the exact nine-source build manifest. Unit
`2356418-1791973643` ran through ot-run on EPYC1 and exited 0. The new module SHA
is `7f09088bb568c5305ba96192f647f6019fb0332a5a39db0871fcf8210dd1d3ab`.
The five formatter/reader/row/fence/provider source files are owned by the
separate `476386f8a` bundle; the manifest hashes were compared with that
immutable commit and this branch's frontend/bridge/sequencer sources. A source
bundle must include those dependencies. Building the library alone proves
elaboration and linking, not numerical or whole-layer execution.

The separately owned mapped gate uses actual f460 attention RTL and real
quarter writes/WDONE, addressed VM stores, and delayed acknowledgements. Its
fresh V2 evidence lives at
`results/arch/qwen_composed_harness_1014/front59_v2_component/receipt.json` in
the composition branch. It passed 2,048 exact output values, including a same
epoch-zero layer transition without reset. Saved old-layer Q responses and
attention acknowledgements, and token/position/segment acknowledgement bit
mutations, faulted. Each attention-acknowledgement mutant follows an actual
current-layer VM write and leaves the actual bridge count at zero. Offered
acknowledgement counts include rejected packets and cannot be called committed
consumer effects.

These operands remain explicit component fixtures. No actual fullshape SU/core,
layer-to-layer X carry, HOST/allocator binding, physical timing, bandwidth, token
or price acceptance is claimed. The reusable VM adapter in this branch retains
optional TAG59 fields without changing the historical untagged adapter API;
the composition owner maintains its separately observed adapter and gate.
