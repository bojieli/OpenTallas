# Tensor-accelerator executable fixture

This redistributable exact-integer fixture exercises the production-path artifact
boundaries: backend-neutral Model Graph IR, target-numeric Tensor Kernel IR, HBM
image placement, banked-SRAM allocation, DMA and compute commands, independent
reconstruction/accounting, and artifact-only data-bearing timing simulation.

It is not Qwen3, DeepSeek, RTL, HBM PHY, 130-nm PPA, or product evidence. The
qualified fixture result is the integer vector 0, -1, 4, 3, 3, 0.
