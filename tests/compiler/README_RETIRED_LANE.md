# The ABI 2.5 lane in this directory

Twelve files here test a pipeline this program has replaced. They are listed
below so that nobody reads a green tick in this directory as evidence for
ABI 3.0, and so that a red one is not mistaken for an ABI 3.0 regression.

    test_tensor_accelerator_qwen_dynamic_control.py
    test_tensor_accelerator_qwen_long_context.py
    test_tensor_accelerator_qwen_rtl_add.py
    test_tensor_accelerator_qwen_rtl_dma.py
    test_tensor_accelerator_qwen_rtl_dma_matmul.py
    test_tensor_accelerator_qwen_rtl_dma_rmsnorm.py
    test_tensor_accelerator_qwen_rtl_head_rmsnorm.py
    test_tensor_accelerator_qwen_rtl_kv_proj.py
    test_tensor_accelerator_qwen_rtl_q_proj.py
    test_tensor_accelerator_qwen_rtl_rope.py
    test_tensor_accelerator_qwen_workload.py
    test_tensor_accelerator_schemas.py

Each reads `results/tensor_accelerator/qwen3_full_model_physical/ir/tensor_kernel_ir.json`
— the ABI 2.5 IR, not `build/ir-v3/<model>/kernel_ir.v3.json` — and several also
read a **second repository** at `/home/ubuntu/OpenTallas-ta-integration/`, so
they cannot be reproduced from this repository alone.

`test_tensor_accelerator_qwen_rtl_rope.py::test_rope_builder_reproduces_retained_artifact`
fails, and fails on a clean checkout. It has not been skipped. Silencing the one
that happens to be red while leaving eleven green ones making claims about a
retired lane would make the suite look better and this repository less honest.

## What is *not* retired

The rest of `test_tensor_accelerator_*.py` is a different matter, and the
distinction is worth stating because the filenames do not make it.
`runtime/tensor_accelerator/` is **shared**: it holds the frozen BF16 and
attention kernels that the ABI 3.0 engines call into, beside the superseded
ABI 2.5 simulators. So `test_tensor_accelerator_bf16_qualification.py` and its
siblings are live coverage of code ABI 3.0 depends on today, and deleting them
along with the lane above would remove exactly the numeric guarantees this
program rests on.

None of these files import `runtime.abi3`, `runtime.sim` or `compiler.ir.v3`,
so that import graph is not the way to tell the two groups apart. The dependency
on the ABI 2.5 IR artifact is.

Tracked as OI-25 in `docs/UNIFIED_EXECUTION_CHECKLIST.md`.
