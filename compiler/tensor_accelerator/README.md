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

This is executable compiler/simulator evidence for the artifact boundaries only.
It is not Qwen3-8B or DeepSeek-V4 execution, target floating-point qualification,
RTL correlation, 130-nm physical evidence, HBM PHY evidence, or a production
performance result. Those gates remain open and must use the same artifact path
without framework fallbacks.
