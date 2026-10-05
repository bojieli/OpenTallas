# DS-V4.1 HBM switch collectives: AUTHORITATIVE scenarios and tables (2026-10-04)

> **TAU SUPERSEDED (owner rule 2026-10-04).** `model.json`/the record is now composed at the third-party published tau (3.8879, `tools/third_party_tau.py`, `results/speculative/third_party_acceptance_20261004/`). Hand-written figures below that quote tau 4.159 are the superseded self-measured composition: scale MTP tok/s by 3.8879/4.159 = 0.9348 (and MTP J/token by its inverse); AR figures and ROM:HBM ratios are unchanged.

**AUTHORITATIVE (owner decision 2026-10-04).** These values replace every earlier switch and collective figure. Two records are SUPERSEDED but kept unchanged:
- the 0.668 us W15 switch term (scenario `w15`);
- the literature range (`results/uarch/hbm_switch_latency_range_20261004/`).

The evidence is a model built on two kinds of input:
- MEASURED anchors: H100 SXM5 HGX NVLS (`results/measured/h100_nvls_20261004/`), **NVLink4 / H100 generation**;
- VENDOR BUDGETS: Broadcom Tomahawk Ultra / Scale-Up Ethernet RM104 Appendix A.

## Defaults (`tools/uarch_model.py` `HBM_SWITCH_DEFAULTS`)

| Design | Switch scenario | Why |
|---|---|---|
| HBM accelerator | `tomahawk_ultra_protocol` | Our accelerator implements its own protocol and endpoint on a stock Tomahawk Ultra tier |
| GPU-organised ablation (`v41_hbm_chain` / `v41_hbm_rows`, W19) | `nvls_measured` | The measured H100 NVLS hardware path |
| GPU-faithful rows | `gpu_fenced` + H100 grid.sync 1.097 us | Measured GPU software costs |
| GPU baseline (tier 2, 8x B200 V4.1) | all-reduce 9.024 us | Measured H100 fenced one-shot. Was 8 us ASSUMED. NCCL without a graph, 32-36 us, is a sensitivity |
| Qwen GPU baseline | MEASURED 1x H100 SXM vLLM FP8 194.1 tok/s (TP8 305.7) | B200 is kept as a labelled model row |

Flags select the other scenarios:
- `--hbm-switch-latency {w15,push_optimistic,nvls_measured,gpu_fenced,tomahawk_ultra_protocol,tomahawk_ultra_inc}`; `low`, `central` and `high` remain as aliases.
- `--hbm-fec {board,kp4}`.

## Scenarios (per collective; + 0.15 us striping tail, range 0.1-0.2)

| Scenario | All-reduce | Gather | Basis |
|---|---|---|---|
| `nvls_measured` | 2.394 us | 1.532 us | MEASURED one-shot NVLS AR with relaxed hardware-path sync: 2.244 us (<= 512 B), 2.597 us (32 KB), flat from 2 to 8 GPUs. Measured multimem.st AG: 1.382 us (128 B), 1.590 us (32 KB). Only the fixed term is replaced; the W15 slopes carry the bytes. |
| `gpu_fenced` | 9.054 us | 8.161 us | MEASURED sys-scope release/acquire one-shot AR: 8.904-9.144 us. The AG is DERIVED: measured AG + 2 x (sys - relaxed barrier). |
| `tomahawk_ultra_protocol` | 1.215 us at 32 KB (1.358 at 10 m SMF) | 0.630 / 0.642 / 0.672 us at 1.5 / 10 / 32 KB | Priced per W19 op at its actual bytes, as derived below. |
| `push_optimistic` | 1.292 us | 1.271 us | Measured in-switch data path (0.783 us) + one notification (0.359 us = half the measured relaxed barrier). |
| `tomahawk_ultra_inc` (SENSITIVITY) | 0.769 us at 32 KB | as protocol | In-switch reduction: 1 crossing + ~50 ns reduce. Excluded from the defaults because the switch's reduction order is unpublished. |
| `w15` (SUPERSEDED) | 0.824 us (KP4) | 0.777 us | RTL model, 2 x 209 + 250 ns |

### Tomahawk Ultra + our protocol, derived

The protocol has four parts:
- hardware-initiated register-to-register sends from the collective engine;
- completion by arrival counting, with no barrier or flag polling;
- link-level retry + CRC;
- credit flow control.

The tier is about 8 Tomahawk Ultra chips in one tier. Each 2-die package stripes over 8 x 800G ports.

**One crossing = 477.6 ns** (3 m twinax; 496 ns for 5 m HCF, 549.2 ns for 10 m SMF). This is the RM104 Appendix A budget, and all four terms are VENDOR BUDGETS:
- endpoint bridge NoC<->Ethernet: 100 ns (Tx+Rx);
- endpoint Ethernet link + PHY: 100 ns (Tx+Rx);
- switch: 250 ns (Tx+Rx, including its PHY/FEC);
- cable: 2 x 4.6 ns/m.

The coordinator's itemisation (100 + 100 + cable + 250 + 100 + 100) would double-count the Tx+Rx pairs. The RM104 totals, 478-549 ns, are the ones used.

Message terms:
- **Serialisation:** bytes / 720 GB/s. That is 8 x 800 Gb/s = 800 GB/s per package per direction, times an ASSUMED 0.9 framing efficiency. Every op uses its actual W19 size multiplied by the P positions.
- **Owner reduction:** 18.3 ns, MEASURED in the HA2 RTL endpoint reducer (`results/rtl/hbm_accel_ha2_ar_20261004`, main c7d138048 / 13b92e71e). It runs the golden pairwise tree over the o-group's 8 contributors with `ot_hdc_fp32_add_lat #(7)`: 7 x 3 levels + 1 cycle `to_bf16` = 22 cycles at 1.2 GHz, cut-through.

Per-collective totals:
- **All-reduce** = reduce-scatter to the slice owner (1 crossing; the switch only forwards) + golden-order owner reduction + cut-through switch multicast (crossing 2) + 2 x serialisation + tail. At 32 KB: 2 x 477.6 + 18.3 + 2 x 45.5 + 150 = **1,214.6 ns**. That is inside the expected 1.0-1.3 us, and it was derived, not copied.
- **Gather** = 1 multicast crossing + serialisation + tail. That gives **0.63-0.67 us** for the W19 gathers of 1.5-32 KB, at the top of the expected 0.5-0.65 us because the 0.15 us tail is applied. The larger merges are 0.83 us (147 KB kv_gather) and 1.17 us (393 KB select merge).

W19 on-path transport for the 265 collectives (40 o-group AR at 32 KB + 225 gather-like):

| P | W15 (superseded) | Tomahawk protocol | NVLS measured | GPU fenced |
|---|---|---|---|---|
| 1 | 237.7 us | 199.1 us | 470.4 us | 2,228.3 us |
| 6 | 310.1 us | 264.0 us | 542.7 us | 2,300.7 us |

Rules:
- Accelerator = the frozen HA firm ladder without R2 (the switch tier is retained; the direct mesh was owner-rejected). Under a replaced transport it is also without R3a, because the measured or budgeted endpoint already contains the cut-through endpoint.
- MTP: tau 4.159 (owner 6-class, gamma 5). Step = verify(P=6) + draft. The HBM draft is the W19-record estimate (51.88 us, ASSUMED). The ROM draft is MEASURED (105.6 us with the fused head, 144.4 us as built at 1M), which is an asymmetry that favours HBM.
- The 200K rows apply the W19 context ratio to the passes and add the transport delta unscaled.
- ROM sources:
  - AR: `results/rtl/dsrom_wavefront_verify_20261004/record.json` (S81).
  - MTP: `results/rtl/dsrom_dspark_step_slices_20261004/composition.json` (main 9ea29b069 / dae91947c, wavefront occupancy, light FEC). The "L1 fused head" column is that record's fused-head variant (main 2a235a9fe calls it L1).
  - The L1+L2 column is an EXPECTED projection from `results/rtl/dsrom_dspark_l1l2_20261004/expected.json`; no lever has been measured. It uses the ROM-read-bound, 5-vector batched head: 7,858 tok/s at 1M and 8,123 at 200K. L2 alone gives 7,320 / 7,550.
  - If the batched head is MAC-bound, L2 gains nothing and L1+L2 = L1.

### 1M: authoritative defaults (ROM S81 + wavefront: AR 2,466.2; MTP 6,733.7 as built / 7,186.2 L1 fused head, measured draft; L1+L2 batched 7,858.1 EXPECTED)

| HBM design | Switch scenario (default) | AR tok/s | MTP tok/s (tau 4.159) | ROM:HBM AR | ROM:HBM MTP as built | ROM:HBM MTP L1 fused head | ROM:HBM MTP L1+L2 (expected) |
|---|---|---|---|---|---|---|---|
| HBM accelerator (firm ladder, switch kept) | TU protocol | 2,624 | 6,352 | 0.94 | 1.06 | 1.13 | 1.24 |
| HBM accelerator, measured composition | TU protocol | 2,563 | 6,032 | 0.96 | 1.12 | 1.19 | 1.30 |
| GPU-organised ablation (W19) | NVLS measured | 1,482 | 4,124 | 1.66 | 1.63 | 1.74 | 1.91 |
| GPU-faithful R0 (H100 grid.sync 1.097 us) | GPU fenced | 359 | 1,250 | 6.87 | 5.39 | 5.75 | 6.29 |

1M: every scenario, AR / MTP tok/s (ROM:HBM AR / MTP as built)

| HBM design | TU protocol | NVLS measured | GPU fenced | push optimistic | TU + INC (sens.) | W15 (superseded) |
|---|---|---|---|---|---|---|
| HBM accelerator (firm ladder, switch kept) | **2,624 / 6,352 (0.94 / 1.06)** | 1,533 / 4,330 (1.61 / 1.55) | 415 / 1,438 (5.94 / 4.68) | 1,820 / 4,908 (1.35 / 1.37) | 2,753 / 6,548 (0.90 / 1.03) | 2,779 / 6,508 (0.89 / 1.03) |
| HBM accelerator, measured composition | **2,563 / 6,032 (0.96 / 1.12)** | 1,512 / 4,179 (1.63 / 1.61) | 413 / 1,421 (5.97 / 4.74) | 1,790 / 4,715 (1.38 / 1.43) | 2,685 / 6,209 (0.92 / 1.08) | 2,585 / 5,999 (0.95 / 1.12) |
| GPU-organised ablation (W19) | 2,478 / 5,918 (0.99 / 1.14) | **1,482 / 4,124 (1.66 / 1.63)** | 411 / 1,414 (6.00 / 4.76) | 1,748 / 4,645 (1.41 / 1.45) | 2,592 / 6,087 (0.95 / 1.11) | 2,498 / 5,885 (0.99 / 1.14) |
| GPU-faithful R0 (H100 grid.sync 1.097 us) | 1,320 / 3,819 (1.87 / 1.76) | 972 / 2,982 (2.54 / 2.26) | **359 / 1,250 (6.87 / 5.39)** | 1,080 / 3,245 (2.28 / 2.08) | 1,352 / 3,889 (1.82 / 1.73) | 1,326 / 3,805 (1.86 / 1.77) |

### 200K: authoritative defaults (ROM S81 + wavefront: AR 2,574.1; MTP 6,927.5 as built / 7,407.3 L1 fused head, measured draft; L1+L2 batched 8,123.2 EXPECTED)

| HBM design | Switch scenario (default) | AR tok/s | MTP tok/s (tau 4.159) | ROM:HBM AR | ROM:HBM MTP as built | ROM:HBM MTP L1 fused head | ROM:HBM MTP L1+L2 (expected) |
|---|---|---|---|---|---|---|---|
| HBM accelerator (firm ladder, switch kept) | TU protocol | 2,630 | 6,365 | 0.98 | 1.09 | 1.16 | 1.28 |
| HBM accelerator, measured composition | TU protocol | 2,568 | 6,045 | 1.00 | 1.15 | 1.23 | 1.34 |
| GPU-organised ablation (W19) | NVLS measured | 1,484 | 4,130 | 1.74 | 1.68 | 1.79 | 1.97 |
| GPU-faithful R0 (H100 grid.sync 1.097 us) | GPU fenced | 359 | 1,251 | 7.17 | 5.54 | 5.92 | 6.50 |

200K: every scenario, AR / MTP tok/s (ROM:HBM AR / MTP as built)

| HBM design | TU protocol | NVLS measured | GPU fenced | push optimistic | TU + INC (sens.) | W15 (superseded) |
|---|---|---|---|---|---|---|
| HBM accelerator (firm ladder, switch kept) | **2,630 / 6,365 (0.98 / 1.09)** | 1,535 / 4,336 (1.68 / 1.60) | 415 / 1,438 (6.20 / 4.82) | 1,823 / 4,916 (1.41 / 1.41) | 2,759 / 6,562 (0.93 / 1.06) | 2,785 / 6,522 (0.92 / 1.06) |
| HBM accelerator, measured composition | **2,568 / 6,045 (1.00 / 1.15)** | 1,514 / 4,185 (1.70 / 1.66) | 414 / 1,421 (6.23 / 4.87) | 1,793 / 4,723 (1.44 / 1.47) | 2,691 / 6,222 (0.96 / 1.11) | 2,590 / 6,011 (0.99 / 1.15) |
| GPU-organised ablation (W19) | 2,483 / 5,930 (1.04 / 1.17) | **1,484 / 4,130 (1.74 / 1.68)** | 411 / 1,415 (6.26 / 4.90) | 1,751 / 4,652 (1.47 / 1.49) | 2,598 / 6,100 (0.99 / 1.14) | 2,504 / 5,897 (1.03 / 1.18) |
| GPU-faithful R0 (H100 grid.sync 1.097 us) | 1,323 / 3,826 (1.95 / 1.81) | 974 / 2,986 (2.64 / 2.32) | **359 / 1,251 (7.17 / 5.54)** | 1,082 / 3,250 (2.38 / 2.13) | 1,355 / 3,897 (1.90 / 1.78) | 1,329 / 3,813 (1.94 / 1.82) |

## Cross-checks (each figure computed two ways; all agree)

- The W19 per-op transport + the wide select (8 x 419 cycles x P) reproduces the study's collective part:
  - P=1: 237.67 + 2.79 = 240.46 us;
  - P=6: 310.06 + 16.76 = 326.81 us.
- Tomahawk per-op sum = grouped (kind, bytes) x count sum: 199.1252 / 263.9945 us. The 32 KB AR by hand is 1.214556 us, equal to the model.
- The NVLS per-op deltas equal the count formula (40 AR + 225 AG) exactly for all three NVLS scenarios.
- Headline rates were recomputed from the study constants in a standalone script and match:
  - ablation at `nvls_measured`: 1,481.9 / 4,123.9 tok/s;
  - GPU-faithful at `gpu_fenced`: 358.9 / 1,249.9;
  - accelerator at `tomahawk_ultra_protocol`: 2,624.4 / 6,351.8.

## Published defaults that move

| Row | Superseded | Authoritative |
|---|---|---|
| `v41_hbm_gpu_groupslot` (ablation, NVLS measured) | 2,801.8 | 1,837.3 tok/s |
| `v41_hbm_gpu_rowslot` | 2,443.3 | 1,676.0 |
| `v41_hbm_gpu_groupslot_grid_sync_{v100 -> h100}` (GPU-faithful: H100 grid sync + fenced) | 1,246.0 | 469.3 |
| Qwen HBM headline (`qwen_hbm_gpu`) | 880.5 | **880.5 (unchanged: no switch collectives, bandwidth-bound)** |
| `qwen_hbm_gpu_grid_sync_{v100 -> h100}` (reference) | 757.2 | 793.4 |
| Tier-2 V4.1 on 8x B200 (all-reduce 8 -> 9.024 us) | 282.4 (spec 547.8) | 266.9 (spec 517.9); NCCL no-graph 32 / 36 us gives 119.9 / 109.4 |
| Qwen GPU baseline | B200 model 331.0 | **MEASURED H100 vLLM FP8 194.1 (TP1) / 305.7 (TP8); BF16 138.1 / 293.4**. Qwen HBM 880.5 is 4.54x TP1 FP8 and 2.88x TP8 FP8 (8K vs short context) |

Kernel launch (2.67 us) and the graph node (1.01 us) are recorded but not added to the tier-2 rows. Their fixed term is a fitted H200 NIM measurement that already contains them.

Replay: `python3 tools/uarch_model.py --hbm-switch-latency-authoritative --out results/uarch/hbm_switch_latency_authoritative_20261004/model.json`
