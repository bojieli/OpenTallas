# HBM comparator system inventory (deliverable 1)

Base `298ba9d79` (branch claude/hbm-system-rtl-20261003). origin/main has since moved to `6fc0a3954`. Its only RTL change is the DS MTP accept leaf.
Machine-readable version: `inventory.json`. It lists every file, every evidence record and the notes in full.

Status legend:
- **RTL+tested**: RTL exists and a committed record passes. This is component or directed scope only. It never means installed, connected or SS/FF-qualified.
- **RTL-untested**: RTL exists but has no passing record.
- **tb-only**: the block exists only inside a bench, or as a simulation-only model.
- **model-only**: the block exists only in Python.
- **missing**: nothing exists.

## Qwen3-8B HBM

Counts: RTL+tested 13, RTL-untested 1, tb-only 4, model-only 3, missing 8

| block | status | owner | evidence |
|---|---|---|---|
| HBM controller + PHY model | tb-only | none | results/rtl/w19_fetch_sm.json (+2) |
| HBM pseudo-channel service (ot_hdc_qwen_hbm_service / pc_service) | RTL+tested | none | results/rtl/qwen_o4_hbm_mixed_service.json (status pass) (+1) |
| W2 exact PC completion (NC6 successor + sealed codec) | RTL+tested | Nash | results/rtl/w2_nc6_parent_terminal_review_20261003/record.json (PASS_COMPONENT_FUNCTIONAL_ONLY) (+3) |
| L2 slices | missing | being built by claude/hbm-system-rtl-20261003 (this branch) | tools/uarch_model.py:1658 (hbm_gpu_design l2 = 4 slices x 2 MB, model-only) (+1) |
| Crossbar / on-die NoC (SM <-> L2 <-> HBM partitions) | missing | being built by claude/hbm-system-rtl-20261003 (this branch) | tools/uarch_model.py:1662 (out['noc'] wire counts only) |
| SM tensor core (ot_gpu_sm_q + tc_col/tree/stack/issue/xstore) | RTL+tested | none | results/rtl/gpu_sm_exact.json (pass, 15 cases exact) (+3) |
| GU64 pair + L2 commit pipeline (ot_gpu_qwen_gu64_pair / _l2 / row_tiles) | RTL+tested | none | results/rtl/qwen_hbm_gu64_pair_20261001/v2/verdict.json (PASS) (+3) |
| Bulk-copy / TMA engine | RTL+tested | none | results/rtl/gpu_supply_barrier.json (+2) |
| Register file service (ot_gpu_rf_service, inside full SM service) | RTL+tested | none | results/rtl/parent_HBM_full128_verilator_execution_20261002_r1/verdict.json (PASS_DIRECTED_FULL128_AND_STORAGE_ONLY) |
| W4 identity-bearing common RF ACK | RTL-untested | Euclid | unpushed local commit 721639931 'Freeze admitted defaultoff W4 fullwidth common ACK source' (+2) |
| SIMD/SIMT vector unit (ot_gpu_full_sm_service) | RTL+tested | none | results/rtl/parent_HBM_full128_verilator_execution_20261002_r1/verdict.json (+1) |
| SFU / transcendental + reduction lanes (norm rsqrt, softmax exp, SiLU) | missing | being built by claude/hbm-system-rtl-20261003 (this branch) (as part of the SIMT SM core) | rtl/gpu/ot_gpu_full_sm_service.sv:5 ('No ... reduction, SFU') |
| Shared memory (ot_gpu_scratch_service) | RTL+tested | none | results/rtl/parent_HBM_full128_verilator_execution_20261002_r1/verdict.json |
| Connected SM + RF/SIMD/SMEM + fence (directed) | RTL+tested | none | results/rtl/hbm_qwen_r11_terminal_owner_20261002_r1/raw/verdict.json (PASS_DIRECTED_NATIVE_QWEN_CONNECTED_ONLY) (+1) |
| RF visibility fence (original + W6 successor) | RTL+tested | Goodall | results/rtl/hbm_W6_local_component_20261003/handoff.json (PASS_W6_LOCAL_COMPONENT_ONLY) (+2) |
| W5 installed owner gate (ot_gpu_hbm_owner_gate) | model-only | Popper | results/uarch/h4_hbm_baseline_bridge_20261003/model.json (FROZEN_DESIGN_FAIL_COMPOSED_CALENDAR_AND_PHYSICAL_ALLOCATION) (+2) |
| KV cache write/read path (FP8 KV, PC adapter, r14 vehicle) | tb-only | Nash (W2 completion), Popper (W3/W8 deferred), Euclid (W1 r14 hygiene) | results/rtl/w19_qwen_hbm_vector_kv_fixture_result.json (status producer_exact: host norm/RoPE/FP8 KV fixtures) (+2) |
| Attention (QK^T, softmax, PV) on SMs | model-only | being built by claude/hbm-system-rtl-20261003 (this branch) (runs on SIMT core + TC) | results/rtl/qwen_hbm_complete_20261001/ordinary_GPU_lowering_progress_r1.json |
| Qwen DFlash speculative decode on the SM design | missing | none | tools/dflash_step_timing.py |
| Inter-die link (TP-2 UCIe pair) and collective endpoint | RTL+tested | none | results/rtl/w15_collectives.json (q* configs, Verilator) (+2) |
| GPU collective endpoint (SM/L2 <-> link DMA) | tb-only | being built by claude/hbm-system-rtl-20261003 (this branch) | results/rtl/w15_hbm_nvls.json |
| CDC on comparator paths (HBM service <-> SM, W10) | missing | Popper (W10); being built by claude/hbm-system-rtl-20261003 (this branch) (ot_gpu_cdc_fifo) | results/rtl/v41_link_cdc_campaign.json (ot_link_afifo all_pass) (+2) |
| Host command/completion interface (ot_host_if) | RTL+tested | none | results/rtl/host_if_campaign.json (status pass; target qwen3-hbm) (+1) |
| Kernel launch / command processor | missing | being built by claude/hbm-system-rtl-20261003 (this branch) | results/uarch/hbm_feasibility_audit.json (6e: 'a persistent hardware-sequenced program, not GPU kernels') (+1) |
| Barrier network (ot_gpu_barrier_node) | RTL+tested | none | results/rtl/gpu_supply_barrier.json (status pass) (+1) |
| Reset / clock control | missing | none | rtl/ot_stage_top.sv instantiates ot_power_reset_controller; no rtl/gpu/* instantiation |
| Checkpoint/weight load into HBM | tb-only | being built by claude/hbm-system-rtl-20261003 (this branch) (host bridge/DMA) | results/rtl/w19_payload_loader_gate_20261001.json |
| Token program / ISA (Qwen HBM) | model-only | Dewey (native calendar/control trace join) | results/rtl/qwen_hbm_complete_20261001/actual_two_token_terminal_r1/terminal.json (CHECKPOINT_SOFTWARE_COMPLETE, actual_RTL_executed=false) (+2) |
| Full-token end-to-end RTL simulation (Qwen HBM) | missing | being built by claude/hbm-system-rtl-20261003 (this branch) (reduced-shape Qwen system top) | results/rtl/qwen_hbm_complete_20261001/actual_two_token_terminal_r1/receipt.json (actual_RTL_executed=false) (+2) |

## DeepSeek-V4.1 HBM

Counts: RTL+tested 16, RTL-untested 2, tb-only 3, model-only 6, missing 8

| block | status | owner | evidence |
|---|---|---|---|
| HBM controller + PHY model | tb-only | none | results/rtl/w19_fetch_sm.json (+2) |
| HBM pseudo-channel service (DS) | missing | Popper (route adapters) / being built by claude/hbm-system-rtl-20261003 (this branch) | /tmp/claude-review-20261003/hbm_owner_ack_gaps.md ('There is no shared multi-client PC service RTL for DS') (+1) |
| W2 exact PC completion | RTL+tested | Nash | results/rtl/w2_nc6_parent_terminal_review_20261003/record.json (PASS_COMPONENT_FUNCTIONAL_ONLY) |
| L2 slices | missing | being built by claude/hbm-system-rtl-20261003 (this branch) | tools/uarch_model.py:1658 (hbm_gpu_design l2 = 4 slices x 2 MB, model-only) (+1) |
| Crossbar / on-die NoC (SM <-> L2 <-> HBM partitions) | missing | being built by claude/hbm-system-rtl-20261003 (this branch) | tools/uarch_model.py:1662 (out['noc'] wire counts only) |
| SM tensor core (ot_gpu_sm_v + tc_col/tree/stack/issue) | RTL+tested | none | results/rtl/w19_sm_real_ops.json (pass, real TP-96 operands of busiest SM) (+3) |
| Block-dot tensor core (ot_gpu_sm_bd / ot_gpu_bd_col) | RTL+tested | none | results/rtl/gpu_sm_blockdot_exact.json (status pass) (+1) |
| Bulk-copy / TMA engine | RTL+tested | none | results/rtl/gpu_supply_barrier.json (+2) |
| Register file service (ot_gpu_rf_service, inside full SM service) | RTL+tested | none | results/rtl/parent_HBM_full128_verilator_execution_20261002_r1/verdict.json (PASS_DIRECTED_FULL128_AND_STORAGE_ONLY) |
| W4 identity-bearing common RF ACK | RTL-untested | Euclid | unpushed local commit 721639931 'Freeze admitted defaultoff W4 fullwidth common ACK source' (+2) |
| SIMD/SIMT vector unit (ot_gpu_full_sm_service) | RTL+tested | none | results/rtl/parent_HBM_full128_verilator_execution_20261002_r1/verdict.json (+1) |
| SFU / transcendental + reduction lanes (norm rsqrt, softmax exp, SiLU) | missing | being built by claude/hbm-system-rtl-20261003 (this branch) (as part of the SIMT SM core) | rtl/gpu/ot_gpu_full_sm_service.sv:5 ('No ... reduction, SFU') |
| Shared memory (ot_gpu_scratch_service) | RTL+tested | none | results/rtl/parent_HBM_full128_verilator_execution_20261002_r1/verdict.json |
| Connected SM + RF/SIMD/SMEM + fence (directed) | RTL+tested | none | results/rtl/hbm_r8_split_terminal_owner_20261002_r2/ds/raw/verdict.json (PASS_DIRECTED_NATIVE_DS_CONNECTED_ONLY) |
| RF visibility fence (original + W6 successor) | RTL+tested | Goodall | results/rtl/hbm_W6_local_component_20261003/handoff.json (PASS_W6_LOCAL_COMPONENT_ONLY) (+2) |
| W5 installed owner gate (ot_gpu_hbm_owner_gate) | model-only | Popper | results/uarch/h4_hbm_baseline_bridge_20261003/model.json (FROZEN_DESIGN_FAIL_COMPOSED_CALENDAR_AND_PHYSICAL_ALLOCATION) (+2) |
| KV cache write/read path (compressed KV, sequence-sharded, kv_gather) | model-only | Kepler (DS numerical continuation) | results/rtl/w19_hbm_tp96_isa.json (STATE: KV sharded by position, ISA-level) (+1) |
| MoE router top-K (ot_gpu_router_topk) | RTL+tested | none | results/rtl/w19_expert_fetch.json (router_topk verdict pass: 40 real + 200 adversarial vectors) (+1) |
| Routed-expert fetch (ot_gpu_expert_fetch) | RTL+tested | none | results/rtl/w19_expert_fetch.json (+3) |
| Payload transport / sector assembly (ot_gpu_payload_assemble) | RTL+tested | none | results/rtl/w19_payload_loader_gate_20261001.json (+3) |
| Checkpoint/weight load into HBM | tb-only | being built by claude/hbm-system-rtl-20261003 (this branch) (host bridge/DMA) | results/rtl/w19_payload_loader_gate_20261001.json |
| NVLink-class switch with in-switch reduction (NVLS) + links | RTL+tested | none | results/rtl/w15_hbm_nvls.json (hbm_p6/p48 deterministic all_passed) (+2) |
| GPU collective endpoint (SM/L2 <-> link DMA) | tb-only | being built by claude/hbm-system-rtl-20261003 (this branch) | results/rtl/w15_hbm_nvls.json |
| Top-k merge collective select (ot_coll_topk_merge) | RTL+tested | none | results/rtl/w15_topk_merge_hbm96_p64.json (exact) (+1) |
| V4.1 dedicated units: HC mixes + Sinkhorn | model-only | none | results/rtl/w19_hbm_tp96_isa.json (+2) |
| V4.1 dedicated units: indexer (index scores + local top-k) and 1-head attention | model-only | Kepler (DS index/numeric continuation) | results/rtl/w19_hbm_tp96_isa.json (+2) |
| V4.1 dedicated units: SU/SFU (norms, RoPE, quantisers, SwiGLU, expert sum, compressor pooling, engram hash) | model-only | being built by claude/hbm-system-rtl-20261003 (this branch) (as SIMT kernels) | results/rtl/w19_hbm_tp96_isa.json (+1) |
| DSpark / MTP (drafter + accept) on DS HBM | RTL-untested | Russell (accept leaf); none for drafter-on-SM | results/rtl/w19_hbm_tp96_isa_mtp.json (ISA-level pass) (+3) |
| CDC on comparator paths (HBM service <-> SM, W10) | missing | Popper (W10); being built by claude/hbm-system-rtl-20261003 (this branch) (ot_gpu_cdc_fifo) | results/rtl/v41_link_cdc_campaign.json (ot_link_afifo all_pass) (+2) |
| Host command/completion interface (ot_host_if) | RTL+tested | none | results/rtl/host_if_campaign.json (status pass; target qwen3-hbm) (+1) |
| Kernel launch / command processor | missing | being built by claude/hbm-system-rtl-20261003 (this branch) | results/uarch/hbm_feasibility_audit.json (6e: 'a persistent hardware-sequenced program, not GPU kernels') (+1) |
| Barrier network (ot_gpu_barrier_node) | RTL+tested | none | results/rtl/gpu_supply_barrier.json (status pass) (+1) |
| Reset / clock control | missing | none | rtl/ot_stage_top.sv instantiates ot_power_reset_controller; no rtl/gpu/* instantiation |
| Token program / ISA (V4.1 HBM, TP-96) | model-only | Kepler (DS numerical continuation); Dewey (native calendar join) | results/rtl/w19_hbm_tp96_isa.json (status pass, ISA-level) (+3) |
| Full-token end-to-end RTL simulation (V4.1 HBM) | missing | being built by claude/hbm-system-rtl-20261003 (this branch) (reduced-shape V4.1 system top) | results/rtl/deepseek_hbm_complete_20261001/checkpoint-full-40-head-r1.json (DUT_RTL_executed=false) (+2) |

## Most important gaps

1. No full-token end-to-end RTL simulation exists for either comparator: every complete-token record has actual_RTL_executed=false / DUT_RTL_executed=false.
2. No die/system top: ot_gpu_sm_q, ot_gpu_sm_v, ot_hdc_qwen_hbm_service, ot_link_nvls_switch, barrier, router and expert fetch are instantiated only by benches.
3. Missing GPU fabric: L2 slices, SM<->L2<->HBM crossbar, command processor/kernel launch, GPU collective endpoint, and CDC on SM/HBM-service boundaries (only ot_link_afifo is in a non-bench module).
4. SIMD unit is FADD/FMUL only, with no ISA, no SFU (exp/rsqrt/sigmoid) and no reductions. Norms, softmax, RoPE, SiLU and attention exist only in Python executors.
5. HBM controller/PHY is a simulation-only behavioural model. DS has no multi-client PC service at all.
6. Ownership bridge is incomplete: W2 (Nash) and W6 (Goodall) are tested components but unconnected; W4 (Euclid) RTL is only on an unpushed local commit 721639931; W5/W10 (Popper) are model-only.
7. V4.1 Sinkhorn/HC, indexer, attention and SU/SFU are model-only on the HBM die, and as dedicated units they are not GPU-legal. DSpark drafter-on-SM has no RTL, and origin/claude/dshbm-dspark-rtl-20261003 does not exist.
