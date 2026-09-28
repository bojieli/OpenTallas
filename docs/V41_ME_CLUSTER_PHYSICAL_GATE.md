# Shared V4.1 ME activation cluster physical gate

This branch probes one candidate 41-consumer wo_a cluster at the real operand
width. It builds on the exact RL3 opt-in adapter interface at `481b4158`.

The cluster boundary takes four 512-bit FP32 VM words in physical bank order,
converts 64 lanes to BF16 RNE in one registered stage, and writes eight 128-bit
words into a 16-macro 1R1W activation store. A tile read uses all 16 macro
read ports to make a 2,048-bit two-position operand beat. One registered
multicast stage drives 41 distinct adapter capture banks. The operating wo_a
schedule requires all 41 consumers to issue the same read descriptor and
accept each beat together. A single store cannot concurrently satisfy
unrelated experts, user requests, or tile schedules without an arbiter.

The matching 2 MiB logical VM is four static 512-bit banks, each 8,192 words
deep. A bank uses four 512×128 1R1W macros in parallel for width and 16
macro groups for depth: 64 macros per bank, 256 for the VM. Preload consumes
one read port in every VM bank each cycle for 128 issue cycles over the two
K=4,096 groups, plus conversion, macro-write and pipeline fill/drain. The
COLLv1 GW4 write service consumes the write port in every bank in a separate
blocking phase. The 1R1W ports permit concurrent reads and writes at distinct
addresses, but this candidate gives no performance credit for such overlap,
same-address read-during-write behavior, or any other core VM read while the
four-bank preload occupies all read ports. The 16:1 depth-group VM read
selector and full read4-to-converter link are not in the cluster route.

[`ot_v41_me_cluster41_phy.sv`](../rtl/chip/physical/ot_v41_me_cluster41_phy.sv)
is a parameterized physical load envelope. Its capture banks stand in for the
adapter's existing local `xr` register; per-consumer enables keep them
separate. Every capture bit is exported so the physical flow cannot remove
unobserved loads. The exact functional bench sets 41 consumers. The physical
route sets `CONSUMERS=4`, whose 8,192 output bits fit a bounded top-level pin
cut. Four physical consumers do not prove the intended 41-consumer multicast;
the latter remains an open hierarchical composition gate. The earlier 41-way
probe using `keep` with only 32-bit samples was invalid: OpenROAD removed its
unobserved flops after synthesis, despite Yosys emitting them. This probe
does not instantiate the MAC tiles, weight banks,
vector memory, global preload tree, or a cluster scheduler. Any positive
route is an operand-delivery gate, not a complete compute-cluster or token-rate
result.

The checkpoint wo_a ACC base is 74,272 FP32 elements, 32 modulo 64. Its four
physical VM banks naturally present each 64-element beat in the order
`[logical 32:47, 48:63, 0:15, 16:31]`. The converter preserves that bank
order and the xbank read selector uses `rd_rot=2`; no 2,048-bit ingress
crossbar is credited. The owner is checking this bank-major mapping against
checkpoint values before any full-shape performance claim.

`rtl/test/tb_v41_me_cluster41_phy.sv` exercises both positions through the
converter, the 16 behavioral macro models, the registered multicast and all
41 capture banks. It checks the complete 2,048-bit operand at every consumer,
including the
`rd_rot=2` lane order. The bench passes in Icarus Verilog with the macro's
behavioral Verilog model. It is a boundary test, not a checkpoint token gate.

Area and power decisions must add the macro-only shared-store sweep in
[`v41_me_shared_cluster_budget.json`](../results/physical_abi3/asap7/chip/v41_me_shared_cluster_budget.json)
to the converter, multicast wires and buffers, adapter capture clocks, VM
read tree, and the die's existing SRAM. The sweep pins both layer-die and
head-die assembly baselines and separates the conditional full-shape VM
replacement delta. A 0.92 ns route must meet setup, hold, DRC, antenna and
port conflicts with all 41 consumer paths; a pre-route or global-route slack
alone is insufficient.
