# Tensor-accelerator compiler and simulator vertical slice

This package is the additive production-path foundation for the programmable
HBM-plus-SRAM tensor accelerator. It does not modify or generalize the older
ROM-bound exact-integer fixture.

The backend-neutral graph contracts are intentionally versioned. Model Graph v1
is the executable exact-integer fixture contract. Production Model Graph v2 is
the admission boundary for real model adapters. V2 requires phase-specific
entrypoints, structured runtime predicates, source anchors, exact checkpoint
payload bindings, and explicit prepare/commit state effects. A Qwen or DeepSeek
adapter is not considered production-neutral merely because its operation names
can be copied into a generic list; it must satisfy the complete v2 contract.

The pinned Qwen semantic graph and checkpoint lock now have a thin v2 adapter.
It independently reconstructs tensor/dataflow shapes, binds every one of the 399
checkpoint payloads, converts per-layer KV writes into prepare/read-prepared and
one terminal atomic commit, and adds prefill/decode affine request guards. The
current real handoff exports 1,053 tensors, 617 operations, and 36 KV resources.
This is graph admission evidence, not a claim that the remaining Qwen kernels or
the common tensor-accelerator simulator execute the complete graph yet.

The current qualified slice implements this complete chain:

~~~text
backend-neutral Model Graph IR
  -> target-numeric Tensor Kernel IR
  -> deterministic HBM image and banked-SRAM physical plan
  -> fixed-width CRC-protected DMA/tensor/vector command stream
  -> independent payload, allocation, command, and counter checker
  -> artifact-only functional or data-bearing timing simulation
  -> independent source-graph oracle and exact known answer
~~~

Compile and execute the redistributable fixture with:

~~~bash
python3 -m compiler.tensor_accelerator \
  --model testdata/compiler/tensor_accelerator_fixture/model_graph.json \
  --capability testdata/compiler/tensor_accelerator_fixture/capability.json \
  --output /tmp/opentallas-ta-fixture

python3 -m runtime.tensor_accelerator \
  --deployment /tmp/opentallas-ta-fixture \
  --request testdata/compiler/tensor_accelerator_fixture/execution_request.json \
  --output /tmp/opentallas-ta-result.json
~~~

The emitted deployment contains payload-free semantic IR, a complete HBM weight
image, an explicit SRAM allocation, target kernels, binary commands and
disassembly, source and capability locks, independently derived expectations,
and content hashes for every runtime artifact. The simulator loads only those
artifacts and the execution request.

The qualified fixture performs one exact integer matrix operation and one exact
integer vector addition. It issues five commands, reads 36 useful HBM bytes in
two 32-byte transfers, and completes in 69 cycles under the fixture capability.
Its output is the integer vector 0, -1, 4, 3, 3, 0.

The first real-model numeric primitive is also frozen and differentially tested:
`bf16_bf16_fp32_sequential_rne_v1` rounds each BF16 product to binary32,
accumulates binary32 values in strictly increasing reduction-index order, and
rounds once to BF16. The independent exact scalar oracle and the separately
implemented NumPy data-bearing kernel agree across known answers, subnormals,
ties, cancellation, saturation, overflow rejection, randomized matrices, and
work-tile choices. This numeric qualification does not by itself claim a Qwen
layer or complete-model gate.

The first checkpoint-bearing qualification applies that contract to Qwen's
actual layer-0 Q projection at its full 4096-by-4096 dimensions. Checkpoint row
zero supplies the 4096-element input, the immutable reader authenticates both
complete source tensors, the data-bearing kernel computes all 4,096 outputs,
and the independent scalar oracle checks eight boundary/interior rows exactly.
The canonical report is retained at
`results/tensor_accelerator/qwen3_bf16_projection.json`. This remains one matrix
operation; it does not close the full-layer, compiled-HBM, or end-to-end gates.

That numerical result now also passes the first production HBM/SRAM deployment
slice. The compiler reads the locked checkpoint without copying it, transforms
the 4096-by-4096 layer-0 Q-projection weight into 64 output tiles by 16 ordered
reduction tiles, emits 1,024 HBM-to-SRAM DMA commands, 1,024 BF16 matrix-tile
commands, and one terminal completion command, and assigns distinct SRAM banks
to the input, weight staging tile, FP32 accumulator, and BF16 output.

An independent module rereads the locked tensor, inverse-reconstructs every
row-major source byte from the HBM image, proves tile and command coverage,
checks SRAM ranges and `INIT`/`FINAL` ordering, and independently derives all
counters. The artifact-only simulator then executes every DMA and segmented
matrix command causally; it does not invoke the whole-matrix kernel. The real
deployment has build ID
`23e937621f93a01802884afea4be503719080a1fad9aec11afbc159ae689d8c1`.
Its 4,096-element output hash is exactly
`b8ee116d31d645204b14b342db84d2f200e8c300f6dc17bb472d0cf3e1b42012`,
and its canonical execution report is retained at
`results/tensor_accelerator/qwen3_hbm_sram_projection_execution.json`.

Reproduce the governed slice from locally pinned artifacts with:

~~~bash
python tools/run_qwen3_hbm_sram_projection.py \
  --snapshot /path/to/pinned/qwen3-8b/snapshot \
  --checkpoint-lock /path/to/qwen3-8b/checkpoint.lock.json \
  --model-graph build/tensor-accelerator/qwen3-8b/model_graph.v2.json \
  --capability configs/hardware/tensor_accelerator_development_v1.json \
  --qualification results/tensor_accelerator/qwen3_bf16_projection.json \
  --deployment /path/to/new/projection-deployment \
  --report /path/to/new/execution-report.json
~~~

The development capability deliberately contains no clock, latency, bandwidth,
or energy values. It declares the model/format union required by Qwen3-8B and
ordinary target-only DeepSeek-V4 Flash, but only the BF16 tensor mode is marked
qualified. Consequently this slice is functional compiler/simulator evidence,
not 130-nm characterization or performance evidence.

This is executable compiler/simulator evidence for one real Qwen operation and
the production artifact boundaries. It is not a complete Qwen layer, complete
Qwen or DeepSeek model execution, RTL correlation, 130-nm physical evidence,
HBM PHY evidence, or a production performance result. Those gates remain open
and must use the same artifact path without framework fallbacks.
